"""Unit tests for skills/kaggle/modules/competitions/hackathons/scripts/list_writeups.py."""

from __future__ import annotations

import json
import sys
from unittest.mock import patch

import pytest

SCRIPT = "skills/kaggle/modules/competitions/hackathons/scripts/list_writeups.py"


@pytest.fixture
def mod(load_script):
    return load_script(SCRIPT)


def _ok(payload: dict) -> dict:
    return {
        "result": {"content": [{"type": "text", "text": json.dumps(payload)}], "isError": False},
        "id": 1,
        "jsonrpc": "2.0",
    }


def _run(mod, argv, handler, capsys, token="KGAT_x"):
    calls = []

    def fake_mcp(tool, args, token="", **kw):
        calls.append((tool, args["request"]))
        return handler(tool, args["request"])

    with (
        patch.object(sys, "argv", ["list_writeups.py", *argv]),
        patch.object(mod, "mcp_call", side_effect=fake_mcp),
        patch.object(mod, "resolve_token", return_value=token),
    ):
        rc = mod.main()
    captured = capsys.readouterr()
    return rc, captured.out, captured.err, calls


def test_normalize_row_resolves_track_and_prize_ids(mod):
    row = {
        "id": 1,
        "write_up": {"id": 5, "title": "T", "subtitle": "S", "collaborators": []},
        "hackathon_track_ids": [363, 999],
        "awarded_hackathon_track_prize_ids": [901, 555],
    }
    out = mod.normalize_row(row, {363: "Clinical", 999: "Other"}, {901: "Clinical: Winner"})
    assert out["track_titles"] == ["Clinical", "Other"]
    assert out["awarded_prizes"] == ["Clinical: Winner", "555"]
    assert out["writeup_id"] == 5


def test_normalize_row_takes_the_slug_from_the_roster_url(mod, mcp_response):
    """Roster rows have no slug or topic id. The slug is the last URL segment."""
    payload = json.loads(
        mcp_response("list_hackathon_write_ups_ok")["result"]["content"][0]["text"]
    )
    out = mod.normalize_row(payload["hackathon_write_ups"][0], {363: "Clinical"})
    assert out["slug"] == "team-alpha-writeup"
    assert (
        out["url"]
        == "https://www.kaggle.com/competitions/example-hackathon/writeups/team-alpha-writeup"
    )
    assert out["topic_id"] is None
    assert out["team_name"] == "Team Alpha"
    assert out["authors"] == "Alice Example"
    assert out["template"] is False


def test_normalize_row_falls_back_to_string_id_when_unknown_track(mod):
    out = mod.normalize_row({"id": 1, "write_up": {}, "hackathon_track_ids": [999]}, {})
    assert out["track_titles"] == ["999"]
    assert out["slug"] is None and out["url"] is None


def test_fetch_tracks_returns_id_to_title_map(mod, mcp_response):
    with patch.object(mod, "mcp_call", return_value=mcp_response("list_hackathon_tracks_ok")):
        tracks = mod.fetch_tracks("example-hackathon", "KGAT_x")
    assert tracks == {
        363: "Clinical Workflow Automation",
        364: "Medical Documentation & NLP",
        365: "Health Data Analytics",
    }


def test_prize_titles_carry_the_track_name(mod, mcp_response):
    with patch.object(mod, "mcp_call", return_value=mcp_response("list_hackathon_tracks_ok")):
        tracks = mod.fetch_track_list("example-hackathon")
    assert mod.prize_titles_by_id(tracks) == {
        901: "Clinical Workflow Automation: Winner (1 of 2)",
        902: "Clinical Workflow Automation: Winner (2 of 2)",
    }


def test_fetch_writeups_page_extracts_rows_and_total(mod, mcp_response):
    with patch.object(mod, "mcp_call", return_value=mcp_response("list_hackathon_write_ups_ok")):
        rows, next_token, total, failed = mod.fetch_writeups_page(
            "example-hackathon",
            "KGAT_x",
            page_size=50,
            page_token=None,
            winner_only=False,
        )
    assert [r["id"] for r in rows] == [1001]
    assert (next_token, total, failed) == (None, 1, None)


def test_fetch_writeups_page_returns_the_failed_response(mod, mcp_response):
    denied = mcp_response("permission_denied")
    with patch.object(mod, "mcp_call", return_value=denied):
        rows, next_token, total, failed = mod.fetch_writeups_page("x", "y", 50, None, False)
    assert (rows, next_token, total) == ([], None, None)
    assert failed == denied


def test_winner_filter_uses_the_field_the_server_reads(mod):
    """`winnerStatus` is silently ignored by the server; the field is `winner`."""
    seen = {}

    def fake_mcp(tool, args, token="", **kw):
        seen.update(args["request"])
        return _ok({"hackathon_write_ups": [], "total_count": 0})

    with patch.object(mod, "mcp_call", side_effect=fake_mcp):
        mod.fetch_writeups_page("x", "t", 50, "page-2", True)
    assert seen == {"competitionName": "x", "pageSize": 50, "pageToken": "page-2", "winner": True}
    assert "winnerStatus" not in seen


def test_denied_roster_is_reported_as_a_denial_not_an_empty_list(mod, mcp_response, capsys, blocks):
    def handler(tool, request):
        if tool == "list_hackathon_tracks":
            return mcp_response("list_hackathon_tracks_ok")
        return mcp_response("permission_denied")

    rc, out, err, _ = _run(mod, ["--competition", "x", "--array"], handler, capsys)
    assert rc == 3
    assert out == "", "no roster block may be printed for a denial"
    assert "denied" in blocks(err)[0].body


def test_role_gated_roster_exits_3_with_the_servers_reason(mod, mcp_response, capsys, blocks):
    """The wording Kaggle uses when the account is not a host, judge or teammate."""

    def handler(tool, request):
        if tool == "list_hackathon_tracks":
            return mcp_response("list_hackathon_tracks_ok")
        return mcp_response("roster_denied")

    rc, out, err, _ = _run(mod, ["--competition", "x"], handler, capsys)
    assert rc == 3
    assert out == ""
    assert "Only hosts, judges, or teammates" in blocks(err)[0].body


def test_unauthenticated_roster_exits_2(mod, mcp_response, capsys):
    def handler(tool, request):
        return mcp_response("unauthenticated")

    rc, out, err, _ = _run(mod, ["--competition", "x"], handler, capsys, token="")
    assert rc == 2
    assert out == ""
    assert "none were found" in err


def test_pages_are_followed_and_array_reports_completeness(mod, mcp_response, capsys, blocks):
    page_two = _ok(
        {"hackathon_write_ups": [{"id": 1002, "write_up": {"id": 5002}}], "total_count": 2}
    )

    def handler(tool, request):
        if tool == "list_hackathon_tracks":
            return mcp_response("list_hackathon_tracks_ok")
        return (
            page_two if request.get("pageToken") else mcp_response("list_hackathon_write_ups_page1")
        )

    rc, out, err, calls = _run(mod, ["--competition", "x", "--array"], handler, capsys)
    assert rc == 0
    body = blocks(out)[0].json()
    assert [r["row_id"] for r in body["rows"]] == [1001, 1002]
    assert (body["total_count"], body["fetched"], body["truncated"]) == (2, 2, False)
    assert body["rows"][0]["template"] is True
    assert calls[-1][1]["pageToken"] == "CfDJ8-page-two"


def test_max_pages_marks_the_roster_as_truncated(mod, mcp_response, capsys, blocks):
    def handler(tool, request):
        if tool == "list_hackathon_tracks":
            return mcp_response("list_hackathon_tracks_ok")
        return mcp_response("list_hackathon_write_ups_page1")

    rc, out, err, _ = _run(
        mod, ["--competition", "x", "--array", "--max-pages", "1"], handler, capsys
    )
    assert rc == 0
    assert blocks(out)[0].json()["truncated"] is True
    assert "incomplete" in err


def test_failure_after_the_first_page_keeps_rows_and_exits_1(mod, mcp_response, capsys, blocks):
    def handler(tool, request):
        if tool == "list_hackathon_tracks":
            return mcp_response("list_hackathon_tracks_ok")
        if request.get("pageToken"):
            return mcp_response("invocation_error")
        return mcp_response("list_hackathon_write_ups_page1")

    rc, out, err, _ = _run(mod, ["--competition", "x", "--array"], handler, capsys)
    assert rc == 1
    body = blocks(out)[0].json()
    assert body["fetched"] == 1 and body["truncated"] is True
    assert "incomplete" in err


def test_line_output_is_one_json_object_per_row_inside_one_block(mod, mcp_response, capsys, blocks):
    def handler(tool, request):
        if tool == "list_hackathon_tracks":
            return mcp_response("list_hackathon_tracks_ok")
        return mcp_response("list_hackathon_write_ups_ok")

    rc, out, _, _ = _run(mod, ["--competition", "x"], handler, capsys)
    assert rc == 0
    [block] = blocks(out)
    rows = [json.loads(line) for line in block.body.splitlines()]
    assert rows[0]["awarded_prizes"] == ["Clinical Workflow Automation: Winner (1 of 2)"]


def test_script_does_not_call_get_hackathon_write_up(repo_root):
    text = (repo_root / SCRIPT).read_text()
    assert 'mcp_call("get_hackathon_write_up"' not in text
    assert "mcp_call('get_hackathon_write_up'" not in text
