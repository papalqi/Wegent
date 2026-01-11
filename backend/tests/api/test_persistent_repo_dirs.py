# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

from shared.utils.persistent_repo import PERSIST_REPO_MOUNT_PATH


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_list_persistent_repo_dirs_returns_items(
    test_client, test_token, tmp_path, monkeypatch
):
    root = tmp_path / "persist"
    root.mkdir(parents=True, exist_ok=True)

    (root / "git-repo" / ".git").mkdir(parents=True, exist_ok=True)

    (root / "p4-repo").mkdir(parents=True, exist_ok=True)
    (root / "p4-repo" / ".p4config").write_text(
        "P4PORT=perforce:1666", encoding="utf-8"
    )

    (root / "group" / "inner" / ".git").mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("WEGENT_PERSIST_REPO_ROOT_HOST", str(root))

    resp = test_client.get(
        "/api/utils/persistent-repo-dirs?depth=2&limit=1000",
        headers=_auth_headers(test_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)

    by_rel = {item["relative_path"]: item for item in data}
    assert "git-repo" in by_rel
    assert "p4-repo" in by_rel
    assert "group" in by_rel
    assert "group/inner" in by_rel

    assert by_rel["git-repo"]["repo_dir"] == f"{PERSIST_REPO_MOUNT_PATH}/git-repo"
    assert by_rel["git-repo"]["repo_vcs"] == "git"
    assert by_rel["git-repo"]["is_p4"] is False

    assert by_rel["p4-repo"]["repo_dir"] == f"{PERSIST_REPO_MOUNT_PATH}/p4-repo"
    assert by_rel["p4-repo"]["repo_vcs"] == "p4"
    assert by_rel["p4-repo"]["is_p4"] is True

    assert by_rel["group"]["repo_dir"] == f"{PERSIST_REPO_MOUNT_PATH}/group"
    assert by_rel["group"]["repo_vcs"] is None
    assert by_rel["group"]["is_p4"] is False

    assert by_rel["group/inner"]["repo_dir"] == f"{PERSIST_REPO_MOUNT_PATH}/group/inner"
    assert by_rel["group/inner"]["repo_vcs"] == "git"
    assert by_rel["group/inner"]["is_p4"] is False


def test_list_persistent_repo_dirs_query_filter(
    test_client, test_token, tmp_path, monkeypatch
):
    root = tmp_path / "persist"
    root.mkdir(parents=True, exist_ok=True)
    (root / "alpha").mkdir(parents=True, exist_ok=True)
    (root / "beta").mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("WEGENT_PERSIST_REPO_ROOT_HOST", str(root))

    resp = test_client.get(
        "/api/utils/persistent-repo-dirs?q=alp&depth=1&limit=1000",
        headers=_auth_headers(test_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    rels = {item["relative_path"] for item in data}
    assert "alpha" in rels
    assert "beta" not in rels


def test_list_persistent_repo_dirs_requires_auth(test_client):
    resp = test_client.get("/api/utils/persistent-repo-dirs")
    assert resp.status_code == 401
