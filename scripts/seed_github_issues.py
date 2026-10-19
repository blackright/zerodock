#!/usr/bin/env python3
"""
ZeroDock - Automated GitHub Issue Seeder
Reads pre-drafted starter issues from .github/starter-issues/ and publishes them to GitHub
using either:
1. GitHub CLI (`gh issue create`)
2. GitHub REST API (via GITHUB_TOKEN environment variable)
"""

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def parse_issue_file(file_path: Path) -> dict:
    content = file_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    title = ""
    labels = []
    body_lines = []

    for line in lines:
        if line.startswith("# ") and not title:
            title = line.lstrip("# ").strip()
        elif line.startswith("**Labels**:") and not labels:
            raw_labels = line.split(":", 1)[1]
            extracted = re.findall(r"`([^`]+)`", raw_labels)
            if not extracted:
                extracted = [lbl.strip() for lbl in raw_labels.split(",") if lbl.strip()]
            labels = extracted
        else:
            body_lines.append(line)

    body = "\n".join(body_lines).strip()
    return {"title": title, "labels": labels, "body": body, "file": file_path.name}


def get_git_remote_repo() -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        match = re.search(r"github\.com[:/]([^/]+/[^/\.]+)", out)
        if match:
            return match.group(1)
    except Exception:
        pass
    return None


def ensure_gh_labels(labels: set[str]) -> None:
    """Pre-creates any custom labels in the repository so gh issue create doesn't fail."""
    for label in sorted(labels):
        cmd = ["gh", "label", "create", label, "--color", "0E8A16", "--force"]
        try:
            subprocess.run(cmd, capture_output=True, text=True)
        except Exception:
            pass


def create_issue_via_gh(title: str, labels: list[str], body: str) -> bool:
    cmd = ["gh", "issue", "create", "--title", title, "--body", body]
    for label in labels:
        cmd.extend(["--label", label])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"  ✅ Created issue: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        # If custom labels failed, retry with repository default labels
        safe_labels = [l for l in labels if l in {"good first issue", "help wanted", "enhancement"}]
        fallback_cmd = ["gh", "issue", "create", "--title", title, "--body", body]
        for l in safe_labels:
            fallback_cmd.extend(["--label", l])
        try:
            fallback_res = subprocess.run(fallback_cmd, capture_output=True, text=True, check=True)
            print(f"  ✅ Created issue: {fallback_res.stdout.strip()}")
            return True
        except subprocess.CalledProcessError as err2:
            print(f"  ❌ Error creating issue with gh: {err2.stderr.strip()}")
            return False
    except FileNotFoundError:
        return False


def create_issue_via_api(repo: str, token: str, title: str, labels: list[str], body: str) -> bool:
    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "ZeroDock-Issue-Seeder",
    }
    payload = json.dumps({"title": title, "body": body, "labels": labels}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"  ✅ Created issue #{data.get('number')}: {data.get('html_url')}")
            return True
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="replace")
        print(f"  ❌ GitHub API error ({e.code}): {err_msg}")
        return False
    except Exception as e:
        print(f"  ❌ Network error: {e}")
        return False


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    starter_dir = repo_root / ".github" / "starter-issues"

    if not starter_dir.exists():
        print(f"❌ Starter issues directory not found: {starter_dir}")
        sys.exit(1)

    issue_files = sorted(starter_dir.glob("*.md"))
    if not issue_files:
        print("❌ No starter issue markdown files found.")
        sys.exit(1)

    print(f"\n🚀 ZeroDock Issue Seeder — Found {len(issue_files)} pre-drafted starter issues\n")
    issues = [parse_issue_file(f) for f in issue_files]

    # Collect all unique labels
    all_labels = set()
    for issue in issues:
        all_labels.update(issue["labels"])

    # 1. Check if gh CLI is available
    has_gh = False
    try:
        check = subprocess.run(["gh", "--version"], capture_output=True, text=True)
        has_gh = check.returncode == 0
    except FileNotFoundError:
        has_gh = False

    if has_gh:
        print("🔑 GitHub CLI (`gh`) detected! Ensuring labels exist on repository...")
        ensure_gh_labels(all_labels)
        print("Publishing issues...\n")
        for issue in issues:
            print(f"Publishing: {issue['title']}...")
            create_issue_via_gh(issue["title"], issue["labels"], issue["body"])
        print("\n✨ All starter issues successfully processed!\n")
        return

    # 2. Check if GITHUB_TOKEN environment variable is set
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    repo = get_git_remote_repo() or "blackright/zerodock"

    if token:
        print(f"🔑 GITHUB_TOKEN detected! Publishing issues to {repo} via GitHub REST API...\n")
        for issue in issues:
            print(f"Publishing: {issue['title']}...")
            create_issue_via_api(repo, token, issue["title"], issue["labels"], issue["body"])
        print("\n✨ All starter issues successfully processed!\n")
        return

    # 3. Fallback preview & guidance
    print("ℹ️  Neither `gh` CLI nor `GITHUB_TOKEN` was detected.")
    print("📋 Preview of issues ready to publish:\n")
    for idx, issue in enumerate(issues, 1):
        print(f"  [{idx}] {issue['title']}")
        print(f"      Labels: {', '.join(issue['labels'])}")
        print(f"      File:   .github/starter-issues/{issue['file']}\n")

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("💡 TO PUBLISH AUTOMATICALLY:")
    print("   Option A (GitHub CLI):")
    print("     gh auth login")
    print("     python scripts/seed_github_issues.py\n")
    print("   Option B (Using GitHub Personal Access Token):")
    print('     $env:GITHUB_TOKEN="ghp_yourTokenHere"')
    print("     python scripts/seed_github_issues.py\n")
    print("   Option C (Manual / Web Browser):")
    print(f"     Visit: https://github.com/{repo}/issues/new/choose")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")


if __name__ == "__main__":
    main()
