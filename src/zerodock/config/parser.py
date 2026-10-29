"""YAML configuration parser and validator for ZeroDock."""

from pathlib import Path
from typing import Union

import yaml
from pydantic import ValidationError

from zerodock.config.models import ServerlessConfig


class ConfigurationError(Exception):
    """Raised when serverless-local.yaml is missing, malformed, or invalid."""

    pass


def load_config(config_path: Union[str, Path] = "serverless-local.yaml") -> ServerlessConfig:
    """Load and validate serverless-local.yaml from disk.

    Resolves relative handler file paths against the directory of the config file.

    Args:
        config_path: Path to the configuration YAML file.

    Returns:
        Validated ServerlessConfig instance.

    Raises:
        ConfigurationError: If the file does not exist, cannot be parsed, or fails validation.
    """
    path = Path(config_path).resolve()

    if not path.exists():
        raise ConfigurationError(f"Configuration file not found at: {path}")

    try:
        raw_text = path.read_text(encoding="utf-8")
    except Exception as exc:
        raise ConfigurationError(f"Failed to read configuration file: {exc}") from exc

    try:
        parsed_yaml = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"Malformed YAML in {path.name}: {exc}") from exc

    if not isinstance(parsed_yaml, dict):
        raise ConfigurationError(
            f"Invalid configuration root in {path.name}: "
            f"expected mapping, got {type(parsed_yaml).__name__}"
        )

    try:
        config = ServerlessConfig.model_validate(parsed_yaml)
    except ValidationError as exc:
        error_messages = []
        for err in exc.errors():
            loc = " -> ".join(str(item) for item in err["loc"])
            error_messages.append(f"  - [{loc}]: {err['msg']}")
        formatted_errors = "\n".join(error_messages)
        raise ConfigurationError(
            f"Configuration validation failed in {path.name}:\n{formatted_errors}"
        ) from exc

    # Resolve relative file paths to absolute paths based on config location and verify existence
    config_dir = path.parent
    for route_path, route_defn in config.routes.items():
        if not route_defn.file.is_absolute():
            resolved_file = (config_dir / route_defn.file).resolve()
            route_defn.file = resolved_file

        if not route_defn.file.exists():
            raise ConfigurationError(
                f"Route '{route_path}' target file does not exist: {route_defn.file}"
            )

    return config
