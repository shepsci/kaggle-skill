#!/usr/bin/env python3
"""Check that Kaggle credentials are configured.

Checks credential sources in priority order:
  1. ~/.kaggle/access_token file (new style, recommended)
  2. KAGGLE_API_TOKEN env var (new style)
  3. KAGGLE_USERNAME + KAGGLE_KEY env vars (legacy)
  4. ~/.kaggle/kaggle.json (legacy)

Usage:
    python3 scripts/check_registration.py

Exit codes:
    0 — Usable credentials found
    1 — No credentials found
"""

import json
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed; skip .env loading


def _read_access_token() -> str:
    """Read ~/.kaggle/access_token if it exists."""
    access_token = Path.home() / ".kaggle" / "access_token"
    if not access_token.exists():
        return ""
    token = access_token.read_text().strip()
    if token:
        mode = oct(access_token.stat().st_mode)[-3:]
        if mode != "600":
            print(f"[WARN] {access_token} permissions are {mode}, should be 600")
            print(f"       Run: chmod 600 {access_token}")
    return token


def _read_kaggle_json() -> dict:
    """Read ~/.kaggle/kaggle.json if it exists and is valid."""
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    if not kaggle_json.exists():
        return {}
    try:
        creds = json.loads(kaggle_json.read_text())
        mode = oct(kaggle_json.stat().st_mode)[-3:]
        if mode != "600":
            print(f"[WARN] {kaggle_json} permissions are {mode}, should be 600")
            print(f"       Run: chmod 600 {kaggle_json}")
        return creds
    except (json.JSONDecodeError, KeyError):
        print(f"[WARN] {kaggle_json} exists but is malformed")
        return {}


def _mask(value: str, prefix_len: int = 0) -> str:
    """Mask a credential value."""
    if not value or len(value) <= prefix_len + 4:
        return "****"
    return value[:prefix_len] + "*" * max(0, len(value) - prefix_len - 4) + value[-4:]


def check_registration() -> bool:
    """Check for Kaggle credentials. Returns True if usable credentials found."""
    found_any = False

    # --- Auto-map KAGGLE_TOKEN → KAGGLE_KEY ---
    if os.getenv("KAGGLE_TOKEN") and not os.getenv("KAGGLE_KEY"):
        print("[WARN] Found KAGGLE_TOKEN but tools expect KAGGLE_KEY")
        print("       Auto-mapping: KAGGLE_KEY = KAGGLE_TOKEN")
        os.environ["KAGGLE_KEY"] = os.environ["KAGGLE_TOKEN"]

    # --- API Token (primary) ---
    access_token_file = _read_access_token()
    api_token_env = os.getenv("KAGGLE_API_TOKEN", "")
    api_token = access_token_file or api_token_env

    if api_token:
        source = "~/.kaggle/access_token" if access_token_file else "env"
        print(f"[OK] API Token: {_mask(api_token, 5)} (from {source})")
        found_any = True
    else:
        print("[MISSING] API Token")
        print("          Generate at: https://www.kaggle.com/settings")
        print("          → API Tokens (Recommended) → Generate New Token")

    # --- Legacy credentials (optional) ---
    kaggle_json = _read_kaggle_json()

    username = os.getenv("KAGGLE_USERNAME") or kaggle_json.get("username")
    if username:
        source = "env" if os.getenv("KAGGLE_USERNAME") else "kaggle.json"
        print(f"[OK] KAGGLE_USERNAME: {username} (from {source})")
    else:
        print("[INFO] KAGGLE_USERNAME not set (optional with API token)")

    key = os.getenv("KAGGLE_KEY") or kaggle_json.get("key")
    if key:
        source = "env" if os.getenv("KAGGLE_KEY") else "kaggle.json"
        print(f"[OK] KAGGLE_KEY: {_mask(key)} (from {source})")
        found_any = True
    else:
        if not api_token:
            print("[MISSING] KAGGLE_KEY")
            print("          Legacy key. Generate at: https://www.kaggle.com/settings")
            print("          → Legacy API Credentials → Create Legacy API Key")
        else:
            print("[INFO] KAGGLE_KEY not set (optional when API token is available)")

    # --- Summary ---
    print()
    if found_any:
        if api_token:
            print("API token found — registration looks good!")
        else:
            print("Legacy credentials found. Consider upgrading to an API token:")
            print("  https://www.kaggle.com/settings → API Tokens → Generate New Token")
    else:
        print("No credentials found. Follow the setup guide:")
        print("  modules/registration/references/kaggle-setup.md")

    return found_any


if __name__ == "__main__":
    ok = check_registration()
    sys.exit(0 if ok else 1)
