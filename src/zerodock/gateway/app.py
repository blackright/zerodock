"""FastAPI application factory and route dispatcher for ZeroDock."""

import asyncio
import inspect
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse, Response

from zerodock.config.models import RouteDefinition, ServerlessConfig
from zerodock.config.parser import load_config
from zerodock.engine.context import InvocationContext
from zerodock.engine.event import build_invocation_event
from zerodock.engine.loader import invoke_handler, load_handler
from zerodock.engine.watcher import HandlerWatcher
from zerodock.gateway.errors import format_error_response, format_timeout_response
from zerodock.gateway.response import normalize_response

logger = logging.getLogger("uvicorn.error.zerodock.lifecycle")


def create_app(config: Optional[ServerlessConfig] = None, *, reload: bool = False) -> FastAPI:
    """Builds and configures the FastAPI gateway application.

    Args:
        config: Optional pre-loaded ServerlessConfig. If None, loads from serverless-local.yaml.
        reload: Observe configured handler files and execute fresh source when enabled.

    Returns:
        Configured FastAPI application instance.
    """
    if config is None:
        config_file = Path("serverless-local.yaml")
        if config_file.exists():
            config = load_config(config_file)
        else:
            # Fallback for bare imports
            config = ServerlessConfig(routes={"/": RouteDefinition(file=Path("./app.py"))})

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        if not reload:
            yield
            return
        watcher = HandlerWatcher(route.file for route in application.state.config.routes.values())
        application.state.handler_watcher = watcher
        try:
            await watcher.start()
            yield
        except BaseException:
            try:
                await watcher.stop()
            except asyncio.CancelledError:
                pass
            except BaseException:
                logger.exception("Handler reload cleanup failed while handling another error")
            raise
        else:
            await watcher.stop()

    app = FastAPI(title="ZeroDock Gateway", version="0.1.0", lifespan=lifespan)
    app.state.config = config
    app.state.handler_watcher = None

    # Register each configured route
    for route_path, route_defn in config.routes.items():
        # Clean path for route registration
        fastapi_path = route_path if route_path.startswith("/") else f"/{route_path}"

        def make_endpoint(r_path: str, r_defn):
            async def endpoint_handler(request: Request) -> Response:
                req_id = "zd-req-init"
                try:
                    # 1. Build the context object
                    context = InvocationContext(
                        function_name=r_defn.handler,
                        timeout_seconds=r_defn.timeout_seconds,
                    )
                    req_id = context.request_id

                    # 2. Load the target handler function
                    handler_fn = load_handler(r_defn.file, r_defn.handler, reload=reload)

                    # 3. Build the AWS-compatible event dictionary
                    route_key = f"{request.method} {r_path}"
                    event = await build_invocation_event(request, route_key=route_key)

                    # 4. Invoke the handler (with timeout enforcement)
                    invocation_task = invoke_handler(handler_fn, event, context)
                    if inspect.iscoroutine(invocation_task):
                        raw_result = await asyncio.wait_for(
                            invocation_task, timeout=r_defn.timeout_seconds
                        )
                    else:
                        raw_result = invocation_task

                    # 5. Normalize and return the HTTP response
                    return normalize_response(raw_result)
                except asyncio.TimeoutError:
                    return format_timeout_response(
                        timeout_seconds=r_defn.timeout_seconds,
                        request_id=req_id,
                    )
                except Exception as exc:
                    return format_error_response(
                        exc=exc,
                        request_id=req_id,
                    )

            return endpoint_handler

        app.add_api_route(
            fastapi_path,
            endpoint=make_endpoint(fastapi_path, route_defn),
            methods=route_defn.methods,
            name=f"route_{route_path}",
        )

    @app.exception_handler(StarletteHTTPException)
    async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            available_routes = sorted(list(config.routes.keys()))
            return JSONResponse(
                status_code=404,
                content={
                    "error": "Not Found",
                    "message": f"No serverless route matches '{request.url.path}'",
                    "availableRoutes": available_routes,
                },
            )
        return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

    return app


# Default app instance for standard ASGI runners (e.g., uvicorn zerodock.gateway.app:app)
app = create_app()
