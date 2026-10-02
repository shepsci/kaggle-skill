"""Unit tests for the maintainer tools under tools/ (offline parts only)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import build_plugin  # noqa: E402
import check_oauth_registration  # noqa: E402
import cli_snapshot  # noqa: E402
import mcp_snapshot  # noqa: E402
import probe_mcp  # noqa: E402
import record_session  # noqa: E402

TOOLS = [
    {"name": "authorize", "inputSchema": {"type": "object", "properties": {}}},
    {
        "name": "get_competition",
        "inputSchema": {
            "type": "object",
            "properties": {
                "request": {"type": "object", "properties": {"competitionName": {"type": "string"}}}
            },
        },
    },
]


def test_mcp_snapshot_reduces_tools_to_names_and_fields():
    assert mcp_snapshot.snapshot_from_tools(TOOLS) == {
        "authorize": {"wrapper": False, "fields": []},
        "get_competition": {"wrapper": True, "fields": ["competitionName"]},
    }


def test_mcp_snapshot_diff_names_every_kind_of_change():
    old = mcp_snapshot.snapshot_from_tools(TOOLS)
    new = {
        "get_competition": {"wrapper": True, "fields": ["competitionId", "competitionName"]},
        "get_quota": {"wrapper": True, "fields": []},
    }
    assert mcp_snapshot.diff(old, old) == []
    assert mcp_snapshot.diff(old, new) == [
        "added tool: get_quota",
        "removed tool: authorize",
        "get_competition: new fields competitionId",
    ]


def test_committed_mcp_snapshot_is_well_formed():
    snapshot = json.loads(mcp_snapshot.SNAPSHOT.read_text())
    assert snapshot["count"] == len(snapshot["tools"]) == 71
    assert [n for n, t in snapshot["tools"].items() if not t["wrapper"]] == ["authorize"]


def test_every_tool_in_the_snapshot_is_classified_by_the_probe_tool():
    """A tool the probe script does not know is neither probed nor marked as a write."""
    snapshot = set(json.loads(mcp_snapshot.SNAPSHOT.read_text())["tools"])
    known = (
        probe_mcp.WRITE_TOOLS
        | set(probe_mcp.NOT_PROBED)
        | set(probe_mcp.NO_ARGUMENTS)
        | set(probe_mcp.STATIC_PROBES)
        | set(probe_mcp.DYNAMIC_PROBES)
    )
    assert snapshot - known == set()
    assert known - snapshot == set()


def test_probe_tool_never_calls_a_tool_that_writes():
    callable_tools = set(probe_mcp.STATIC_PROBES) | set(probe_mcp.DYNAMIC_PROBES)
    assert callable_tools & probe_mcp.WRITE_TOOLS == set()
    risky = [
        name
        for name in callable_tools
        if name.startswith(
            ("create_", "update_", "upload_", "save_", "submit_", "cancel_", "start_", "delete_")
        )
    ]
    assert risky == []


def test_cli_snapshot_resolves_commands_and_aliases():
    snapshot = json.loads(cli_snapshot.SNAPSHOT.read_text())
    commands, aliases = snapshot["commands"], snapshot["aliases"]
    resolve = lambda text: cli_snapshot.resolve(text.split(), commands, aliases)  # noqa: E731
    assert resolve("competitions submit titanic -f x.csv") == ("competitions submit", 2)
    assert resolve("c submit titanic") == ("competitions submit", 2)
    assert resolve("models variations versions download a/b/c/d/1") == (
        "models instances versions download",
        4,
    )
    assert resolve("kernels get owner/kernel") == ("kernels pull", 2)
    assert resolve("frobnicate") == (None, 0)


@pytest.mark.parametrize(
    "usage, expected",
    [
        ("usage: kaggle kernels pull [-h] [-p PATH] [kernel]", ["kernels", "pull"]),
        (
            "usage: kaggle competitions pages [competition] list [-h] [-v]",
            ["competitions", "pages", "list"],
        ),
        ("usage: kaggle [-h] [-v] [-W] {competitions,c} ...", []),
        ("kaggle: error: something", []),
    ],
)
def test_usage_path(usage, expected):
    assert cli_snapshot._usage_path(usage) == expected


def test_cli_snapshot_diff():
    old = {"commands": {"a": ["--x"], "b": []}, "aliases": {"c": "a"}}
    new = {"commands": {"a": ["--x", "--y"], "d": []}, "aliases": {}}
    assert cli_snapshot.diff(old, old) == []
    assert cli_snapshot.diff(old, new) == [
        "added command: kaggle d",
        "removed command: kaggle b",
        "kaggle a: new options --y",
        "removed alias: kaggle c",
    ]


# ── tools/build_casts.py ─────────────────────────────────────────────────────


def test_cast_output_is_cleaned_of_terminal_codes():
    import build_casts

    assert build_casts.clean("\x1b[32mok\x1b[0m\r\nnext\x07") == "ok\nnext"


def test_cut_output_says_how_much_was_left_out_and_keeps_the_closing_tag():
    import build_casts

    lines = [
        '<untrusted-content-0a1b2c3d source="kaggle-mcp" tool="t" competition="' + "x" * 90 + '">'
    ]
    lines += [f"line {i} " + "y" * 120 for i in range(30)]
    lines += ["</untrusted-content-0a1b2c3d>"]
    shown = build_casts.shorten("\n".join(lines), max_lines=5, max_width=40).splitlines()
    assert shown[0] == lines[0], "a block's opening tag is never cut"
    assert all(len(line) <= 40 for line in shown[1:5])
    assert shown[5] == "… (26 more lines)"
    assert shown[6] == "</untrusted-content-0a1b2c3d>"
    assert build_casts.shorten("a\nb\n\n", 5, 40) == "a\nb"


def test_gif_screen_wraps_and_scrolls():
    import build_casts

    text = "x" * (build_casts.COLS + 5) + "\r\n" + "\r\n".join(str(i) for i in range(60))
    screen = build_casts._screen_lines(text)
    assert len(screen) == build_casts.ROWS
    assert screen[-1] == "59"
    assert build_casts._screen_lines("y" * (build_casts.COLS + 5))[:2] == [
        "y" * build_casts.COLS,
        "y" * 5,
    ]


def test_every_cast_file_has_a_definition_or_a_recorded_session(tmp_path):
    import build_casts

    defined = {cast.name for cast in build_casts.casts(tmp_path)}
    recorded = {session["name"] for session in build_casts.sessions()}
    committed = {path.stem for path in (REPO_ROOT / "docs" / "demo").glob("*.cast")}
    assert committed == defined | recorded
    assert not defined & recorded


def test_long_lines_wrap_at_words_under_their_own_text():
    import build_casts

    cols = build_casts.COLS
    line = "  deadline:    " + "word " * 12
    rows = build_casts._wrap_row(line.rstrip())
    assert all(len(row) <= cols for row in rows) and len(rows) == 2
    assert rows[1].startswith(" " * 15 + "word"), "the continuation sits under the value"
    assert build_casts._wrap_row("short") == ["short"]
    url = "  url: https://www.kaggle.com/" + "x" * 60
    rows = build_casts._wrap_row(url)
    assert rows[0].startswith("  url: https://") and "".join(r.strip() for r in rows).endswith("x")


def test_the_screen_is_narrow_enough_to_read_on_a_phone():
    """48 columns: GitHub shrinks the image to about 343 pixels on a phone."""
    import build_casts

    assert build_casts.COLS <= 60
    font = build_casts._font()
    width = build_casts.COLS * font.getlength("M") + 36
    assert build_casts.FONT_SIZE * 343 / width >= 10.5


SESSION = {
    "name": "agent-example",
    "title": "An example",
    "recorded": "2026-10-02",
    "agent": "Claude Code (Claude Opus 5.5)",
    "agent_short": "Claude",
    "question": "What is the metric of the Titanic competition on Kaggle?",
    "steps": [
        {
            "command": "python3 scripts/kaggle_skill.py brief titanic",
            "output": '<untrusted-content-0a1b2c3d source="kaggle-mcp">\n'
            + "\n".join(f"line {n}" for n in range(30))
            + "\n</untrusted-content-0a1b2c3d>",
            "show_lines": 4,
        }
    ],
    "answer": "Categorization accuracy.\n- It is the share of passengers predicted correctly.",
}


def test_a_recorded_session_becomes_events_without_running_anything(monkeypatch):
    import build_casts

    def forbidden(*args, **kwargs):
        raise AssertionError("a session is a recording; nothing may be run")

    monkeypatch.setattr(build_casts.subprocess, "run", forbidden)
    events = build_casts.session_events(SESSION)
    text = "".join(event[2] for event in events).replace("\r\n", "\n")
    assert text.startswith("You\n  What is the metric")
    assert "Claude runs\n  $ python3 scripts/kaggle_skill.py brief titanic\n" in text
    assert "  line 2\n  … (27 more lines)\n  </untrusted-content-0a1b2c3d>" in text
    assert "  - It is the share of passengers" in text and text.rstrip().endswith("correctly.")
    stamps = [event[0] for event in events]
    assert stamps == sorted(stamps) and stamps[-1] <= 15


def test_a_session_caption_names_the_commands_that_ran():
    import build_casts

    two = {
        **SESSION,
        "steps": [
            *SESSION["steps"],
            {"command": "S=scripts/kaggle_skill.py; python3 $S pages x; python3 $S brief x"},
        ],
    }
    assert build_casts.session_commands(two) == ["brief", "pages"]
    caption = build_casts.session_caption(two, "agent-example")
    assert "recorded 2026-10-02 in Claude Code (Claude Opus 5.5)" in caption
    assert "ran `brief` and `pages`, then answered" in caption
    assert "docs/demo/sessions/agent-example.json" in caption


def test_a_long_answer_is_cut_on_screen_and_says_so():
    import build_casts

    long = {**SESSION, "answer": "\n".join(f"**point** {n}" for n in range(30))}
    text = "".join(event[2] for event in build_casts.session_events(long))
    assert "point 29" in text and "**" not in text, "all of it, without bold markers"
    cut = "".join(
        event[2] for event in build_casts.session_events({**long, "answer_show_lines": 5})
    )
    assert "point 4" in cut and "point 5" not in cut
    assert "… (25 more lines in the session file)" in cut


def test_a_session_file_must_be_complete(tmp_path):
    import build_casts

    path = tmp_path / "broken.json"
    path.write_text(json.dumps({"name": "x"}))
    with pytest.raises(ValueError, match="has no 'title'"):
        build_casts.load_session(path)


def test_readme_blocks_use_a_recorded_session_only_when_its_gif_exists(monkeypatch, tmp_path):
    import build_casts

    monkeypatch.setattr(build_casts, "MEDIA_DIR", tmp_path)
    hero = {**SESSION, "name": build_casts.HERO_SESSION}
    blocks = build_casts.readme_blocks({hero["name"]: hero})
    assert "competition-brief.gif" in blocks["hero"], "no GIF yet: the command demo stands in"
    (tmp_path / f"{build_casts.HERO_SESSION}.gif").write_bytes(b"GIF89a")
    blocks = build_casts.readme_blocks({hero["name"]: hero})
    assert "> **You:** What is the metric" in blocks["hero"]
    assert f"docs/demo/media/{build_casts.HERO_SESSION}.gif" in blocks["hero"]
    assert "recorded 2026-10-02 in Claude Code (Claude Opus 5.5)" in blocks["hero"]
    assert "Categorization accuracy" not in blocks["hero"], "the GIF and the file hold the answer"
    assert "install-and-demo.gif" in blocks["demos"]
    assert "vesuvius-top-writeups.gif" in blocks["demos"], "until a solutions session exists"

    text = "a\n<!-- hero:start -->\nold\n<!-- hero:end -->\nb\n"
    assert build_casts._replace_block(text, "hero", "new") == (
        "a\n<!-- hero:start -->\nnew\n<!-- hero:end -->\nb\n"
    )
    with pytest.raises(ValueError):
        build_casts._replace_block("no markers", "hero", "x")


# ── check_oauth_registration ─────────────────────────────────────────────────

REGISTRATION_ANSWER = {
    "client_id": "claude-code-(kaggle)",
    "client_secret": "",
    "token_endpoint_auth_method": "none",
}
METADATA_ANSWER = {"registration_endpoint": "https://www.kaggle.com/api/v1/oauth2/register"}


def test_oauth_facts_describe_the_secret_without_keeping_it():
    facts = check_oauth_registration.facts
    assert facts(REGISTRATION_ANSWER, METADATA_ANSWER)["client_secret"] == "empty"
    assert facts({"client_id": "x"}, {})["client_secret"] == "absent"
    with_secret = facts({"client_id": "x", "client_secret": "s3cr3t-value"}, {})
    assert with_secret["client_secret"] == "set"
    assert "s3cr3t-value" not in json.dumps(with_secret)


def test_committed_oauth_snapshot_matches_what_the_tool_would_record():
    snapshot = json.loads(check_oauth_registration.SNAPSHOT.read_text())
    assert snapshot["client_name"] == check_oauth_registration.CLIENT_NAME
    assert set(snapshot["facts"]) == set(
        check_oauth_registration.facts(REGISTRATION_ANSWER, METADATA_ANSWER)
    )


def test_oauth_check_passes_when_kaggle_answers_as_recorded(monkeypatch, capsys):
    recorded = json.loads(check_oauth_registration.SNAPSHOT.read_text())["facts"]
    monkeypatch.setattr(check_oauth_registration, "fetch_live", lambda: dict(recorded))
    assert check_oauth_registration.main(["--check"]) == 0
    assert "matches the snapshot" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ({"client_id": "a1b2c3"}, 'client_id: was "claude-code-(kaggle)", now "a1b2c3"'),
        ({"client_secret": "absent"}, 'client_secret: was "empty", now "absent"'),
        (
            {"token_endpoint_auth_methods_supported": ["none"]},
            'token_endpoint_auth_methods_supported: was null, now ["none"]',
        ),
    ],
)
def test_oauth_check_reports_each_change_inside_a_block(
    change, expected, monkeypatch, capsys, blocks, outside
):
    recorded = json.loads(check_oauth_registration.SNAPSHOT.read_text())["facts"]
    monkeypatch.setattr(check_oauth_registration, "fetch_live", lambda: {**recorded, **change})
    assert check_oauth_registration.main(["--check"]) == 1
    out = capsys.readouterr().out
    (block,) = blocks(out)
    assert block.attrs["source"] == "kaggle-oauth"
    assert expected in block.body
    assert "changed since" in outside(out)
    assert expected not in outside(out)


def test_oauth_check_says_when_kaggle_cannot_be_reached(monkeypatch, capsys):
    def offline():
        raise OSError("no route to host")

    monkeypatch.setattr(check_oauth_registration, "fetch_live", offline)
    assert check_oauth_registration.main(["--check"]) == 2
    assert "could not read Kaggle's OAuth endpoints" in capsys.readouterr().err


# -- build_plugin.py -----------------------------------------------------------


def test_the_plugin_only_build_holds_the_plugin_and_nothing_else(tmp_path, repo_root):
    """What a marketplace or the directory would install from the plugin branch."""
    import shutil

    if not (repo_root / ".git").exists() or not shutil.which("git"):
        pytest.skip("the build copies what git tracks; this is not a git checkout")
    target = tmp_path / "plugin"
    files = build_plugin.build(target)
    top = {name.split("/")[0] for name in files}
    assert top == {
        ".agents",
        ".claude-plugin",
        ".codex-plugin",
        ".mcp.json",
        "CHANGELOG.md",
        "LICENSE",
        "PRIVACY.md",
        "README.md",
        "SECURITY.md",
        "THIRD_PARTY_NOTICES.md",
        "assets",
        "plugin.json",
        "skills",
    }
    assert not {"tests", "tools", "docs", "evals", ".github"} & top
    assert len(files) < 140, "the build is the plugin, not the repository"
    assert not [name for name in files if "__pycache__" in name or name.endswith(".gif")]

    manifest = json.loads((target / ".claude-plugin" / "plugin.json").read_text())
    for skill in manifest["skills"]:
        assert (target / skill / "SKILL.md").is_file()
    assert (target / manifest["icon"]).is_file()
    assert (target / "skills/kaggle/scripts/kaggle_skill.py").is_file()
    assert manifest["version"] in (target / "README.md").read_text()
    # The built copy runs: the entry point lists its commands.
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, str(target / "skills/kaggle/scripts/kaggle_skill.py"), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0 and "brief" in result.stdout


def test_the_build_refuses_a_folder_that_has_files(tmp_path, capsys):
    used = tmp_path / "used"
    used.mkdir()
    (used / "keep.txt").write_text("x")
    assert build_plugin.main([str(used)]) == 2
    assert "is not empty" in capsys.readouterr().err
    assert sorted(p.name for p in used.iterdir()) == ["keep.txt"]


def test_the_icon_is_a_square_png_of_the_size_the_directory_asks_for(repo_root):
    from PIL import Image

    manifest = json.loads((repo_root / ".claude-plugin" / "plugin.json").read_text())
    with Image.open(repo_root / manifest["icon"]) as image:
        assert image.format == "PNG"
        assert image.size[0] == image.size[1] and 512 <= image.size[0] <= 2048


# -- record_session.py ---------------------------------------------------------


def _stub_claude(tmp_path, status: dict) -> str:
    from conftest import write_stub

    return str(write_stub(tmp_path / "bin", "claude", f"#!/bin/sh\necho '{json.dumps(status)}'\n"))


def test_recording_refuses_an_api_key_and_a_non_subscription_login(tmp_path, monkeypatch):
    subscription = {"loggedIn": True, "authMethod": "claude.ai", "subscriptionType": "max"}
    claude = _stub_claude(tmp_path, subscription)
    record_session.check_subscription(claude)  # passes

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    with pytest.raises(SystemExit, match="never use the API"):
        record_session.check_subscription(claude)
    monkeypatch.delenv("ANTHROPIC_API_KEY")

    for status in (
        {"loggedIn": True, "authMethod": "api_key"},
        {"loggedIn": False, "authMethod": "none"},
    ):
        with pytest.raises(SystemExit, match="claude auth login --claudeai"):
            record_session.check_subscription(_stub_claude(tmp_path / str(len(status)), status))


def test_a_session_stream_becomes_a_session_file(tmp_path):
    skill = record_session.SKILL_DIR
    events = [
        # Hook events come before the init event, as in a real stream.
        {"type": "system", "subtype": "hook_started", "hook_name": "SessionStart"},
        {
            "type": "system",
            "subtype": "init",
            "model": "claude-opus-5-5",
            "claude_code_version": "2.1.288",
        },
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "tool_use", "id": "t1", "name": "Skill", "input": {"skill": "kaggle"}},
                    {
                        "type": "tool_use",
                        "id": "t2",
                        "name": "Bash",
                        "input": {
                            "command": f"python3 {skill}/scripts/kaggle_skill.py brief titanic"
                        },
                    },
                    {"type": "tool_use", "id": "t3", "name": "Bash", "input": {"command": "ls"}},
                ]
            },
        },
        {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "t2",
                        "content": [{"type": "text", "text": f"metric: accuracy\n{tmp_path}/x"}],
                    },
                    {"type": "tool_result", "tool_use_id": "t3", "content": "a.txt"},
                ]
            },
        },
        {"type": "result", "result": "The metric is accuracy."},
    ]
    session = record_session.to_session(events, "agent-x", "X", "What metric?", tmp_path)
    assert session["agent"] == "Claude Code 2.1.288 (claude-opus-5-5)"
    assert session["steps"] == [
        {
            "command": "python3 scripts/kaggle_skill.py brief titanic",
            "output": "metric: accuracy\n./x",
            "show_lines": 2,
        }
    ], "only the skill's commands are kept, with the folders shortened"
    assert session["answer"] == "The metric is accuracy."
    with pytest.raises(SystemExit, match="without an answer"):
        record_session.to_session(events[:-1], "agent-x", "X", "Q", tmp_path)


def test_a_session_file_keeps_only_the_lines_a_demo_shows():
    """A writeup is someone's text, and some include contact details: keep its heading."""
    body = "\n".join(['<untrusted-content-ab12cd34 source="s" tool="t">', "# Title", "sub"])
    body += "\nby A, B\nhttps://www.kaggle.com/x\n\n" + "\n".join(
        f"line {n} someone@example.com" for n in range(40)
    )
    body += "\n</untrusted-content-ab12cd34>"
    step = record_session.step("python3 scripts/kaggle_skill.py writeup 71617", body)
    lines = step["output"].splitlines()
    assert lines[1] == "# Title" and lines[-2] == "… (40 more lines)"
    assert lines[-1] == "</untrusted-content-ab12cd34>" and "@" not in step["output"]
    assert step["show_lines"] == len(lines) == 8
    brief = record_session.step("python3 scripts/kaggle_skill.py brief titanic", body)
    assert len(brief["output"].splitlines()) == 12, "ten lines, the count, and the closing tag"


def test_a_recorded_session_sees_no_kaggle_credential(tmp_path, monkeypatch):
    """The agent's shell commands get an empty HOME; Claude Code keeps its own."""
    monkeypatch.setenv("KAGGLE_API_TOKEN", "KGAT_should_not_pass")
    env = record_session.session_env(tmp_path)
    assert "KAGGLE_API_TOKEN" not in env and env["KAGGLE_SKILL_READ_ONLY"] == "1"
    assert env["HOME"] == os.environ["HOME"], "the CLI's own sign-in stays"
    script = Path(env["CLAUDE_ENV_FILE"]).read_text()
    assert script.strip() == f"export HOME={tmp_path}"
    kept = record_session.session_env(None)
    assert "CLAUDE_ENV_FILE" not in kept and kept["KAGGLE_SKILL_READ_ONLY"] == "1"
