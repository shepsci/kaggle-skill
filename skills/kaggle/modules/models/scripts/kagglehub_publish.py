#!/usr/bin/env python3
"""Publish private models to Kaggle using kagglehub.

Usage:
    python kagglehub_publish.py <handle> <local-dir> [version-notes] [license-name]
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
    parser = argparse.ArgumentParser(description="Publish or version a Kaggle model via kagglehub")
    parser.add_argument("handle", help="Model handle (owner/model/framework/variation)")
    parser.add_argument("local_dir", help="Local model directory")
    parser.add_argument("version_notes", nargs="?", default="Upload via kagglehub")
    parser.add_argument("license_name", nargs="?", default="Apache-2.0")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    publish_model(args.handle, args.local_dir, args.version_notes, args.license_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
