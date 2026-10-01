#!/usr/bin/env python3
"""Report which Kaggle credentials are configured.

Looks in the same places, in the same order, as the Kaggle CLI:

  1. API token   KAGGLE_API_TOKEN, then ~/.kaggle/access_token
  2. Legacy key  KAGGLE_USERNAME + KAGGLE_KEY, then kaggle.json
  3. OAuth       ~/.kaggle/credentials.json, written by `kaggle auth login`

The script only reads. It never writes, moves or prints a credential.

Usage:
    python3 modules/setup/scripts/check_all_credentials.py
    python3 modules/setup/scripts/check_all_credentials.py --verify
    python3 modules/setup/scripts/check_all_credentials.py --json

Finding a credential does not prove the server accepts it. --verify makes one
call that needs a signed-in account (`kaggle quota`) and reports the account.

Exit codes:
    0  a credential was found (and accepted, with --verify)
    1  no credential was found, or --verify failed
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))

from shared import credentials  # noqa: E402

LABELS = {
    "api_token": "API token",
    "legacy_key": "Legacy API key",
    "oauth": "OAuth login",
}
SETUP_HELP = """No Kaggle credentials found. Pick one:

  1. Sign in with OAuth (recommended by the Kaggle CLI):
       kaggle auth login

  2. Use an API token from https://www.kaggle.com/settings ("Generate New Token"):
       mkdir -p ~/.kaggle && chmod 700 ~/.kaggle
       (umask 077 && cat > ~/.kaggle/access_token)   # paste the token, then Ctrl-D
     or export KAGGLE_API_TOKEN in your shell profile.

Public reads (competition pages, public datasets) work without credentials.
Full guide: modules/setup/references/kaggle-setup.md"""


def _loose_permissions(path: Path) -> str | None:
    """Return the file mode as text when group or others can read it."""
    try:
        mode = path.stat().st_mode & 0o777
    except OSError:
        return None
    return oct(mode)[-3:] if mode & 0o077 else None


def _credential_files() -> list[Path]:
    home = Path.home() / ".kaggle"
    return [
        home / "access_token",
        home / "access_token.txt",
        home / "credentials.json",
        credentials.config_dir() / "kaggle.json",
    ]


def collect(verify: bool = False) -> dict:
    """Gather the report as plain data. No secret values are included."""
    found = credentials.discover()
    report: dict = {
        "credentials": [
            {
                "kind": cred.kind,
                "label": LABELS[cred.kind],
                "source": cred.source,
                "username": cred.username or None,
                "token_type": credentials.describe_token(cred.secret) if cred.secret else None,
            }
            for cred in found
        ],
        "active": None,
        "warnings": [],
        "verified": None,
        "username": None,
    }
    if found:
        report["active"] = {"kind": found[0].kind, "source": found[0].source}

    for path in _credential_files():
        mode = _loose_permissions(path)
        if mode:
            report["warnings"].append(
                f"{path} is readable by other users (mode {mode}); run: chmod 600 {path}"
            )
    if os.environ.get("KAGGLE_TOKEN") and not os.environ.get("KAGGLE_API_TOKEN"):
        report["warnings"].append(
            "KAGGLE_TOKEN is set, but no Kaggle tool reads it; use KAGGLE_API_TOKEN"
        )

    if verify:
        ok, username = credentials.verify()
        report["verified"] = ok
        report["username"] = username or None
    return report


def print_report(report: dict) -> None:
    creds = report["credentials"]
    for cred in creds:
        details = [f"from {cred['source']}"]
        if cred["kind"] == "api_token" and cred["token_type"] not in (None, "token", "API token"):
            details.append(f"looks like: {cred['token_type']}")
        if cred["username"]:
            details.append(f"user: {cred['username']}")
        print(f"[OK] {cred['label']}: found ({', '.join(details)})")
    for warning in report["warnings"]:
        print(f"[WARN] {warning}")

    print()
    if not creds:
        print(SETUP_HELP)
        return

    active = report["active"]
    print(f"The Kaggle CLI will try the {LABELS[active['kind']]} from {active['source']} first.")
    if report["verified"] is True:
        who = f" as {report['username']}" if report["username"] else ""
        print(f"[OK] Verified: Kaggle accepted the credential{who}.")
    elif report["verified"] is False:
        print("[FAIL] Kaggle did not accept what is configured.")
        print("       The credential may be revoked or expired, or the Kaggle CLI is missing")
        print("       or older than 2.2.4.")
    else:
        print("Found is not the same as accepted: run again with --verify to check.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report which Kaggle credentials are configured.")
    parser.add_argument("--json", action="store_true", help="Print the report as JSON only")
    parser.add_argument(
        "--verify", action="store_true", help="Ask the Kaggle CLI to authenticate with the server"
    )
    args = parser.parse_args(argv)

    credentials.load_configured_env_file()
    report = collect(verify=args.verify)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)

    if not report["credentials"]:
        return 1
    if args.verify and not report["verified"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
