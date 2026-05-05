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

import sys

import kagglehub


def publish_dataset(handle: str, local_dir: str, version_notes: str = "Upload via kagglehub"):
    """Publish a private dataset to Kaggle using kagglehub."""
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
    result = kagglehub.model_upload(
        handle=handle,
        local_model_dir=local_dir,
        version_notes=version_notes,
        license_name=license_name,
    )
    print(f"Model published: {result}")
    return result


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage:")
        print("  python kagglehub_publish.py dataset <handle> <local-dir> [version-notes]")
        print("  python kagglehub_publish.py model <handle> <local-dir> [version-notes] [license-name]")
        sys.exit(1)

    action = sys.argv[1]
    handle = sys.argv[2]
    local_dir = sys.argv[3]

    if action == "dataset":
        notes = sys.argv[4] if len(sys.argv) > 4 else "Upload via kagglehub"
        publish_dataset(handle, local_dir, notes)
    elif action == "model":
        notes = sys.argv[4] if len(sys.argv) > 4 else "Upload via kagglehub"
        license_name = sys.argv[5] if len(sys.argv) > 5 else "Apache-2.0"
        publish_model(handle, local_dir, notes, license_name)
    else:
        print(f"Unknown action: {action}")
        print("Use 'dataset' or 'model'")
        sys.exit(1)
