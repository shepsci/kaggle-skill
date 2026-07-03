"""Unit tests for skills/kaggle/modules/discussions/scripts/forums.py."""

from __future__ import annotations

import importlib.util
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "skills" / "kaggle" / "modules" / "discussions" / "scripts" / "forums.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("cli_forums", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_forum_topics_command_includes_filters_and_json_format():
    mod = _load_module()
    args = mod.parse_args([
        "forum-topics",
        "getting-started",
        "--category",
        "competition_write_ups",
        "--group",
        "bookmarked",
        "--sort-by",
        "recent",
        "--search",
        "ensemble",
        "--page-size",
        "25",
        "--format",
        "json",
    ])
    cmd, tool = mod.build_command(args)
    assert tool == "forums.topics.list"
    assert cmd == [
        "kaggle",
        "forums",
        "topics",
        "list",
        "getting-started",
        "--sort-by",
        "recent",
        "--search",
        "ensemble",
        "--category",
        "competition_write_ups",
        "--group",
        "bookmarked",
        "--page-size",
        "25",
        "--format",
        "json",
    ]


def test_resource_topics_command_supports_competitions():
    mod = _load_module()
    args = mod.parse_args([
        "resource-topics",
        "competitions",
        "titanic",
        "--sort-by",
        "top",
        "--format",
        "json",
    ])
    cmd, tool = mod.build_command(args)
    assert tool == "competitions.topics.list"
    assert cmd == [
        "kaggle",
        "competitions",
        "topics",
        "list",
        "titanic",
        "--sort-by",
        "top",
        "--format",
        "json",
    ]


def test_run_wrapped_emits_untrusted_markers_and_no_shell():
    mod = _load_module()
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout='{"title": "hello"}\n', stderr="")

    out = io.StringIO()
    with patch.object(mod.subprocess, "run", side_effect=fake_run), redirect_stdout(out):
        rc = mod.run_wrapped(["kaggle", "forums", "--format", "json"], "forums")

    assert rc == 0
    assert captured["cmd"] == ["kaggle", "forums", "--format", "json"]
    assert "shell" not in captured["kwargs"]
    text = out.getvalue()
    assert '<untrusted-content source="kaggle-cli" tool="forums"' in text
    assert '{"title": "hello"}' in text
    assert "</untrusted-content>" in text


def test_help_exits_zero():
    mod = _load_module()
    with patch.object(sys, "argv", ["forums.py", "--help"]):
        try:
            mod.parse_args(["--help"])
        except SystemExit as exc:
            assert exc.code == 0
