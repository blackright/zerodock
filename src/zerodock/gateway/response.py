"""HTTP response normalizer for ZeroDock handlers."""

import json
from typing import Any

from starlette.responses import JSONResponse, Response


def normalize_response(result: Any) -> Response:
    """Translates any handler return value into a Starlette/FastAPI Response.

    Supports:
    - Standard Serverless: {'statusCode': 200, 'headers': {...}, 'body': '...'}
    - Status tuple: (200, {'message': 'ok'})
    - Raw dict/list: {'id': 1} -> HTTP 200 JSON
    - Raw string: "hello" -> HTTP 200 text/plain
    - None: -> HTTP 204 No Content

    Args:
        result: The raw object returned by the serverless handler.

    Returns:
        A compliant Starlette Response.
    """
    if isinstance(result, Response):
        return result

    if result is None:
        return Response(content=b"", status_code=204)

    # Handle (status_code, body) tuple
    if isinstance(result, tuple) and len(result) == 2 and isinstance(result[0], int):
        status_code, body = result
        if isinstance(body, (dict, list)):
            return JSONResponse(content=body, status_code=status_code)
        return Response(
            content=str(body), status_code=status_code, media_type="text/plain; charset=utf-8"
        )

    # Handle standard serverless dictionary format: {"statusCode": ..., "body": ...}
    if isinstance(result, dict) and "statusCode" in result:
        status_code = int(result["statusCode"])
        headers = dict(result.get("headers") or {})
        body = result.get("body", "")

        # If body is already a dict or list, serialize to JSON if needed
        if isinstance(body, (dict, list)):
            serialized_body = json.dumps(body)
            if "content-type" not in {k.lower(): v for k, v in headers.items()}:
                headers["Content-Type"] = "application/json"
            return Response(content=serialized_body, status_code=status_code, headers=headers)

        # Body is string or bytes
        body_bytes = body.encode("utf-8") if isinstance(body, str) else bytes(body)
        return Response(content=body_bytes, status_code=status_code, headers=headers)

    # Handle raw dict or list
    if isinstance(result, (dict, list)):
        return JSONResponse(content=result, status_code=200)

    # Handle plain string
    if isinstance(result, str):
        return Response(content=result, status_code=200, media_type="text/plain; charset=utf-8")

    # Fallback to string representation
    return Response(content=str(result), status_code=200)
