"""Verify wheel installation and CLI execution in an isolated target directory."""

import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import pytest


def get_latest_wheel(dist_dir: Path) -> Path:
    wheels = sorted(dist_dir.glob("zerodock-*.whl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not wheels:
        pytest.skip("No pre-built wheel found in dist/. Run 'uv build' first.")
    return wheels[0]


def test_clean_room_wheel_install_and_cli_execution() -> None:
    """Verify the unpacked wheel enables the CLI without dev packages."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    dist_dir = repo_root / "dist"

    wheel_path = get_latest_wheel(dist_dir)

    with tempfile.TemporaryDirectory(prefix="zd_smoke_") as tmp_dir:
        site_packages = Path(tmp_dir) / "site-packages"
        site_packages.mkdir(parents=True, exist_ok=True)

        # Unpack the binary wheel directly (wheels are standards-compliant zip archives)
        with zipfile.ZipFile(wheel_path, "r") as zf:
            zf.extractall(site_packages)

        # Verify py.typed was unpacked
        assert (site_packages / "zerodock" / "py.typed").exists(), (
            "py.typed missing from unpacked wheel"
        )

        # Verify entrypoint file was unpacked in dist-info
        dist_infos = list(site_packages.glob("zerodock-*.dist-info"))
        assert len(dist_infos) == 1, "Expected exactly 1 dist-info directory in wheel"
        entry_points_file = dist_infos[0] / "entry_points.txt"
        assert entry_points_file.exists(), "entry_points.txt missing from wheel"
        assert "zerodock=zerodock.cli:main" in entry_points_file.read_text(
            encoding="utf-8"
        ).replace(" ", "")

        # Execute CLI using the clean site-packages via PYTHONPATH
        env = os.environ.copy()
        env["PYTHONPATH"] = str(site_packages)

        # 1. Test version command
        version_cmd = [sys.executable, "-m", "zerodock.cli", "--version"]
        res_version = subprocess.run(version_cmd, env=env, capture_output=True, text=True)
        assert res_version.returncode == 0, f"Version check failed: {res_version.stderr}"
        wheel_version = wheel_path.stem.split("-")[1]
        assert f"ZeroDock {wheel_version}" in res_version.stdout

        # 2. Test dev help command
        help_cmd = [sys.executable, "-m", "zerodock.cli", "dev", "--help"]
        res_help = subprocess.run(help_cmd, env=env, capture_output=True, text=True)
        assert res_help.returncode == 0, f"Dev help failed: {res_help.stderr}"
        assert "usage: zerodock dev" in res_help.stdout
        assert "--config" in res_help.stdout
        assert "--port" in res_help.stdout
