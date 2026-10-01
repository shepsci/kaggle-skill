"""Install smoke tests for the Claude Code and Codex plugin surfaces.

Each test runs only when its CLI is on PATH and its switch is set, and uses a
throwaway home directory so no real configuration is touched:

    RUN_CLAUDE_PLUGIN_SMOKE=1 pytest tests/e2e -k claude
    RUN_CODEX_PLUGIN_SMOKE=1  pytest tests/e2e -k codex

They are marked ``manual`` so the hermetic fixture leaves PATH and HOME alone.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.manual


def _run(args: list[str], env: dict[str, str], timeout: int = 120) -> subprocess.CompletedProcess:
    result = subprocess.run(
        args, capture_output=True, text=True, timeout=timeout, check=False, env=env
    )
    assert result.returncode == 0, (
        f"command failed: {' '.join(args)}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    return result


def _contains_plugin_name(value: object, name: str) -> bool:
    if isinstance(value, dict):
        if value.get("name") == name or value.get("id") == f"{name}@shepsci":
            return True
        return any(_contains_plugin_name(child, name) for child in value.values())
    if isinstance(value, list):
        return any(_contains_plugin_name(child, name) for child in value)
    return False


def test_codex_plugin_marketplace_smoke(tmp_path: Path):
    if os.environ.get("RUN_CODEX_PLUGIN_SMOKE") != "1":
        pytest.skip("set RUN_CODEX_PLUGIN_SMOKE=1 to run against a temporary CODEX_HOME")
    codex = shutil.which("codex")
    if not codex:
        pytest.skip("codex CLI not found")

    env = os.environ.copy()
    env["CODEX_HOME"] = str(tmp_path / "codex-home")
    env["HOME"] = str(tmp_path / "home")
    Path(env["CODEX_HOME"]).mkdir(parents=True)
    Path(env["HOME"]).mkdir(parents=True)

    _run([codex, "plugin", "marketplace", "add", str(REPO_ROOT), "--json"], env)
    _run([codex, "plugin", "add", "kaggle@shepsci", "--json"], env)
    # Codex reads the MCP entry that its manifest names, not the root .mcp.json.
    listed = _run([codex, "mcp", "list"], env)
    assert "https://www.kaggle.com/mcp" in listed.stdout


def test_claude_plugin_validate_and_install_smoke(tmp_path: Path):
    if os.environ.get("RUN_CLAUDE_PLUGIN_SMOKE") != "1":
        pytest.skip("set RUN_CLAUDE_PLUGIN_SMOKE=1 when the claude CLI is installed")
    claude = shutil.which("claude")
    if not claude:
        pytest.skip("claude CLI not found")

    env = os.environ.copy()
    env["HOME"] = str(tmp_path / "home")
    env["CLAUDE_CONFIG_DIR"] = str(tmp_path / "claude-config")
    Path(env["HOME"]).mkdir(parents=True)
    Path(env["CLAUDE_CONFIG_DIR"]).mkdir(parents=True)

    # `claude plugin validate <dir>` checks only marketplace.json when one exists, so the
    # plugin manifest is validated by its own path. The missing "type" on the MCP entry went
    # unnoticed for that reason.
    _run(
        [
            claude,
            "plugin",
            "validate",
            str(REPO_ROOT / ".claude-plugin" / "plugin.json"),
            "--strict",
        ],
        env,
    )
    _run(
        [
            claude,
            "plugin",
            "validate",
            str(REPO_ROOT / ".claude-plugin" / "marketplace.json"),
            "--strict",
        ],
        env,
    )
    _run([claude, "plugin", "marketplace", "add", str(REPO_ROOT)], env)
    _run([claude, "plugin", "install", "kaggle@shepsci"], env)
    installed = _run([claude, "plugin", "list", "--json"], env)
    assert _contains_plugin_name(json.loads(installed.stdout), "kaggle")
