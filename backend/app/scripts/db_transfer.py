#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
import base64
import dataclasses
import datetime as dt
import json
import os
import sys
import time
import zipfile
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from sqlalchemy import MetaData, Table, create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import URL, make_url

BYTES_SENTINEL_TYPE = "__type__"
BYTES_SENTINEL_VALUE = "bytes"
DEFAULT_CHUNK_SIZE = 500


@dataclasses.dataclass(frozen=True)
class DumpMetadata:
    created_at_epoch: int
    dialect: str
    database: str | None
    alembic_revision: str | None
    tables: list[str]


def _eprint(message: str) -> None:
    print(message, file=sys.stderr)


def _mask_database_url(raw_url: str) -> str:
    try:
        url = make_url(raw_url)
    except Exception:
        return "<invalid database url>"

    if url.password is None:
        return str(url)

    safe = url.set(password="***")
    return str(safe)


def _to_sync_database_url(raw_url: str) -> str:
    url = make_url(raw_url)
    drivername = url.drivername
    if drivername.startswith("mysql+asyncmy"):
        return str(url.set(drivername="mysql+pymysql"))
    return str(url)


def _resolve_database_url(database_url: str | None) -> str:
    if database_url:
        return database_url

    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url

    try:
        from app.core.config import settings

        return settings.DATABASE_URL
    except Exception as exc:  # pragma: no cover
        raise SystemExit(
            "DATABASE_URL not provided and could not load app settings"
        ) from exc


def _create_engine(database_url: str) -> Engine:
    sync_url = _to_sync_database_url(database_url)
    engine = create_engine(
        sync_url,
        pool_pre_ping=True,
        connect_args={"charset": "utf8mb4", "init_command": "SET time_zone = '+08:00'"},
    )
    return engine


def _get_current_database(engine: Engine) -> str | None:
    with engine.connect() as conn:
        return conn.execute(text("SELECT DATABASE()")).scalar()


def _get_alembic_revision(engine: Engine) -> str | None:
    with engine.connect() as conn:
        try:
            return conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar()
        except Exception:
            return None


def _list_tables(engine: Engine, exclude_tables: set[str]) -> list[str]:
    inspector = inspect(engine)
    tables = [t for t in inspector.get_table_names() if t not in exclude_tables]
    tables.sort()
    return tables


def _quote_ident(name: str) -> str:
    return "`" + name.replace("`", "``") + "`"


def _mysql_show_create_table(engine: Engine, table_name: str) -> str:
    with engine.connect() as conn:
        row = (
            conn.execute(text(f"SHOW CREATE TABLE {_quote_ident(table_name)}"))
            .mappings()
            .one()
        )
        create_sql = row.get("Create Table")
        if not isinstance(create_sql, str):
            raise RuntimeError(
                f"SHOW CREATE TABLE returned invalid result for {table_name}"
            )
        return create_sql


def _encode_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        raw = bytes(value)
        return {
            BYTES_SENTINEL_TYPE: BYTES_SENTINEL_VALUE,
            "base64": base64.b64encode(raw).decode("ascii"),
        }
    return str(value)


def _decode_value(value: Any) -> Any:
    if (
        isinstance(value, dict)
        and value.get(BYTES_SENTINEL_TYPE) == BYTES_SENTINEL_VALUE
        and isinstance(value.get("base64"), str)
    ):
        return base64.b64decode(value["base64"])
    return value


def _iter_table_rows(
    engine: Engine, table_name: str, chunk_size: int
) -> Iterable[list[dict[str, Any]]]:
    stmt = text(f"SELECT * FROM {_quote_ident(table_name)}")
    with engine.connect() as conn:
        result = conn.execute(stmt)
        while True:
            chunk = result.fetchmany(chunk_size)
            if not chunk:
                break
            rows: list[dict[str, Any]] = []
            for row in chunk:
                mapping = row._mapping  # type: ignore[attr-defined]
                rows.append({k: _encode_value(v) for k, v in mapping.items()})
            yield rows


def export_database(
    *,
    database_url: str,
    output_path: Path,
    exclude_tables: set[str],
    chunk_size: int,
) -> None:
    engine = _create_engine(database_url)
    safe_url = _mask_database_url(database_url)

    dialect = engine.dialect.name
    current_db = _get_current_database(engine)
    tables = _list_tables(engine, exclude_tables)
    revision = _get_alembic_revision(engine)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    metadata = DumpMetadata(
        created_at_epoch=int(time.time()),
        dialect=dialect,
        database=current_db,
        alembic_revision=revision,
        tables=tables,
    )

    _eprint(f"Exporting database from {safe_url}")
    _eprint(f"Found {len(tables)} tables")

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("metadata.json", json.dumps(dataclasses.asdict(metadata), indent=2))

        for table in tables:
            schema_sql = _mysql_show_create_table(engine, table)
            if not schema_sql.rstrip().endswith(";"):
                schema_sql = schema_sql.rstrip() + ";\n"
            zf.writestr(f"schema/{table}.sql", schema_sql)

            with zf.open(f"data/{table}.jsonl", "w") as fp:
                for rows in _iter_table_rows(engine, table, chunk_size):
                    for row in rows:
                        line = json.dumps(
                            row, separators=(",", ":"), ensure_ascii=False
                        )
                        fp.write((line + "\n").encode("utf-8"))

    _eprint(f"Export written to {output_path}")


def _database_url_without_database(url: URL) -> str:
    return str(url.set(database=None))


def _maybe_create_database(database_url: str) -> None:
    url = make_url(_to_sync_database_url(database_url))
    if not url.database:
        return

    server_engine = create_engine(
        _database_url_without_database(url), pool_pre_ping=True
    )
    db_name = url.database
    with server_engine.begin() as conn:
        conn.execute(
            text(
                f"CREATE DATABASE IF NOT EXISTS {_quote_ident(db_name)} "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        )


def _table_exists(engine: Engine, table_name: str) -> bool:
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def _drop_tables(engine: Engine, tables: Sequence[str]) -> None:
    with engine.begin() as conn:
        conn.exec_driver_sql("SET FOREIGN_KEY_CHECKS=0")
        for table in tables:
            conn.exec_driver_sql(f"DROP TABLE IF EXISTS {_quote_ident(table)}")
        conn.exec_driver_sql("SET FOREIGN_KEY_CHECKS=1")


def _truncate_tables(engine: Engine, tables: Sequence[str]) -> None:
    with engine.begin() as conn:
        conn.exec_driver_sql("SET FOREIGN_KEY_CHECKS=0")
        for table in tables:
            conn.exec_driver_sql(f"TRUNCATE TABLE {_quote_ident(table)}")
        conn.exec_driver_sql("SET FOREIGN_KEY_CHECKS=1")


def _apply_schema_from_zip(
    engine: Engine, zf: zipfile.ZipFile, tables: Sequence[str]
) -> None:
    with engine.begin() as conn:
        conn.exec_driver_sql("SET FOREIGN_KEY_CHECKS=0")
        for table in tables:
            schema_sql = zf.read(f"schema/{table}.sql").decode("utf-8")
            schema_sql = schema_sql.strip()
            if schema_sql.endswith(";"):
                schema_sql = schema_sql[:-1]
            conn.exec_driver_sql(schema_sql)
        conn.exec_driver_sql("SET FOREIGN_KEY_CHECKS=1")


def _load_jsonl_lines(zf: zipfile.ZipFile, path: str) -> Iterable[dict[str, Any]]:
    with zf.open(path, "r") as fp:
        for raw_line in fp:
            line = raw_line.decode("utf-8").strip()
            if not line:
                continue
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError(f"Invalid JSONL row payload in {path}")
            yield {k: _decode_value(v) for k, v in item.items()}


def _insert_table_data(
    engine: Engine, table_name: str, rows: Iterable[dict[str, Any]], chunk_size: int
) -> int:
    metadata = MetaData()
    table = Table(table_name, metadata, autoload_with=engine)
    inserted = 0
    buffer: list[dict[str, Any]] = []

    with engine.begin() as conn:
        conn.exec_driver_sql("SET FOREIGN_KEY_CHECKS=0")
        for row in rows:
            buffer.append(row)
            if len(buffer) >= chunk_size:
                conn.execute(table.insert(), buffer)
                inserted += len(buffer)
                buffer.clear()
        if buffer:
            conn.execute(table.insert(), buffer)
            inserted += len(buffer)
        conn.exec_driver_sql("SET FOREIGN_KEY_CHECKS=1")

    return inserted


def import_database(
    *,
    database_url: str,
    dump_path: Path,
    create_db: bool,
    apply_schema: bool,
    force: bool,
    chunk_size: int,
) -> None:
    if create_db:
        _maybe_create_database(database_url)

    engine = _create_engine(database_url)
    safe_url = _mask_database_url(database_url)

    _eprint(f"Importing database into {safe_url}")
    if not dump_path.exists():
        raise SystemExit(f"Dump file not found: {dump_path}")

    with zipfile.ZipFile(dump_path, "r") as zf:
        metadata = json.loads(zf.read("metadata.json").decode("utf-8"))
        tables = metadata.get("tables")
        if not isinstance(tables, list) or not all(isinstance(t, str) for t in tables):
            raise SystemExit("Invalid dump metadata: tables")

        existing = [t for t in tables if _table_exists(engine, t)]
        if existing and not force:
            raise SystemExit(
                "Target database already has tables from this dump. "
                "Re-run with --force to overwrite."
            )

        if existing and force:
            if apply_schema:
                _drop_tables(engine, tables)
            else:
                _truncate_tables(engine, existing)

        if apply_schema:
            _apply_schema_from_zip(engine, zf, tables)

        total = 0
        for table in tables:
            rows = _load_jsonl_lines(zf, f"data/{table}.jsonl")
            inserted = _insert_table_data(engine, table, rows, chunk_size)
            total += inserted
            _eprint(f"Imported {inserted} rows into {table}")

    _eprint(f"Import complete: {total} rows")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wegent-db-transfer",
        description="Export/import Wegent MySQL database as a portable ZIP dump.",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Database URL; defaults to DATABASE_URL env or backend settings (.env).",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help=f"Rows per batch (default: {DEFAULT_CHUNK_SIZE}).",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    export_p = sub.add_parser("export", help="Export database to a ZIP dump file.")
    export_p.add_argument(
        "--out",
        required=True,
        type=Path,
        help="Output dump path (e.g. ./dump.zip).",
    )
    export_p.add_argument(
        "--exclude-table",
        action="append",
        default=[],
        help="Exclude a table by exact name (repeatable).",
    )

    import_p = sub.add_parser("import", help="Import database from a ZIP dump file.")
    import_p.add_argument(
        "--in", dest="inp", required=True, type=Path, help="Dump path."
    )
    import_p.add_argument(
        "--create-db",
        action="store_true",
        help="Create database if missing (requires privileges).",
    )
    import_p.add_argument(
        "--no-schema",
        action="store_true",
        help="Do not apply CREATE TABLE statements; only load data.",
    )
    import_p.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing tables from the dump (drop or truncate).",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    database_url = _resolve_database_url(args.database_url)

    if args.command == "export":
        exclude = set(args.exclude_table)
        export_database(
            database_url=database_url,
            output_path=args.out,
            exclude_tables=exclude,
            chunk_size=args.chunk_size,
        )
        return 0

    if args.command == "import":
        import_database(
            database_url=database_url,
            dump_path=args.inp,
            create_db=bool(args.create_db),
            apply_schema=not bool(args.no_schema),
            force=bool(args.force),
            chunk_size=args.chunk_size,
        )
        return 0

    raise SystemExit("Unknown command")


if __name__ == "__main__":
    raise SystemExit(main())
