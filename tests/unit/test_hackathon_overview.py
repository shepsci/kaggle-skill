"""Unit tests for skills/kaggle/modules/competitions/hackathons/scripts/hackathon_overview.py."""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

SCRIPT = "skills/kaggle/modules/competitions/hackathons/scripts/hackathon_overview.py"


@pytest.fixture
def mod(load_script):
    return load_script(SCRIPT)


def _run(mod, argv, response, capsys, token=""):
    sent = {}

    def fake_mcp(tool, args, token="", **kw):
        sent.update(tool=tool, args=args, token=token)
        return response

    with (
        patch.object(sys, "argv", ["hackathon_overview.py", *argv]),
        patch.object(mod, "mcp_call", side_effect=fake_mcp),
        patch.object(mod, "resolve_token", return_value=token),
    ):
        rc = mod.main()
    captured = capsys.readouterr()
    return rc, captured.out, captured.err, sent


def test_find_page_matches_by_substring(mod):
    pages = [{"name": "rules", "content": "x"}, {"name": "rubric", "content": "y"}]
    assert mod.find_page(pages, "rule") == pages[0]
    assert mod.find_page(pages, "rubric", "judging") == pages[1]


def test_find_page_returns_none_when_no_match(mod):
    assert mod.find_page([{"name": "overview"}], "rule", "rubric") is None
    assert mod.find_page(None, "rule") is None


def test_find_page_case_insensitive(mod):
    pages = [{"name": "Official Rules", "content": "..."}]
    assert mod.find_page(pages, "official") == pages[0]


def test_fetch_overview_returns_pages_array(mod, mcp_response):
    with patch.object(mod, "mcp_call", return_value=mcp_response("get_hackathon_overview_ok")):
        result = mod.fetch_overview("example-hackathon")
    assert result["status"] == "ok"
    names = [p["name"] for p in result["data"]["pages"]]
    assert names == ["rules", "Description", "Submission Requirements", "Evaluation"]


@pytest.mark.parametrize(
    "fixture, status",
    [
        ("permission_denied", "error: Permission 'kernels.get' was denied"),
        ("not_found", "error: Not found"),
        ("unauthenticated", "unauthenticated"),
    ],
)
def test_fetch_overview_reports_server_failures(mod, mcp_response, fixture, status):
    with patch.object(mod, "mcp_call", return_value=mcp_response(fixture)):
        result = mod.fetch_overview("x", "KGAT_x")
    assert result["status"] == status


def test_overview_works_without_a_credential(mod, mcp_response, capsys, blocks, outside):
    rc, out, err, sent = _run(
        mod,
        ["--competition", "example-hackathon"],
        mcp_response("get_hackathon_overview_ok"),
        capsys,
    )
    assert rc == 0
    assert sent["token"] == ""
    assert sent["args"] == {"request": {"competitionName": "example-hackathon"}}
    [block] = blocks(out)
    assert block.attrs["tool"] == "get_hackathon_overview"
    assert block.attrs["competition"] == "example-hackathon"
    assert block.json()["data"]["pages"][0]["name"] == "rules"
    assert outside(out).strip() == ""


def test_summary_stays_inside_the_block(mod, mcp_response, capsys, blocks, outside):
    rc, out, _, _ = _run(
        mod, ["--competition", "x", "--summary"], mcp_response("get_hackathon_overview_ok"), capsys
    )
    assert rc == 0
    body = blocks(out)[0].body
    assert "page count: 4" in body
    assert "rules:       found" in body
    assert "rubric:      found" in body
    assert outside(out).strip() == ""


def test_missing_hackathon_exits_nonzero_with_no_stdout(mod, mcp_response, capsys):
    rc, out, err, _ = _run(mod, ["--competition", "nope"], mcp_response("not_found"), capsys)
    assert rc == 1
    assert out == ""
    assert "Not found" in err
