#!/usr/bin/env python3
"""Publish a dataset, or a new version of one, with kagglehub.

Usage:
    python3 kagglehub_publish.py <owner/dataset> <local-dir> [version-notes]

Creates the dataset if it does not exist (private), and adds a version if it
does. Everything in the folder is uploaded, so the folder is checked for
credential files first.

For models use modules/models/scripts/kagglehub_publish.py. Notebooks are
published with the kaggle CLI (`kaggle kernels push`).

Exit status: 0 uploaded, 1 the upload failed, 2 wrong arguments,
5 refused because the folder holds a credential file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))

from shared import hub, preflight  # noqa: E402


def publish_dataset(
    handle: str, local_dir: str, version_notes: str = "Upload via kagglehub"
) -> None:
    """Upload ``local_dir`` as ``handle``. kagglehub returns nothing on success."""
    kagglehub = hub.load()
    kagglehub.dataset_upload(
        handle=handle,
        local_dataset_dir=local_dir,
        version_notes=version_notes,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish or version a Kaggle dataset via kagglehub"
    )
    parser.add_argument("handle", help="Dataset handle (owner/name)")
    parser.add_argument("local_dir", help="Local dataset directory")
    parser.add_argument("version_notes", nargs="?", default="Upload via kagglehub")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    status = preflight.check(Path(args.local_dir))
    if status:
        return status
    try:
        publish_dataset(args.handle, args.local_dir, args.version_notes)
    except Exception as exc:  # noqa: BLE001 - kagglehub raises many types; none should traceback
        return hub.fail("dataset_upload", exc)
    print(f"Dataset uploaded: https://www.kaggle.com/datasets/{args.handle}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
