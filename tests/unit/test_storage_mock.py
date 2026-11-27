"""Unit tests for LocalStorageMock (issue #2 / FEAT-010)."""

from __future__ import annotations

from pathlib import Path

import pytest

from zerodock.plugins.storage import (
    BucketNotFoundError,
    LocalStorageMock,
    ObjectNotFoundError,
)


def test_put_get_and_list_objects(tmp_path: Path) -> None:
    storage = LocalStorageMock(base_dir=tmp_path / "buckets")

    meta = storage.put_object("user-uploads", "avatars/pic.png", b"\x89PNG\r\n\x1a\n")
    assert meta["bucket"] == "user-uploads"
    assert meta["key"] == "avatars/pic.png"
    assert meta["size"] == 8
    assert meta["content_type"] == "image/png"
    assert (tmp_path / "buckets" / "user-uploads" / "avatars" / "pic.png").is_file()

    assert storage.get_object("user-uploads", "avatars/pic.png") == b"\x89PNG\r\n\x1a\n"
    obj = storage.get_object_with_metadata("user-uploads", "avatars/pic.png")
    assert obj["body"] == b"\x89PNG\r\n\x1a\n"
    assert obj["content_type"] == "image/png"
    assert obj["size"] == 8
    assert storage.list_objects("user-uploads") == ["avatars/pic.png"]


def test_missing_bucket_and_object_errors(tmp_path: Path) -> None:
    storage = LocalStorageMock(base_dir=tmp_path / "buckets")

    with pytest.raises(BucketNotFoundError):
        storage.get_object("missing-bucket", "file.txt")

    with pytest.raises(BucketNotFoundError):
        storage.list_objects("missing-bucket")

    storage.ensure_bucket("reports")
    assert storage.list_objects("reports") == []

    with pytest.raises(ObjectNotFoundError):
        storage.get_object("reports", "missing.pdf")


def test_rejects_path_traversal(tmp_path: Path) -> None:
    storage = LocalStorageMock(base_dir=tmp_path / "buckets")

    with pytest.raises(ValueError):
        storage.put_object("../escape", "a.txt", b"x")

    with pytest.raises(ValueError):
        storage.put_object("reports", "../../escape.txt", b"x")


def test_optional_storage_config_in_serverless_yaml(tmp_path: Path) -> None:
    from zerodock.config.parser import load_config

    handler_file = tmp_path / "h.py"
    handler_file.write_text(
        "def handler(event): return {'statusCode': 200, 'body': 'ok'}\n", encoding="utf-8"
    )
    cfg_file = tmp_path / "serverless-local.yaml"
    cfg_file.write_text(
        'version: "1.0"\n'
        "routes:\n"
        "  test:\n"
        '    file: "./h.py"\n'
        '    handler: "handler"\n'
        "storage:\n"
        "  buckets:\n"
        "    - user-uploads\n"
        "    - reports\n",
        encoding="utf-8",
    )
    cfg = load_config(cfg_file)
    assert cfg.storage.buckets == ["user-uploads", "reports"]


def test_create_app_initializes_configured_buckets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from zerodock.config.parser import load_config
    from zerodock.gateway.app import create_app

    monkeypatch.chdir(tmp_path)
    handler_file = tmp_path / "h.py"
    handler_file.write_text(
        "def handler(event): return {'statusCode': 200, 'body': 'ok'}\n", encoding="utf-8"
    )
    cfg_file = tmp_path / "serverless-local.yaml"
    cfg_file.write_text(
        'version: "1.0"\n'
        "routes:\n"
        "  test:\n"
        '    file: "./h.py"\n'
        '    handler: "handler"\n'
        "storage:\n"
        "  buckets:\n"
        "    - user-uploads\n"
        "    - reports\n",
        encoding="utf-8",
    )
    app = create_app(load_config(cfg_file))
    assert app.state.storage is not None
    assert (tmp_path / ".zerodock" / "buckets" / "user-uploads").is_dir()
    assert (tmp_path / ".zerodock" / "buckets" / "reports").is_dir()
