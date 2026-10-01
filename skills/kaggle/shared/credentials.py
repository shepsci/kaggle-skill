"""Find Kaggle credentials the way the Kaggle CLI does.

One resolver for every script, so a checker and the tool it checks never
disagree. The order mirrors ``kaggle`` 2.2.x and ``kagglesdk``:

1. API token: ``KAGGLE_API_TOKEN`` (the token itself, or a path to a file that
   holds it), then ``~/.kaggle/access_token``, then ``~/.kaggle/access_token.txt``.
2. Legacy key: ``KAGGLE_USERNAME`` + ``KAGGLE_KEY``, then ``kaggle.json`` in
   ``KAGGLE_CONFIG_DIR`` or ``~/.kaggle``.
3. OAuth: ``~/.kaggle/credentials.json``, written by ``kaggle auth login``.

Nothing here writes a credential or prints one.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared import kaggle_cli  # noqa: E402

ENV_FILE_VAR = "KAGGLE_ENV_FILE"
# The only variables taken from an env file. Anything else in it is ignored,
# including settings that redirect the CLI or switch on its request logging.
ENV_FILE_KEYS = frozenset(
    {
        "KAGGLE_API_TOKEN",
        "KAGGLE_USERNAME",
        "KAGGLE_KEY",
        "KAGGLE_CONFIG_DIR",
        "KAGGLE_MCP_TOKEN",
    }
)
_HEX32_RE = re.compile(r"^[0-9a-f]{32}$")
# A bearer token is one run of printable ASCII: no spaces, no line breaks.
_BEARER_RE = re.compile(r"^[\x21-\x7e]+$")


@dataclass(frozen=True)
class Credential:
    """One credential that was found. ``repr`` never includes the secret."""

    kind: str  # "api_token" | "legacy_key" | "oauth"
    source: str  # where it was found, never the value
    username: str = ""
    secret: str = field(default="", repr=False)


def config_dir() -> Path:
    """Directory the CLI reads ``kaggle.json`` from."""
    override = os.environ.get("KAGGLE_CONFIG_DIR")
    if override:
        return Path(override)
    default = Path.home() / ".kaggle"
    if sys.platform.startswith("linux") and not default.exists():
        xdg = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
        return Path(xdg) / "kaggle"
    return default


def _read_token_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def api_token() -> Credential | None:
    """The API token, from the environment first and then the token file."""
    value = os.environ.get("KAGGLE_API_TOKEN", "").strip()
    if value:
        as_path = Path(value)
        try:
            is_file = as_path.is_file()
        except OSError:
            is_file = False
        if is_file:
            token = _read_token_file(as_path)
            if token:
                return Credential("api_token", "file named by KAGGLE_API_TOKEN", secret=token)
        else:
            return Credential("api_token", "KAGGLE_API_TOKEN", secret=value)
    for name in ("access_token", "access_token.txt"):
        path = Path.home() / ".kaggle" / name
        token = _read_token_file(path)
        if token:
            return Credential("api_token", f"~/.kaggle/{name}", secret=token)
    return None


def _read_kaggle_json() -> dict:
    path = config_dir() / "kaggle.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def legacy_key() -> Credential | None:
    """Legacy username + key, from the environment or ``kaggle.json``."""
    username = os.environ.get("KAGGLE_USERNAME", "").strip()
    key = os.environ.get("KAGGLE_KEY", "").strip()
    if username and key:
        return Credential("legacy_key", "KAGGLE_USERNAME + KAGGLE_KEY", username, key)
    data = _read_kaggle_json()
    username = str(data.get("username") or username)
    key = str(data.get("key") or key)
    if username and key:
        return Credential("legacy_key", "kaggle.json", username, key)
    return None


def oauth() -> Credential | None:
    """OAuth credentials saved by ``kaggle auth login``."""
    path = Path.home() / ".kaggle" / "credentials.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or not data.get("refresh_token"):
        return None
    return Credential("oauth", "~/.kaggle/credentials.json", str(data.get("username") or ""))


def discover() -> list[Credential]:
    """Every credential present, in the order the CLI would try them."""
    return [cred for cred in (api_token(), legacy_key(), oauth()) if cred is not None]


def resolve() -> Credential | None:
    """The credential the CLI would try first, or None."""
    found = discover()
    return found[0] if found else None


def usable_bearer(value: str) -> str:
    """``value`` when it can go into an HTTP header as it is, otherwise ``""``.

    A value with a space or a line break is not a token. Sending it would make
    the HTTP library raise an error whose text quotes the value.
    """
    return value if _BEARER_RE.match(value) else ""


def oauth_access_token() -> str:
    """The OAuth access token from ``kaggle auth print-access-token``, or ``""``.

    The CLI can print warnings on standard output before the token (an
    out-of-date notice, a file-permission warning), so only the last line is
    taken, and only when it looks like a token.
    """
    if oauth() is None:
        return ""
    result = kaggle_cli.run(["auth", "print-access-token"], timeout=60)
    if result.returncode != 0:
        return ""
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return usable_bearer(lines[-1]) if lines else ""


def bearer_token() -> str:
    """A bearer token for the MCP server, or ``""`` when there is none.

    ``KAGGLE_MCP_TOKEN`` overrides everything. Then, in order: the API token,
    the OAuth access token from ``kaggle auth print-access-token``, and last
    the legacy key. The legacy key comes last because the MCP server is
    documented for tokens; the key is kept only so older setups behave as
    before. A value that could not be sent as a header is skipped.
    """
    override = usable_bearer(os.environ.get("KAGGLE_MCP_TOKEN", "").strip())
    if override:
        return override
    token = api_token()
    if token is not None and usable_bearer(token.secret):
        return token.secret
    access = oauth_access_token()
    if access:
        return access
    legacy = legacy_key()
    return usable_bearer(legacy.secret) if legacy is not None else ""


def describe_token(value: str) -> str:
    """Name the token type from its shape, without revealing it."""
    if value.startswith("KGAT_"):
        return "API token"
    if value.startswith("KGRT_"):
        return "OAuth refresh token"
    if _HEX32_RE.match(value):
        return "legacy API key"
    return "token"


def username() -> str:
    """Kaggle username: environment, ``kaggle.json``, saved OAuth login, then the CLI."""
    name = os.environ.get("KAGGLE_USERNAME", "").strip()
    if name:
        return name
    name = str(_read_kaggle_json().get("username") or "")
    if name:
        return name
    cred = oauth()
    if cred and cred.username and api_token() is None:
        return cred.username
    ok, name = verify()
    return name if ok else ""


def verify() -> tuple[bool, str]:
    """Ask Kaggle whether the configured credential works. Returns ``(ok, username)``.

    Two CLI calls are needed. ``kaggle config view`` names the account, but
    for a legacy key or a saved OAuth login it does not contact the server, so
    a revoked key still passes it. ``kaggle quota`` needs a signed-in account
    and fails for a credential the server no longer accepts.
    """
    view = kaggle_cli.run(["config", "view"], timeout=60)
    if view.returncode != 0:
        return False, ""
    if kaggle_cli.run(["quota"], timeout=60).returncode != 0:
        return False, ""
    match = re.search(r"^- username: (\S+)", view.stdout, re.MULTILINE)
    return True, match.group(1) if match else ""


def load_env_file(path: Path) -> list[str]:
    """Load credential variables from one file without overriding the environment.

    Lines are ``KEY=value``; ``export`` prefixes and surrounding quotes are
    accepted. Only the names in ``ENV_FILE_KEYS`` are used. Returns the names
    that were set.
    """
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return []
    loaded: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key not in ENV_FILE_KEYS:
            continue
        if key not in os.environ:
            os.environ[key] = value
            loaded.append(key)
    return loaded


def load_configured_env_file() -> list[str]:
    """Load the file named by ``KAGGLE_ENV_FILE``, if that variable is set.

    This is the only ``.env`` file the skill reads. Nothing is searched for.
    """
    path = os.environ.get(ENV_FILE_VAR, "").strip()
    return load_env_file(Path(path).expanduser()) if path else []
