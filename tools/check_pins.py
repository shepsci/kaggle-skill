#!/usr/bin/env python3
"""Report when a Kaggle package on PyPI is newer than the version this skill was checked with.

    python3 tools/check_pins.py --check     # exit 1 if any package has a newer release
    python3 tools/check_pins.py --update    # record today's latest versions as checked

The versions the docs, snapshots and tests were last verified against live in
tests/fixtures/upstream_versions.json. A newer release does not mean something
is broken; it means the references should be looked at again.
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VERSIONS = REPO_ROOT / "tests" / "fixtures" / "upstream_versions.json"
PACKAGES = ("kaggle", "kagglehub", "kagglesdk", "kaggle-benchmarks")


def latest_version(package: str) -> str:
    url = f"https://pypi.org/pypi/{package}/json"
    with urllib.request.urlopen(url, timeout=30) as response:  # noqa: S310 - fixed https URL
        return json.load(response)["info"]["version"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--update", action="store_true")
    args = parser.parse_args(argv)

    try:
        latest = {package: latest_version(package) for package in PACKAGES}
    except OSError as exc:
        print(f"error: could not reach PyPI: {exc}", file=sys.stderr)
        return 2

    if args.update:
        VERSIONS.write_text(
            json.dumps(
                {
                    "checked": datetime.date.today().isoformat(),
                    "packages": latest,
                },
                indent=1,
            )
            + "\n"
        )
        print(f"wrote {VERSIONS.relative_to(REPO_ROOT)}: {latest}")
        return 0

    recorded = json.loads(VERSIONS.read_text())
    changed = [
        f"{package}: checked with {recorded['packages'].get(package)}, PyPI now has {version}"
        for package, version in latest.items()
        if recorded["packages"].get(package) != version
    ]
    if not changed:
        print(f"no new releases since {recorded['checked']}: {latest}")
        return 0
    print(f"new releases since {recorded['checked']}:")
    print("\n".join(changed))
    return 1


if __name__ == "__main__":
    sys.exit(main())
