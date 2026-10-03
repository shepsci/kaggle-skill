#!/usr/bin/env python3
"""Refuse to upload a folder that contains credential files.

The Kaggle CLI and kagglehub upload everything in the folder except a short
built-in ignore list (``.git``, ``.cache``, ``.huggingface``). A stray ``.env``
or ``kaggle.json`` would be published with the dataset or model. They follow
links too, so a link to a file or folder outside the upload folder is refused
as well: ``notes.txt`` can point at ``~/.kaggle/kaggle.json``.

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


def looks_secret(name: str) -> bool:
    """True when a file name looks like a credential file."""
    return name not in ALLOWED and any(fnmatch.fnmatch(name, p) for p in SECRET_PATTERNS)


def links_outside(path: Path, folder: Path) -> bool:
    """True when ``path`` is a link whose target is not inside ``folder``."""
    if not path.is_symlink():
        return False
    try:
        target, base = path.resolve(), folder.resolve()
    except (OSError, RuntimeError):
        return True
    return target != base and base not in target.parents


def find_secret_files(folder: Path) -> list[str]:
    """Relative paths under ``folder`` that look like credential files or link outside it."""
    found: list[str] = []
    for root, dirs, files in os.walk(folder):
        at_top = Path(root) == folder
        dirs[:] = [
            d for d in dirs if d not in SKIPPED_ANYWHERE and not (at_top and d in SKIPPED_AT_TOP)
        ]
        for name in [*dirs, *files]:
            path = Path(root) / name
            relative = str(path.relative_to(folder))
            if links_outside(path, folder):
                found.append(f"{relative} (a link to something outside the folder)")
            elif name in files and looks_secret(name):
                found.append(relative)
    return sorted(found)


def folder_facts(folder: Path) -> tuple[int, int]:
    """How many files an upload of ``folder`` would send, and their total size."""
    count = size = 0
    for root, dirs, files in os.walk(folder):
        at_top = Path(root) == folder
        dirs[:] = [
            d for d in dirs if d not in SKIPPED_ANYWHERE and not (at_top and d in SKIPPED_AT_TOP)
        ]
        for name in files:
            try:
                size += (Path(root) / name).stat().st_size
            except OSError:
                continue
            count += 1
    return count, size


def _amount(size: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1000 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1000
    return ""


def size_text(path: Path) -> str:
    """``3.4 MB``: the size of one file."""
    try:
        return _amount(path.stat().st_size)
    except OSError:
        return "size unknown"


def describe(folder: Path) -> str:
    """``./data (12 files, 3.4 MB)`` for a dry run."""
    count, size = folder_facts(folder)
    return f"{folder} ({count} files, {_amount(size)})"


def check(folder: Path) -> int:
    if not folder.is_dir():
        print("error: the upload folder is not a directory", file=sys.stderr)
        return 2
    found = find_secret_files(folder)
    if not found:
        return 0
    allowed = os.environ.get(OVERRIDE_VAR) == "1"
    if allowed:
        print("warning: uploading despite credential-like files or links:", file=sys.stderr)
    else:
        print(
            "error: refusing to upload; these look like credential files or link outside "
            "the folder:",
            file=sys.stderr,
        )
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
