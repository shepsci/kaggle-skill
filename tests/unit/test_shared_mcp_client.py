"""Unit tests for skills/kaggle/shared/mcp_client.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "skills" / "kaggle"))

from shared.mcp_client import (  # noqa: E402
    classify_result,
    extract_json,
    extract_text,
    get_kgat_token,
    get_legacy_key,
    get_username,
    load_dotenv,
    mcp_call,
    resolve_token,
)


# ── classify_result ──────────────────────────────────────────────────────────

def test_classify_parse_fail_when_raw_present():
    assert classify_result({"raw": "garbage"}) == "parse_fail"


def test_classify_error_with_message():
    resp = {"error": {"message": "boom"}}
    assert classify_result(resp).startswith("error: boom")


def test_classify_unauthenticated_in_string_content():
    resp = {"result": {"content": "Unauthenticated request"}}
    assert classify_result(resp) == "unauthenticated"


def test_classify_unauthenticated_in_list_content():
    resp = {"result": {"content": [{"text": "Unauthenticated"}]}}
    assert classify_result(resp) == "unauthenticated"


def test_classify_error_in_list_content():
    resp = {"result": {"content": [{"text": 'Error: something {"error": true}'}]}}
    assert classify_result(resp).startswith("error:")


def test_classify_empty_when_result_is_empty_dict():
    assert classify_result({"result": {}}) == "empty"


def test_classify_ok_for_normal_response():
    resp = {"result": {"content": [{"text": '{"data": [1,2,3]}'}]}}
    assert classify_result(resp) == "ok"


def test_classify_ok_for_string_content():
    resp = {"result": {"content": "ok"}}
    assert classify_result(resp) == "ok"


# ── extract_text / extract_json ──────────────────────────────────────────────

def test_extract_text_from_string_content():
    assert extract_text({"result": {"content": "hello"}}) == "hello"


def test_extract_text_from_list_content():
    resp = {"result": {"content": [{"text": "first"}, {"text": "second"}]}}
    assert extract_text(resp) == "first"


def test_extract_text_returns_empty_when_no_content():
    assert extract_text({"result": {}}) == ""


def test_extract_json_parses_valid_json_in_text_block():
    resp = {"result": {"content": [{"text": '{"x": 1}'}]}}
    assert extract_json(resp) == {"x": 1}


def test_extract_json_returns_none_for_non_json_text():
    resp = {"result": {"content": [{"text": "not json"}]}}
    assert extract_json(resp) is None


# ── load_dotenv ──────────────────────────────────────────────────────────────

def test_load_dotenv_skips_comments_and_blank_lines(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("# comment\n\nFOO=bar\n  BAZ = qux\n")
    monkeypatch.delenv("FOO", raising=False)
    monkeypatch.delenv("BAZ", raising=False)
    load_dotenv(env_file)
    import os
    assert os.environ["FOO"] == "bar"
    assert os.environ["BAZ"] == "qux"


def test_load_dotenv_does_not_overwrite_existing_env(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("PRESET=newvalue\n")
    monkeypatch.setenv("PRESET", "original")
    load_dotenv(env_file)
    import os
    assert os.environ["PRESET"] == "original"


# ── get_kgat_token / get_legacy_key / get_username ───────────────────────────

def test_get_kgat_token_recognizes_prefix(monkeypatch):
    monkeypatch.setenv("KAGGLE_API_TOKEN", "KGAT_xxxxxxxx")
    monkeypatch.delenv("KAGGLE_MCP_TOKEN", raising=False)
    assert get_kgat_token() == "KGAT_xxxxxxxx"


def test_get_kgat_token_rejects_legacy_format(monkeypatch):
    monkeypatch.setenv("KAGGLE_API_TOKEN", "abcdef0123456789abcdef0123456789")
    monkeypatch.delenv("KAGGLE_MCP_TOKEN", raising=False)
    assert get_kgat_token() == ""


def test_get_kgat_token_prefers_mcp_token_override(monkeypatch):
    monkeypatch.setenv("KAGGLE_MCP_TOKEN", "KGAT_override")
    monkeypatch.setenv("KAGGLE_API_TOKEN", "KGAT_default")
    assert get_kgat_token() == "KGAT_override"


def test_get_legacy_key_from_env(monkeypatch):
    monkeypatch.setenv("KAGGLE_KEY", "abcdef0123456789abcdef0123456789")
    monkeypatch.setenv("HOME", "/tmp/no-such-home-xyz")
    assert get_legacy_key() == "abcdef0123456789abcdef0123456789"


def test_get_legacy_key_rejects_kgat_prefixed(monkeypatch):
    monkeypatch.setenv("KAGGLE_KEY", "KGAT_xxxx")
    monkeypatch.setenv("HOME", "/tmp/no-such-home-xyz")
    assert get_legacy_key() == ""


def test_get_legacy_key_from_kaggle_json(tmp_path, monkeypatch):
    monkeypatch.delenv("KAGGLE_KEY", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    kaggle_dir = tmp_path / ".kaggle"
    kaggle_dir.mkdir()
    (kaggle_dir / "kaggle.json").write_text('{"username": "alice", "key": "0123456789abcdef0123456789abcdef"}')
    assert get_legacy_key() == "0123456789abcdef0123456789abcdef"


def test_get_legacy_key_from_kaggle_json_skips_kgat(tmp_path, monkeypatch):
    monkeypatch.delenv("KAGGLE_KEY", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    kaggle_dir = tmp_path / ".kaggle"
    kaggle_dir.mkdir()
    (kaggle_dir / "kaggle.json").write_text('{"username": "alice", "key": "KGAT_xxx"}')
    assert get_legacy_key() == ""


def test_get_legacy_key_handles_malformed_json(tmp_path, monkeypatch):
    monkeypatch.delenv("KAGGLE_KEY", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    kaggle_dir = tmp_path / ".kaggle"
    kaggle_dir.mkdir()
    (kaggle_dir / "kaggle.json").write_text("not json")
    assert get_legacy_key() == ""


def test_get_username_from_env(monkeypatch):
    monkeypatch.setenv("KAGGLE_USERNAME", "alice")
    assert get_username() == "alice"


def test_get_username_falls_back_to_kaggle_json(tmp_path, monkeypatch):
    monkeypatch.delenv("KAGGLE_USERNAME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    kaggle_dir = tmp_path / ".kaggle"
    kaggle_dir.mkdir()
    (kaggle_dir / "kaggle.json").write_text('{"username": "bob", "key": "x"}')
    assert get_username() == "bob"


# ── resolve_token ────────────────────────────────────────────────────────────

def test_resolve_token_prefers_mcp_override(monkeypatch):
    monkeypatch.setenv("KAGGLE_MCP_TOKEN", "raw_override")
    monkeypatch.setenv("KAGGLE_API_TOKEN", "KGAT_other")
    assert resolve_token() == "raw_override"


def test_resolve_token_returns_kgat_when_no_override(monkeypatch, tmp_path):
    monkeypatch.delenv("KAGGLE_MCP_TOKEN", raising=False)
    monkeypatch.delenv("KAGGLE_KEY", raising=False)
    monkeypatch.setenv("KAGGLE_API_TOKEN", "KGAT_real")
    monkeypatch.setenv("HOME", str(tmp_path))
    assert resolve_token() == "KGAT_real"


def test_resolve_token_returns_empty_when_nothing_set(monkeypatch, tmp_path):
    for v in ("KAGGLE_MCP_TOKEN", "KAGGLE_API_TOKEN", "KAGGLE_KEY"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert resolve_token() == ""


# ── mcp_call (mocked subprocess) ─────────────────────────────────────────────

def test_mcp_call_sends_jsonrpc_envelope():
    captured = {}

    def fake_run(cmd, capture_output, text, timeout):
        captured["cmd"] = cmd
        idx = cmd.index("-d")
        captured["payload"] = json.loads(cmd[idx + 1])
        from types import SimpleNamespace
        return SimpleNamespace(stdout='{"result": {}}')

    with patch("shared.mcp_client.subprocess.run", fake_run):
        mcp_call("authorize", {}, token="KGAT_test")

    assert captured["payload"]["jsonrpc"] == "2.0"
    assert captured["payload"]["method"] == "tools/call"
    assert captured["payload"]["params"]["name"] == "authorize"
    assert "id" in captured["payload"]


def test_mcp_call_includes_bearer_auth_header():
    captured = {}

    def fake_run(cmd, capture_output, text, timeout):
        captured["cmd"] = cmd
        from types import SimpleNamespace
        return SimpleNamespace(stdout='{"result": {}}')

    with patch("shared.mcp_client.subprocess.run", fake_run):
        mcp_call("authorize", {}, token="KGAT_secret")

    assert "Authorization: Bearer KGAT_secret" in captured["cmd"]


def test_mcp_call_parses_sse_data_line():
    sse = 'event: message\ndata: {"result":{"x":1}}\n\n'
    from types import SimpleNamespace

    def fake_run(*a, **kw):
        return SimpleNamespace(stdout=sse)

    with patch("shared.mcp_client.subprocess.run", fake_run):
        resp = mcp_call("authorize", {}, token="KGAT_x")
    assert resp == {"result": {"x": 1}}


def test_mcp_call_falls_back_to_raw_json_when_no_sse():
    from types import SimpleNamespace

    def fake_run(*a, **kw):
        return SimpleNamespace(stdout='{"result":{"y":2}}')

    with patch("shared.mcp_client.subprocess.run", fake_run):
        resp = mcp_call("authorize", {}, token="KGAT_x")
    assert resp == {"result": {"y": 2}}


def test_mcp_call_returns_parse_fail_marker_on_garbage():
    from types import SimpleNamespace

    def fake_run(*a, **kw):
        return SimpleNamespace(stdout="garbage not json at all")

    with patch("shared.mcp_client.subprocess.run", fake_run):
        resp = mcp_call("authorize", {}, token="KGAT_x")
    assert "raw" in resp


def test_mcp_call_returns_timeout_error_on_subprocess_timeout():
    import subprocess
    from shared.mcp_client import mcp_call as mc

    def fake_run(*a, **kw):
        raise subprocess.TimeoutExpired(cmd="curl", timeout=1)

    with patch("shared.mcp_client.subprocess.run", fake_run):
        resp = mc("authorize", {}, token="KGAT_x", timeout=1)
    assert resp.get("error", {}).get("message") == "timeout"
