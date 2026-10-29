# Handler, Event, and Response Reference

Handlers are ordinary Python callables loaded from configured source files.
Both synchronous `def` and asynchronous `async def` functions are supported.
Use either `(event)` or `(event, context)` as the documented calling convention.

## Basic handler

```python
def lambda_handler(event, context):
    parameters = event.get("queryStringParameters") or {}
    return {"message": f"Hello, {parameters.get('name', 'World')}!"}
```

The plain dictionary is returned as HTTP 200 JSON. Set `handler: "lambda_handler"`
in the route configuration to select this entrypoint.

## Event reference

ZeroDock builds an AWS HTTP API v2-style event for local HTTP requests. This is a
local convenience format, not a claim of complete AWS/cloud runtime emulation.

| Field | Value |
| --- | --- |
| `version` | `"2.0"` |
| `routeKey` | Method and configured route, such as `GET /api/hello` |
| `rawPath` | Request URL path |
| `rawQueryString` | Query string without the leading `?` |
| `headers` | Dictionary with lowercase header names |
| `queryStringParameters` | Dictionary, or `None` when no parameters are present |
| `requestContext.http.method` | HTTP method |
| `requestContext.http.path` | Request path |
| `requestContext.http.sourceIp` | Client address reported by the request |
| `requestContext.requestId` | Generated event request identifier |
| `body` | UTF-8 text, base64-encoded binary text, or `None` |
| `isBase64Encoded` | Whether body bytes required base64 encoding |

Use `event["requestContext"]["http"]["method"]` for the method. The event does not
provide legacy `httpMethod` and `path` fields. Query parameters are represented as
a dictionary, not a lossless multi-value query model.

### Reading JSON explicitly

Request bodies are not automatically parsed into dictionaries, including requests
with a JSON content type. This complete example returns the decoded JSON value:

```python
import base64
import json

def lambda_handler(event, context):
    body = event.get("body")
    if body is None:
        return 400, {"error": "A JSON body is required"}
    try:
        if event.get("isBase64Encoded"):
            body = base64.b64decode(body).decode("utf-8")
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return 400, {"error": "Invalid JSON"}
    return {"received": payload}
```

Binary applications should handle decoded bytes deliberately rather than assume
all base64 data is UTF-8 JSON. This example expects a JSON document.

## Context reference

The optional second argument is an `InvocationContext`:

| Member | Meaning |
| --- | --- |
| `function_name` | Configured callable name |
| `request_id` | Local invocation identifier |
| `timeout_seconds` | Configured timeout, default 30 seconds |
| `get_remaining_time_in_millis()` | Non-negative remaining time estimate |
| `memory_limit_in_mb` | Metadata, default 128; not an enforced process memory limit |

Remaining time varies during execution; examples should not expect an exact initial
value. Context metadata is not a complete provider-specific cloud context.

## Response formats

| Handler result | HTTP behavior |
| --- | --- |
| Plain dictionary or list | HTTP 200 JSON |
| String | HTTP 200 text |
| `(status_code, body)` | Selected status; dictionary/list body becomes JSON |
| Dictionary containing `statusCode` | Selected status, optional headers, and body |
| `None` | HTTP 204 with no content |
| A Starlette response object | Passed through by the normalizer |

An explicit response dictionary can contain a JSON-compatible body directly:

```python
def lambda_handler(event, context):
    return {
        "statusCode": 201,
        "headers": {"Content-Type": "application/json"},
        "body": {"created": True},
    }
```

Convert datetimes and custom objects before returning them. Do not assume every
cloud response-envelope field has local semantics; for example, the response
normalizer does not implement provider-specific base64 decoding flags.

## Execution limits

Handler modules execute on every request in both loading modes. Module-level
initialization and side effects therefore repeat; imported dependencies can still
retain ordinary Python import state. Do not treat handler globals as durable storage
or this loading behavior as a security boundary.

Synchronous handler execution and module top-level code run inline. Blocking work
can delay the event loop, other requests, and observation. Asynchronous results are
awaited with the configured timeout, but synchronous work is not forcibly stopped.

Exceptions produce development-oriented HTTP 500 responses and terminal tracebacks.
Asynchronous timeouts produce HTTP 504. These diagnostics may contain sensitive
information; use trusted local code and clients only.
