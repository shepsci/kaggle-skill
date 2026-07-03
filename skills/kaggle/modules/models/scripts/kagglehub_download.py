#!/usr/bin/env python3
"""Download models from Kaggle using kagglehub.

Usage:
    python kagglehub_download.py google/gemma/transformers/2b
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


def download_model(handle: str) -> str:
    """Download a model. Returns the local path."""
    kagglehub = _load_kagglehub()
    path = kagglehub.model_download(handle)
    print(f"Model downloaded to: {path}")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Download a Kaggle model via kagglehub")
    parser.add_argument("handle", help="Model handle (owner/model/framework/variation)")
    args = parser.parse_args()
    download_model(args.handle)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
