"""Validate .claude/settings.json — permissions and SessionStart hook."""

from __future__ import annotations

import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SETTINGS = REPO_ROOT / ".claude" / "settings.json"


def test_settings_exists_and_parses():
    assert SETTINGS.exists()
    json.loads(SETTINGS.read_text())


def test_permissions_allow_list_present():
    cfg = json.loads(SETTINGS.read_text())
    allow = cfg.get("permissions", {}).get("allow", [])
    assert any("kaggle.com" in entry for entry in allow), "no kaggle.com in allow list"


def test_session_start_hook_command_resolves():
    cfg = json.loads(SETTINGS.read_text())
    hooks = cfg.get("hooks", {}).get("SessionStart", [])
    if not hooks:
        return
    for hook_group in hooks:
        for hook in hook_group.get("hooks", []):
            cmd = hook.get("command", "")
            if not cmd:
                continue
            for token in cmd.split():
                if "/" in token and not token.startswith(("-", "$")):
                    if "||" in token or token.endswith(":"):
                        continue
                    if token.endswith(".sh") or token.endswith(".py"):
                        path = REPO_ROOT / token
                        if not path.exists():
                            alt = REPO_ROOT / "skills" / "kaggle" / token
                            assert alt.exists(), (
                                f"SessionStart hook references missing script: {token}"
                            )
                        break
