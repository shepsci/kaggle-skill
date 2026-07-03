"""Manifest tests for Codex and Claude plugin distribution files."""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _json(path: str) -> dict:
    return json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))


def _pyproject_version() -> str:
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert match
    return match.group(1)


def test_codex_plugin_manifest_paths_and_version():
    plugin = _json(".codex-plugin/plugin.json")
    assert plugin["name"] == "kaggle"
    assert plugin["version"] == _pyproject_version()
    assert (REPO_ROOT / plugin["skills"]).resolve().is_dir()
    assert (REPO_ROOT / plugin["mcpServers"]).resolve().is_file()
    assert plugin["interface"]["displayName"] == "Kaggle Skill"
    assert plugin["interface"]["privacyPolicyURL"].startswith("https://")


def test_codex_repo_marketplace_lists_kaggle_plugin():
    marketplace = _json(".agents/plugins/marketplace.json")
    assert marketplace["name"] == "shepsci"
    entries = [entry for entry in marketplace["plugins"] if entry["name"] == "kaggle"]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["source"] == {"source": "local", "path": "./"}
    assert entry["policy"]["installation"] == "AVAILABLE"
    assert entry["policy"]["authentication"] == "ON_INSTALL"
    assert entry["category"] == "Data Science"


def test_claude_plugin_and_in_repo_marketplace_use_public_name():
    plugin = _json(".claude-plugin/plugin.json")
    marketplace = _json(".claude-plugin/marketplace.json")
    assert plugin["name"] == "kaggle"
    assert plugin["version"] == _pyproject_version()
    entries = [entry for entry in marketplace["plugins"] if entry["name"] == "kaggle"]
    assert len(entries) == 1
    assert entries[0]["version"] == plugin["version"]
    assert entries[0]["description"] == plugin["description"]
    assert entries[0]["source"] == "./"
