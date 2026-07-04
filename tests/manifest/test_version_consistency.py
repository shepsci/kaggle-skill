"""Cross-file version consistency guard.

Canonical version = .claude-plugin/plugin.json "version". Every other manifest
that carries a structured version field must match it exactly, and every doc
that mentions the version as prose text must contain that literal string
somewhere. This intentionally does not hardcode a version number so it keeps
passing across releases (and mid-bump, as long as the tree is consistent).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _json(path: str) -> dict:
    return json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))


def _canonical_version() -> str:
    return _json(".claude-plugin/plugin.json")["version"]


def _pyproject_version() -> str:
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert match, "pyproject.toml missing a top-level version field"
    return match.group(1)


def _skill_md_frontmatter_metadata() -> dict:
    text = (REPO_ROOT / "skills" / "kaggle" / "SKILL.md").read_text(encoding="utf-8")
    match = re.search(r'^metadata:\s*(\{.*\})\s*$', text, re.MULTILINE)
    assert match, "skills/kaggle/SKILL.md frontmatter missing a metadata JSON line"
    return json.loads(match.group(1))


def test_claude_marketplace_entry_matches_canonical_version():
    canonical = _canonical_version()
    marketplace = _json(".claude-plugin/marketplace.json")
    entries = [entry for entry in marketplace["plugins"] if entry["name"] == "kaggle"]
    assert len(entries) == 1, "expected exactly one kaggle entry in .claude-plugin/marketplace.json"
    assert entries[0]["version"] == canonical


def test_codex_plugin_matches_canonical_version():
    canonical = _canonical_version()
    codex_plugin = _json(".codex-plugin/plugin.json")
    assert codex_plugin["version"] == canonical


def test_pyproject_matches_canonical_version():
    assert _pyproject_version() == _canonical_version()


def test_skill_md_frontmatter_metadata_matches_canonical_version():
    canonical = _canonical_version()
    metadata = _skill_md_frontmatter_metadata()
    assert metadata.get("version") == canonical


DOCS_WITH_LITERAL_VERSION_MENTION = [
    "tests/e2e/INSTALL_CHECKLIST.md",
    "docs/distribution/claude-community-submission.md",
    "docs/demo/demo-script.md",
    "docs/demo/record.sh",
]


def test_docs_mention_the_canonical_version_string():
    canonical = _canonical_version()
    missing = []
    for rel_path in DOCS_WITH_LITERAL_VERSION_MENTION:
        text = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        if canonical not in text:
            missing.append(rel_path)
    assert not missing, (
        f"canonical version {canonical!r} not found verbatim in: {missing}"
    )
