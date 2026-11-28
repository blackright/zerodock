"""Unit and integration tests for Rich TUI / plain-text CLI UI (issue #4)."""

from __future__ import annotations

import io
from pathlib import Path

import httpx
import pytest

from zerodock.cli import build_parser
from zerodock.cli_ui import format_request_log, render_request_log, render_startup_banner
from zerodock.config.models import RouteDefinition, ServerlessConfig
from zerodock.config.parser import load_config
from zerodock.gateway.app import create_app


def _sample_config() -> ServerlessConfig:
    return ServerlessConfig(
        routes={
            "/api/hello": RouteDefinition(
                file=Path("./functions/hello.py"),
                handler="lambda_handler",
                methods=["GET", "POST"],
            )
        }
    )


def test_render_startup_banner_plain_has_routes_and_no_ansi() -> None:
    buf = io.StringIO()
    render_startup_banner(_sample_config(), version="0.1.1", plain=True, stream=buf)
    output = buf.getvalue()
    assert "ZeroDock v0.1.1" in output
    assert "127.0.0.1:8080" in output
    assert "/api/hello" in output
    assert "GET,POST" in output
    assert "\x1b[" not in output


def test_format_request_log_status_colors_and_plain_fallback() -> None:
    ok_colored = format_request_log("GET", "/api/hello", 200, 4.2, plain=False)
    not_found_colored = format_request_log("GET", "/missing", 404, 1.0, plain=False)
    err_colored = format_request_log("POST", "/boom", 500, 12.34, plain=False)

    assert "\x1b[32m200\x1b[0m" in ok_colored
    assert "4.2ms" in ok_colored
    assert "\x1b[33m404\x1b[0m" in not_found_colored
    assert "\x1b[1;31m500\x1b[0m" in err_colored
    assert "12.3ms" in err_colored

    plain_line = format_request_log("GET", "/api/hello", 200, 4.2, plain=True)
    assert "\x1b[" not in plain_line
    assert "GET" in plain_line and "/api/hello" in plain_line and "200" in plain_line


def test_no_color_env_forces_plain_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    buf = io.StringIO()
    render_request_log("GET", "/test", 200, 1.5, plain=False, stream=buf)
    assert "\x1b[" not in buf.getvalue()
    assert "200 (1.5ms)" in buf.getvalue()


def test_cli_parser_supports_plain_and_no_color() -> None:
    parser = build_parser()
    assert parser.parse_args(["dev"]).plain is False
    assert parser.parse_args(["dev", "--plain"]).plain is True
    assert parser.parse_args(["dev", "--no-color"]).plain is True


@pytest.mark.asyncio
async def test_gateway_middleware_logs_request_latency(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "handler.py").write_text(
        "def handler(event): return {'statusCode': 200, 'body': 'ok'}\n", encoding="utf-8"
    )
    cfg_file = tmp_path / "serverless-local.yaml"
    cfg_file.write_text(
        'version: "1.0"\n'
        "routes:\n"
        "  ping:\n"
        '    file: "./handler.py"\n'
        '    handler: "handler"\n'
        '    methods: ["GET"]\n',
        encoding="utf-8",
    )
    logged: list[tuple[str, str, int, float]] = []
    monkeypatch.setattr(
        "zerodock.gateway.app.render_request_log",
        lambda method, path, status, duration_ms, **kw: logged.append(
            (method, path, status, duration_ms)
        ),
    )

    app = create_app(load_config(cfg_file), enable_request_log=True, plain_ui=True)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8080") as client:
        resp = await client.get("/ping")

    assert resp.status_code == 200
    assert len(logged) == 1
    method, path, status, duration_ms = logged[0]
    assert (method, path, status) == ("GET", "/ping", 200)
    assert duration_ms >= 0.0
