"""Shared utilities for Kaggle competition report generation."""

from __future__ import annotations

import contextlib
import io
import sys
import time
from pathlib import Path
from typing import Any

# Rate limiting: seconds between API calls
API_DELAY = 3

# Skill root: skills/kaggle
SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))

from shared import credentials, kaggle_cli  # noqa: E402

_MISSING = object()


class KaggleAuthError(RuntimeError):
    """No credential the Kaggle library accepts was found."""


def get_api():
    """Initialize and authenticate the Kaggle API client.

    Raises KaggleAuthError instead of letting the library print its help text
    and exit the process, or fail with a traceback when Kaggle cannot be
    reached.
    """
    credentials.load_configured_env_file()
    kaggle_cli.scrub_process_env()
    captured = io.StringIO()
    try:
        with contextlib.redirect_stdout(captured):
            from kaggle.api.kaggle_api_extended import KaggleApi

            api = KaggleApi()
            api.authenticate()
    except SystemExit as exc:
        raise KaggleAuthError(
            "no usable Kaggle credentials: run `kaggle auth login`, set KAGGLE_API_TOKEN, "
            "or create ~/.kaggle/access_token"
        ) from exc
    except Exception as exc:  # noqa: BLE001 - sign-in talks to the network and can fail many ways
        raise KaggleAuthError(
            f"could not sign in to Kaggle ({type(exc).__name__}); check the network and the "
            "credential with check_all_credentials.py --verify"
        ) from exc
    return api


def call_quiet(fn, *args: Any, **kwargs: Any):
    """Call a Kaggle library method and swallow what it prints.

    Several list methods print ``Next Page Token = ...`` to stdout, which would
    otherwise end up in front of this skill's JSON output.
    """
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kwargs)


def attr(obj: Any, *names: str, default: Any = None) -> Any:
    """First attribute among ``names`` that exists and is not None.

    kagglesdk objects use snake_case (``team_count``). Older releases exposed
    camelCase (``teamCount``), so callers pass both spellings.
    """
    for name in names:
        value = getattr(obj, name, _MISSING)
        if value is not _MISSING and value is not None:
            return value
    return default


def get_username() -> str:
    """Kaggle username from the shared credential resolver."""
    return credentials.username()


def check_credentials() -> bool:
    """Verify that the Kaggle CLI can authenticate with what is configured."""
    ok, username = credentials.verify()
    if ok:
        print(
            f"OK: Kaggle API authenticated as '{username}'"
            if username
            else "OK: Kaggle API authenticated"
        )
        return True
    print("ERROR: no usable Kaggle credentials.")
    print("  Run `kaggle auth login`, set KAGGLE_API_TOKEN, or create ~/.kaggle/access_token")
    return False


def unwrap_response(result, attr_name: str = "competitions") -> list:
    """Unwrap a Kaggle API response object to get the inner list.

    The newer kagglesdk returns response objects (e.g. ApiListCompetitionsResponse)
    with the actual data in a named attribute (e.g. .competitions). Older versions
    returned plain lists. This handles both.
    """
    if isinstance(result, list):
        return result
    if hasattr(result, attr_name):
        return getattr(result, attr_name) or []
    # Try common attributes
    for fallback in ["competitions", "files", "kernels", "results"]:
        if hasattr(result, fallback):
            return getattr(result, fallback) or []
    # Last resort: try to iterate
    try:
        return list(result)
    except TypeError:
        return []


def rate_limit():
    """Sleep for API_DELAY seconds to avoid throttling."""
    time.sleep(API_DELAY)


if __name__ == "__main__":
    sys.exit(0 if check_credentials() else 1)
