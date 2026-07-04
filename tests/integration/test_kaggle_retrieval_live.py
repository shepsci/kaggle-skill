"""Gated live tests that prove Kaggle retrieval succeeds instead of refusing content."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
LEADERBOARD_WRITEUPS = (
    REPO_ROOT / "skills" / "kaggle" / "modules" / "discussions" / "scripts" / "leaderboard_writeups.py"
)
REFUSAL_PHRASES = (
    "user-generated content",
    "too dangerous",
    "cannot retrieve",
    "can't access that",
    "couldn't do that",
    "could not retrieve",
)

pytestmark = pytest.mark.live


def _load_leaderboard_writeups():
    spec = importlib.util.spec_from_file_location("leaderboard_writeups", LEADERBOARD_WRITEUPS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_live_kagglehub_dataset_download_retrieves_non_empty_asset(tmp_path, monkeypatch):
    kagglehub = pytest.importorskip("kagglehub")
    monkeypatch.setenv("KAGGLEHUB_CACHE", str(tmp_path / "kagglehub-cache"))

    path = Path(kagglehub.dataset_download("heptapod/titanic"))
    files = [file for file in path.rglob("*") if file.is_file()]

    assert path.exists()
    assert files, f"dataset_download returned {path}, but no files were retrieved"
    assert any(file.stat().st_size > 0 for file in files)


def test_live_vesuvius_leaderboard_writeups_are_retrieved_and_previewed(kgat_token: str):
    mod = _load_leaderboard_writeups()
    competition = os.getenv(
        "KAGGLE_VESUVIUS_COMPETITION",
        "vesuvius-challenge-surface-detection",
    )

    payload = mod.fetch_leaderboard_payload(competition, kgat_token)
    rows = mod.extract_writeup_links(payload, top_k=3)
    rows = mod.add_writeup_previews(rows, kgat_token, max_chars=240)
    rendered = json.dumps({"competition": competition, "writeups": rows}).lower()

    assert len(rows) == 3
    assert [row["rank"] for row in rows] == [1, 2, 3]
    assert all(row["writeup_url"].startswith("https://www.kaggle.com/") for row in rows)
    assert all((row.get("preview") or {}).get("title") for row in rows)
    assert all((row.get("preview") or {}).get("excerpt") for row in rows)
    assert not any(phrase in rendered for phrase in REFUSAL_PHRASES)
