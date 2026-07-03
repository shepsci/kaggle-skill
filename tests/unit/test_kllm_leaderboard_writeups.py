"""Unit tests for skills/kaggle/modules/kllm/scripts/leaderboard_writeups.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "skills" / "kaggle" / "modules" / "kllm" / "scripts" / "leaderboard_writeups.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("leaderboard_writeups", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_competition_slug_normalizes_urls_and_slugs():
    mod = _load_module()
    assert mod.competition_slug("titanic") == "titanic"
    assert mod.competition_slug("https://www.kaggle.com/competitions/titanic/leaderboard") == "titanic"
    assert mod.competition_slug("https://www.kaggle.com/c/connectx") == "connectx"


def test_extract_writeup_links_sorts_dedupes_and_absolutizes():
    mod = _load_module()
    payload = {
        "teams": [
            {
                "teamId": 2,
                "teamName": "Second",
                "privateLeaderboardRank": 2,
                "privateScore": "0.9",
                "solutionWriteUpUrl": "/competitions/example/writeups/second",
            },
            {
                "teamId": 1,
                "teamName": "First",
                "privateLeaderboardRank": 1,
                "privateScore": "0.95",
                "solutionWriteUpUrl": "https://www.kaggle.com/competitions/example/writeups/first",
            },
            {
                "teamId": 3,
                "teamName": "Duplicate",
                "privateLeaderboardRank": 3,
                "solutionWriteUpUrl": "https://www.kaggle.com/competitions/example/writeups/first",
            },
        ]
    }
    rows = mod.extract_writeup_links(payload)
    assert [row["team_name"] for row in rows] == ["First", "Second"]
    assert rows[0]["rank"] == 1
    assert rows[1]["writeup_url"] == "https://www.kaggle.com/competitions/example/writeups/second"


def test_extract_writeup_links_respects_top_k():
    mod = _load_module()
    payload = {
        "leaderboard": [
            {"rank": 1, "solutionWriteupUrl": "/one"},
            {"rank": 2, "solutionWriteupUrl": "/two"},
        ]
    }
    rows = mod.extract_writeup_links(payload, top_k=1)
    assert len(rows) == 1
    assert rows[0]["writeup_url"].endswith("/one")
