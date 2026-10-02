"""Validate the bundled Kaggle MCP server entries.

Claude Code reads `.mcp.json`. Codex reads the file its manifest names,
`.codex-plugin/mcp.json`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MCP_JSON = REPO_ROOT / ".mcp.json"
CODEX_MCP_JSON = REPO_ROOT / ".codex-plugin" / "mcp.json"
BOTH = pytest.mark.parametrize("path", [MCP_JSON, CODEX_MCP_JSON], ids=["claude", "codex"])


def _server(path: Path = MCP_JSON) -> dict:
    return json.loads(path.read_text())["mcpServers"]["kaggle"]


@BOTH
def test_file_has_exactly_the_kaggle_server(path):
    config = json.loads(path.read_text())
    assert list(config) == ["mcpServers"]
    assert list(config["mcpServers"]) == ["kaggle"]


@BOTH
def test_server_declares_the_http_transport(path):
    """Claude Code drops an entry that has a `url` and no `type`, without a message."""
    assert _server(path)["type"] == "http"


@BOTH
def test_server_url_is_kaggles_https_endpoint(path):
    assert _server(path)["url"] == "https://www.kaggle.com/mcp"


@BOTH
def test_entry_carries_no_credential(path):
    """The client signs in; nothing forwards an environment variable.

    A header template such as `Bearer ${KAGGLE_API_TOKEN}` would send whatever that
    variable holds on every request, and Claude Code offers no sign-in for an entry
    that has an `Authorization` header.
    """
    server = _server(path)
    assert "headers" not in server and "env" not in server
    raw = path.read_text()
    assert "Authorization" not in raw and "Bearer" not in raw and "${" not in raw
    assert "secret" not in raw.lower()


def test_claude_entry_names_the_oauth_client_id():
    """Without a client ID, Claude Code registers itself, Kaggle answers with an empty
    `client_secret`, and the sign-in stops with "client_secret_basic authentication
    requires a client_secret". A client ID is public; it is not a credential."""
    server = _server()
    assert set(server) == {"type", "url", "oauth"}
    assert server["oauth"] == {"clientId": "claude-code-(kaggle)"}


def test_client_id_is_the_one_kaggle_gives_to_claude_code():
    """tools/check_oauth_registration.py keeps the snapshot current; the weekly drift
    job reports when Kaggle's answer changes."""
    snapshot = json.loads(
        (REPO_ROOT / "tests" / "fixtures" / "oauth_registration.json").read_text()
    )
    assert snapshot["client_name"] == "Claude Code (kaggle)"
    assert _server()["oauth"]["clientId"] == snapshot["facts"]["client_id"]


def test_codex_entry_is_the_url_only():
    """Codex registers its own client and its sign-in completes without help."""
    assert set(_server(CODEX_MCP_JSON)) == {"type", "url"}


def test_codex_manifest_points_at_the_codex_entry():
    manifest = json.loads((REPO_ROOT / ".codex-plugin" / "plugin.json").read_text())
    assert (REPO_ROOT / manifest["mcpServers"]).resolve() == CODEX_MCP_JSON.resolve()
