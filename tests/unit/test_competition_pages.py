"""Unit tests for skills/kaggle/modules/competitions/scripts/competition_pages.py."""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "skills" / "kaggle"))

SCRIPT = REPO_ROOT / "skills" / "kaggle" / "modules" / "competitions" / "scripts" / "competition_pages.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("list_competition_pages", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_find_page_matches_by_substring_case_insensitive():
    mod = _load_module()
    pages = [{"name": "Rules", "content": "x"}, {"name": "Evaluation", "content": "y"}]
    assert mod.find_page(pages, "rule") == pages[0]
    assert mod.find_page(pages, "evaluation") == pages[1]
    assert mod.find_page(pages, "RUBRIC", "evaluation") == pages[1]


def test_find_page_returns_none_when_no_match():
    mod = _load_module()
    assert mod.find_page([{"name": "rules"}], "evaluation") is None


def test_find_page_handles_empty_list():
    mod = _load_module()
    assert mod.find_page([], "anything") is None
    assert mod.find_page(None, "anything") is None


def test_fetch_pages_returns_ok_for_valid_response():
    mod = _load_module()
    canned = {
        "result": {"content": [{"text": json.dumps({
            "pages": [
                {"name": "rules", "content": "Rule text"},
                {"name": "Evaluation", "content": "Metric: accuracy"},
            ]
        })}]}
    }
    with patch.object(mod, "mcp_call", return_value=canned):
        result = mod.fetch_pages("titanic", "KGAT_x")
    assert result["status"] == "ok"
    assert result["competition"] == "titanic"
    pages = result["data"]["pages"]
    assert len(pages) == 2
    assert pages[0]["name"] == "rules"


def test_fetch_pages_surfaces_error_on_bad_response():
    mod = _load_module()
    err = {"result": {"content": [{"text": "Error: permission denied"}]}}
    with patch.object(mod, "mcp_call", return_value=err):
        result = mod.fetch_pages("titanic", "KGAT_x")
    assert result["status"] != "ok"


def test_script_calls_list_competition_pages_endpoint():
    """Sanity: the script must hit list_competition_pages, not get_competition."""
    text = SCRIPT.read_text()
    assert '"list_competition_pages"' in text
    assert 'mcp_call("get_competition"' not in text


def test_script_emits_untrusted_content_wrapper():
    """Page content is host-authored markdown — must be wrapped to prevent prompt injection."""
    text = SCRIPT.read_text()
    assert "<untrusted-content" in text
    assert "</untrusted-content>" in text
