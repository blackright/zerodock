#!/usr/bin/env python3
"""
ZeroDock - Local Release & PyPI Publishing Automation Tool
Simplifies and automates pre-flight checks, testing, artifact building,
and release publishing (via GitHub Actions OIDC tag push or local upload).

Usage:
    python scripts/publish.py --check      # Run pre-flight validations & tests only
    python scripts/publish.py --dry-run    # Run validations, build wheel & smoke-test
    python scripts/publish.py --tag        # Tag version and push to trigger GitHub Actions PyPI release
    python scripts/publish.py --local      # Directly upload built dist to PyPI (requires PyPI token)
    python scripts/publish.py --test       # Target TestPyPI instead of production PyPI
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = REPO_ROOT / "dist"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"


def log(msg: str, symbol: str = "ℹ️") -> None:
    print(f"{symbol}  {msg}")


def log_success(msg: str) -> None:
    print(f"✅ {msg}")


def log_error(msg: str) -> None:
    print(f"❌ {msg}", file=sys.stderr)


def log_warn(msg: str) -> None:
    print(f"⚠️  {msg}")


def run_cmd(
    cmd: list[str],
    cwd: Path = REPO_ROOT,
    check: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=check,
        text=True,
        capture_output=capture,
    )


def get_current_version() -> str:
    """Extracts package version from pyproject.toml."""
    if not PYPROJECT_PATH.exists():
        log_error("pyproject.toml not found in repository root!")
        sys.exit(1)

    content = PYPROJECT_PATH.read_text(encoding="utf-8")
    match = re.search(r'version\s*=\s*"([^"]+)"', content)
    if not match:
        log_error("Could not find version string in pyproject.toml!")
        sys.exit(1)
    return match.group(1)


def get_git_branch() -> str:
    res = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return res.stdout.strip() if res.returncode == 0 else "unknown"


def check_git_clean() -> bool:
    res = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    # Check if there are tracked modifications
    lines = [line for line in res.stdout.strip().splitlines() if not line.startswith("??")]
    return len(lines) == 0


def run_tests() -> bool:
    log("Running automated pytest test suite...", "🧪")
    # Try using virtualenv pytest if available, otherwise fallback
    venv_pytest = REPO_ROOT / ".venv" / "Scripts" / "pytest.exe"
    if not venv_pytest.exists():
        venv_pytest = REPO_ROOT / ".venv" / "bin" / "pytest"

    pytest_cmd = [str(venv_pytest) if venv_pytest.exists() else "pytest", "-v"]
    try:
        res = subprocess.run(pytest_cmd, cwd=REPO_ROOT, text=True)
        return res.returncode == 0
    except Exception as e:
        log_error(f"Failed to execute pytest: {e}")
        return False


def build_distribution() -> bool:
    log("Building distribution archives (.whl and .tar.gz)...", "📦")
    # Clean old dist/
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    # Use uv build if available, else python -m build
    has_uv = shutil.which("uv") is not None
    build_cmd = ["uv", "build"] if has_uv else [sys.executable, "-m", "build"]

    try:
        res = subprocess.run(build_cmd, cwd=REPO_ROOT, text=True)
        if res.returncode != 0:
            log_error("Build command failed!")
            return False

        wheels = list(DIST_DIR.glob("*.whl"))
        sdists = list(DIST_DIR.glob("*.tar.gz"))
        if not wheels or not sdists:
            log_error("Expected both .whl and .tar.gz in dist/ directory.")
            return False

        log_success(f"Built {len(wheels)} wheel(s) and {len(sdists)} source archive(s) in dist/")
        for f in wheels + sdists:
            size_kb = f.stat().st_size / 1024
            print(f"   • {f.name} ({size_kb:.1f} KB)")
        return True
    except Exception as e:
        log_error(f"Failed to build distribution: {e}")
        return False


def run_smoke_test() -> bool:
    log("Verifying clean-room wheel smoke test...", "🔍")
    venv_pytest = REPO_ROOT / ".venv" / "Scripts" / "pytest.exe"
    if not venv_pytest.exists():
        venv_pytest = REPO_ROOT / ".venv" / "bin" / "pytest"

    smoke_cmd = [
        str(venv_pytest) if venv_pytest.exists() else "pytest",
        "tests/integration/test_wheel_install.py",
        "-v",
    ]
    res = subprocess.run(smoke_cmd, cwd=REPO_ROOT, text=True)
    return res.returncode == 0


def push_release_tag(version: str) -> bool:
    tag = f"v{version}"
    log(f"Preparing to tag and push {tag} to trigger GitHub Actions release...", "🚀")

    # Check if tag exists locally
    res_local = subprocess.run(["git", "tag", "-l", tag], capture_output=True, text=True)
    if tag in res_local.stdout.split():
        log_error(f"Git tag '{tag}' already exists locally!")
        return False

    # Check if tag exists remotely
    res_remote = subprocess.run(
        ["git", "ls-remote", "--tags", "origin", tag],
        capture_output=True,
        text=True,
    )
    if tag in res_remote.stdout:
        log_error(f"Git tag '{tag}' already exists on origin!")
        return False

    # Create tag
    log(f"Creating git tag: {tag}")
    run_cmd(["git", "tag", "-a", tag, "-m", f"Release {tag}"])

    # Push tag
    log(f"Pushing git tag '{tag}' to origin...")
    try:
        run_cmd(["git", "push", "origin", tag])
        log_success(f"Successfully pushed tag {tag} to origin!")
        print("\n" + "=" * 65)
        print("🎉 Release Triggered Successfully!")
        print(f"GitHub Actions will now build, test, and publish ZeroDock {version}.")
        print("Track workflow progress:")
        print("👉 https://github.com/blackright/zerodock/actions/workflows/publish.yml")
        print("=" * 65)
        return True
    except subprocess.CalledProcessError as e:
        log_error(f"Failed to push tag to origin: {e}")
        return False


def upload_direct_local(target_testpypi: bool = False) -> bool:
    repo_name = "TestPyPI" if target_testpypi else "PyPI"
    log(f"Uploading distribution archives directly to {repo_name}...", "📤")

    has_uv = shutil.which("uv") is not None
    if has_uv:
        upload_cmd = ["uv", "publish"]
        if target_testpypi:
            upload_cmd.extend(["--publish-url", "https://test.pypi.org/legacy/"])
    else:
        upload_cmd = [sys.executable, "-m", "twine", "upload", "dist/*"]
        if target_testpypi:
            upload_cmd.extend(["--repository", "testpypi"])

    try:
        res = subprocess.run(upload_cmd, cwd=REPO_ROOT)
        return res.returncode == 0
    except Exception as e:
        log_error(f"Upload failed: {e}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ZeroDock Local Release & PyPI Publishing Automation",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run pre-flight checks and tests only (no build or release)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run tests, build distribution archives, and verify wheel without publishing",
    )
    parser.add_argument(
        "--tag",
        action="store_true",
        help="Create and push Git release tag (v<version>) to trigger GitHub Actions OIDC release",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Directly upload dist/* to PyPI from local machine using uv or twine",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="When using --local, upload to TestPyPI instead of production PyPI",
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip interactive confirmation prompts",
    )

    args = parser.parse_args()

    print("\n" + "=" * 65)
    print("🚀 ZeroDock — Release & PyPI Publishing Helper")
    print("=" * 65)

    version = get_current_version()
    branch = get_git_branch()
    log(f"Package Version:  zerodock v{version}")
    log(f"Current Branch:   {branch}")

    if branch != "main" and (args.tag or args.local):
        log_warn(f"You are currently on branch '{branch}', not 'main'!")
        if not args.yes:
            confirm = input("⚠️  Releases typically originate from 'main'. Continue anyway? [y/N]: ")
            if confirm.lower() != "y":
                print("Aborted.")
                sys.exit(0)

    # Pre-flight check: Git status
    if not check_git_clean() and (args.tag or args.local):
        log_warn("You have uncommitted changes in your working tree.")
        if not args.yes:
            confirm = input("Continue with dirty working tree? [y/N]: ")
            if confirm.lower() != "y":
                print("Aborted. Please commit or stash changes.")
                sys.exit(0)

    # Step 1: Run tests
    if not run_tests():
        log_error("Test suite failed! Fix errors before releasing.")
        sys.exit(1)
    log_success("All tests passed cleanly!")

    if args.check:
        log_success("Pre-flight validation complete! Ready for release.")
        return

    # Step 2: Build distribution
    if not build_distribution():
        sys.exit(1)

    # Step 3: Run isolated wheel smoke test
    if not run_smoke_test():
        log_error("Wheel clean-room smoke test failed!")
        sys.exit(1)
    log_success("Wheel installation and CLI smoke test passed!")

    if args.dry_run:
        log_success(f"Dry-run complete! ZeroDock v{version} package is verified and ready.")
        return

    # Step 4: Publish
    if args.tag:
        if not args.yes:
            confirm = input(f"\nCreate and push Git tag 'v{version}' to trigger automated PyPI release? [y/N]: ")
            if confirm.lower() != "y":
                print("Cancelled.")
                sys.exit(0)
        success = push_release_tag(version)
        if not success:
            sys.exit(1)

    elif args.local:
        target = "TestPyPI" if args.test else "PyPI"
        if not args.yes:
            confirm = input(f"\nUpload archives directly to {target}? [y/N]: ")
            if confirm.lower() != "y":
                print("Cancelled.")
                sys.exit(0)
        success = upload_direct_local(target_testpypi=args.test)
        if not success:
            sys.exit(1)
        log_success(f"Published successfully to {target}!")
    else:
        # Default menu if no action flag given
        print("\n" + "-" * 65)
        print("Package validation and build complete! Select an action:")
        print("  1) Tag & push to GitHub (Trigger GitHub Actions PyPI OIDC release) [Recommended]")
        print("  2) Upload directly to TestPyPI (local dry run)")
        print("  3) Upload directly to PyPI (local publish)")
        print("  4) Exit without publishing")
        choice = input("\nEnter choice [1-4]: ").strip()

        if choice == "1":
            push_release_tag(version)
        elif choice == "2":
            upload_direct_local(target_testpypi=True)
        elif choice == "3":
            upload_direct_local(target_testpypi=False)
        else:
            print("Done. No release action taken.")


if __name__ == "__main__":
    main()
