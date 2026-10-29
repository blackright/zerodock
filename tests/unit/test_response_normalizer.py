"""Unit tests for handler response normalization into HTTP responses."""

from starlette.responses import Response

from zerodock.gateway.response import normalize_response


def test_normalize_standard_serverless_dict():
    """Verify standard statusCode + headers + body dict."""
    handler_result = {
        "statusCode": 201,
        "headers": {"X-Created": "yes"},
        "body": '{"status": "created"}',
    }
    resp: Response = normalize_response(handler_result)
    assert resp.status_code == 201
    assert resp.headers["x-created"] == "yes"
    assert resp.body.decode("utf-8") == '{"status": "created"}'


def test_normalize_raw_dict():
    """Verify raw Python dictionary is auto-wrapped as JSON."""
    handler_result = {"user_id": 42, "role": "admin"}
    resp: Response = normalize_response(handler_result)
    assert resp.status_code == 200
    assert "application/json" in resp.headers["content-type"]
    assert b'"user_id":42' in resp.body or b'"user_id": 42' in resp.body


def test_normalize_raw_string():
    """Verify raw string is returned as text/plain."""
    handler_result = "Plain text message"
    resp: Response = normalize_response(handler_result)
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    assert resp.body.decode("utf-8") == "Plain text message"


def test_normalize_none():
    """Verify None return produces HTTP 204 No Content."""
    resp: Response = normalize_response(None)
    assert resp.status_code == 204
    assert len(resp.body) == 0


def test_normalize_status_and_body_tuple():
    """Verify (status_code, body) tuple syntax."""
    handler_result = (202, {"accepted": True})
    resp: Response = normalize_response(handler_result)
    assert resp.status_code == 202
    assert "application/json" in resp.headers["content-type"]
