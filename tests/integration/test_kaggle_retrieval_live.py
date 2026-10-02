"""Read-only live tests: the skill's own scripts retrieve real content.

Skipped by default. Run with `pytest --run-live tests/integration/test_kaggle_retrieval_live.py`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

SKILL = "skills/kaggle"
LEADERBOARD_WRITEUPS = f"{SKILL}/modules/discussions/scripts/leaderboard_writeups.py"
REFUSAL_PHRASES = (
    "user-generated content",
    "too dangerous",
    "cannot retrieve",
    "can't access that",
    "couldn't do that",
    "could not retrieve",
)

pytestmark = pytest.mark.live


def _run(repo_root: Path, script: str, *args: str, env: dict | None = None):
    import subprocess
    import sys

    return subprocess.run(
        [sys.executable, str(repo_root / script), *args],
        capture_output=True,
        text=True,
        timeout=180,
        env=env,
        check=False,
    )


def _anonymous_env(tmp_path: Path) -> dict:
    """An environment with no Kaggle credential: empty HOME, no KAGGLE_* variables."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("KAGGLE_")}
    env["HOME"] = str(tmp_path)
    return env


def test_competition_pages_work_with_no_credential(repo_root, tmp_path, blocks):
    result = _run(
        repo_root,
        f"{SKILL}/modules/competitions/scripts/competition_pages.py",
        "--competition",
        "titanic",
        "--summary",
        env=_anonymous_env(tmp_path),
    )
    assert result.returncode == 0, result.stderr[:300]
    [block] = blocks(result.stdout)
    assert "rules:            found" in block.body


def test_hackathon_overview_works_with_no_credential(repo_root, tmp_path, blocks):
    result = _run(
        repo_root,
        f"{SKILL}/modules/competitions/hackathons/scripts/hackathon_overview.py",
        "--competition",
        "kaggle-measuring-agi",
        "--summary",
        env=_anonymous_env(tmp_path),
    )
    assert result.returncode == 0, result.stderr[:300]
    assert "rules:       found" in blocks(result.stdout)[0].body


def test_roster_without_a_credential_is_a_clear_failure_not_an_empty_list(repo_root, tmp_path):
    result = _run(
        repo_root,
        f"{SKILL}/modules/competitions/hackathons/scripts/list_writeups.py",
        "--competition",
        "kaggle-measuring-agi",
        "--array",
        env=_anonymous_env(tmp_path),
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert "none were found" in result.stderr


def test_winner_roster_and_writeup_body(repo_root, kaggle_token, blocks):
    roster = _run(
        repo_root,
        f"{SKILL}/modules/competitions/hackathons/scripts/list_writeups.py",
        "--competition",
        "kaggle-measuring-agi",
        "--winner-only",
        "--array",
    )
    assert roster.returncode == 0, roster.stderr[:300]
    body = blocks(roster.stdout)[0].json()
    assert 0 < body["fetched"] == body["total_count"] < 100
    assert body["truncated"] is False
    row = body["rows"][0]
    assert row["slug"] and row["writeup_id"] and row["awarded_prize_ids"]

    writeup = _run(
        repo_root,
        f"{SKILL}/modules/competitions/hackathons/scripts/fetch_writeup.py",
        "--writeup-id",
        str(row["writeup_id"]),
    )
    assert writeup.returncode == 0, writeup.stderr[:300]
    data = blocks(writeup.stdout)[0].json()["data"]
    assert data["title"] == row["title"]
    assert data["message"]["raw_markdown"]


def test_competition_details_report_real_numbers(repo_root, kaggle_token, blocks):
    result = _run(
        repo_root,
        f"{SKILL}/modules/competitions/scripts/competition_details.py",
        "--slug",
        "titanic",
        "--top-n",
        "3",
    )
    assert result.returncode == 0, result.stderr[:300]
    details = blocks(result.stdout)[0].json()
    assert any(f["size"] > 0 for f in details["files"])
    assert any(k["votes"] > 0 for k in details["top_kernels"])
    assert len(details["leaderboard_top"]) == 3


def test_kagglehub_dataset_download_retrieves_a_non_empty_file(tmp_path, monkeypatch):
    kagglehub = pytest.importorskip("kagglehub")
    monkeypatch.setenv("KAGGLEHUB_CACHE", str(tmp_path / "kagglehub-cache"))

    path = Path(kagglehub.dataset_download("heptapod/titanic"))
    files = [file for file in path.rglob("*") if file.is_file()]
    assert files and any(file.stat().st_size > 0 for file in files)


def test_leaderboard_writeups_are_retrieved_and_previewed_without_a_credential(load_script):
    mod = load_script(LEADERBOARD_WRITEUPS)
    competition = os.getenv("KAGGLE_VESUVIUS_COMPETITION", "vesuvius-challenge-surface-detection")

    payload = mod.fetch_leaderboard_payload(competition)
    rows = mod.add_writeup_previews(mod.extract_writeup_links(payload, top_k=3), max_chars=240)
    rendered = json.dumps({"competition": competition, "writeups": rows}).lower()

    assert [row["rank"] for row in rows] == [1, 2, 3]
    assert all(row["writeup_url"].startswith("https://www.kaggle.com/") for row in rows)
    assert all((row.get("preview") or {}).get("title") for row in rows)
    assert all((row.get("preview") or {}).get("excerpt") for row in rows)
    assert not any(phrase in rendered for phrase in REFUSAL_PHRASES)
