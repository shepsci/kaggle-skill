#!/usr/bin/env python3
"""Download datasets from Kaggle using kagglehub.

Usage:
    python kagglehub_download.py                       # default example dataset
    python kagglehub_download.py heptapod/titanic
"""

import argparse


def _load_kagglehub():
    try:
        import kagglehub  # type: ignore
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "error: kagglehub is required for downloads. "
            "Install dependencies with `python3 -m pip install kagglehub`."
        ) from exc
    return kagglehub


def download_dataset(handle: str) -> str:
    """Download a dataset. Returns the local path."""
    kagglehub = _load_kagglehub()
    path = kagglehub.dataset_download(handle)
    print(f"Dataset downloaded to: {path}")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Download a Kaggle dataset via kagglehub")
    parser.add_argument("handle", nargs="?", default="heptapod/titanic", help="Dataset handle (owner/name)")
    args = parser.parse_args()
    download_dataset(args.handle)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
