#!/usr/bin/env python3
"""Check that Kaggle credentials are configured and valid.

Checks (in priority order):
  1. ~/.kaggle/access_token file (new style, recommended)
  2. KAGGLE_API_TOKEN env var (new style)
  3. KAGGLE_USERNAME + KAGGLE_KEY env vars (legacy)
  4. KAGGLE_TOKEN env var (common misconfiguration — auto-maps to KAGGLE_KEY)
  5. .env file in current directory
  6. ~/.kaggle/kaggle.json (legacy)

If an API token is found but ~/.kaggle/access_token doesn't exist,
this script will create it so that kagglehub and kaggle-cli work.

If legacy credentials are found via env vars but ~/.kaggle/kaggle.json
is missing, this script will create it for CLI compatibility.

Usage:
    python scripts/check_credentials.py
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


def _ensure_access_token(token: str) -> None:
    """Create ~/.kaggle/access_token if it doesn't exist."""
    access_token = Path.home() / ".kaggle" / "access_token"
    if access_token.exists():
        return
    access_token.parent.mkdir(parents=True, exist_ok=True)
    access_token.write_text(token)
    access_token.chmod(0o600)
    print(f"[INFO] Created {access_token} (chmod 600)")


def _ensure_kaggle_json(username: str, key: str) -> None:
    """Create ~/.kaggle/kaggle.json if it doesn't exist."""
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    if kaggle_json.exists():
        return
    kaggle_json.parent.mkdir(parents=True, exist_ok=True)
    kaggle_json.write_text(json.dumps({"username": username, "key": key}))
    kaggle_json.chmod(0o600)
    print(f"[INFO] Created {kaggle_json} (chmod 600)")


def check_credentials() -> bool:
    """Check for valid Kaggle credentials. Returns True if found."""
    # 1. Check ~/.kaggle/access_token file (new style, recommended)
    access_token_file = Path.home() / ".kaggle" / "access_token"
    if access_token_file.exists():
        token = access_token_file.read_text().strip()
        if token:
            print(f"[OK] Credentials found via {access_token_file}")
            mode = oct(access_token_file.stat().st_mode)[-3:]
            if mode != "600":
                print(f"[WARN] File permissions are {mode}, should be 600")
                print(f"       Run: chmod 600 {access_token_file}")
            return True

    # 2. Check new-style KAGGLE_API_TOKEN env var
    api_token = os.getenv("KAGGLE_API_TOKEN")
    if api_token:
        print("[OK] Credentials found via KAGGLE_API_TOKEN environment variable")
        _ensure_access_token(api_token)
        return True

    # 3. Check legacy KAGGLE_USERNAME + KAGGLE_KEY env vars
    username = os.getenv("KAGGLE_USERNAME")
    key = os.getenv("KAGGLE_KEY")
    if username and key:
        print(f"[OK] Credentials found via KAGGLE_USERNAME + KAGGLE_KEY (user: {username})")
        _ensure_kaggle_json(username, key)
        return True

    # 4. Check for common misconfiguration: KAGGLE_TOKEN instead of KAGGLE_KEY
    token = os.getenv("KAGGLE_TOKEN")
    if token and username:
        print(f"[WARN] Found KAGGLE_TOKEN but tools expect KAGGLE_KEY or KAGGLE_API_TOKEN")
        print(f"       Auto-mapping: KAGGLE_KEY=KAGGLE_TOKEN, KAGGLE_API_TOKEN=KAGGLE_TOKEN")
        os.environ["KAGGLE_KEY"] = token
        os.environ["KAGGLE_API_TOKEN"] = token
        _ensure_kaggle_json(username, token)
        _ensure_access_token(token)
        print(f"[OK] Credentials configured (user: {username})")
        return True
    elif token and not username:
        print(f"[WARN] Found KAGGLE_TOKEN but KAGGLE_USERNAME is not set")
        print(f"       Set KAGGLE_USERNAME to use token-based auth")

    # 5. Check ~/.kaggle/kaggle.json (legacy)
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    if kaggle_json.exists():
        try:
            creds = json.loads(kaggle_json.read_text())
            if "username" in creds and "key" in creds:
                print(f"[OK] Credentials found in {kaggle_json} (user: {creds['username']})")

                mode = oct(kaggle_json.stat().st_mode)[-3:]
                if mode != "600":
                    print(f"[WARN] File permissions are {mode}, should be 600")
                    print(f"       Run: chmod 600 {kaggle_json}")

                return True
        except (json.JSONDecodeError, KeyError):
            print(f"[ERROR] {kaggle_json} exists but is malformed")
            return False

    print("[ERROR] No Kaggle credentials found.")
    print()
    print("To fix, do ONE of the following:")
    print()
    print("  Option 1 (recommended): Generate an API token")
    print("    1. Go to https://www.kaggle.com/settings")
    print("    2. Under 'API Tokens (Recommended)', click 'Generate New Token'")
    print("    3. Save it:")
    print("       mkdir -p ~/.kaggle")
    print("       echo 'YOUR_TOKEN' > ~/.kaggle/access_token")
    print("       chmod 600 ~/.kaggle/access_token")
    print()
    print("  Option 2: Set KAGGLE_API_TOKEN env var")
    print('    export KAGGLE_API_TOKEN="your_api_token"')
    print()
    print("  Option 3 (legacy): Set username + key env vars")
    print('    export KAGGLE_USERNAME="your_username"')
    print('    export KAGGLE_KEY="your_api_key"')
    print()
    print("  Option 4 (legacy): Create kaggle.json")
    print("    mkdir -p ~/.kaggle")
    print('    echo \'{"username":"your_username","key":"your_api_key"}\' > ~/.kaggle/kaggle.json')
    print("    chmod 600 ~/.kaggle/kaggle.json")
    return False


if __name__ == "__main__":
    ok = check_credentials()
    sys.exit(0 if ok else 1)
