#!/usr/bin/env python3
"""Fail when the skill changed since the last release tag but the version did not.

    python3 tools/check_release.py

Claude Code keeps serving a plugin's cached copy until its version string
changes, so a change under skills/ that ships with the old version never
reaches installed users. Exit status 0 means the version is fine, 1 means it
must be raised.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SHIPPED_PATHS = ("skills", ".mcp.json", ".claude-plugin", ".codex-plugin", "plugin.json")


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def main() -> int:
    version = json.loads((REPO_ROOT / ".claude-plugin" / "plugin.json").read_text())["version"]
    tag = _git("describe", "--tags", "--abbrev=0", "--match", "v[0-9]*")
    if not tag:
        print("no release tag found; nothing to compare")
        return 0
    changed = _git("diff", "--name-only", f"{tag}..HEAD", "--", *SHIPPED_PATHS).splitlines()
    if not changed:
        print(f"nothing shipped has changed since {tag}")
        return 0
    if version == tag.removeprefix("v"):
        print(
            f"error: {len(changed)} shipped file(s) changed since {tag}, "
            f"but the version is still {version}",
            file=sys.stderr,
        )
        for name in changed[:20]:
            print(f"  {name}", file=sys.stderr)
        print("Raise the version in every manifest and add a CHANGELOG entry.", file=sys.stderr)
        return 1
    print(f"version {version} differs from {tag}; {len(changed)} shipped file(s) changed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
