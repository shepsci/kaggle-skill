"""mcp-reference.md must match the committed tool snapshot and probe results.

Offline. The snapshot (tests/fixtures/mcp_tools_snapshot.json) is compared
with the live server by tests/integration/test_mcp_live.py and by the weekly
drift job; this file keeps the reference page in step with the snapshot.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import probe_mcp  # noqa: E402

REFERENCE = REPO_ROOT / "skills" / "kaggle" / "modules" / "references" / "mcp-reference.md"
SNAPSHOT = json.loads((REPO_ROOT / "tests" / "fixtures" / "mcp_tools_snapshot.json").read_text())
RESULTS = json.loads((REPO_ROOT / "tests" / "fixtures" / "mcp_probe_results.json").read_text())


def _table_block() -> str:
    text = REFERENCE.read_text(encoding="utf-8")
    return text.split(probe_mcp.TABLE_START, 1)[1].split(probe_mcp.TABLE_END, 1)[0]


def _documented_tools() -> list[str]:
    return re.findall(r"^\| `([a-z_]+)` \|", _table_block(), re.MULTILINE)


def test_every_tool_is_documented_exactly_once():
    documented = _documented_tools()
    assert sorted(documented) == sorted(SNAPSHOT["tools"])
    assert len(documented) == len(set(documented)) == SNAPSHOT["count"]


def test_reference_states_the_tool_count():
    assert f"{SNAPSHOT['count']} tools" in REFERENCE.read_text(encoding="utf-8")


def test_table_is_what_the_probe_results_render_to():
    """Edit the notes in tools/probe_mcp.py and run `--render`; do not edit the table by hand."""
    assert _table_block().strip() == probe_mcp.render_table(RESULTS, SNAPSHOT).strip()


def test_probe_results_cover_every_tool_and_hold_no_secret():
    assert set(RESULTS["tools"]) == set(SNAPSHOT["tools"])
    raw = json.dumps(RESULTS)
    assert "KGAT_" not in raw and "KGRT_" not in raw and "Bearer" not in raw


def test_write_tools_were_not_called():
    for name in probe_mcp.WRITE_TOOLS:
        entry = RESULTS["tools"][name]
        assert entry["kind"] == "write"
        assert set(entry) == {"kind", "note"}, f"{name} has probe results; it must never be called"


def test_examples_use_the_request_wrapper():
    text = REFERENCE.read_text(encoding="utf-8")
    calls = re.findall(r'"arguments"\s*:\s*\{(.{0,40})', text)
    assert calls, "the reference should show at least one raw tools/call example"
    assert all(call.lstrip().startswith('"request"') for call in calls)
    assert "Accept: application/json, text/event-stream" in text


def test_reference_links_no_private_repository():
    assert "kmcp-tools" not in REFERENCE.read_text(encoding="utf-8")


def test_measured_counts_in_the_text_match_the_probe_results():
    probed = {n: e for n, e in RESULTS["tools"].items() if "note" not in e}
    anonymous = sum(1 for e in probed.values() if e["anonymous"] == "ok")
    credential = sum(
        1 for e in probed.values() if e["anonymous"] != "ok" and e["api_token"] == "ok"
    )
    gated = len(probed) - anonymous - credential
    text = REFERENCE.read_text(encoding="utf-8")
    assert f"measured on {RESULTS['probed']}, for the {len(probed)} read tools" in text
    assert f"- {anonymous} answer with no credential." in text
    assert f"- {credential} answer only with one." in text
    assert f"- {gated} are limited to hosts and judges." in text
    same = all(e.get("oauth") == e["api_token"] for e in probed.values() if "oauth" in e)
    assert same, "the text says OAuth and API tokens behave the same; the results disagree"
