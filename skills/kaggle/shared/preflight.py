#!/usr/bin/env python3
"""Refuse to upload a folder that contains credential files.

The Kaggle CLI and kagglehub upload everything in the folder except a short
built-in ignore list (``.git``, ``.cache``, ``.huggingface``). A stray ``.env``
or ``kaggle.json`` would be published with the dataset, model or notebook.

    python3 shared/preflight.py ./data

Exit status 0 means nothing suspicious was found. Exit status 5 lists what
was. Set ``KAGGLE_PUBLISH_ALLOW_SECRETS=1`` to upload anyway.
"""

from __future__ import annotations

import fnmatch
import os
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared import untrusted  # noqa: E402

SECRET_PATTERNS = (
    ".env",
    ".env.*",
    "*.env",
    "kaggle.json",
    "access_token",
    "access_token.txt",
    "credentials.json",
    ".netrc",
    "id_rsa",
    "id_ed25519",
    "*.pem",
    "*.p12",
    "*.pfx",
)
ALLOWED = (".env.example", ".env.sample", ".env.template")
# What the uploaders leave out by themselves (kaggle 2.2.4 and kagglehub 1.0.2):
# `.git` at any depth, `.cache` and `.huggingface` only at the top of the folder.
SKIPPED_ANYWHERE = {".git"}
SKIPPED_AT_TOP = {".cache", ".huggingface"}
OVERRIDE_VAR = "KAGGLE_PUBLISH_ALLOW_SECRETS"
EXIT_REFUSED = 5


def find_secret_files(folder: Path) -> list[str]:
    """Relative paths under ``folder`` whose names look like credential files."""
    found: list[str] = []
    for root, dirs, files in os.walk(folder):
        at_top = Path(root) == folder
        dirs[:] = [
            d for d in dirs if d not in SKIPPED_ANYWHERE and not (at_top and d in SKIPPED_AT_TOP)
        ]
        for name in files:
            if name in ALLOWED:
                continue
            if any(fnmatch.fnmatch(name, pattern) for pattern in SECRET_PATTERNS):
                found.append(str((Path(root) / name).relative_to(folder)))
    return sorted(found)


def check(folder: Path) -> int:
    if not folder.is_dir():
        print("error: the upload folder is not a directory", file=sys.stderr)
        return 2
    found = find_secret_files(folder)
    if not found:
        return 0
    allowed = os.environ.get(OVERRIDE_VAR) == "1"
    if allowed:
        print("warning: uploading despite credential-like files:", file=sys.stderr)
    else:
        print("error: refusing to upload; these look like credential files:", file=sys.stderr)
    # File names can come from a Kaggle download that is being republished.
    untrusted.emit_text("\n".join(found), source="local", tool="preflight", file=sys.stderr)
    if allowed:
        return 0
    print(
        f"Remove them, or set {OVERRIDE_VAR}=1 if they are meant to be published.",
        file=sys.stderr,
    )
    return EXIT_REFUSED


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or args[0] in ("-h", "--help"):
        print("Usage: preflight.py <folder>")
        return 0 if args and args[0] in ("-h", "--help") else 2
    return check(Path(args[0]))


if __name__ == "__main__":
    sys.exit(main())
