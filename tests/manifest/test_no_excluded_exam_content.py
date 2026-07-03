"""Ensure the explicitly excluded Kaggle exam content is not vendored here."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = [
    "standardized" + "-agent" + "-exam",
    "standardized" + " agent " + "exam",
    "kaggle" + "-agent" + "-api" + "-key",
]
SKIP_PARTS = {".git", ".pytest_cache", "__pycache__", ".ruff_cache"}


def _text_files():
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        yield path


def test_excluded_exam_content_is_not_present():
    offenders: list[str] = []
    for path in _text_files():
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        if any(phrase in text for phrase in FORBIDDEN):
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, f"excluded Kaggle exam content found in: {offenders}"
