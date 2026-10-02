"""Every `kaggle ...` command shown in the docs must exist in the Kaggle CLI.

The docs are checked against tests/fixtures/cli_help_snapshot.json, which
tools/cli_snapshot.py builds from `kaggle --help` for the release named in the
snapshot. A command or option that the CLI does not have fails here, offline.

Text between `<!-- cli-check: off -->` and `<!-- cli-check: on -->` is skipped.
That is for commands shown as wrong on purpose and for commands that exist
only on the CLI's main branch.
"""

from __future__ import annotations

import json
import re
import shlex
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import cli_snapshot  # noqa: E402

SNAPSHOT = json.loads((REPO_ROOT / "tests" / "fixtures" / "cli_help_snapshot.json").read_text())
COMMANDS: dict[str, list[str]] = SNAPSHOT["commands"]
ALIASES: dict[str, str] = SNAPSHOT["aliases"]
CLI_REFERENCE = REPO_ROOT / "skills" / "kaggle" / "modules" / "references" / "cli-reference.md"
GLOBAL_FLAGS = {"--help", "--version", "--no-warn"}

OFF, ON = "<!-- cli-check: off -->", "<!-- cli-check: on -->"
CODE_SPAN_RE = re.compile(r"`(kaggle [^`\n]+)`")


def _docs() -> list[Path]:
    docs = [REPO_ROOT / "README.md", REPO_ROOT / "SECURITY.md", REPO_ROOT / "PRIVACY.md"]
    docs += sorted((REPO_ROOT / "docs").rglob("*.md"))
    docs += sorted((REPO_ROOT / "skills").rglob("*.md"))
    docs += sorted((REPO_ROOT / "tests" / "e2e").glob("*.md"))
    return [d for d in docs if d.exists()]


def _checked_text(text: str) -> str:
    """Drop the regions the docs mark as not to be checked."""
    return re.sub(re.escape(OFF) + r".*?" + re.escape(ON), "", text, flags=re.DOTALL)


def kaggle_invocations(text: str) -> list[str]:
    """`kaggle ...` command lines in fenced code blocks and inline code spans."""
    found: list[str] = []
    in_fence = False
    pending = ""
    for raw in _checked_text(text).splitlines():
        stripped = raw.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            pending = ""
            continue
        if in_fence:
            line = pending + stripped
            if line.endswith("\\"):
                pending = line[:-1] + " "
                continue
            pending = ""
            line = " ".join(re.sub(r"^\$\s+", "", line).split())
            if line.startswith("kaggle "):
                found.append(line)
        else:
            found.extend(CODE_SPAN_RE.findall(raw))
    return found


def _children(command: str) -> set[str]:
    prefix = command + " "
    return {name[len(prefix) :].split()[0] for name in COMMANDS if name.startswith(prefix)}


def problems_in(invocation: str) -> list[str]:
    """Why ``invocation`` is not a valid command for the snapshot's CLI, if it is not."""
    line = invocation.split(" | ")[0].split(" && ")[0].split(" > ")[0].split(" #")[0]
    line = re.sub(r"<[^<>\s]*>", "PLACEHOLDER", line)
    try:
        tokens = shlex.split(line)[1:]
    except ValueError:
        return ["cannot be parsed as a shell command"]
    tokens = [t for t in tokens if t not in ("...", "…")]
    if tokens and tokens[0] == "PLACEHOLDER":
        return []
    if not tokens or tokens[0].startswith("-"):
        flags = {t.split("=")[0] for t in tokens if t.startswith("--")}
        return [f"unknown option {flag}" for flag in sorted(flags - GLOBAL_FLAGS)]

    command, used = cli_snapshot.resolve(tokens, COMMANDS, ALIASES)
    if command is None:
        return [f"unknown command `{tokens[0]}`"]
    rest = tokens[used:]
    children = _children(command)
    issues: list[str] = []
    if children and not COMMANDS[command] and rest and not rest[0].startswith("-"):
        if (
            rest[0] not in children
            and f"{command} {rest[0]}" not in ALIASES
            and rest[0] != "PLACEHOLDER"
            and not rest[0].isupper()
        ):
            issues.append(f"`kaggle {command}` has no subcommand `{rest[0]}`")
    allowed = set(COMMANDS[command]) | GLOBAL_FLAGS
    for token in rest:
        if token.startswith("--"):
            flag = token.split("=")[0]
            if flag not in allowed:
                issues.append(f"`kaggle {command}` has no option {flag}")
    return issues


@pytest.mark.parametrize("doc", _docs(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_documented_kaggle_commands_exist(doc: Path):
    failures = []
    for invocation in kaggle_invocations(doc.read_text(encoding="utf-8")):
        for issue in problems_in(invocation):
            failures.append(f"{invocation!r}: {issue}")
    assert not failures, (
        f"{doc.relative_to(REPO_ROOT)} shows commands kaggle "
        f"{SNAPSHOT['kaggle_version']} does not have:\n  " + "\n  ".join(failures)
    )


# ── the checker itself ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "invocation",
    [
        "kaggle competitions submit titanic -f submission.csv -m 'first try'",
        "kaggle c submit titanic -f submission.csv -m msg",
        "kaggle competitions list --group community --format json",
        "kaggle competitions pages titanic --content --page-name rules",
        "kaggle models variations versions download owner/model/pytorch/base/1 -p ./model",
        "kaggle kernels get owner/kernel -p ./nb",
        "kaggle auth login",
        "kaggle --version",
        "kaggle competitions submission-limits <competition>",
        "kaggle datasets list --mine --format json | head",
    ],
)
def test_checker_accepts_real_commands(invocation):
    assert problems_in(invocation) == []


@pytest.mark.parametrize(
    "invocation, issue",
    [
        ("kaggle competitions list --group inClass", None),
        ("kaggle competitions frobnicate titanic", "has no subcommand `frobnicate`"),
        ("kaggle competitions submit titanic --wait", "has no option --wait"),
        ("kaggle kernels list --output-kind visualizations", "has no option --output-kind"),
        ("kaggle search titanic", "unknown command `search`"),
        ("kaggle --verbose", "unknown option --verbose"),
    ],
)
def test_checker_rejects_what_the_cli_lacks(invocation, issue):
    found = problems_in(invocation)
    if issue is None:
        # Option values are not checked, only option names.
        assert found == []
    else:
        assert any(issue in f for f in found), found


def test_checker_reads_code_blocks_spans_and_respects_the_off_switch():
    text = (
        "Run `kaggle auth login` first.\n\n"
        "```bash\n$ kaggle datasets list \\\n    --mine\nkaggle kernels status o/k\n```\n\n"
        f"{OFF}\n```bash\nkaggle search titanic\n```\n{ON}\n"
    )
    assert kaggle_invocations(text) == [
        "kaggle auth login",
        "kaggle datasets list --mine",
        "kaggle kernels status o/k",
    ]


# ── what the reference must cover ────────────────────────────────────────────

REQUIRED_SNIPPETS = [
    "kaggle auth login",
    "kaggle competitions pages",
    "kaggle competitions submission-limits",
    "kaggle competitions team-submissions",
    "kaggle competitions episodes",
    "kaggle competitions list --group community",
    "kaggle datasets topics list",
    "kaggle kernels logs",
    "kaggle models variations create",
    "kaggle forums topics list",
    "kaggle benchmarks tasks push",
    "kaggle quota",
    "Next page token",
    "--help",
]


@pytest.mark.parametrize("snippet", REQUIRED_SNIPPETS)
def test_cli_reference_covers_the_current_command_surface(snippet: str):
    assert snippet in CLI_REFERENCE.read_text(encoding="utf-8")


def test_cli_reference_names_the_version_it_was_checked_with():
    assert f"kaggle {SNAPSHOT['kaggle_version']}" in CLI_REFERENCE.read_text(
        encoding="utf-8"
    ) or SNAPSHOT["kaggle_version"] in CLI_REFERENCE.read_text(encoding="utf-8")
