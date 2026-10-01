"""Read-only checks of the installed Kaggle CLI against what the docs and scripts assume.

Skipped by default. Run with `pytest --run-live tests/integration/test_cli_live.py`.
Nothing here writes to Kaggle.
"""

from __future__ import annotations

import json
import re

import pytest

from shared import kaggle_cli

pytestmark = pytest.mark.live


def _run(*args: str):
    return kaggle_cli.run(list(args), timeout=120)


def _json_rows(stdout: str) -> list:
    """The CLI prints a `Next page token` line next to JSON output; read only the array."""
    start, end = stdout.find("["), stdout.rfind("]")
    assert 0 <= start < end, "no JSON array in the output"
    return json.loads(stdout[start : end + 1])


def test_cli_version_is_at_least_the_documented_floor():
    result = _run("--version")
    assert result.returncode == 0
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", result.stdout + result.stderr)
    assert match, "could not read the version"
    assert tuple(int(part) for part in match.groups()) >= (2, 2, 4)


def test_installed_cli_matches_the_committed_command_snapshot():
    """Fails when the CLI gained or lost commands or options. Refresh with tools/cli_snapshot.py."""
    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root / "tools"))
    import cli_snapshot

    committed = json.loads(cli_snapshot.SNAPSHOT.read_text())
    version = cli_snapshot.cli_version(kaggle_cli.kaggle_bin())
    if version != committed["kaggle_version"]:
        pytest.skip(f"installed kaggle {version}; snapshot is for {committed['kaggle_version']}")
    commands, aliases = cli_snapshot.walk(kaggle_cli.kaggle_bin())
    assert cli_snapshot.diff(committed, {"commands": commands, "aliases": aliases}) == []


def test_forums_list_gives_json():
    result = _run("forums", "list", "--format", "json")
    assert result.returncode == 0
    assert _json_rows(result.stdout)


def test_competition_topics_give_json():
    result = _run("competitions", "topics", "list", "titanic", "--page", "1", "--format", "json")
    assert result.returncode == 0
    assert _json_rows(result.stdout)


def test_field_projection_takes_the_fields_the_cli_lists():
    """`json(title,url,totalComments)` is rejected: topics have no such fields."""
    good = _run("competitions", "topics", "list", "titanic", "--format", "json(title,commentCount)")
    assert good.returncode == 0
    assert set(_json_rows(good.stdout)[0]) == {"title", "commentCount"}
    bad = _run(
        "competitions", "topics", "list", "titanic", "--format", "json(title,url,totalComments)"
    )
    assert bad.returncode != 0
    assert "Unknown field in projection" in bad.stdout + bad.stderr


def test_community_competitions_are_a_group():
    result = _run("competitions", "list", "--group", "community", "--format", "json")
    assert result.returncode == 0
    assert kaggle_cli.find_failure(result.stdout) is None


def test_submission_limits_command_exists_and_answers():
    result = _run("competitions", "submission-limits", "titanic")
    assert result.returncode == 0, "the pre-submit check in cli_submit.sh depends on this"


def test_kernel_status_line_has_the_quoted_enum_the_scripts_parse():
    result = _run("kernels", "status", "alexisbcook/titanic-tutorial")
    assert result.returncode == 0
    assert re.search(r' has status "KernelWorkerStatus\.[A-Z_]+"', result.stdout)


def test_config_view_reports_the_signed_in_user():
    from shared import credentials

    ok, username = credentials.verify()
    if not credentials.discover():
        pytest.skip("no Kaggle credential configured")
    assert ok and username
