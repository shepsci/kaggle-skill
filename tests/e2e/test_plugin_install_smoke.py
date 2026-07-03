"""Optional local install smoke tests for Codex and Claude plugin surfaces."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_plugin_command(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
        env=env,
    )
    assert result.returncode == 0, (
        f"command failed: {' '.join(args)}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    return result


def _contains_plugin_name(value: object, name: str) -> bool:
    if isinstance(value, dict):
        if value.get("name") == name:
            return True
        if value.get("id") == f"{name}@shepsci":
            return True
        return any(_contains_plugin_name(child, name) for child in value.values())
    if isinstance(value, list):
        return any(_contains_plugin_name(child, name) for child in value)
    return False


def test_codex_plugin_marketplace_smoke(tmp_path: Path):
    if os.environ.get("RUN_CODEX_PLUGIN_SMOKE") != "1":
        pytest.skip("set RUN_CODEX_PLUGIN_SMOKE=1 to mutate a temporary CODEX_HOME")
    codex = shutil.which("codex")
    if not codex:
        pytest.skip("codex CLI not found")

    env = os.environ.copy()
    env["CODEX_HOME"] = str(tmp_path / "codex-home")
    env["HOME"] = str(tmp_path / "home")
    Path(env["CODEX_HOME"]).mkdir(parents=True)
    Path(env["HOME"]).mkdir(parents=True)

    add_marketplace = subprocess.run(
        [codex, "plugin", "marketplace", "add", str(REPO_ROOT), "--json"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env=env,
    )
    assert add_marketplace.returncode == 0, add_marketplace.stderr

    add_plugin = subprocess.run(
        [codex, "plugin", "add", "kaggle@shepsci", "--json"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env=env,
    )
    assert add_plugin.returncode == 0, add_plugin.stderr


def test_claude_plugin_install_smoke(tmp_path: Path):
    if os.environ.get("RUN_CLAUDE_PLUGIN_SMOKE") != "1":
        pytest.skip("set RUN_CLAUDE_PLUGIN_SMOKE=1 when claude CLI is installed")
    claude = shutil.which("claude")
    if not claude:
        pytest.skip("claude CLI not found")

    env = os.environ.copy()
    env["HOME"] = str(tmp_path / "home")
    env["XDG_CONFIG_HOME"] = str(tmp_path / "xdg-config")
    Path(env["HOME"]).mkdir(parents=True)
    Path(env["XDG_CONFIG_HOME"]).mkdir(parents=True)

    _run_plugin_command([claude, "plugin", "validate", str(REPO_ROOT)], env=env)
    _run_plugin_command(
        [claude, "plugin", "marketplace", "add", str(REPO_ROOT), "--scope", "local"],
        env=env,
    )
    _run_plugin_command(
        [claude, "plugin", "install", "kaggle@shepsci", "--scope", "local"],
        env=env,
    )
    installed = _run_plugin_command(
        [claude, "plugin", "list", "--json"],
        env=env,
    )
    assert _contains_plugin_name(json.loads(installed.stdout), "kaggle")
