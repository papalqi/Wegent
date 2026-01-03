# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import base64

import pytest

from app.scripts.db_transfer import (
    BYTES_SENTINEL_TYPE,
    BYTES_SENTINEL_VALUE,
    _decode_value,
    _encode_value,
    _to_sync_database_url,
)


@pytest.mark.unit
def test_to_sync_database_url_rewrites_asyncmy():
    url = "mysql+asyncmy://user:pass@localhost:3306/db"
    assert _to_sync_database_url(url).startswith("mysql+pymysql://")


@pytest.mark.unit
def test_encode_decode_bytes_roundtrip():
    raw = b"\x00\xffhello"
    encoded = _encode_value(raw)
    assert isinstance(encoded, dict)
    assert encoded[BYTES_SENTINEL_TYPE] == BYTES_SENTINEL_VALUE
    assert base64.b64decode(encoded["base64"]) == raw
    assert _decode_value(encoded) == raw

