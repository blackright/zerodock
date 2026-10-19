#!/usr/bin/env python3
"""
ZeroDock - Automated GitHub Issue Seeder
Reads pre-drafted starter issues from .github/starter-issues/ and publishes them to GitHub
using either the GitHub CLI (`gh issue create`) or the GitHub REST API.
"""

import os
import re
import subprocess
import sys
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

    for i, line in enumerate(lines):
        if line.startswith("# ") and not title:
            title = line.lstrip("# ").strip()
        elif line.startswith("**Labels**:") and not labels:
            # Extract labels from backticks or comma-separated list
            raw_labels = line.split(":", 1)[1]
            extracted = re.findall(r"`([^`]+)`", raw_labels)
            if not extracted:
                extracted = [lbl.strip() for lbl in raw_labels.split(",") if lbl.strip()]
            labels = extracted
        else:
            body_lines.append(line)

    body = "\n".join(body_lines).strip()
    return {"title": title, "labels": labels, "body": body, "file": file_path.name}


def create_issue_via_gh(title: str, labels: list[str], body: str) -> bool:
    cmd = ["gh", "issue", "create", "--title", title, "--body", body]
    for label in labels:
        cmd.extend(["--label", label])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"  ✅ Created issue: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Error creating issue with gh: {e.stderr.strip()}")
        return False
    except FileNotFoundError:
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

    print(f"\n🚀 ZeroDock Issue Seeder — Found {len(issue_files)} pre-drafted issues\n")

    # Check if gh CLI is available
    has_gh = False
    try:
        check = subprocess.run(["gh", "--version"], capture_output=True, text=True)
        has_gh = check.returncode == 0
    except FileNotFoundError:
        has_gh = False

    issues = [parse_issue_file(f) for f in issue_files]

    if not has_gh:
        print("ℹ️  GitHub CLI (`gh`) was not detected on system PATH.")
        print("📋 Preview of issues ready to publish:\n")
        for idx, issue in enumerate(issues, 1):
            print(f"  [{idx}] {issue['title']}")
            print(f"      Labels: {', '.join(issue['labels'])}")
            print(f"      Source: .github/starter-issues/{issue['file']}\n")
        print("💡 When you have installed and authenticated with `gh auth login`, rerun this script to post them automatically!")
        return

    print("🔑 GitHub CLI detected. Publishing issues to current repository...\n")
    for issue in issues:
        print(f"Publishing: {issue['title']}...")
        create_issue_via_gh(issue["title"], issue["labels"], issue["body"])

    print("\n✨ All starter issues successfully processed!\n")


if __name__ == "__main__":
    main()
