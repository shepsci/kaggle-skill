#!/usr/bin/env python3
"""Extract a zip archive without letting any member leave the target folder.

    python3 shared/safe_extract.py data.zip ./data

Kaggle archives are untrusted input. Every member's resolved path is checked
before anything is written, and symlink members are refused (exit status 5).
"""

from __future__ import annotations

import os
import stat
import sys
import zipfile
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared import untrusted  # noqa: E402


class UnsafeArchiveError(ValueError):
    """A member would land outside the target folder, or is a symlink."""

    def __init__(self, reason: str, member: str):
        super().__init__(f"{reason}: {member!r}")
        self.reason = reason
        self.member = member


def safe_extract(archive: Path, dest: Path) -> list[str]:
    """Extract ``archive`` into ``dest``. Returns the member names written.

    Raises UnsafeArchiveError (a ValueError) if a member would resolve outside
    ``dest`` or is a symlink. Nothing is written in that case.
    """
    dest_real = os.path.realpath(dest)
    with zipfile.ZipFile(archive) as zf:
        members = zf.infolist()
        for info in members:
            target = os.path.realpath(os.path.join(dest_real, info.filename))
            if not (target == dest_real or target.startswith(dest_real + os.sep)):
                raise UnsafeArchiveError("member escapes the target folder", info.filename)
            if stat.S_ISLNK(info.external_attr >> 16):
                raise UnsafeArchiveError("member is a symlink", info.filename)
        os.makedirs(dest_real, exist_ok=True)
        zf.extractall(dest_real)
        return [info.filename for info in members]


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2 or args[0] in ("-h", "--help"):
        print("Usage: safe_extract.py <archive.zip> <dest-dir>")
        return 0 if args and args[0] in ("-h", "--help") else 2
    archive, dest = Path(args[0]), Path(args[1])
    try:
        names = safe_extract(archive, dest)
    except UnsafeArchiveError as exc:
        print(f"error: refusing to extract: {exc.reason}:", file=sys.stderr)
        # The member name is chosen by whoever built the archive.
        untrusted.emit_text(exc.member, source="local", tool="safe_extract", file=sys.stderr)
        return 5
    except (zipfile.BadZipFile, OSError) as exc:
        print(f"error: could not extract the archive ({type(exc).__name__})", file=sys.stderr)
        return 1
    print(f"extracted {len(names)} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
