"""Validate the frontmatter of every SKILL.md in the repository."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SKIP_PARTS = {".git", "node_modules", ".venv", "venv"}

SKILL_MD_FILES = sorted(
    p
    for p in REPO_ROOT.rglob("SKILL.md")
    if not any(part in SKIP_PARTS for part in p.relative_to(REPO_ROOT).parts)
)
KAGGLE_SKILL = REPO_ROOT / "skills" / "kaggle" / "SKILL.md"

# The fields the Agent Skills specification defines.
ALLOWED_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}


def frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path} has no YAML frontmatter"
    end = text.index("\n---\n", 4)
    data = yaml.safe_load(text[4:end])
    assert isinstance(data, dict), f"{path}: frontmatter is not a mapping"
    return data


def test_at_least_one_skill_md_exists():
    assert KAGGLE_SKILL in SKILL_MD_FILES


@pytest.mark.parametrize("skill_path", SKILL_MD_FILES, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_frontmatter_follows_the_agent_skills_specification(skill_path: Path):
    fm = frontmatter(skill_path)
    assert set(fm) <= ALLOWED_FIELDS, (
        f"fields outside the specification: {set(fm) - ALLOWED_FIELDS}"
    )
    assert fm["name"] == skill_path.parent.name, "name must equal the folder name"
    assert fm["name"] == fm["name"].lower() and len(fm["name"]) <= 64
    assert 0 < len(fm["description"]) <= 1024
    assert len(fm.get("compatibility", "")) <= 500
    metadata = fm.get("metadata", {})
    assert isinstance(metadata, dict)
    assert isinstance(metadata.get("version"), str), "metadata.version must be a quoted string"


def test_only_read_tools_are_pre_approved():
    """`allowed-tools` grants the listed tools without a prompt for the turn that loads the
    skill. Untrusted Kaggle text is in context in that same turn, so nothing that runs
    commands, writes files or fetches from the network may be listed."""
    assert frontmatter(KAGGLE_SKILL)["allowed-tools"] == "Read Grep Glob"


def test_description_says_when_to_use_and_when_not_to():
    description = frontmatter(KAGGLE_SKILL)["description"]
    assert "Use when" in description
    assert "Do not use" in description


def test_openclaw_metadata_is_in_the_documented_place():
    openclaw = frontmatter(KAGGLE_SKILL)["metadata"]["openclaw"]
    assert openclaw["homepage"] == "https://github.com/shepsci/kaggle-skill"
    assert openclaw["primaryEnv"] == "KAGGLE_API_TOKEN"
    assert openclaw["requires"] == {"bins": ["python3"]}, (
        "the token must not be a hard requirement: a token file or OAuth login also works"
    )
    [token] = openclaw["envVars"]
    assert token["name"] == "KAGGLE_API_TOKEN" and token["required"] is False


def test_compatibility_names_the_dependency_floors():
    compatibility = frontmatter(KAGGLE_SKILL)["compatibility"]
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for requirement in ("kaggle>=2.2.4", "kagglehub>=1.0.2", "requests>=2.32.4"):
        assert requirement in compatibility
        assert f'"{requirement}"' in pyproject


def test_skill_body_is_short_enough_to_load_whole():
    lines = KAGGLE_SKILL.read_text(encoding="utf-8").splitlines()
    assert len(lines) <= 500, "the specification recommends keeping SKILL.md under 500 lines"
