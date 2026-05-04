"""Validate every SKILL.md in the repo: frontmatter parses, required fields present."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

SKILL_MD_FILES = list(REPO_ROOT.rglob("SKILL.md"))


def _parse_frontmatter(text: str) -> dict:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    block = text[4:end]
    out: dict = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        out[k.strip()] = v.strip().strip('"')
    return out


@pytest.mark.parametrize("skill_path", SKILL_MD_FILES, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_skill_md_has_frontmatter(skill_path: Path):
    text = skill_path.read_text()
    assert text.startswith("---\n"), f"{skill_path} missing YAML frontmatter"


@pytest.mark.parametrize("skill_path", SKILL_MD_FILES, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_skill_md_has_required_fields(skill_path: Path):
    fm = _parse_frontmatter(skill_path.read_text())
    assert "name" in fm and fm["name"], f"{skill_path}: missing 'name'"
    assert "description" in fm and fm["description"], f"{skill_path}: missing 'description'"


@pytest.mark.parametrize("skill_path", SKILL_MD_FILES, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_skill_md_description_not_too_long(skill_path: Path):
    fm = _parse_frontmatter(skill_path.read_text())
    desc = fm.get("description", "")
    assert len(desc) < 1024, f"{skill_path}: description {len(desc)} chars, marketplace caps below 1024"


def test_at_least_one_skill_md_exists():
    assert SKILL_MD_FILES, "no SKILL.md files found in repo"
