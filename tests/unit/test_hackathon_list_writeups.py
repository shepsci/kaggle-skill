"""Unit tests for skills/kaggle/modules/competitions/hackathons/scripts/list_writeups.py."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "skills" / "kaggle"))

SCRIPT = REPO_ROOT / "skills" / "kaggle" / "modules" / "competitions" / "hackathons" / "scripts" / "list_writeups.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("list_writeups", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_normalize_row_resolves_track_ids():
    mod = _load_module()
    row = {
        "id": 1,
        "write_up": {"id": 5, "topic_id": 7, "slug": "x", "title": "T", "subtitle": "S", "collaborators": []},
        "hackathon_track_ids": [363, 999],
    }
    out = mod.normalize_row(row, {363: "Clinical", 999: "Other"})
    assert out["track_titles"] == ["Clinical", "Other"]
    assert out["writeup_id"] == 5
    assert out["topic_id"] == 7
    assert out["slug"] == "x"


def test_normalize_row_falls_back_to_string_id_when_unknown_track():
    mod = _load_module()
    row = {"id": 1, "write_up": {}, "hackathon_track_ids": [999]}
    out = mod.normalize_row(row, {})
    assert out["track_titles"] == ["999"]


def test_fetch_tracks_returns_id_to_title_map(fixtures_dir):
    mod = _load_module()
    canned = json.loads((fixtures_dir / "mcp_responses" / "list_hackathon_tracks_ok.json").read_text())
    with patch.object(mod, "mcp_call", return_value=canned):
        tracks = mod.fetch_tracks("kaggle-measuring-agi", "KGAT_x")
    assert tracks == {363: "Clinical Workflow Automation", 364: "Medical Documentation & NLP", 365: "Health Data Analytics"}


def test_fetch_writeups_page_extracts_rows_and_total(fixtures_dir):
    mod = _load_module()
    canned = json.loads((fixtures_dir / "mcp_responses" / "list_hackathon_write_ups_ok.json").read_text())
    with patch.object(mod, "mcp_call", return_value=canned):
        rows, next_token, total = mod.fetch_writeups_page(
            "kaggle-measuring-agi", "KGAT_x", page_size=50, page_token=None, winner_only=False,
        )
    assert len(rows) == 1
    assert rows[0]["id"] == 1001
    assert total == 1
    assert next_token is None


def test_fetch_writeups_page_returns_empty_on_error(fixtures_dir):
    mod = _load_module()
    err = json.loads((fixtures_dir / "mcp_responses" / "permission_denied.json").read_text())
    with patch.object(mod, "mcp_call", return_value=err):
        rows, next_token, total = mod.fetch_writeups_page(
            "x", "y", 50, None, False,
        )
    assert rows == []
    assert next_token is None
    assert total is None


def test_script_does_not_call_get_hackathon_write_up():
    """Regression guard: the script must never invoke the broken endpoint as a tool call."""
    text = SCRIPT.read_text()
    # The string may appear in docstrings/comments documenting why we avoid it.
    # What must NEVER appear is an actual mcp_call invocation of that tool.
    assert 'mcp_call("get_hackathon_write_up"' not in text
    assert "mcp_call('get_hackathon_write_up'" not in text
