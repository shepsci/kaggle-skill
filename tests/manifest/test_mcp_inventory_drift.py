"""Detect drift between mcp-reference.md and the live Kaggle MCP server.

Whenever Kaggle adds or removes tools, our reference docs need updating.
This test pulls `tools/list` against the live server and asserts that:

1. The live tool count remains high enough to catch auth or server regressions.
2. Every tool documented in mcp-reference.md exists on the live server.
3. Every tool the live server exposes is documented in mcp-reference.md.

Skipped without --run-live and KAGGLE_API_TOKEN.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "skills" / "kaggle"))

from shared.mcp_client import mcp_list_tools  # noqa: E402

MCP_REFERENCE = REPO_ROOT / "skills" / "kaggle" / "modules" / "kllm" / "references" / "mcp-reference.md"

pytestmark = pytest.mark.live


def _documented_tools() -> set[str]:
    r"""Extract tool names from mcp-reference.md inventory section.

    Tools are formatted as bullet items: ``- ✅ `tool_name` `` (or other
    status emoji). We pull anything in backticks that follows a bullet
    + status marker.
    """
    text = MCP_REFERENCE.read_text()
    # Match bullet-list backticked tool names, e.g.  `- ✅ \`search_competitions\``
    # or `- ⚠️ \`get_hackathon_write_up\``
    pattern = re.compile(r"^\s*-\s*[^\s]+?\s*`([a-z_][a-z0-9_]*)`", re.MULTILINE)
    return {m.group(1) for m in pattern.finditer(text)}


def _live_tools(token: str) -> set[str]:
    resp = mcp_list_tools(token=token, timeout=30)
    tools = resp.get("result", {}).get("tools", [])
    return {t.get("name", "") for t in tools if t.get("name")}


def test_live_server_returns_at_least_60_tools(kgat_token: str):
    live = _live_tools(kgat_token)
    assert len(live) >= 70, f"live server returned only {len(live)} tools; 2026-07-03 docs claim 70"


def test_no_documented_tool_is_missing_from_live_server(kgat_token: str):
    documented = _documented_tools()
    live = _live_tools(kgat_token)
    missing = documented - live
    # Some "tools" referenced in docs are aliases or comments; allow a small leak.
    assert not missing, (
        f"mcp-reference.md documents {len(missing)} tools not exposed by the live server: "
        f"{sorted(missing)}. Either Kaggle removed them or our docs have typos."
    )


def test_no_live_tool_is_missing_from_docs(kgat_token: str):
    documented = _documented_tools()
    live = _live_tools(kgat_token)
    undocumented = live - documented
    assert not undocumented, (
        f"Live server exposes {len(undocumented)} tools not documented in mcp-reference.md: "
        f"{sorted(undocumented)}. Kaggle has shipped new endpoints — update the docs."
    )


def test_competition_overview_endpoint_is_present_and_documented(kgat_token: str):
    """Specifically guard list_competition_pages — the headline endpoint for v2.2.0."""
    live = _live_tools(kgat_token)
    documented = _documented_tools()
    assert "list_competition_pages" in live, "list_competition_pages missing from live server"
    assert "list_competition_pages" in documented, (
        "list_competition_pages missing from mcp-reference.md — required for v2.2.0"
    )
