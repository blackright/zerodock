"""Error response formatters and traceback visualizer for ZeroDock."""

import sys
import traceback

from starlette.responses import JSONResponse


def format_error_response(exc: Exception, request_id: str = "") -> JSONResponse:
    """Formats an uncaught handler exception into a standard HTTP 500 response.

    Also outputs the full unmasked traceback to stderr for developer debugging.

    Args:
        exc: The caught exception.
        request_id: Unique invocation identifier.

    Returns:
        JSONResponse with HTTP 500 and diagnostic details.
    """
    # Print clear, unmasked traceback to standard error for developer visibility
    print(f"\n[ZeroDock ERROR] Exception in handler (Request ID: {request_id}):", file=sys.stderr)
    traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)
    print("", file=sys.stderr)

    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "exceptionType": type(exc).__name__,
            "message": str(exc),
            "requestId": request_id,
        },
    )


def format_timeout_response(timeout_seconds: int, request_id: str = "") -> JSONResponse:
    """Formats an execution timeout into an HTTP 504 Gateway Timeout response.

    Args:
        timeout_seconds: Configured timeout limit in seconds.
        request_id: Unique invocation identifier.

    Returns:
        JSONResponse with HTTP 504 and diagnostic details.
    """
    print(
        f"\n[ZeroDock TIMEOUT] Function exceeded limit of {timeout_seconds}s "
        f"(Request ID: {request_id})",
        file=sys.stderr,
    )
    return JSONResponse(
        status_code=504,
        content={
            "error": "GatewayTimeout",
            "message": f"Function execution timed out after {timeout_seconds} seconds",
            "requestId": request_id,
        },
    )
