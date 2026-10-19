"""Invocation runtime context and result structures for ZeroDock."""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class InvocationContext:
    """Runtime context object passed as second parameter to serverless handlers."""

    function_name: str
    request_id: str = field(default_factory=lambda: f"zd-req-{uuid.uuid4().hex[:12]}")
    memory_limit_in_mb: int = 128
    started_at: float = field(default_factory=time.monotonic)
    timeout_seconds: int = 30

    def get_remaining_time_in_millis(self) -> int:
        """Returns the number of milliseconds remaining before execution timeout."""
        elapsed = time.monotonic() - self.started_at
        remaining = (self.timeout_seconds - elapsed) * 1000.0
        return max(0, int(remaining))


@dataclass
class InvocationResult:
    """Normalized output produced by the serverless handler invocation."""

    status_code: int = 200
    headers: Dict[str, str] = field(default_factory=lambda: {"Content-Type": "application/json"})
    body: Any = ""
    is_base64_encoded: bool = False
