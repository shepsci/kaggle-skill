#!/usr/bin/env python3
"""Publish private datasets and models to Kaggle using kagglehub.

kagglehub supports:
  - dataset_upload() — create or version a private/public dataset
  - model_upload()   — create or version a private/public model

NOT supported:
  - Notebook publishing (use kaggle-cli `kernels push` instead)
  - Benchmark publishing (use Kaggle UI instead)

Usage:
    python scripts/kagglehub_publish.py dataset <handle> <local-dir> [version-notes]
    python scripts/kagglehub_publish.py model <handle> <local-dir> [version-notes] [license-name]
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


def publish_model(
    handle: str,
    local_dir: str,
    version_notes: str = "Upload via kagglehub",
    license_name: str = "Apache-2.0",
):
    """Publish a private model to Kaggle using kagglehub."""
    kagglehub = _load_kagglehub()
    result = kagglehub.model_upload(
        handle=handle,
        local_model_dir=local_dir,
        version_notes=version_notes,
        license_name=license_name,
    )
    print(f"Model published: {result}")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish to Kaggle via kagglehub")
    subparsers = parser.add_subparsers(dest="action", required=True)

    dataset = subparsers.add_parser("dataset", help="Publish or version a dataset")
    dataset.add_argument("handle", help="Dataset handle (owner/name)")
    dataset.add_argument("local_dir", help="Local dataset directory")
    dataset.add_argument("version_notes", nargs="?", default="Upload via kagglehub")

    model = subparsers.add_parser("model", help="Publish or version a model")
    model.add_argument("handle", help="Model handle (owner/name/framework/variation)")
    model.add_argument("local_dir", help="Local model directory")
    model.add_argument("version_notes", nargs="?", default="Upload via kagglehub")
    model.add_argument("license_name", nargs="?", default="Apache-2.0")

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.action == "dataset":
        publish_dataset(args.handle, args.local_dir, args.version_notes)
    else:
        publish_model(args.handle, args.local_dir, args.version_notes, args.license_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
