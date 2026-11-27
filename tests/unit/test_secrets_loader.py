"""Unit and integration tests for local .env / .env.local loader (issue #3)."""

from __future__ import annotations

import os
from pathlib import Path

import httpx
import pytest

from zerodock.config.parser import load_config
from zerodock.config.secrets import (
    SecretsLoadError,
    inject_local_env,
    load_local_env,
    parse_env_file,
)
from zerodock.gateway.app import create_app


def test_parse_env_file_comments_quotes_and_export(tmp_path: Path) -> None:
    env_file = tmp_path / ".env.local"
    env_file.write_text(
        "# Comment line\n"
        "\n"
        "PLAIN_KEY=abc123\n"
        'QUOTED_KEY="hello world"\n'
        "SINGLE_QUOTED='single val'\n"
        "export EXPORTED_KEY=exported_val\n",
        encoding="utf-8",
    )
    parsed = parse_env_file(env_file)
    assert parsed == {
        "PLAIN_KEY": "abc123",
        "QUOTED_KEY": "hello world",
        "SINGLE_QUOTED": "single val",
        "EXPORTED_KEY": "exported_val",
    }


def test_precedence_env_local_over_env_and_preserves_system(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".env").write_text(
        "SHARED=from_env\nONLY_ENV=1\nSYS_KEY=from_env\n", encoding="utf-8"
    )
    (tmp_path / ".env.local").write_text(
        "SHARED=from_local\nONLY_LOCAL=2\nSYS_KEY=from_local\n", encoding="utf-8"
    )
    monkeypatch.setenv("SYS_KEY", "from_system")
    monkeypatch.delenv("SHARED", raising=False)
    monkeypatch.delenv("ONLY_ENV", raising=False)
    monkeypatch.delenv("ONLY_LOCAL", raising=False)

    loaded = load_local_env(base_dir=tmp_path)
    assert loaded == {
        "SHARED": "from_local",
        "ONLY_ENV": "1",
        "ONLY_LOCAL": "2",
        "SYS_KEY": "from_local",
    }

    effective = inject_local_env(loaded)
    assert os.environ["SHARED"] == "from_local"
    assert os.environ["ONLY_ENV"] == "1"
    assert os.environ["ONLY_LOCAL"] == "2"
    assert os.environ["SYS_KEY"] == "from_system"
    assert effective["SYS_KEY"] == "from_system"


def test_missing_env_files_fallback_gracefully(tmp_path: Path) -> None:
    assert load_local_env(base_dir=tmp_path) == {}
    assert load_local_env(tmp_path / "does-not-exist.env") == {}


def test_malformed_line_raises_without_leaking_secret(tmp_path: Path) -> None:
    bad = tmp_path / ".env.local"
    bad.write_text("SUPER_SECRET_TOKEN_NO_EQUALS\n", encoding="utf-8")
    with pytest.raises(SecretsLoadError) as exc_info:
        parse_env_file(bad)
    assert "line 1" in str(exc_info.value)
    assert "SUPER_SECRET_TOKEN_NO_EQUALS" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_handler_reads_env_stage_variables_and_client_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ZD_TEST_SECRET", raising=False)
    (tmp_path / ".env.local").write_text("ZD_TEST_SECRET=top_secret_42\n", encoding="utf-8")
    (tmp_path / "handler.py").write_text(
        "import os\n"
        "def handler(event, context):\n"
        "    return {\n"
        "        'statusCode': 200,\n"
        "        'body': {\n"
        "            'env': os.environ.get('ZD_TEST_SECRET'),\n"
        "            'stage': event.get('stageVariables', {}).get('ZD_TEST_SECRET'),\n"
        "            'ctx': context.client_context.get('ZD_TEST_SECRET'),\n"
        "        },\n"
        "    }\n",
        encoding="utf-8",
    )
    cfg_file = tmp_path / "serverless-local.yaml"
    cfg_file.write_text(
        'version: "1.0"\n'
        "routes:\n"
        "  secret-check:\n"
        '    file: "./handler.py"\n'
        '    handler: "handler"\n'
        '    methods: ["GET"]\n',
        encoding="utf-8",
    )
    app = create_app(load_config(cfg_file))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8080") as client:
        resp = await client.get("/secret-check")
    assert resp.status_code == 200
    assert resp.json() == {
        "env": "top_secret_42",
        "stage": "top_secret_42",
        "ctx": "top_secret_42",
    }
