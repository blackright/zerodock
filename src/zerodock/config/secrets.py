"""Local environment and secrets loader (.env.local / .env) for ZeroDock."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path


class SecretsLoadError(ValueError):
    """Raised when a local environment file cannot be parsed safely."""


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse KEY=VALUE lines from an env file without logging secret values."""
    parsed: dict[str, str] = {}
    text = path.read_text(encoding="utf-8")
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            raise SecretsLoadError(f"Malformed env entry in {path.name} at line {line_no}")
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or not key.replace("_", "").isalnum():
            raise SecretsLoadError(f"Invalid env key in {path.name} at line {line_no}")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        parsed[key] = value
    return parsed


def load_local_env(
    env_file_path: Path | None = None,
    *,
    base_dir: Path | None = None,
) -> dict[str, str]:
    """Load local env variables with precedence: .env.local > .env.

    Returns an empty dictionary gracefully if no env file exists.
    """
    if env_file_path is not None:
        target = Path(env_file_path)
        return parse_env_file(target) if target.is_file() else {}

    root = Path(base_dir) if base_dir is not None else Path.cwd()
    merged: dict[str, str] = {}
    for filename in (".env", ".env.local"):
        candidate = root / filename
        if candidate.is_file():
            merged.update(parse_env_file(candidate))
    return merged


def inject_local_env(
    values: Mapping[str, str],
    *,
    override_system: bool = False,
) -> dict[str, str]:
    """Inject parsed env values into os.environ respecting host precedence."""
    effective: dict[str, str] = {}
    for key, value in values.items():
        if override_system or key not in os.environ:
            os.environ[key] = value
            effective[key] = value
        else:
            effective[key] = os.environ[key]
    return effective
