#!/usr/bin/env python3
"""Download a Kaggle model with kagglehub.

Usage:
    python3 kagglehub_download.py owner/model/framework/variation
    python3 kagglehub_download.py owner/model/framework/variation/3
    python3 kagglehub_download.py owner/model/framework/variation --output-dir ./model

The four-part handle downloads the latest version; add a number for a
specific one. Without --output-dir the files go to the kagglehub cache
(~/.cache/kagglehub), and the path is printed.

--output-dir must be a new or empty folder: kagglehub deletes what is in the
folder before it downloads again, so a folder with files in it is refused.

Exit status: 0 downloaded, 1 the download failed, 2 wrong arguments,
5 refused because --output-dir is not empty.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))

from shared import hub  # noqa: E402


def download_model(
    handle: str, path: str | None = None, output_dir: str | None = None, force: bool = False
) -> str:
    """Download a model, or one file of it. Returns the local path."""
    kagglehub = hub.load()
    kwargs: dict = {"force_download": force}
    if path:
        kwargs["path"] = path
    if output_dir:
        kwargs["output_dir"] = output_dir
    return kagglehub.model_download(handle, **kwargs)


def main() -> int:
    parser = argparse.ArgumentParser(description="Download a Kaggle model via kagglehub")
    parser.add_argument("handle", help="Model handle: owner/model/framework/variation[/version]")
    parser.add_argument("--path", help="Download only this file from the model")
    parser.add_argument(
        "--output-dir", help="Download into this new or empty folder instead of the cache"
    )
    parser.add_argument("--force", action="store_true", help="Download again even if cached")
    args = parser.parse_args()

    status = hub.check_output_dir(args.output_dir, args.path, args.force)
    if status:
        return status
    try:
        local_path = download_model(args.handle, args.path, args.output_dir, args.force)
    except Exception as exc:  # noqa: BLE001 - kagglehub raises many types; none should traceback
        return hub.fail("model_download", exc)
    print(f"Model downloaded to: {local_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
