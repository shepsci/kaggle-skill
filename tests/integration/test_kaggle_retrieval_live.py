"""Read-only live tests: the skill's own commands retrieve real content.

Skipped by default. Run with `pytest --run-live tests/integration/test_kaggle_retrieval_live.py`.
Nothing here writes to Kaggle: every command is a read, and no command is given --yes.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SKILL = "skills/kaggle"
ENTRY = f"{SKILL}/scripts/kaggle_skill.py"
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


def _commands(repo_root: Path) -> dict:
    import importlib.util

    spec = importlib.util.spec_from_file_location("kaggle_skill_entry", repo_root / ENTRY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.COMMANDS


def _run(repo_root: Path, *args: str, env: dict | None = None, bare: bool = False, cwd=None):
    """Run one of the skill's commands through the entry point.

    ``bare`` runs the command's own script with ``python -S``, which hides
    every installed package: what works then needs the standard library only.
    """
    if bare:
        script, first, _, _ = _commands(repo_root)[args[0]]
        command = [sys.executable, "-S", str(repo_root / SKILL / script), *first, *args[1:]]
    else:
        command = [sys.executable, str(repo_root / ENTRY), *args]
    return subprocess.run(
        command, capture_output=True, text=True, timeout=180, env=env, cwd=cwd, check=False
    )


@pytest.fixture
def anonymous(tmp_path) -> dict:
    """An environment with no Kaggle credential: empty HOME, no KAGGLE_* variables."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("KAGGLE_")}
    env["HOME"] = str(tmp_path)
    return env


# -- public reads: no credential, no installed package -----------------------


def test_brief_needs_no_credential_and_no_package(repo_root, anonymous, blocks):
    result = _run(repo_root, "brief", "titanic", env=anonymous, bare=True)
    assert result.returncode == 0, result.stderr[:300]
    [block] = blocks(result.stdout)
    assert "metric:" in block.body and "Categorization Accuracy" in block.body
    assert "deadline:" in block.body and "pages:" in block.body and "data:" in block.body
    assert "you:" not in block.body
    assert len(result.stdout) < 2000, "a brief is short"


def test_pages_list_and_one_page_with_no_credential(repo_root, anonymous, blocks):
    listing = _run(repo_root, "pages", "titanic", env=anonymous, bare=True)
    assert listing.returncode == 0, listing.stderr[:300]
    body = blocks(listing.stdout)[0].body
    assert body.startswith("Pages of titanic (") and "rules" in body and "Evaluation" in body
    assert len(listing.stdout) < 1500, "the listing is short however long the pages are"

    page = _run(repo_root, "pages", "titanic", "--page", "evaluation", env=anonymous, bare=True)
    assert page.returncode == 0
    text = blocks(page.stdout)[0].body
    assert text.startswith("## Evaluation") and "<p>" not in text and "<h2>" not in text


def test_hackathon_overview_works_with_no_credential(repo_root, anonymous, blocks):
    result = _run(repo_root, "hackathon", "kaggle-measuring-agi", env=anonymous, bare=True)
    assert result.returncode == 0, result.stderr[:300]
    assert "rules" in blocks(result.stdout)[0].body


def test_discussions_work_with_no_credential(repo_root, anonymous, blocks):
    topics = _run(
        repo_root, "topics", "--competition", "titanic", "--sort", "top", env=anonymous, bare=True
    )
    assert topics.returncode == 0, topics.stderr[:300]
    lines = blocks(topics.stdout)[0].body.splitlines()
    assert "in the titanic competition" in lines[0] and len(lines) > 5
    topic_id = lines[2].split()[0]
    assert topic_id.isdigit()

    topic = _run(repo_root, "topic", topic_id, "--comments", "2", env=anonymous, bare=True)
    assert topic.returncode == 0, topic.stderr[:300]
    body = blocks(topic.stdout)[0].body
    assert body.startswith("# ") and "votes" in body.splitlines()[1]
    assert len(body.splitlines()) > 4, "the post itself is printed, not only the comments"


def test_solutions_are_previewed_without_a_credential(repo_root, anonymous, blocks):
    competition = os.getenv("KAGGLE_VESUVIUS_COMPETITION", "vesuvius-challenge-surface-detection")
    result = _run(
        repo_root, "solutions", competition, "--top", "3", "--preview", env=anonymous, bare=True
    )
    assert result.returncode == 0, result.stderr[:300]
    body = blocks(result.stdout)[0].body
    assert all(f"#{rank}" in body for rank in (1, 2, 3))
    assert body.count("https://www.kaggle.com/") >= 3
    assert not any(phrase in body.lower() for phrase in REFUSAL_PHRASES)


def test_leaderboard_writeup_functions(load_script):
    mod = load_script(LEADERBOARD_WRITEUPS)
    competition = os.getenv("KAGGLE_VESUVIUS_COMPETITION", "vesuvius-challenge-surface-detection")
    payload = mod.fetch_leaderboard_payload(competition)
    rows = mod.add_writeup_previews(mod.extract_writeup_links(payload, top_k=3), max_chars=240)
    assert [row["rank"] for row in rows] == [1, 2, 3]
    assert all(row["writeup_url"].startswith("https://www.kaggle.com/") for row in rows)
    assert all((row.get("preview") or {}).get("title") for row in rows)
    assert all((row.get("preview") or {}).get("excerpt") for row in rows)


def test_doctor_on_a_bare_machine_says_public_reads_work(repo_root, anonymous):
    env = {**anonymous, "PATH": "/usr/bin:/bin"}
    result = _run(repo_root, "doctor", env=env, bare=True)
    assert result.returncode == 0, result.stdout[-400:]
    assert "yes  public reads" in result.stdout
    assert "no   reads on your account" in result.stdout
    assert "none found" in result.stdout


# -- what needs a credential says so -----------------------------------------


@pytest.mark.parametrize(
    "argv",
    [
        ["status", "titanic"],
        ["leaderboard", "titanic", "--no-save"],
        ["competitions"],
        ["details", "titanic"],
        ["watch", "titanic", "--timeout", "0"],
        ["writeups", "kaggle-measuring-agi"],
    ],
)
def test_account_commands_without_a_credential_exit_2(repo_root, anonymous, argv, tmp_path):
    result = _run(repo_root, *argv, env=anonymous, cwd=tmp_path)
    assert result.returncode == 2, result.stderr[:300]
    assert result.stdout == ""
    assert "credential" in result.stderr or "Kaggle account" in result.stderr


# -- reads on the account ----------------------------------------------------


def test_winner_roster_and_writeup_body(repo_root, kaggle_token, blocks):
    roster = _run(repo_root, "writeups", "kaggle-measuring-agi", "--winners", "--full")
    assert roster.returncode == 0, roster.stderr[:300]
    body = blocks(roster.stdout)[0].json()
    assert 0 < body["fetched"] == body["total_count"] < 100
    assert body["truncated"] is False
    row = body["rows"][0]
    assert row["slug"] and row["writeup_id"] and row["awarded_prize_ids"]

    short = _run(repo_root, "writeups", "kaggle-measuring-agi", "--winners")
    assert short.returncode == 0 and len(short.stdout) < len(roster.stdout) / 2

    writeup = _run(repo_root, "writeup", str(row["writeup_id"]))
    assert writeup.returncode == 0, writeup.stderr[:300]
    text = blocks(writeup.stdout)[0].body
    assert text.startswith(f"# {row['title']}")

    full = _run(repo_root, "writeup", str(row["writeup_id"]), "--full")
    data = blocks(full.stdout)[0].json()["data"]
    assert data["message"]["raw_markdown"]
    assert len(writeup.stdout) < len(full.stdout), "the default prints the body once"


def test_competition_details_report_real_numbers(repo_root, kaggle_token, blocks):
    result = _run(repo_root, "details", "titanic", "--top", "3", "--json")
    assert result.returncode == 0, result.stderr[:300]
    details = blocks(result.stdout)[0].json()
    assert any(f["size"] > 0 for f in details["files"])
    assert any(k["votes"] > 0 for k in details["top_kernels"])
    assert len(details["leaderboard_top"]) == 3


def test_competition_listing_is_short_and_real(repo_root, kaggle_token, blocks):
    result = _run(repo_root, "competitions", "--days", "30", "--limit", "10")
    assert result.returncode == 0, result.stderr[:300]
    lines = blocks(result.stdout)[0].body.splitlines()
    assert "competitions in the last 30 days" in lines[0]
    assert 2 < len(lines) <= 12 and all(len(line) < 160 for line in lines)


def test_status_and_leaderboard_read_the_account(repo_root, kaggle_token, blocks, tmp_path):
    status = _run(repo_root, "status", "titanic", "--json", cwd=tmp_path)
    assert status.returncode == 0, status.stderr[:300]
    report = blocks(status.stdout)[0].json()
    assert report["competition"]["metric"] and report["competition"]["deadline"]
    assert report["quota"].get("gpu_quota"), "the weekly quota is reported"
    assert kaggle_token not in status.stdout + status.stderr

    board = _run(repo_root, "leaderboard", "titanic", "--top", "3", "--no-save", cwd=tmp_path)
    assert board.returncode == 0, board.stderr[:300]
    assert "Public leaderboard of titanic" in blocks(board.stdout)[0].body
    assert not (tmp_path / ".kaggle-skill").exists(), "--no-save writes nothing"


def test_submit_dry_run_reads_the_limits_and_sends_nothing(repo_root, kaggle_token, tmp_path):
    submission = tmp_path / "submission.csv"
    submission.write_text("PassengerId,Survived\n892,0\n")
    result = _run(
        repo_root, "submit", "titanic", str(submission), "-m", "live dry run", cwd=tmp_path
    )
    assert result.returncode == 0, result.stderr[:300]
    assert result.stdout.startswith("Dry run. Nothing was sent to Kaggle.")
    assert "submissions left today" in result.stdout or "submissions a day" in result.stdout
    assert not (tmp_path / ".kaggle-skill").exists(), "a dry run records nothing"


def test_kagglehub_dataset_download_retrieves_a_non_empty_file(tmp_path, monkeypatch):
    kagglehub = pytest.importorskip("kagglehub")
    monkeypatch.setenv("KAGGLEHUB_CACHE", str(tmp_path / "kagglehub-cache"))

    path = Path(kagglehub.dataset_download("heptapod/titanic"))
    files = [file for file in path.rglob("*") if file.is_file()]
    assert files and any(file.stat().st_size > 0 for file in files)


def test_live_output_keeps_readable_text(repo_root, anonymous, blocks):
    """No escape codes for ordinary characters: a title with a dash prints the dash."""
    result = _run(repo_root, "brief", "titanic", "--json", env=anonymous, bare=True)
    info = blocks(result.stdout)[0].json()
    assert "\\u" not in json.dumps(info["title"], ensure_ascii=False)
