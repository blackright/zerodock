"""Integration test verifying exception handling and gateway resilience."""

from pathlib import Path

import httpx
import pytest

from zerodock.config.models import RouteDefinition, ServerlessConfig
from zerodock.gateway.app import create_app


@pytest.fixture
def error_test_app():
    """Builds a test application with both healthy and crashing routes."""
    config = ServerlessConfig(
        routes={
            "/api/hello": RouteDefinition(
                file=Path("tests/fixtures/handlers/hello.py").resolve(),
                handler="lambda_handler",
                methods=["GET"],
            ),
            "/api/crash": RouteDefinition(
                file=Path("tests/fixtures/handlers/crash.py").resolve(),
                handler="lambda_handler",
                methods=["GET"],
            ),
        }
    )
    return create_app(config)


@pytest.mark.asyncio
async def test_crashing_handler_returns_500(error_test_app):
    """Verify that an unhandled exception returns HTTP 500 with diagnostic payload."""
    transport = httpx.ASGITransport(app=error_test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8080") as client:
        response = await client.get("/api/crash")

        assert response.status_code == 500
        assert response.headers["content-type"] == "application/json"

        data = response.json()
        assert data["error"] == "InternalServerError"
        assert data["exceptionType"] == "ValueError"
        assert data["message"] == "Simulated crash for debugging"
        assert data["requestId"].startswith("zd-req-")


@pytest.mark.asyncio
async def test_gateway_remains_resilient_after_crash(error_test_app):
    """Verify that after a crash, subsequent requests to healthy routes continue working."""
    transport = httpx.ASGITransport(app=error_test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8080") as client:
        # First trigger a crash
        crash_response = await client.get("/api/crash")
        assert crash_response.status_code == 500

        # Then immediately call a healthy route
        healthy_response = await client.get("/api/hello?name=ResilienceTest")
        assert healthy_response.status_code == 200
        assert healthy_response.json()["message"] == "Hello, ResilienceTest!"
