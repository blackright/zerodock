"""Unit tests for configuration pre-flight diagnostics and route validation."""

from pathlib import Path

import pytest

from zerodock.config.parser import ConfigurationError, load_config


def test_missing_handler_file_raises_diagnostic_error(tmp_path: Path):
    """Verify that a route pointing to a non-existent file produces an actionable error."""
    bad_config = tmp_path / "bad_config.yaml"
    bad_config.write_text(
        "version: '1.0'\n"
        "routes:\n"
        "  api/ghost:\n"
        "    file: './does_not_exist.py'\n"
        "    handler: 'missing'\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="target file does not exist"):
        load_config(bad_config)


def test_valid_file_passes_preflight(tmp_path: Path):
    """Verify that a route pointing to a real file passes preflight."""
    py_file = tmp_path / "real_handler.py"
    py_file.write_text("def handler(event): return 'ok'\n", encoding="utf-8")

    good_config = tmp_path / "good_config.yaml"
    good_config.write_text(
        "version: '1.0'\nroutes:\n  api/real:\n    file: './real_handler.py'\n",
        encoding="utf-8",
    )

    cfg = load_config(good_config)
    assert "/api/real" in cfg.routes
    assert cfg.routes["/api/real"].file.exists()
