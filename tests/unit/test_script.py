"""Unit tests for skills/kaggle/shared/script.py."""

from __future__ import annotations

import argparse

import pytest

from shared import script


@pytest.mark.parametrize(
    "value, slug",
    [
        ("titanic", "titanic"),
        (" titanic ", "titanic"),
        ("https://www.kaggle.com/competitions/titanic", "titanic"),
        ("https://www.kaggle.com/competitions/titanic/overview/evaluation", "titanic"),
        ("https://www.kaggle.com/c/playground-series-s6e2/data", "playground-series-s6e2"),
        ("competitions/arc-prize-2025", "arc-prize-2025"),
    ],
)
def test_competition_slug(value, slug):
    assert script.competition_slug(value) == slug


@pytest.mark.parametrize("value", ["", "--yes", "../x", "a b", "tit;anic", "x\ny"])
def test_competition_slug_rejects_what_is_not_a_slug(value):
    with pytest.raises(ValueError):
        script.competition_slug(value)


def test_is_handle():
    assert script.is_handle("owner/name", 2)
    assert script.is_handle("google/gemma/transformers/2b-it", 4)
    assert not script.is_handle("owner/name/extra", 2)
    assert not script.is_handle("../name", 2)
    assert not script.is_handle("-x/name", 2)
    assert not script.is_handle("", 2)


def _parser(*names):
    parser = argparse.ArgumentParser(prog="t")
    script.add_competition(parser, *names)
    return parser


@pytest.mark.parametrize(
    "argv, expected",
    [
        (["titanic", "sub.csv"], ["titanic", "sub.csv", None]),
        (["titanic", "sub.csv", "msg"], ["titanic", "sub.csv", "msg"]),
        (["-c", "titanic", "sub.csv"], ["titanic", "sub.csv", None]),
        (["--competition", "titanic", "sub.csv", "msg"], ["titanic", "sub.csv", "msg"]),
        (["--slug", "titanic", "sub.csv"], ["titanic", "sub.csv", None]),
        (["-c", "titanic", "titanic", "sub.csv", "msg"], ["titanic", "sub.csv", "msg"]),
        (["https://www.kaggle.com/c/titanic", "sub.csv"], ["titanic", "sub.csv", None]),
    ],
)
def test_positionals_accept_the_competition_either_way(argv, expected):
    parser = _parser("file", "message?")
    assert script.positionals(parser, parser.parse_args(argv), "file", "message?") == expected


@pytest.mark.parametrize(
    "argv",
    [[], ["titanic"], ["-c", "titanic"], ["-c", "a", "b", "f.csv", "m"], ["bad slug", "f.csv"]],
)
def test_positionals_report_what_is_missing(argv, capsys):
    parser = _parser("file", "message?")
    with pytest.raises(SystemExit) as caught:
        script.positionals(parser, parser.parse_args(argv), "file", "message?")
    assert caught.value.code == 2
    assert "error:" in capsys.readouterr().err


def test_write_gate_is_a_dry_run_without_yes(capsys):
    code = script.write_gate(
        False, action="submit to titanic", details=[("file", "sub.csv")], cost="1 slot"
    )
    out = capsys.readouterr().out
    assert code == 0
    assert out.startswith("Dry run. Nothing was sent to Kaggle.")
    assert "action:" in out and "file:" in out and "cost:" in out
    assert out.rstrip().endswith("Add --yes to do it, after the user has confirmed.")


def test_write_gate_lets_a_confirmed_write_through(capsys):
    assert script.write_gate(True, action="submit to titanic", details=[]) is None
    assert capsys.readouterr().out == "Confirmed with --yes: submit to titanic\n"


@pytest.mark.parametrize("value", ["1", "true", "yes"])
def test_the_read_only_switch_refuses_a_confirmed_write(monkeypatch, capsys, value):
    monkeypatch.setenv(script.READ_ONLY_VAR, value)
    code = script.write_gate(True, action="submit to titanic", details=[("file", "s.csv")])
    out = capsys.readouterr().out
    assert code == 5
    assert out.startswith("Refused: KAGGLE_SKILL_READ_ONLY is set")
    assert "Add --yes" not in out


@pytest.mark.parametrize("value", ["", "0", "false"])
def test_the_read_only_switch_is_off_by_default(monkeypatch, value):
    monkeypatch.setenv(script.READ_ONLY_VAR, value)
    assert not script.read_only()


def test_messages_and_exit_codes(capsys, monkeypatch):
    assert script.missing_package("kaggle", "listing competitions") == 127
    assert script.no_credential("status") == 2
    err = capsys.readouterr().err
    assert "python3 -m pip install 'kaggle>=2.2.4'" in err
    assert "kaggle auth login" in err
    assert err.count("\n") == 2
    assert str(script.state_dir()) == ".kaggle-skill"
    monkeypatch.setenv(script.STATE_DIR_VAR, "/tmp/elsewhere")
    assert str(script.state_dir()) == "/tmp/elsewhere"


def test_positive_int():
    assert script.positive_int("3") == 3
    for bad in ("0", "-1", "x", "1.5"):
        with pytest.raises(argparse.ArgumentTypeError):
            script.positive_int(bad)


def test_a_line_break_inside_a_competition_path_is_refused():
    with pytest.raises(ValueError):
        script.competition_slug("competitions/titanic\n/x")
    assert script.competition_slug("titanic\n") == "titanic", "surrounding space is stripped"


def test_handles_and_tokens_refuse_a_trailing_line_break():
    from shared import credentials

    assert not script.is_handle("me/nb\n", 2)
    assert script.is_handle("me/nb", 2)
    assert credentials.usable_bearer("tok\n") == ""
    assert credentials.usable_bearer("KGAT_abc") == "KGAT_abc"


def test_positionals_can_follow_options():
    """Python 3.11's parse_args rejects `download titanic --unzip ./data`."""
    parser = argparse.ArgumentParser()
    script.add_competition(parser, "dir?")
    parser.add_argument("--unzip", action="store_true")
    args = script.parse(parser, ["titanic", "--unzip", "./data"])
    assert script.positionals(parser, args, "dir?") == ["titanic", "./data"] and args.unzip


def test_the_same_competition_twice_is_not_a_folder():
    parser = argparse.ArgumentParser()
    script.add_competition(parser, "dir?")
    args = script.parse(parser, ["titanic", "-c", "titanic"])
    assert script.positionals(parser, args, "dir?") == ["titanic", None]
    args = script.parse(parser, ["-c", "titanic", "./data"])
    assert script.positionals(parser, args, "dir?") == ["titanic", "./data"]


def test_help_names_every_positional(capsys):
    parser = argparse.ArgumentParser()
    script.add_competition(parser, "file", "message?")
    parser.print_help()
    out = capsys.readouterr().out
    assert "The submission file" in out and "The submission message" in out
