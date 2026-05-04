"""Unit tests for skills/kaggle/modules/hackathon/scripts/fetch_writeup.py."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "skills" / "kaggle"))

SCRIPT = REPO_ROOT / "skills" / "kaggle" / "modules" / "hackathon" / "scripts" / "fetch_writeup.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("fetch_writeup", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_is_role_gated_detects_permission_denied(fixtures_dir):
    mod = _load_module()
    canned = json.loads((fixtures_dir / "mcp_responses" / "permission_denied.json").read_text())
    assert mod.is_role_gated(canned)


def test_is_role_gated_false_for_normal_response(fixtures_dir):
    mod = _load_module()
    canned = json.loads((fixtures_dir / "mcp_responses" / "get_writeup_ok.json").read_text())
    assert not mod.is_role_gated(canned)


def test_fetch_by_id_calls_get_writeup_endpoint():
    mod = _load_module()
    captured = {}

    def fake_mcp(tool, args, token, **kw):
        captured["tool"] = tool
        captured["args"] = args
        return {"result": {"content": [{"text": "{}"}]}}

    with patch.object(mod, "mcp_call", side_effect=fake_mcp):
        mod.fetch_by_id(1234, "KGAT_x")

    assert captured["tool"] == "get_writeup"
    assert captured["args"]["request"]["writeUpId"] == 1234


def test_fetch_by_topic_calls_get_writeup_by_topic_endpoint():
    mod = _load_module()
    captured = {}

    def fake_mcp(tool, args, token, **kw):
        captured["tool"] = tool
        return {"result": {"content": [{"text": "{}"}]}}

    with patch.object(mod, "mcp_call", side_effect=fake_mcp):
        mod.fetch_by_topic(7777, "KGAT_x")

    assert captured["tool"] == "get_writeup_by_topic"


def test_fetch_by_slug_calls_get_writeup_by_slug_endpoint():
    mod = _load_module()
    captured = {}

    def fake_mcp(tool, args, token, **kw):
        captured["tool"] = tool
        captured["args"] = args
        return {"result": {"content": [{"text": "{}"}]}}

    with patch.object(mod, "mcp_call", side_effect=fake_mcp):
        mod.fetch_by_slug("kaggle-measuring-agi", "team-alpha", "KGAT_x")

    assert captured["tool"] == "get_writeup_by_slug"
    assert captured["args"]["request"]["competitionName"] == "kaggle-measuring-agi"
    assert captured["args"]["request"]["slug"] == "team-alpha"


def test_script_never_calls_get_hackathon_write_up():
    text = SCRIPT.read_text()
    # The string `get_hackathon_write_up` must not appear as a function call.
    # Allow it in the docstring/comments referring to the broken endpoint.
    code_lines = [
        line for line in text.splitlines()
        if not line.lstrip().startswith("#") and not line.lstrip().startswith('"""')
    ]
    code = "\n".join(code_lines)
    assert 'mcp_call("get_hackathon_write_up"' not in code
    assert "'get_hackathon_write_up'" not in code or "is_role_gated" in code
