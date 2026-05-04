"""Integration tests against the live https://www.kaggle.com/mcp server.

Skipped by default. Run with `pytest --run-live tests/integration/test_mcp_live.py`.
Requires KAGGLE_API_TOKEN (KGAT-prefixed) in the environment or in
~/.kaggle/access_token. Some endpoints require host/judge access on specific
hackathons; those are marked KNOWN_FAIL/KNOWN_BLOCKED rather than failing.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "skills" / "kaggle"))

from shared.mcp_client import classify_result, mcp_call, mcp_list_tools  # noqa: E402

pytestmark = pytest.mark.live


# (tool_name, arguments, expected_statuses)
# expected_statuses is a tuple of acceptable classify_result outcomes.
TOOL_PROBES: list[tuple[str, dict, tuple[str, ...]]] = [
    # ── Auth ──
    ("authorize", {}, ("ok",)),

    # ── Competition ──
    ("search_competitions", {"request": {"search": "titanic", "hasSearch": True, "pageSize": 2, "hasPageSize": True}}, ("ok",)),
    ("get_competition", {"request": {"competitionName": "spaceship-titanic"}}, ("ok",)),
    ("get_competition_data_files_summary", {"request": {"competitionName": "titanic"}}, ("ok",)),
    ("get_competition_leaderboard", {"request": {"competitionName": "titanic", "pageSize": 2, "hasPageSize": True}}, ("ok",)),
    ("list_competition_data_files", {"request": {"competitionName": "titanic", "pageSize": 3, "hasPageSize": True}}, ("ok",)),
    ("list_competition_data_tree_files", {"request": {"competitionName": "titanic", "pageSize": 3, "hasPageSize": True}}, ("ok",)),
    ("list_competition_pages", {"request": {"competitionName": "titanic"}}, ("ok", "empty")),
    ("download_competition_data_file", {"request": {"competitionName": "titanic", "fileName": "train.csv"}}, ("ok",)),
    ("download_competition_leaderboard", {"request": {"competitionName": "titanic"}}, ("ok",)),
    ("search_competition_submissions", {"request": {"competitionName": "titanic", "sortBy": "Date", "group": "All", "pageSize": 2, "hasPageSize": True}}, ("ok", "empty")),

    # ── Dataset ──
    ("search_datasets", {"request": {"search": "titanic", "hasSearch": True, "pageSize": 2, "hasPageSize": True, "sortBy": "Hottest"}}, ("ok",)),
    ("get_dataset_info", {"request": {"ownerSlug": "heptapod", "datasetSlug": "titanic"}}, ("ok",)),
    ("get_dataset_metadata", {"request": {"ownerSlug": "heptapod", "datasetSlug": "titanic"}}, ("ok",)),
    ("get_dataset_files_summary", {"request": {"ownerSlug": "heptapod", "datasetSlug": "titanic"}}, ("ok",)),
    ("get_dataset_status", {"request": {"ownerSlug": "heptapod", "datasetSlug": "titanic"}}, ("ok",)),
    ("list_dataset_files", {"request": {"ownerSlug": "heptapod", "datasetSlug": "titanic", "pageSize": 3, "hasPageSize": True}}, ("ok",)),
    ("list_dataset_tree_files", {"request": {"ownerSlug": "heptapod", "datasetSlug": "titanic", "pageSize": 3, "hasPageSize": True}}, ("ok",)),

    # ── Notebook ──
    ("search_notebooks", {"request": {"search": "titanic", "hasSearch": True, "pageSize": 2, "hasPageSize": True, "sortBy": "Hotness", "group": "Everyone"}}, ("ok",)),
    ("get_notebook_info", {"request": {"userName": "alexisbcook", "kernelSlug": "titanic-tutorial"}}, ("ok",)),
    ("list_notebook_files", {"request": {"userName": "alexisbcook", "kernelSlug": "titanic-tutorial", "pageSize": 3, "hasPageSize": True}}, ("ok",)),

    # ── Model ──
    ("list_models", {"request": {"pageSize": 2, "hasPageSize": True}}, ("ok",)),
    ("list_model_variations", {"request": {"ownerSlug": "google", "modelSlug": "gemma"}}, ("ok",)),

    # ── Forum ──
    ("list_forums", {"request": {}}, ("ok",)),

    # ── Hackathon (newer surface) ──
    ("get_hackathon_overview", {"request": {"competitionName": "kaggle-measuring-agi"}}, ("ok",)),
    ("list_hackathon_write_ups", {"request": {"competitionName": "kaggle-measuring-agi", "pageSize": 2}}, ("ok",)),
    ("list_hackathon_tracks", {"request": {"competitionName": "kaggle-measuring-agi"}}, ("ok", "empty")),
    # As of 2026-05-04 retest, these endpoints — degraded in the kmcp-tools
    # 2026-04-22 audit — now return ok. Kaggle appears to have shipped fixes.
    # The hackathon module's fallback chain (get_writeup over get_hackathon_write_up)
    # remains defensive but is no longer load-bearing.
    ("get_hackathon_write_up", {"request": {"competitionName": "kaggle-measuring-agi", "hackathonWriteUpId": 1}}, ("ok", "empty", "error: not found", "error: invalid")),
    ("get_benchmark_leaderboard", {"request": {"benchmarkSlug": "x", "ownerSlug": "y"}}, ("ok", "empty", "error: not found")),
    ("get_competition", {"request": {"competitionName": "titanic"}}, ("ok",)),

    # ── Search ──
    ("search_content", {"request": {"search": "titanic", "pageSize": 2, "hasPageSize": True}}, ("ok",)),
]

# Tools the audit shows are KNOWN_FAIL or BLOCKED — record but don't fail the
# suite. Empty as of the 2026-05-04 retest because Kaggle fixed everything
# kmcp-tools had documented as degraded. Keep the parametrize machinery in
# place so future degradations can be flagged with one entry here.
KNOWN_DEGRADED: list[tuple[str, dict, str]] = []


@pytest.mark.parametrize("tool,args,expected", TOOL_PROBES, ids=[t[0] for t in TOOL_PROBES])
def test_endpoint_responds(kgat_token: str, tool: str, args: dict, expected: tuple[str, ...]):
    """Each documented-passing endpoint should classify within an expected status set."""
    resp = mcp_call(tool, args, token=kgat_token)
    status = classify_result(resp)
    assert status in expected, (
        f"{tool}: got status={status}, expected one of {expected}. "
        f"raw={resp}"
    )


@pytest.mark.parametrize("tool,args,reason", KNOWN_DEGRADED, ids=[t[0] for t in KNOWN_DEGRADED])
def test_known_degraded_endpoint_still_degraded(kgat_token: str, tool: str, args: dict, reason: str):
    """Documented-failing endpoints should not silently start passing — that means re-audit time."""
    resp = mcp_call(tool, args, token=kgat_token)
    status = classify_result(resp)
    if status == "ok":
        pytest.fail(
            f"{tool} returned ok but is documented as degraded ({reason}). "
            f"Re-audit endpoints.md against kmcp-tools 2026-04-22."
        )


def test_tools_list_includes_at_least_60_tools(kgat_token: str):
    resp = mcp_list_tools(token=kgat_token)
    tools = resp.get("result", {}).get("tools", [])
    assert len(tools) >= 60, (
        f"server returned only {len(tools)} tools; audit expected ~66"
    )


def test_tools_list_includes_hackathon_endpoints(kgat_token: str):
    resp = mcp_list_tools(token=kgat_token)
    names = {t.get("name") for t in resp.get("result", {}).get("tools", [])}
    expected = {
        "get_hackathon_overview",
        "list_hackathon_write_ups",
        "list_hackathon_tracks",
        "get_writeup",
        "get_writeup_by_topic",
        "get_writeup_by_slug",
    }
    missing = expected - names
    assert not missing, f"missing hackathon/writeup endpoints: {missing}"
