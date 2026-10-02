#!/usr/bin/env python3
"""Build the plugin alone: the tree an install needs, without tests, tools or media.

    python3 tools/build_plugin.py <output-folder>

The repository root is the plugin root, so an install from it also carries the
test suite, the maintainer tools and the demo media: about 240 files where the
plugin needs about 100. This writes only what the plugin needs into
<output-folder>, which must be new or empty. Publishing that folder as a
branch gives marketplaces and the Claude directory a smaller thing to install
and to scan, with nothing moved on `main`.

Only files that git tracks are copied, so a leftover file in the checkout
never reaches the output.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Paths, relative to the repository root, that make up the plugin.
INCLUDED = (
    ".claude-plugin",
    ".codex-plugin",
    ".agents/plugins",
    ".mcp.json",
    "plugin.json",
    "assets/icon.png",
    "skills",
    "LICENSE",
    "PRIVACY.md",
    "SECURITY.md",
    "THIRD_PARTY_NOTICES.md",
    "CHANGELOG.md",
)
README = """# Kaggle (unofficial): plugin build

This tree is the plugin alone, built from
https://github.com/shepsci/kaggle-skill at version {version}. The source, the
tests and the documentation are on the `main` branch there.

It is an independent, unofficial project. It is not affiliated with, endorsed
by, or sponsored by Kaggle or Google.
"""


def tracked_files() -> list[str]:
    """Every tracked file under the included paths."""
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "-z", "--", *INCLUDED],
        capture_output=True,
        check=True,
    )
    return sorted(name for name in result.stdout.decode().split("\0") if name)


def build(target: Path) -> list[str]:
    """Copy the plugin into ``target`` and return the relative paths written."""
    if target.exists() and any(target.iterdir()):
        raise FileExistsError(f"{target} is not empty")
    files = tracked_files()
    for name in files:
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / name, destination)
    version = json.loads((REPO_ROOT / ".claude-plugin" / "plugin.json").read_text())["version"]
    (target / "README.md").write_text(README.format(version=version), encoding="utf-8")
    return [*files, "README.md"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("target", help="A new or empty folder to write the plugin into")
    args = parser.parse_args(argv)
    target = Path(args.target)
    try:
        files = build(target)
    except FileExistsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"error: could not build the plugin ({type(exc).__name__})", file=sys.stderr)
        return 1
    size = sum((target / name).stat().st_size for name in files)
    print(f"wrote {len(files)} files, {size / 1000:.0f} KB, to {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
