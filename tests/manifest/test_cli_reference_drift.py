"""Static drift guard for the documented Kaggle CLI command tree."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_REFERENCE = REPO_ROOT / "skills" / "kaggle" / "modules" / "references" / "cli-reference.md"

REQUIRED_SNIPPETS = [
    "kaggle auth login",
    "kaggle competitions pages",
    "kaggle competitions pages create",
    "kaggle competitions launch",
    "kaggle competitions team-submissions",
    "kaggle competitions episodes",
    "kaggle competitions replay",
    "kaggle competitions logs",
    "kaggle datasets topics list",
    "kaggle kernels logs",
    "kaggle models topics list",
    "kaggle forums topics list",
    "kaggle forums topics show",
    "kaggle benchmarks auth",
    "kaggle benchmarks tasks push",
    "kaggle benchmarks topics list",
    "kaggle quota",
    "--format 'json(title,url,totalComments)'",
    "a430f0b",
]


@pytest.mark.parametrize("snippet", REQUIRED_SNIPPETS)
def test_cli_reference_includes_current_command_surface(snippet: str):
    text = CLI_REFERENCE.read_text(encoding="utf-8")
    assert snippet in text
