"""Unit tests for package metadata, semantic versioning, and PEP 621 compliance."""

import re
import sys
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from unittest.mock import patch

import pytest

import zerodock

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        tomllib = None  # type: ignore[assignment]



def test_version_is_valid_semver() -> None:
    """zerodock.__version__ must be a valid semantic version string."""
    version = zerodock.__version__
    assert isinstance(version, str)
    # Match standard semver like 0.1.0 or pre-release 0.1.0.dev0
    assert re.match(r"^\d+\.\d+\.\d+", version) is not None


def _get_pyproject_version() -> str:
    repo_root = Path(__file__).resolve().parent.parent.parent
    pyproject_path = repo_root / "pyproject.toml"
    content = pyproject_path.read_text(encoding="utf-8")
    m = re.search(r'version\s*=\s*"([^"]+)"', content)
    assert m, "version not found in pyproject.toml"
    return m.group(1)


def test_version_fallback_on_package_not_found() -> None:
    """If package is not installed, version fallback must resolve version from pyproject.toml."""
    expected_version = _get_pyproject_version()
    with patch("importlib.metadata.version", side_effect=PackageNotFoundError):
        import importlib
        import zerodock as zd
        importlib.reload(zd)
        assert zd.__version__ == expected_version


def test_pyproject_metadata_completeness() -> None:
    """pyproject.toml must contain all PEP 621 metadata fields required for PyPI."""
    if tomllib is None:
        pytest.skip("tomllib (Python 3.11+) or tomli is required to parse TOML")

    repo_root = Path(__file__).resolve().parent.parent.parent
    pyproject_path = repo_root / "pyproject.toml"
    assert pyproject_path.exists(), "pyproject.toml must exist in repo root"

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    project = data.get("project", {})
    assert project.get("name") == "zerodock"
    assert re.match(r"^\d+\.\d+\.\d+", project.get("version", "")) is not None
    assert project.get("version") == _get_pyproject_version()
    assert len(project.get("description", "")) > 10
    assert len(project.get("keywords", [])) >= 3
    assert len(project.get("classifiers", [])) >= 5

    urls = project.get("urls", {})
    assert "Homepage" in urls
    assert "Repository" in urls
    assert "Issues" in urls

    scripts = project.get("scripts", {})
    assert scripts.get("zerodock") == "zerodock.cli:main"
