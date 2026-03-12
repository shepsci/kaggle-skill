#!/usr/bin/env python3
"""Unified Kaggle credential checker.

Checks all credential sources in priority order:
  1. ~/.kaggle/access_token file (new style, recommended)
  2. KAGGLE_API_TOKEN env var (new style)
  3. KAGGLE_USERNAME + KAGGLE_KEY env vars (legacy)
  4. ~/.kaggle/kaggle.json (legacy)

Also detects token type from prefix:
  - kagat_ → OAuth 2.0 access token (3-hour expiry)
  - kagrt_ → OAuth 2.0 refresh token
  - KGAT_  → Legacy scoped API token
  - Plain hex → Legacy API key

Returns structured JSON output for easy parsing.
Never prints actual credential values — only masked status.

Usage:
    python3 shared/check_all_credentials.py
    python3 shared/check_all_credentials.py --json

Exit codes:
    0 — Credentials found (at least API token or legacy key)
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
    pass


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


def _detect_token_type(token: str) -> str:
    """Detect the type of a Kaggle token from its prefix."""
    if not token:
        return "unknown"
    if token.startswith("kagat_"):
        return "OAuth access token"
    if token.startswith("kagrt_"):
        return "OAuth refresh token"
    if token.startswith("KGAT_"):
        return "Legacy scoped API token"
    # 32-char hex is a legacy API key
    if len(token) == 32 and all(c in "0123456789abcdef" for c in token):
        return "Legacy API key"
    return "API token"


def _mask(value: str, prefix_len: int = 0) -> str:
    """Mask a credential value, showing only first prefix_len and last 4 chars."""
    if not value:
        return "****"
    if len(value) <= prefix_len + 4:
        return "****"
    return value[:prefix_len] + "*" * max(0, len(value) - prefix_len - 4) + value[-4:]


def check_all_credentials(output_json: bool = False) -> bool:
    """Check for Kaggle credentials. Returns True if usable credentials found."""
    results = {}
    found_any = False

    # --- Auto-map KAGGLE_TOKEN → KAGGLE_KEY ---
    if os.getenv("KAGGLE_TOKEN") and not os.getenv("KAGGLE_KEY"):
        print("[WARN] Found KAGGLE_TOKEN but tools expect KAGGLE_KEY")
        print("       Auto-mapping: KAGGLE_KEY = KAGGLE_TOKEN")
        os.environ["KAGGLE_KEY"] = os.environ["KAGGLE_TOKEN"]

    # --- API Token (primary, recommended) ---
    # Check sources in priority order: access_token file → env var
    access_token_file = _read_access_token()
    api_token_env = os.getenv("KAGGLE_API_TOKEN", "")
    api_token = access_token_file or api_token_env

    if api_token:
        source = "~/.kaggle/access_token" if access_token_file else "env"
        token_type = _detect_token_type(api_token)
        results["KAGGLE_API_TOKEN"] = {
            "status": "OK", "value": _mask(api_token, 5),
            "source": source, "type": token_type,
        }
        print(f"[OK] API Token: {_mask(api_token, 5)} ({token_type}, from {source})")
        found_any = True
    else:
        results["KAGGLE_API_TOKEN"] = {"status": "MISSING", "value": None, "source": None}
        print("[MISSING] API Token")
        print("          Generate at: https://www.kaggle.com/settings")
        print("          → API Tokens (Recommended) → Generate New Token")
        print("          Save as ~/.kaggle/access_token or set KAGGLE_API_TOKEN env var")

    # --- Legacy credentials (optional) ---
    kaggle_json_data = _read_kaggle_json()

    # KAGGLE_USERNAME
    username = os.getenv("KAGGLE_USERNAME") or kaggle_json_data.get("username")
    if username:
        source = "env" if os.getenv("KAGGLE_USERNAME") else "kaggle.json"
        results["KAGGLE_USERNAME"] = {"status": "OK", "value": username, "source": source}
        print(f"[OK] KAGGLE_USERNAME: {username} (from {source})")
    else:
        results["KAGGLE_USERNAME"] = {"status": "MISSING", "value": None, "source": None}
        print("[INFO] KAGGLE_USERNAME not set (optional with API token)")

    # KAGGLE_KEY
    key = os.getenv("KAGGLE_KEY") or kaggle_json_data.get("key")
    if key:
        source = "env" if os.getenv("KAGGLE_KEY") else "kaggle.json"
        token_type = _detect_token_type(key)
        results["KAGGLE_KEY"] = {
            "status": "OK", "value": _mask(key),
            "source": source, "type": token_type,
        }
        print(f"[OK] KAGGLE_KEY: {_mask(key)} ({token_type}, from {source})")
        found_any = True
    else:
        results["KAGGLE_KEY"] = {"status": "MISSING", "value": None, "source": None}
        if not api_token:
            print("[MISSING] KAGGLE_KEY")
            print("          Legacy API key. Generate at: https://www.kaggle.com/settings")
            print("          → Legacy API Credentials → Create Legacy API Key")
        else:
            print("[INFO] KAGGLE_KEY not set (optional when API token is available)")

    # --- Summary ---
    print()
    if found_any:
        if api_token:
            print("API token found — you're ready to go!")
            print("(Supported by kaggle CLI >= 1.8.0, kagglehub >= 0.4.1, MCP Server)")
        else:
            print("Legacy credentials found. Consider upgrading to an API token:")
            print("  https://www.kaggle.com/settings → API Tokens → Generate New Token")
    else:
        print("No Kaggle credentials found. To set up:")
        print()
        print("  1. Go to https://www.kaggle.com/settings")
        print("  2. Under 'API Tokens (Recommended)', click 'Generate New Token'")
        print("  3. Copy the token and save it:")
        print()
        print("     # Option A: Save to file (recommended)")
        print("     mkdir -p ~/.kaggle")
        print("     echo 'YOUR_TOKEN' > ~/.kaggle/access_token")
        print("     chmod 600 ~/.kaggle/access_token")
        print()
        print("     # Option B: Set env var in .env")
        print("     KAGGLE_API_TOKEN=YOUR_TOKEN")
        print()
        print("  Full guide: modules/registration/references/kaggle-setup.md")

    if output_json:
        print()
        print("--- JSON ---")
        print(json.dumps(results, indent=2))

    return found_any


if __name__ == "__main__":
    json_mode = "--json" in sys.argv
    ok = check_all_credentials(output_json=json_mode)
    sys.exit(0 if ok else 1)
