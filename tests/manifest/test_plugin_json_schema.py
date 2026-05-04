"""Validate .claude-plugin/plugin.json structure for Claude Code marketplace."""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_JSON = REPO_ROOT / ".claude-plugin" / "plugin.json"


def _load() -> dict:
    return json.loads(PLUGIN_JSON.read_text())


def test_plugin_json_exists():
    assert PLUGIN_JSON.exists()


def test_required_fields_present():
    p = _load()
    for field in ("name", "description", "version"):
        assert field in p, f"missing required field: {field}"
        assert p[field], f"empty required field: {field}"


def test_name_is_kebab_case():
    name = _load()["name"]
    assert re.fullmatch(r"[a-z][a-z0-9-]*[a-z0-9]", name), (
        f"name '{name}' is not kebab-case"
    )


def test_version_matches_semver():
    version = _load()["version"]
    assert re.fullmatch(r"\d+\.\d+\.\d+(-[a-z0-9.-]+)?", version), (
        f"version '{version}' is not semver"
    )


def test_version_is_at_least_2_1_0():
    parts = [int(x) for x in _load()["version"].split("-")[0].split(".")]
    assert parts >= [2, 1, 0], f"version regressed to {parts} below 2.1.0"


def test_skills_array_paths_exist():
    p = _load()
    skills = p.get("skills") or []
    for s in skills:
        path = REPO_ROOT / s.lstrip("./")
        assert path.exists(), f"skills array references missing path: {s}"
        assert (path / "SKILL.md").exists(), f"missing SKILL.md at {path}"


def test_keywords_include_kaggle_and_hackathons():
    keywords = _load().get("keywords") or []
    assert "kaggle" in keywords
    assert "hackathons" in keywords, "v2.1.0 added hackathon support — keyword required"


def test_repository_is_https_github():
    p = _load()
    assert p.get("repository", "").startswith("https://github.com/")


def test_license_is_present():
    assert _load().get("license"), "license field missing"
