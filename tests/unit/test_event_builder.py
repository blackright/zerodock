"""Unit tests for HTTP Request to InvocationEvent transformation."""

import pytest
from starlette.requests import Request
from zerodock.engine.event import build_invocation_event


def create_mock_request(
    method: str = "GET",
    path: str = "/api/hello",
    query_string: str = "name=Alice&tag=test",
    headers: dict = None,
    body: bytes = b"",
) -> Request:
    """Helper to synthesize Starlette Request objects."""
    if headers is None:
        headers = {"host": "localhost:8080", "user-agent": "test-client"}

    raw_headers = [(k.encode("latin-1"), v.encode("latin-1")) for k, v in headers.items()]

    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": query_string.encode("ascii"),
        "headers": raw_headers,
        "client": ("127.0.0.1", 12345),
        "server": ("127.0.0.1", 8080),
        "scheme": "http",
        "http_version": "1.1",
    }

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(scope, receive)


@pytest.mark.asyncio
async def test_build_event_get_request():
    """Verify standard GET request event schema."""
    req = create_mock_request(method="GET", path="/api/hello", query_string="name=Alice")
    event = await build_invocation_event(req, route_key="GET /api/hello")

    assert event["version"] == "2.0"
    assert event["routeKey"] == "GET /api/hello"
    assert event["rawPath"] == "/api/hello"
    assert event["rawQueryString"] == "name=Alice"
    assert event["queryStringParameters"] == {"name": "Alice"}
    assert event["headers"]["host"] == "localhost:8080"
    assert event["requestContext"]["http"]["method"] == "GET"
    assert event["body"] is None
    assert event["isBase64Encoded"] is False


@pytest.mark.asyncio
async def test_build_event_post_json_request():
    """Verify POST request with JSON payload."""
    payload = b'{"action": "create", "value": 123}'
    req = create_mock_request(
        method="POST",
        path="/api/orders",
        query_string="",
        headers={"content-type": "application/json"},
        body=payload,
    )
    event = await build_invocation_event(req, route_key="POST /api/orders")

    assert event["requestContext"]["http"]["method"] == "POST"
    assert event["body"] == '{"action": "create", "value": 123}'
    assert event["isBase64Encoded"] is False
