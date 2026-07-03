#!/usr/bin/env python3
"""Publish private datasets to Kaggle using kagglehub.

kagglehub supports:
  - dataset_upload() — create or version a private/public dataset

NOT supported:
  - Model publishing (use modules/models/scripts/kagglehub_publish.py)
  - Notebook publishing (use kaggle-cli `kernels push` instead)
  - Benchmark publishing (use Kaggle UI instead)

Usage:
    python scripts/kagglehub_publish.py <handle> <local-dir> [version-notes]
"""

import argparse


def _load_kagglehub():
    try:
        import kagglehub  # type: ignore
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "error: kagglehub is required for publishing. "
            "Install dependencies with `python3 -m pip install kagglehub`."
        ) from exc
    return kagglehub


def publish_dataset(handle: str, local_dir: str, version_notes: str = "Upload via kagglehub"):
    """Publish a private dataset to Kaggle using kagglehub."""
    kagglehub = _load_kagglehub()
    result = kagglehub.dataset_upload(
        handle=handle,
        local_dataset_dir=local_dir,
        version_notes=version_notes,
    )
    print(f"Dataset published: {result}")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish or version a Kaggle dataset via kagglehub")
    parser.add_argument("handle", help="Dataset handle (owner/name)")
    parser.add_argument("local_dir", help="Local dataset directory")
    parser.add_argument("version_notes", nargs="?", default="Upload via kagglehub")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    publish_dataset(args.handle, args.local_dir, args.version_notes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
