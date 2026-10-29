"""HTTP request to cloud event transformer for ZeroDock."""

import base64
import time
import uuid
from typing import Any, Dict

from starlette.requests import Request


async def build_invocation_event(request: Request, route_key: str = "") -> Dict[str, Any]:
    """Converts a Starlette/FastAPI Request into an AWS Lambda API Gateway v2 event.

    Args:
        request: Incoming HTTP request.
        route_key: Configured route key string (e.g. 'GET /api/users').

    Returns:
        Structured event dictionary.
    """
    raw_path = request.url.path
    raw_query = request.url.query

    # Query string parameters mapping
    query_params = dict(request.query_params)

    # Normalize headers to lowercase keys
    headers = {k.lower(): v for k, v in request.headers.items()}

    # Read and decode body
    body_bytes = await request.body()
    body_str = None
    is_base64 = False

    if body_bytes:
        try:
            body_str = body_bytes.decode("utf-8")
        except UnicodeDecodeError:
            body_str = base64.b64encode(body_bytes).decode("ascii")
            is_base64 = True

    client_ip = request.client.host if request.client else "127.0.0.1"
    req_id = f"zd-req-{uuid.uuid4().hex[:12]}"

    if not route_key:
        route_key = f"{request.method} {raw_path}"

    return {
        "version": "2.0",
        "routeKey": route_key,
        "rawPath": raw_path,
        "rawQueryString": raw_query,
        "headers": headers,
        "queryStringParameters": query_params if query_params else None,
        "requestContext": {
            "http": {
                "method": request.method,
                "path": raw_path,
                "protocol": "HTTP/1.1",
                "sourceIp": client_ip,
                "userAgent": headers.get("user-agent", "zerodock-client"),
            },
            "requestId": req_id,
            "timeEpoch": int(time.time() * 1000),
        },
        "body": body_str,
        "isBase64Encoded": is_base64,
    }
