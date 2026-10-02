"""Read-only tests against the live https://www.kaggle.com/mcp server.

Skipped by default. Run with `pytest --run-live tests/integration/test_mcp_live.py`.

Nothing here writes to Kaggle. The tools that create, update, upload or submit
are never called. Tests that need a credential use the shared resolver and are
skipped when none is configured; the anonymous tests need nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shared import kaggle_cli
from shared.mcp_client import classify_result, extract_json, mcp_call, mcp_list_tools

pytestmark = pytest.mark.live

REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = REPO_ROOT / "tests" / "fixtures" / "mcp_tools_snapshot.json"
HACKATHON = "kaggle-measuring-agi"


def _request(**fields) -> dict:
    return {"request": fields}


# Tools that answered without credentials on 2026-09-30 (tools/probe_mcp.py).
ANONYMOUS_PROBES: list[tuple[str, dict]] = [
    ("get_competition", _request(competitionName="titanic")),
    ("get_competition_data_files_summary", _request(competitionName="titanic")),
    ("list_competition_data_tree_files", _request(competitionName="titanic", pageSize=3)),
    ("list_competition_pages", _request(competitionName="titanic")),
    ("list_competition_pages", _request(competitionName="playground-series-s6e2")),
    ("list_competition_pages", _request(competitionName=HACKATHON)),
    ("list_competition_topics", _request(competitionName="titanic")),
    ("search_datasets", _request(search="titanic", pageSize=2)),
    ("get_dataset_info", _request(ownerSlug="heptapod", datasetSlug="titanic")),
    ("get_dataset_metadata", _request(ownerSlug="heptapod", datasetSlug="titanic")),
    ("get_dataset_files_summary", _request(ownerSlug="heptapod", datasetSlug="titanic")),
    ("list_dataset_files", _request(ownerSlug="heptapod", datasetSlug="titanic", pageSize=3)),
    ("list_dataset_tree_files", _request(ownerSlug="heptapod", datasetSlug="titanic", pageSize=3)),
    ("get_notebook_info", _request(userName="alexisbcook", kernelSlug="titanic-tutorial")),
    ("list_models", _request(pageSize=2)),
    ("get_model", _request(ownerSlug="google", modelSlug="gemma")),
    ("list_forums", _request()),
    ("get_forum", _request(forumSlug="getting-started")),
    ("list_forum_topics", _request(searchQuery="titanic")),
    ("search_content", _request(filters={"query": "titanic"}, maxPageSize=2)),
    ("get_user_profile", _request(userName="alexisbcook")),
    ("get_benchmark_leaderboard", _request(ownerSlug="kaggle", benchmarkSlug="icml-2025-experts")),
    ("get_hackathon_overview", _request(competitionName=HACKATHON)),
    ("list_hackathon_tracks", _request(competitionName=HACKATHON)),
]

# Tools that answered "Unauthenticated" without credentials and "ok" with them.
CREDENTIAL_PROBES: list[tuple[str, dict]] = [
    ("search_competitions", _request(search="titanic", pageSize=2)),
    ("get_competition_leaderboard", _request(competitionName="titanic", pageSize=2)),
    ("list_competition_data_files", _request(competitionName="titanic", pageSize=3)),
    ("download_competition_data_file", _request(competitionName="titanic", fileName="train.csv")),
    ("download_competition_leaderboard", _request(competitionName="titanic")),
    ("search_competition_submissions", _request(competitionName="titanic", pageSize=2)),
    ("search_notebooks", _request(search="titanic", pageSize=2)),
    (
        "list_notebook_files",
        _request(userName="alexisbcook", kernelSlug="titanic-tutorial", pageSize=3),
    ),
    ("list_model_variations", _request(ownerSlug="google", modelSlug="gemma", pageSize=2)),
    ("get_accelerator_quota", _request()),
    ("list_hackathon_write_ups", _request(competitionName=HACKATHON, pageSize=2)),
]


def _ids(probes):
    return [f"{tool}:{next(iter(args['request'].values()), '')}" for tool, args in probes]


def _status(tool: str, args: dict, token: str = "") -> str:
    """Classify one call. The response body is never put in an assertion message."""
    return classify_result(mcp_call(tool, args, token=token, timeout=60))


@pytest.mark.parametrize("tool,args", ANONYMOUS_PROBES, ids=_ids(ANONYMOUS_PROBES))
def test_public_reads_answer_without_credentials(tool: str, args: dict):
    assert _status(tool, args) == "ok"


@pytest.mark.parametrize("tool,args", CREDENTIAL_PROBES, ids=_ids(CREDENTIAL_PROBES))
def test_other_reads_need_a_credential(kaggle_token, tool: str, args: dict):
    assert _status(tool, args) == "unauthenticated"
    assert _status(tool, args, kaggle_token) == "ok"


def test_an_invalid_bearer_token_is_treated_as_anonymous():
    """A dead token does not give a 401. Public reads still work; the rest say Unauthenticated."""
    bogus = "KGAT_00000000000000000000000000000000"
    assert _status("get_competition", _request(competitionName="titanic"), bogus) == "ok"
    assert _status("get_accelerator_quota", _request(), bogus) == "unauthenticated"


def test_arguments_must_be_inside_the_request_object():
    assert _status("get_competition", {"competitionName": "titanic"}).startswith(
        "error: An error occurred invoking"
    )


def test_search_content_needs_filters():
    assert (
        _status("search_content", _request(query="titanic")) == "error: You must specify `filters`."
    )


def test_missing_competition_is_an_error_not_an_empty_success():
    assert (
        _status("get_competition", _request(competitionName="this-competition-does-not-exist-xyz"))
        == "error: Not found"
    )


def test_winner_filter_is_the_boolean_winner_field(kaggle_token):
    """`winnerStatus` is ignored by the server and returns the whole roster."""

    def total(**extra):
        payload = (
            extract_json(
                mcp_call(
                    "list_hackathon_write_ups",
                    _request(competitionName=HACKATHON, pageSize=1, **extra),
                    token=kaggle_token,
                )
            )
            or {}
        )
        return payload.get("total_count")

    everything, winners, ignored = total(), total(winner=True), total(winnerStatus="WINNER")
    assert winners is not None and everything is not None
    assert 0 < winners < everything
    assert ignored == everything


def test_get_hackathon_write_up_takes_the_roster_row_id(kaggle_token):
    roster = (
        extract_json(
            mcp_call(
                "list_hackathon_write_ups",
                _request(competitionName=HACKATHON, pageSize=1, winner=True),
                token=kaggle_token,
            )
        )
        or {}
    )
    row = roster["hackathon_write_ups"][0]
    row_id, writeup_id = row["id"], row["write_up"]["id"]
    assert (
        _status(
            "get_hackathon_write_up",
            _request(competitionName=HACKATHON, hackathonWriteUpId=row_id),
            kaggle_token,
        )
        == "ok"
    )
    assert _status(
        "get_hackathon_write_up",
        _request(competitionName=HACKATHON, hackathonWriteUpId=writeup_id),
        kaggle_token,
    ).startswith("error:"), "the writeup id is not what this tool takes"
    # The writeup id is what get_writeup takes, and that one is public.
    assert _status("get_writeup", _request(writeUpId=writeup_id)) == "ok"


def test_roster_rows_have_a_url_but_no_slug_or_topic_id(kaggle_token):
    """list_writeups.py derives the slug from the URL because of this."""
    roster = (
        extract_json(
            mcp_call(
                "list_hackathon_write_ups",
                _request(competitionName=HACKATHON, pageSize=1),
                token=kaggle_token,
            )
        )
        or {}
    )
    write_up = roster["hackathon_write_ups"][0]["write_up"]
    assert "/writeups/" in write_up["url"]
    assert "slug" not in write_up and "topic_id" not in write_up


def test_get_dataset_status_answers_for_a_dataset_you_own(kaggle_token):
    listing = kaggle_cli.run(
        ["datasets", "list", "--mine", "--format", "json", "--page-size", "1"], timeout=60
    )
    start, end = listing.stdout.find("["), listing.stdout.rfind("]")
    if listing.returncode != 0 or not 0 <= start < end:
        pytest.skip("could not list this account's datasets")
    rows = json.loads(listing.stdout[start : end + 1])
    if not rows:
        pytest.skip("this account owns no datasets")
    owner, slug = rows[0]["ref"].split("/")[-2:]
    assert (
        _status("get_dataset_status", _request(ownerSlug=owner, datasetSlug=slug), kaggle_token)
        == "ok"
    )
    # For someone else's dataset the server answers "Not found".
    assert (
        _status(
            "get_dataset_status",
            _request(ownerSlug="heptapod", datasetSlug="titanic"),
            kaggle_token,
        )
        == "error: Not found"
    )


def test_tool_list_matches_the_committed_snapshot():
    """Fails when Kaggle adds, removes or changes a tool. Refresh with tools/mcp_snapshot.py."""
    import sys

    sys.path.insert(0, str(REPO_ROOT / "tools"))
    import mcp_snapshot

    live = mcp_snapshot.snapshot_from_tools(
        (mcp_list_tools(timeout=60).get("result") or {}).get("tools", [])
    )
    committed = json.loads(SNAPSHOT.read_text())["tools"]
    assert mcp_snapshot.diff(committed, live) == [], (
        "the live tool list differs from tests/fixtures/mcp_tools_snapshot.json"
    )


def test_tool_list_needs_no_credential_and_has_the_tools_the_scripts_call():
    names = {t["name"] for t in (mcp_list_tools(timeout=60).get("result") or {}).get("tools", [])}
    assert {
        "list_competition_pages",
        "get_hackathon_overview",
        "list_hackathon_write_ups",
        "list_hackathon_tracks",
        "get_writeup",
        "get_writeup_by_topic",
        "get_writeup_by_slug",
        "search_content",
    } <= names
