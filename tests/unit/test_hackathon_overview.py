"""Unit tests for skills/kaggle/modules/hackathon/scripts/hackathon_overview.py."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "skills" / "kaggle"))

SCRIPT = REPO_ROOT / "skills" / "kaggle" / "modules" / "hackathon" / "scripts" / "hackathon_overview.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("hackathon_overview", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_find_page_matches_by_substring():
    mod = _load_module()
    pages = [{"name": "rules", "content": "x"}, {"name": "rubric", "content": "y"}]
    assert mod.find_page(pages, "rule") == pages[0]
    assert mod.find_page(pages, "rubric", "judging") == pages[1]


def test_find_page_returns_none_when_no_match():
    mod = _load_module()
    pages = [{"name": "overview"}]
    assert mod.find_page(pages, "rule", "rubric") is None


def test_find_page_case_insensitive():
    mod = _load_module()
    pages = [{"name": "Official Rules", "content": "..."}]
    assert mod.find_page(pages, "official") == pages[0]


def test_fetch_overview_returns_pages_array(fixtures_dir):
    mod = _load_module()
    canned = json.loads((fixtures_dir / "mcp_responses" / "get_hackathon_overview_ok.json").read_text())
    with patch.object(mod, "mcp_call", return_value=canned):
        result = mod.fetch_overview("kaggle-measuring-agi", "KGAT_x")
    assert result["status"] == "ok"
    pages = result["data"]["pages"]
    assert any(p["name"] == "rules" for p in pages)
    assert any(p["name"] == "rubric" for p in pages)
    assert any(p["name"] == "eligibility" for p in pages)


def test_fetch_overview_surfaces_error_status_on_failure(fixtures_dir):
    mod = _load_module()
    canned = json.loads((fixtures_dir / "mcp_responses" / "permission_denied.json").read_text())
    with patch.object(mod, "mcp_call", return_value=canned):
        result = mod.fetch_overview("x", "KGAT_x")
    assert result["status"] != "ok"
