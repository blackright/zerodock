"""Data models for ZeroDock declarative configuration."""

from pathlib import Path
from typing import Dict, List, Literal
from pydantic import BaseModel, Field, field_validator


class GatewayConfig(BaseModel):
    """Network and runtime configuration for the local gateway."""

    host: str = Field(default="127.0.0.1", description="Bind IP address")
    port: int = Field(default=8080, ge=1024, le=65535, description="Port number between 1024 and 65535")
    log_level: Literal["debug", "info", "warning", "error"] = Field(
        default="info", description="Logging verbosity"
    )


class RouteDefinition(BaseModel):
    """Configuration definition for a single serverless route."""

    file: Path = Field(description="Path to Python handler source file")
    handler: str = Field(default="handler", description="Callable entrypoint function name")
    methods: List[str] = Field(
        default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
        description="Allowed HTTP methods",
    )
    timeout_seconds: int = Field(
        default=30, ge=1, le=900, description="Execution timeout limit in seconds"
    )

    @field_validator("methods")
    @classmethod
    def validate_methods(cls, methods: List[str]) -> List[str]:
        valid_methods = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
        normalized = [m.upper().strip() for m in methods]
        for m in normalized:
            if m not in valid_methods:
                raise ValueError(f"Invalid HTTP method '{m}'. Allowed: {sorted(valid_methods)}")
        return normalized

    @field_validator("handler")
    @classmethod
    def validate_handler_name(cls, handler_name: str) -> str:
        name = handler_name.strip()
        if not name.isidentifier():
            raise ValueError(f"Handler '{name}' is not a valid Python identifier.")
        return name


class ServerlessConfig(BaseModel):
    """Top-level configuration schema for serverless-local.yaml."""

    version: str = Field(default="1.0", description="Configuration schema version")
    gateway: GatewayConfig = Field(
        default_factory=GatewayConfig, description="Gateway network settings"
    )
    routes: Dict[str, RouteDefinition] = Field(
        ..., min_length=1, description="Mapping of route paths to execution definitions"
    )

    @field_validator("routes")
    @classmethod
    def normalize_route_keys(cls, routes: Dict[str, RouteDefinition]) -> Dict[str, RouteDefinition]:
        normalized = {}
        for path, defn in routes.items():
            # Clean up route path: ensure single leading slash and no trailing slash (unless root "/")
            clean_path = path.strip()
            if not clean_path.startswith("/"):
                clean_path = f"/{clean_path}"
            if len(clean_path) > 1 and clean_path.endswith("/"):
                clean_path = clean_path.rstrip("/")
            normalized[clean_path] = defn
        return normalized
