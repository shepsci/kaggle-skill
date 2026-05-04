"""Regression test: the deprecated 'Overlap guard' warning must not reappear."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _all_markdown() -> list[Path]:
    return [p for p in REPO_ROOT.rglob("*.md") if ".git" not in p.parts]


def test_no_overlap_guard_in_any_markdown():
    offenders = []
    for path in _all_markdown():
        text = path.read_text(errors="ignore")
        if "Overlap guard" in text or "overlap guard" in text:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, (
        f"'Overlap guard' phrase found in: {offenders}. "
        "This warning was removed in v2.1.0 — see Part 2 of the plan."
    )


def test_no_kaggle_hackathon_grading_reference_in_markdown():
    offenders = []
    for path in _all_markdown():
        text = path.read_text(errors="ignore")
        if "kaggle-hackathon-grading" in text:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, (
        f"'kaggle-hackathon-grading' referenced in: {offenders}. "
        "Hackathon workflow is now bundled in this skill's hackathon module."
    )


def test_plugin_json_description_does_not_mention_kaggle_hackathon_grading():
    plugin_json = json.loads((REPO_ROOT / ".claude-plugin" / "plugin.json").read_text())
    desc = plugin_json.get("description", "")
    assert "kaggle-hackathon-grading" not in desc
    assert "overlap guard" not in desc.lower()
