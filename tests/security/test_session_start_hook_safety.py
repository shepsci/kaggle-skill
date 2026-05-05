"""Guards on the SessionStart hook (.claude/settings.json → setup_env.sh).

The hook runs unattended on every Claude Code session start. Anything it
silently does is a security smell. These tests pin the safety properties.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SETTINGS = REPO_ROOT / ".claude" / "settings.json"
SETUP_ENV = REPO_ROOT / "skills" / "kaggle" / "modules" / "kllm" / "scripts" / "setup_env.sh"


def _hook_command() -> str:
    cfg = json.loads(SETTINGS.read_text())
    hooks = cfg.get("hooks", {}).get("SessionStart", [])
    cmds = []
    for group in hooks:
        for h in group.get("hooks", []):
            cmd = h.get("command")
            if cmd:
                cmds.append(cmd)
    return " ".join(cmds)


def test_session_start_hook_runs_setup_env():
    assert "setup_env.sh" in _hook_command()


def test_setup_env_does_not_pip_install_on_session_start():
    """pip install must NOT run silently on every session — security review MEDIUM-3."""
    text = SETUP_ENV.read_text()
    # Allow `pip install` only inside echo/print messages telling the user what to run.
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if stripped.startswith("echo ") or stripped.startswith("printf "):
            continue
        if "pip install" in line:
            raise AssertionError(
                f"setup_env.sh:{line_no}: pip install runs unconditionally — "
                "must only be printed as instructions, not executed. Line: {line!r}"
            )


def test_setup_env_does_not_source_env_from_cwd():
    """source .env from the current working directory lets any project inject env vars."""
    text = SETUP_ENV.read_text()
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "source .env" in stripped or 'source "./.env"' in stripped or 'source "${PWD}' in stripped:
            raise AssertionError(
                f"setup_env.sh:{line_no}: sources .env from CWD — must source from "
                "PLUGIN_ROOT/.env or skip. Line: {line!r}"
            )


def test_setup_env_uses_set_euo_pipefail():
    """Bash safety: -e (exit on err), -u (unset var = err), -o pipefail (catch piped errors)."""
    text = SETUP_ENV.read_text()
    assert "set -euo pipefail" in text


def test_setup_env_chmod_600_on_credential_files():
    text = SETUP_ENV.read_text()
    assert "chmod 600" in text, "credential files must be chmod 600 immediately after creation"
