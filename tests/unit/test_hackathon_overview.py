"""Unit tests for skills/kaggle/modules/competitions/hackathons/scripts/hackathon_overview.py."""

from __future__ import annotations

import pytest

SCRIPT = "skills/kaggle/modules/competitions/hackathons/scripts/hackathon_overview.py"


@pytest.fixture
def mod(load_script):
    return load_script(SCRIPT)


def test_overview_lists_pages_without_a_credential(
    mod, fake_mcp, mcp_response, run_main, blocks, outside
):
    state = fake_mcp({"get_hackathon_overview": mcp_response("get_hackathon_overview_ok")})
    code, out, err = run_main(mod, "example-hackathon")
    assert code == 0 and err == ""
    [call] = state.calls
    assert (call.tool, call.request, call.token) == (
        "get_hackathon_overview",
        {"competitionName": "example-hackathon"},
        "",
    )
    [block] = blocks(out)
    assert block.attrs == {
        "source": "kaggle-mcp",
        "tool": "get_hackathon_overview",
        "competition": "example-hackathon",
    }
    assert block.body.splitlines()[0] == "Pages of example-hackathon (4):"
    assert "Submission Requirements" in block.body
    assert "MISSING" not in out
    assert outside(out).strip() == "Read one with --page NAME; part of the name is enough."


def test_one_page_and_the_older_flags(mod, fake_mcp, mcp_response, run_main, blocks):
    fake_mcp({"get_hackathon_overview": mcp_response("get_hackathon_overview_ok")})
    code, out, _ = run_main(mod, "--competition", "example-hackathon", "--page", "evaluation")
    assert code == 0
    assert blocks(out)[0].body == (
        "## Evaluation\n\nJudging criteria: novelty 30%, impact 30%, execution 40%"
    )
    code, out, _ = run_main(mod, "--competition", "example-hackathon", "--summary")
    assert code == 0 and blocks(out)[0].body.startswith("Pages of example-hackathon")


def test_full_prints_the_servers_answer(mod, fake_mcp, mcp_response, run_main, blocks):
    fake_mcp({"get_hackathon_overview": mcp_response("get_hackathon_overview_ok")})
    document = blocks(run_main(mod, "example-hackathon", "--full")[1])[0].json()
    assert document["status"] == "ok" and document["competition"] == "example-hackathon"
    assert document["data"]["pages"][0]["mime_type"] == "text/markdown"


@pytest.mark.parametrize(
    "fixture, code",
    [("not_found", 1), ("unauthenticated", 2), ("permission_denied", 3), ("invocation_error", 1)],
)
def test_failures_exit_with_the_documented_codes(
    mod, fake_mcp, mcp_response, run_main, blocks, fixture, code
):
    fake_mcp({"get_hackathon_overview": mcp_response(fixture)})
    got, out, err = run_main(mod, "nope")
    assert got == code and out == ""
    assert len(blocks(err)) == 1
