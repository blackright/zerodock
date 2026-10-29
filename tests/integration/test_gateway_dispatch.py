"""End-to-end integration tests for ZeroDock gateway route dispatching."""

import time
from pathlib import Path

import httpx
import pytest

from zerodock.config.parser import load_config
from zerodock.gateway.app import create_app


@pytest.fixture
def test_app():
    """Create test FastAPI instance configured with the valid test fixture."""
    config_path = Path("tests/fixtures/configs/valid.yaml")
    config = load_config(config_path)
    return create_app(config)


@pytest.mark.asyncio
async def test_get_request_dispatch_loop(test_app):
    """Verify complete GET request lifecycle invokes handler and returns response."""
    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8080") as client:
        start_time = time.perf_counter()
        response = await client.get("/api/hello?name=Developer")
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Verify performance budget (< 100ms dispatch)
        assert elapsed_ms < 100, f"Request took too long: {elapsed_ms:.2f}ms"

        # Verify response attributes
        assert response.status_code == 200
        assert response.headers["X-ZeroDock-Test"] == "True"

        data = response.json()
        assert data["message"] == "Hello, Developer!"
        assert data["requestId"].startswith("zd-req-")


@pytest.mark.asyncio
async def test_post_request_dispatch_loop(test_app):
    """Verify POST request reaches handler properly."""
    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8080") as client:
        response = await client.post("/api/hello?name=Tester", json={"some": "payload"})
        assert response.status_code == 200
        assert response.json()["message"] == "Hello, Tester!"


@pytest.mark.asyncio
async def test_root_serverless_local_config():
    """Verify gateway works with the root serverless-local.yaml and functions/hello.py."""
    config = load_config("serverless-local.yaml")
    app = create_app(config)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8080") as client:
        response = await client.get("/api/hello?name=OpenSource")
        assert response.status_code == 200
        assert "Hello, OpenSource! Sent natively from ZeroDock." in response.json()["message"]
