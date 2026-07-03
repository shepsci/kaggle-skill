"""Gated live smoke tests for the current Kaggle CLI surface."""

from __future__ import annotations

import os
import re
import shutil
import subprocess

import pytest

pytestmark = pytest.mark.live


def _kaggle_bin() -> str:
    return os.environ.get("KAGGLE_CLI_BIN") or shutil.which("kaggle") or "kaggle"


def _run_kaggle(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [_kaggle_bin(), *args],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def _version_tuple(text: str) -> tuple[int, int, int]:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", text)
    assert match, f"could not parse Kaggle CLI version from {text!r}"
    return tuple(int(part) for part in match.groups())


def test_live_kaggle_cli_version_is_current_floor():
    result = _run_kaggle("--version")
    assert result.returncode == 0, result.stderr
    assert _version_tuple(result.stdout + result.stderr) >= (2, 2, 3)


def test_live_forums_list_supports_json_format():
    result = _run_kaggle("forums", "list", "--format", "json")
    assert result.returncode == 0, result.stderr[:500]
    assert result.stdout.lstrip().startswith("[") or result.stdout.lstrip().startswith("{")


def test_live_competition_topics_support_json_format():
    result = _run_kaggle(
        "competitions",
        "topics",
        "list",
        "titanic",
        "--page",
        "1",
        "--format",
        "json",
    )
    assert result.returncode == 0, result.stderr[:500]
    assert result.stdout.lstrip().startswith("[") or result.stdout.lstrip().startswith("{")
