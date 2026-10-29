"""Integration tests for route diagnostics and 404 suggestions."""

from pathlib import Path

import httpx
import pytest

from zerodock.config.parser import load_config
from zerodock.gateway.app import create_app


@pytest.fixture
def diagnostics_app():
    """Create test application from valid fixture."""
    config = load_config(Path("tests/fixtures/configs/valid.yaml"))
    return create_app(config)


@pytest.mark.asyncio
async def test_unmatched_route_returns_404_with_suggestions(diagnostics_app):
    """Verify that calling an unknown route returns HTTP 404 listing registered routes."""
    transport = httpx.ASGITransport(app=diagnostics_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8080") as client:
        response = await client.get("/api/unregistered_endpoint")

        assert response.status_code == 404
        assert response.headers["content-type"] == "application/json"

        data = response.json()
        assert data["error"] == "Not Found"
        assert "No serverless route matches '/api/unregistered_endpoint'" in data["message"]
        assert "/api/hello" in data["availableRoutes"]


@pytest.mark.asyncio
async def test_matched_route_still_works(diagnostics_app):
    """Verify registered routes continue functioning normally alongside custom 404."""
    transport = httpx.ASGITransport(app=diagnostics_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8080") as client:
        response = await client.get("/api/hello?name=DiagnosticCheck")
        assert response.status_code == 200
        assert response.json()["message"] == "Hello, DiagnosticCheck!"
