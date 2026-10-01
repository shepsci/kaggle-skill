#!/usr/bin/env python3
"""Publish a model variation, or a new version of one, with kagglehub.

Usage:
    python3 kagglehub_publish.py <owner/model/framework/variation> <local-dir> \
        [version-notes] [license-name]

Creates the model and the variation if they do not exist (private), and adds
a version if they do. Everything in the folder is uploaded, so the folder is
checked for credential files first.

license-name is optional. When given it must be a name Kaggle lists for
models, such as "Apache 2.0" or "MIT".

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


def publish_model(
    handle: str,
    local_dir: str,
    version_notes: str = "Upload via kagglehub",
    license_name: str | None = None,
) -> None:
    """Upload ``local_dir`` as ``handle``. kagglehub returns nothing on success."""
    kagglehub = hub.load()
    kwargs: dict = {"version_notes": version_notes}
    if license_name:
        kwargs["license_name"] = license_name
    kagglehub.model_upload(handle=handle, local_model_dir=local_dir, **kwargs)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish or version a Kaggle model via kagglehub")
    parser.add_argument("handle", help="Model handle (owner/model/framework/variation)")
    parser.add_argument("local_dir", help="Local model directory")
    parser.add_argument("version_notes", nargs="?", default="Upload via kagglehub")
    parser.add_argument("license_name", nargs="?", default=None, help='Optional, e.g. "Apache 2.0"')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    status = preflight.check(Path(args.local_dir))
    if status:
        return status
    try:
        publish_model(args.handle, args.local_dir, args.version_notes, args.license_name)
    except Exception as exc:  # noqa: BLE001 - kagglehub raises many types; none should traceback
        return hub.fail("model_upload", exc)
    owner_model = "/".join(args.handle.split("/")[:2])
    print(f"Model uploaded: https://www.kaggle.com/models/{owner_model}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
