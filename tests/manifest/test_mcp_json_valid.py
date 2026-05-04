"""Validate .mcp.json — bundled Kaggle MCP server configuration."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MCP_JSON = REPO_ROOT / ".mcp.json"


def test_mcp_json_exists_and_parses():
    assert MCP_JSON.exists()
    json.loads(MCP_JSON.read_text())


def test_kaggle_server_present():
    cfg = json.loads(MCP_JSON.read_text())
    assert "kaggle" in cfg.get("mcpServers", {})


def test_kaggle_server_uses_https():
    cfg = json.loads(MCP_JSON.read_text())
    url = cfg["mcpServers"]["kaggle"].get("url", "")
    assert url.startswith("https://"), f"insecure URL: {url}"
    assert "kaggle.com" in url


def test_authorization_uses_env_substitution():
    cfg = json.loads(MCP_JSON.read_text())
    headers = cfg["mcpServers"]["kaggle"].get("headers", {})
    auth = headers.get("Authorization", "")
    assert "${" in auth, (
        f"Authorization header should reference env var, got literal: {auth}"
    )
    assert "KAGGLE" in auth, "expected reference to a KAGGLE_* env var"
