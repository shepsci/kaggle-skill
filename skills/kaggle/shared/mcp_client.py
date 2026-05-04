"""Shared MCP JSON-RPC client for the Kaggle MCP server.

Used by both the integration test suite and the hackathon module scripts.
Single source of truth for SSE parsing, auth header construction, response
classification, and credential discovery.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

MCP_ENDPOINT = "https://www.kaggle.com/mcp"


def load_dotenv(*search_paths: Path) -> None:
    """Populate os.environ from .env files. Repo-root .env wins over $HOME/.env."""
    paths = list(search_paths) or [Path.cwd() / ".env", Path.home() / ".env"]
    for env_path in paths:
        if not env_path.exists():
            continue
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def get_kgat_token() -> str:
    """Return KGAT-prefixed token from env, or empty string if absent."""
    token = os.getenv("KAGGLE_MCP_TOKEN") or os.getenv("KAGGLE_API_TOKEN", "")
    return token if token.startswith("KGAT_") else ""


def get_legacy_key() -> str:
    """Return legacy 32-char hex key from env or ~/.kaggle/kaggle.json."""
    key = os.getenv("KAGGLE_KEY", "")
    if key and not key.startswith("KGAT_"):
        return key
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    if kaggle_json.exists():
        try:
            data = json.loads(kaggle_json.read_text())
            k = data.get("key", "")
            if k and not k.startswith("KGAT_"):
                return k
        except (json.JSONDecodeError, KeyError):
            pass
    return ""


def get_username() -> str:
    """Return Kaggle username from env or ~/.kaggle/kaggle.json."""
    u = os.getenv("KAGGLE_USERNAME", "")
    if u:
        return u
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    if kaggle_json.exists():
        try:
            return json.loads(kaggle_json.read_text()).get("username", "")
        except (json.JSONDecodeError, KeyError):
            pass
    return ""


def get_access_token() -> str:
    """Return token from ~/.kaggle/access_token if present."""
    p = Path.home() / ".kaggle" / "access_token"
    if p.exists():
        return p.read_text().strip()
    return ""


def resolve_token() -> str:
    """Pick the best available token: explicit MCP override → KGAT env → access_token file → legacy key."""
    return (
        os.getenv("KAGGLE_MCP_TOKEN")
        or get_kgat_token()
        or get_access_token()
        or get_legacy_key()
        or ""
    )


def mcp_call(
    tool: str,
    arguments: dict[str, Any],
    token: str,
    timeout: int = 30,
    endpoint: str = MCP_ENDPOINT,
) -> dict[str, Any]:
    """Call an MCP tool via JSON-RPC over HTTP. Returns parsed response.

    Handles both SSE-framed and raw JSON responses. On timeout/parse failure
    returns a structured error rather than raising.
    """
    payload = json.dumps({
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": tool, "arguments": arguments},
        "id": 1,
    })
    try:
        result = subprocess.run(
            [
                "curl", "-s", "-m", str(timeout),
                "-X", "POST", endpoint,
                "-H", "Content-Type: application/json",
                "-H", f"Authorization: Bearer {token}",
                "-d", payload,
            ],
            capture_output=True, text=True, timeout=timeout + 5,
        )
    except subprocess.TimeoutExpired:
        return {"error": {"message": "timeout"}}

    raw = result.stdout
    for line in raw.split("\n"):
        if line.startswith("data:"):
            try:
                return json.loads(line[5:].strip())
            except json.JSONDecodeError:
                pass
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        return {"raw": raw[:300]}


def mcp_list_tools(token: str, timeout: int = 30, endpoint: str = MCP_ENDPOINT) -> dict[str, Any]:
    """Call tools/list and return the parsed response."""
    payload = json.dumps({"jsonrpc": "2.0", "method": "tools/list", "id": 1})
    try:
        result = subprocess.run(
            [
                "curl", "-s", "-m", str(timeout),
                "-X", "POST", endpoint,
                "-H", "Content-Type: application/json",
                "-H", f"Authorization: Bearer {token}",
                "-d", payload,
            ],
            capture_output=True, text=True, timeout=timeout + 5,
        )
    except subprocess.TimeoutExpired:
        return {"error": {"message": "timeout"}}

    raw = result.stdout
    for line in raw.split("\n"):
        if line.startswith("data:"):
            try:
                return json.loads(line[5:].strip())
            except json.JSONDecodeError:
                pass
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        return {"raw": raw[:300]}


def classify_result(resp: dict[str, Any]) -> str:
    """Classify MCP response: ok | empty | unauthenticated | error:<msg> | parse_fail."""
    if "raw" in resp:
        return "parse_fail"
    error = resp.get("error", {})
    if error:
        return f"error: {error.get('message', 'unknown')[:80]}"
    result = resp.get("result", {})
    content = result.get("content", [])
    if isinstance(content, str):
        if "unauthenticated" in content.lower():
            return "unauthenticated"
        return "ok"
    if isinstance(content, list):
        for c in content:
            if not isinstance(c, dict):
                continue
            text = c.get("text", "")
            tl = text.lower()
            if "unauthenticated" in tl:
                return "unauthenticated"
            if tl.startswith("error") or '"error"' in tl or "server error" in tl:
                return f"error: {text[:100]}"
    if result and result != {}:
        return "ok"
    return "empty"


def extract_text(resp: dict[str, Any]) -> str:
    """Pull the first text block out of an MCP response. Returns '' if none."""
    result = resp.get("result", {})
    content = result.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for c in content:
            if isinstance(c, dict) and "text" in c:
                return c["text"]
    return ""


def extract_json(resp: dict[str, Any]) -> dict[str, Any] | list[Any] | None:
    """Pull the first text block and parse it as JSON. Returns None if not JSON."""
    text = extract_text(resp)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
