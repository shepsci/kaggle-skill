#!/usr/bin/env python3
"""Save a Kaggle credential from the environment into ~/.kaggle. A dry run unless --yes.

    save_credentials.py          dry run: what would be written
    save_credentials.py --yes    write it

The Kaggle CLI and kagglehub read ~/.kaggle in every shell, so a credential
saved there keeps working after the environment variable is gone.

    KAGGLE_API_TOKEN               ->  ~/.kaggle/access_token
    KAGGLE_USERNAME + KAGGLE_KEY   ->  ~/.kaggle/kaggle.json   (legacy)

A file that already exists is never overwritten, the files are created
readable by you alone (mode 600), and the value is never printed. Run it only
when the user wants the credential stored on disk.

The only .env file read is the one named by KAGGLE_ENV_FILE, and only its
credential lines are used.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))

from shared import credentials, script  # noqa: E402


def plan() -> tuple[Path, str, str] | str:
    """What would be saved: ``(file, content, where it comes from)``, or why nothing would."""
    folder = Path.home() / ".kaggle"
    token_file = folder / "access_token"
    key_file = folder / "kaggle.json"
    token = os.environ.get("KAGGLE_API_TOKEN", "").strip()
    username = os.environ.get("KAGGLE_USERNAME", "").strip()
    key = os.environ.get("KAGGLE_KEY", "").strip()

    if token_file.exists():
        return f"{token_file} already exists; it is left unchanged"
    if token:
        try:
            names_a_file = Path(token).is_file()
        except OSError:
            names_a_file = False
        if names_a_file:
            return "KAGGLE_API_TOKEN names a token file; there is nothing to save"
        return token_file, token, "KAGGLE_API_TOKEN"
    if key_file.exists():
        return f"{key_file} already exists; it is left unchanged"
    if username and key:
        content = json.dumps({"username": username, "key": key}) + "\n"
        return key_file, content, "KAGGLE_USERNAME and KAGGLE_KEY"
    if (folder / "credentials.json").exists():
        return "an OAuth login is saved already (kaggle auth login); there is nothing to save"
    return (
        "no credential in the environment. Sign in with `kaggle auth login`, or create a "
        "token at https://www.kaggle.com/settings and set KAGGLE_API_TOKEN"
    )


def write_private(path: Path, content: str) -> None:
    """Create ``path`` with mode 600. Fails if it exists."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(content)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Save a Kaggle credential from the environment into ~/.kaggle. A dry run "
        "unless --yes.",
        epilog="Never overwrites a file and never prints the value.",
    )
    script.add_yes(parser)
    args = parser.parse_args(argv)

    credentials.load_configured_env_file()
    planned = plan()
    if isinstance(planned, str):
        print(f"Nothing to do: {planned}.")
        return script.EXIT_OK
    path, content, origin = planned
    gate = script.write_gate(
        args.yes,
        action="store a credential on this computer",
        details=[("from", origin), ("to", f"{path} (mode 600)")],
        target="disk",
    )
    if gate is not None:
        return gate
    try:
        write_private(path, content)
    except FileExistsError:
        return script.fail(f"{path} appeared in the meantime; it was left unchanged")
    except OSError as exc:
        return script.fail(f"could not write {path} ({type(exc).__name__})")
    print(f"Saved the credential from {origin} to {path}.")
    return script.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
