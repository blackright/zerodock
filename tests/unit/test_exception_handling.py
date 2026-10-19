"""Unit tests for exception interception and traceback formatting."""

from zerodock.gateway.errors import format_error_response, format_timeout_response


def test_format_error_response():
    """Verify error payload includes exception type, message, and request ID."""
    try:
        raise ValueError("Missing database credentials")
    except Exception as exc:
        resp = format_error_response(exc, request_id="zd-req-test-123")

    assert resp.status_code == 500
    assert resp.headers["content-type"] == "application/json"

    import json
    data = json.loads(resp.body.decode("utf-8"))
    assert data["error"] == "InternalServerError"
    assert data["exceptionType"] == "ValueError"
    assert data["message"] == "Missing database credentials"
    assert data["requestId"] == "zd-req-test-123"


def test_format_timeout_response():
    """Verify timeout payload produces HTTP 504 with timeout duration."""
    resp = format_timeout_response(timeout_seconds=15, request_id="zd-req-timeout-456")

    assert resp.status_code == 504
    import json
    data = json.loads(resp.body.decode("utf-8"))
    assert data["error"] == "GatewayTimeout"
    assert "timed out after 15 seconds" in data["message"]
    assert data["requestId"] == "zd-req-timeout-456"
