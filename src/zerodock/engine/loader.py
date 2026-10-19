"""Dynamic module loader and function invoker for serverless handlers."""

import asyncio
import hashlib
import importlib.util
import inspect
import sys
from pathlib import Path
from typing import Any, Callable, cast


class HandlerLoadError(Exception):
    """Raised when a handler file cannot be imported or callable not found."""
    pass


def load_handler(file_path: Path, handler_name: str) -> Callable[..., Any]:
    """Dynamically loads a Python file and returns the target handler function.

    Uses an isolated module namespace in sys.modules to prevent collisions across handlers.

    Args:
        file_path: Absolute or relative Path to target Python file.
        handler_name: Name of the entrypoint callable function.

    Returns:
        The callable handler object.

    Raises:
        HandlerLoadError: If file does not exist, syntax fails, or handler missing.
    """
    resolved_path = Path(file_path).resolve()

    if not resolved_path.exists():
        raise HandlerLoadError(f"File not found: {resolved_path}")

    # Generate a unique module name based on the file path to avoid sys.modules collisions
    path_hash = hashlib.sha256(str(resolved_path).encode("utf-8")).hexdigest()[:12]
    module_name = f"zerodock.handlers.mod_{path_hash}"

    try:
        spec = importlib.util.spec_from_file_location(module_name, resolved_path)
        if spec is None or spec.loader is None:
            raise HandlerLoadError(f"Could not load importlib spec for {resolved_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    except Exception as exc:
        raise HandlerLoadError(f"Failed to load module from {resolved_path}: {exc}") from exc

    if not hasattr(module, handler_name):
        raise HandlerLoadError(
            f"Handler function '{handler_name}' not found in module {resolved_path}"
        )

    handler_fn = getattr(module, handler_name)
    if not callable(handler_fn):
        raise HandlerLoadError(
            f"Target attribute '{handler_name}' in {resolved_path} is not callable."
        )

    return cast(Callable[..., Any], handler_fn)


def invoke_handler(handler_fn: Callable[..., Any], event: dict, context: Any = None) -> Any:
    """Executes a handler function, handling sync/async and parameter arity.

    Args:
        handler_fn: Target callable function.
        event: Invocation event dictionary.
        context: Optional InvocationContext runtime object.

    Returns:
        The handler return value, or a coroutine if async.
    """
    # Inspect callable signature to see if it accepts 1 or 2+ parameters
    sig = inspect.signature(handler_fn)
    params = list(sig.parameters.values())

    # Check if only accepting event (1 positional arg or kwargs)
    if len(params) == 1:
        result = handler_fn(event)
    else:
        result = handler_fn(event, context)

    # If the handler is a coroutine or returned a coroutine, return the coroutine
    if inspect.iscoroutine(result):
        return result

    return result
