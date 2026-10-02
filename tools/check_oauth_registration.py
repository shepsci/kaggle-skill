#!/usr/bin/env python3
"""Compare Kaggle's OAuth client registration with what the bundled client ID relies on.

    python3 tools/check_oauth_registration.py --check     # exit 1 and list what differs
    python3 tools/check_oauth_registration.py --update    # record today's answer

Claude Code cannot finish signing in to the Kaggle MCP server when it registers
itself. Kaggle answers the registration with an empty `client_secret` and lists
no token-endpoint authentication methods; Claude Code then picks
`client_secret_basic` and stops, because the secret is empty. `.mcp.json`
therefore names the client ID that Kaggle gives to a client called
"Claude Code (kaggle)", and Claude Code skips the registration.

This check sends that same registration and reads the authorization-server
metadata. A difference means one of two things: Kaggle derives the client ID
another way, so the bundled ID may stop working, or Kaggle changed its answer,
so the bundled ID may no longer be needed. No credential is sent, and the
request is not tied to an account.
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "skills" / "kaggle"))

from shared import untrusted  # noqa: E402

SNAPSHOT = REPO_ROOT / "tests" / "fixtures" / "oauth_registration.json"
METADATA_URL = "https://www.kaggle.com/.well-known/oauth-authorization-server"
REGISTRATION_URL = "https://www.kaggle.com/api/v1/oauth2/register"
CLIENT_NAME = "Claude Code (kaggle)"

# What Claude Code sends when it registers a server named "kaggle".
REGISTRATION = {
    "client_name": CLIENT_NAME,
    "redirect_uris": ["http://localhost:3118/callback"],
    "grant_types": ["authorization_code", "refresh_token"],
    "response_types": ["code"],
    "token_endpoint_auth_method": "none",
}


def facts(registration: dict, metadata: dict) -> dict:
    """Reduce the two answers to what the bundled client ID depends on.

    A secret is recorded as ``absent``, ``empty`` or ``set``, never by value.
    """
    if "client_secret" not in registration:
        secret = "absent"  # noqa: S105 - a label, not a secret
    elif registration["client_secret"] == "":
        secret = "empty"  # noqa: S105 - a label, not a secret
    else:
        secret = "set"  # noqa: S105 - a label, not a secret
    return {
        "client_id": registration.get("client_id"),
        "client_secret": secret,
        "token_endpoint_auth_method": registration.get("token_endpoint_auth_method"),
        "registration_endpoint": metadata.get("registration_endpoint"),
        "token_endpoint_auth_methods_supported": metadata.get(
            "token_endpoint_auth_methods_supported"
        ),
    }


def diff(old: dict, new: dict) -> list[str]:
    """Human-readable differences between two sets of facts. Empty when they match."""
    return [
        f"{key}: was {json.dumps(old.get(key))}, now {json.dumps(new.get(key))}"
        for key in sorted(set(old) | set(new))
        if old.get(key) != new.get(key)
    ]


def _get_json(request: urllib.request.Request | str) -> dict:
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - fixed https URL
        return json.load(response)


def fetch_live() -> dict:
    metadata = _get_json(METADATA_URL)
    request = urllib.request.Request(  # noqa: S310 - fixed https URL
        REGISTRATION_URL,
        data=json.dumps(REGISTRATION).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    return facts(_get_json(request), metadata)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Compare; exit 1 on any difference")
    mode.add_argument("--update", action="store_true", help="Rewrite the snapshot")
    args = parser.parse_args(argv)

    try:
        live = fetch_live()
    except (OSError, ValueError) as exc:
        print(
            f"error: could not read Kaggle's OAuth endpoints ({type(exc).__name__})",
            file=sys.stderr,
        )
        return 2

    if args.update:
        SNAPSHOT.write_text(
            json.dumps(
                {
                    "checked": datetime.date.today().isoformat(),
                    "client_name": CLIENT_NAME,
                    "facts": live,
                },
                indent=1,
            )
            + "\n"
        )
        print(f"wrote {SNAPSHOT.relative_to(REPO_ROOT)}")
        return 0

    recorded = json.loads(SNAPSHOT.read_text())
    changes = diff(recorded["facts"], live)
    if not changes:
        print(f"Kaggle's OAuth registration matches the snapshot of {recorded['checked']}")
        return 0
    print(f"Kaggle's OAuth registration changed since {recorded['checked']}:")
    # The values come from Kaggle's server.
    untrusted.emit_text("\n".join(changes), source="kaggle-oauth", tool="register")
    print("Check that sign-in still works with the client ID in .mcp.json; see mcp-reference.md.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
