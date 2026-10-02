#!/usr/bin/env python3
"""Rebuild the demo casts in docs/demo/ from real command output.

    python3 tools/build_casts.py                 # every cast
    python3 tools/build_casts.py competition-brief vesuvius-top-writeups
    python3 tools/build_casts.py --gif-only      # re-render the GIFs from the casts

Each cast is a short list of commands. The commands are run for real and their
output goes into an asciinema v2 file, so a cast always shows what the tools
print today. Three things are changed on the way, and only these:

- terminal colour codes are removed;
- long output is cut, with a line that says how much was left out;
- temporary folder paths are replaced by a short one.

Everything here reads. Nothing is submitted, published or installed into your
own agent configuration: the plugin installs run in throwaway config folders.
The casts are not recordings of an agent session. They show the commands an
agent runs and what comes back.

Needs: the Kaggle CLI, a Kaggle credential for the roster and forum steps, and
Pillow for the GIFs. Casts that need `claude`, `codex`, `agy` or `npx` are
skipped with a note when that program is not installed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = REPO_ROOT / "docs" / "demo"
MEDIA_DIR = DEMO_DIR / "media"
SKILL = "skills/kaggle"
HACKATHONS = f"{SKILL}/modules/competitions/hackathons/scripts"

COLS, ROWS = 100, 30
ANSI_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


@dataclass
class Run:
    """One command: what is shown, what is run, and how much output to keep."""

    shown: str
    argv: list[str]
    max_lines: int = 24
    max_width: int = 160
    env: dict[str, str] = field(default_factory=dict)
    cwd: Path | None = None
    needs: str | None = None
    stderr: bool = False
    stdin: str | None = None


@dataclass
class Cast:
    name: str
    title: str
    intro: list[str]
    steps: list[Run | str]
    outro: list[str] = field(default_factory=list)


def clean(text: str) -> str:
    """Drop colour codes and control characters; normalise line ends."""
    text = ANSI_RE.sub("", text).replace("\r\n", "\n").replace("\r", "\n")
    return CONTROL_RE.sub("", text)


def shorten(text: str, max_lines: int, max_width: int) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    kept = []
    for line in lines[:max_lines]:
        # A block's own tags are kept whole, so the reader can see where it starts and ends.
        whole = line.startswith(("<untrusted-content-", "</untrusted-content-"))
        kept.append(line if whole or len(line) <= max_width else line[: max_width - 1] + "…")
    if len(lines) > max_lines:
        closing = lines[-1] if lines[-1].startswith("</untrusted-content-") else None
        left_out = len(lines) - max_lines - (1 if closing else 0)
        if left_out > 0:
            kept.append(f"… ({left_out} more lines)")
        if closing:
            kept.append(closing)
    return "\n".join(kept)


def execute(step: Run, replacements: dict[str, str]) -> str | None:
    """Run one step and return its cleaned output, or None when it cannot run."""
    if step.needs and not shutil.which(step.needs):
        return None
    # Variables an agent session sets would make some tools behave as if run by that agent.
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("VERBOSE", "VERBOSE_OUTPUT")
        and not k.startswith(("CLAUDE", "ANTHROPIC", "CODEX", "AI_AGENT"))
    }
    env.update(NO_COLOR="1", TERM="dumb", COLUMNS=str(COLS), PYTHONDONTWRITEBYTECODE="1")
    env.update(step.env)
    result = subprocess.run(
        step.argv,
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
        cwd=step.cwd or REPO_ROOT,
        input=step.stdin,
        check=False,
    )
    output = result.stdout + (result.stderr if step.stderr or result.returncode else "")
    output = clean(output)
    for old, new in replacements.items():
        output = output.replace(old, new)
    return shorten(output, step.max_lines, step.max_width)


def build_events(cast: Cast, replacements: dict[str, str]) -> list[list] | None:
    """asciinema events for a cast, or None when a needed program is missing."""
    events: list[list] = []
    clock = 0.2

    def emit(text: str, pause: float) -> None:
        nonlocal clock
        events.append([round(clock, 2), "o", text.replace("\n", "\r\n")])
        clock += pause

    emit("\n".join(cast.intro) + "\n\n", 1.2)
    for step in cast.steps:
        if isinstance(step, str):
            emit(step + "\n", 1.0)
            continue
        output = execute(step, replacements)
        if output is None:
            print(f"  skipped {cast.name}: `{step.needs}` is not installed", file=sys.stderr)
            return None
        emit(f"$ {step.shown}\n", 0.9)
        lines = output.splitlines()
        for start in range(0, len(lines), 12):
            emit("\n".join(lines[start : start + 12]) + "\n", 1.1)
        emit("\n", 0.6)
    if cast.outro:
        emit("\n".join(cast.outro) + "\n", 2.0)
    return events


def write_cast(cast: Cast, events: list[list]) -> Path:
    header = {
        "version": 2,
        "width": COLS,
        "height": ROWS,
        "timestamp": int(time.time()),
        "idle_time_limit": 1.5,
        "env": {"SHELL": "/bin/bash", "TERM": "xterm-256color"},
        "title": cast.title,
    }
    path = DEMO_DIR / f"{cast.name}.cast"
    lines = [json.dumps(header)] + [json.dumps(event, ensure_ascii=False) for event in events]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# ── GIF rendering ────────────────────────────────────────────────────────────

FONT_CANDIDATES = (
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/Monaco.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
    "C:/Windows/Fonts/consola.ttf",
)
BACKGROUND, TEXT, PROMPT, DIM = (13, 17, 23), (201, 209, 217), (126, 231, 135), (139, 148, 158)


def _font(size: int = 14):
    from PIL import ImageFont

    for candidate in FONT_CANDIDATES:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def _screen_lines(text: str) -> list[str]:
    """What a terminal COLS wide shows for ``text``: wrapped lines, last ROWS kept."""
    lines: list[str] = []
    for line in text.replace("\r\n", "\n").split("\n"):
        printable = "".join(ch for ch in line if ord(ch) < 0x2190 or 0x2500 <= ord(ch) < 0x2600)
        while len(printable) > COLS:
            lines.append(printable[:COLS])
            printable = printable[COLS:]
        lines.append(printable)
    if lines and lines[-1] == "":
        lines.pop()
    return lines[-ROWS:]


def render_gif(cast_path: Path) -> Path:
    """Render a cast as an animated GIF: one frame per output event."""
    from PIL import Image, ImageDraw

    rows = cast_path.read_text(encoding="utf-8").splitlines()
    events = [json.loads(row) for row in rows[1:]]
    font = _font()
    left, top, right, bottom = font.getbbox("M")
    cell_w, cell_h = right - left, int((bottom - top) * 1.55)
    pad = 14
    size = (COLS * cell_w + 2 * pad, ROWS * cell_h + 2 * pad)

    frames, durations = [], []
    shown = ""
    for index, (stamp, _, data) in enumerate(events):
        shown += data
        image = Image.new("RGB", size, BACKGROUND)
        draw = ImageDraw.Draw(image)
        for row, line in enumerate(_screen_lines(shown)):
            colour = PROMPT if line.startswith("$ ") else DIM if line.startswith("… (") else TEXT
            draw.text((pad, pad + row * cell_h), line, font=font, fill=colour)
        frames.append(image.quantize(colors=32))
        following = events[index + 1][0] if index + 1 < len(events) else stamp + 4.0
        durations.append(int(max(0.3, min(following - stamp, 2.5)) * 1000))
    durations[-1] = 4000

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    gif_path = MEDIA_DIR / f"{cast_path.stem}.gif"
    frames[0].save(
        gif_path,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
        disposal=1,
    )
    return gif_path


# ── the casts ────────────────────────────────────────────────────────────────


def casts(scratch: Path) -> list[Cast]:
    python = sys.executable
    claude_env = {
        "HOME": str(scratch / "claude-home"),
        "CLAUDE_CONFIG_DIR": str(scratch / "claude-config"),
    }
    codex_env = {
        "HOME": str(scratch / "codex-home-user"),
        "CODEX_HOME": str(scratch / "codex-home"),
    }
    for folder in (*claude_env.values(), *codex_env.values(), str(scratch / "skills-home")):
        Path(folder).mkdir(parents=True, exist_ok=True)

    pages = Run(
        f"python3 {SKILL}/modules/competitions/scripts/competition_pages.py "
        "--competition titanic --summary",
        [
            python,
            f"{SKILL}/modules/competitions/scripts/competition_pages.py",
            "--competition",
            "titanic",
            "--summary",
        ],
        max_width=COLS,
    )
    return [
        Cast(
            "vesuvius-top-writeups",
            "kaggle-skill - Vesuvius top writeups",
            [
                "kaggle-skill: solution writeups of the top teams",
                'Asked of the agent: "retrieve and preview the writeups of the top 3 teams in the',
                'Vesuvius Challenge surface detection competition". The agent runs:',
            ],
            [
                Run(
                    f"python3 {SKILL}/modules/discussions/scripts/leaderboard_writeups.py "
                    "vesuvius-challenge-surface-detection --top-k 3 --preview --pretty",
                    [
                        python,
                        f"{SKILL}/modules/discussions/scripts/leaderboard_writeups.py",
                        "vesuvius-challenge-surface-detection",
                        "--top-k",
                        "3",
                        "--preview",
                        "--pretty",
                    ],
                    max_lines=48,
                )
            ],
            ["No credential was used. The text inside the block is data from Kaggle."],
        ),
        Cast(
            "competition-brief",
            "kaggle-skill - competition briefing",
            ["kaggle-skill: a competition's pages, with no credential"],
            [
                pages,
                Run(
                    f"python3 {SKILL}/modules/competitions/scripts/competition_pages.py "
                    "--competition titanic --page evaluation",
                    [
                        python,
                        f"{SKILL}/modules/competitions/scripts/competition_pages.py",
                        "--competition",
                        "titanic",
                        "--page",
                        "evaluation",
                    ],
                    max_lines=14,
                    max_width=COLS,
                ),
            ],
        ),
        Cast(
            "hackathon-writeups",
            "kaggle-skill - hackathon writeups",
            ["kaggle-skill: a hackathon's overview and its winning writeups"],
            [
                Run(
                    f"python3 {HACKATHONS}/hackathon_overview.py "
                    "--competition kaggle-measuring-agi --summary",
                    [
                        python,
                        f"{SKILL}/modules/competitions/hackathons/scripts/hackathon_overview.py",
                        "--competition",
                        "kaggle-measuring-agi",
                        "--summary",
                    ],
                    max_width=COLS,
                ),
                Run(
                    f"python3 {SKILL}/modules/competitions/hackathons/scripts/list_writeups.py "
                    "--competition kaggle-measuring-agi --winner-only --array",
                    [
                        python,
                        f"{SKILL}/modules/competitions/hackathons/scripts/list_writeups.py",
                        "--competition",
                        "kaggle-measuring-agi",
                        "--winner-only",
                        "--array",
                    ],
                    max_lines=18,
                    max_width=COLS,
                ),
            ],
            ["The roster needs a credential and is limited to hosts, judges and teammates."],
        ),
        Cast(
            "install-and-demo",
            "kaggle-skill - Claude Code install and first workflow",
            [
                "kaggle-skill: install in Claude Code, then two read-only workflows",
                "(installed here from a local checkout, in a throwaway config folder)",
            ],
            [
                Run(
                    "claude plugin marketplace add ./kaggle-skill",
                    ["claude", "plugin", "marketplace", "add", str(REPO_ROOT)],
                    env=claude_env,
                    needs="claude",
                    stderr=True,
                ),
                Run(
                    "claude plugin install kaggle@shepsci",
                    ["claude", "plugin", "install", "kaggle@shepsci"],
                    env=claude_env,
                    needs="claude",
                    stderr=True,
                ),
                pages,
                Run(
                    f"python3 {SKILL}/modules/discussions/scripts/forums.py forum-topics "
                    "--category competition_write_ups --sort-by recent --page-size 2",
                    [
                        python,
                        f"{SKILL}/modules/discussions/scripts/forums.py",
                        "forum-topics",
                        "--category",
                        "competition_write_ups",
                        "--sort-by",
                        "recent",
                        "--page-size",
                        "2",
                    ],
                    max_lines=22,
                    max_width=COLS,
                ),
            ],
        ),
        Cast(
            "codex-install",
            "kaggle-skill - Codex install",
            [
                "kaggle-skill: install in Codex",
                "(installed here from a local checkout, in a throwaway CODEX_HOME)",
            ],
            [
                Run(
                    "codex plugin marketplace add ./kaggle-skill --json",
                    ["codex", "plugin", "marketplace", "add", str(REPO_ROOT), "--json"],
                    env=codex_env,
                    needs="codex",
                    stderr=True,
                ),
                Run(
                    "codex plugin add kaggle@shepsci --json",
                    ["codex", "plugin", "add", "kaggle@shepsci", "--json"],
                    env=codex_env,
                    needs="codex",
                    stderr=True,
                ),
            ],
        ),
        Cast(
            "antigravity-install",
            "kaggle-skill - Antigravity CLI and skills.sh",
            [
                "kaggle-skill: find the skill with the skills CLI, which Antigravity CLI, Cursor",
                "and other agents use. Listing only; add `-a <agent>` to install.",
            ],
            [
                Run("agy --version", ["agy", "--version"], needs="agy"),
                Run(
                    "npx skills add ./kaggle-skill --list",
                    ["npx", "--yes", "skills@latest", "add", str(REPO_ROOT), "--list"],
                    env={
                        "HOME": str(scratch / "skills-home"),
                        "DO_NOT_TRACK": "1",
                        "DISABLE_TELEMETRY": "1",
                    },
                    cwd=scratch / "skills-home",
                    needs="npx",
                    max_lines=40,
                    max_width=COLS,
                ),
            ],
        ),
        Cast(
            "mcp-config",
            "kaggle-skill - Kaggle MCP server",
            ["kaggle-skill: the bundled Kaggle MCP server entry holds no credential"],
            [
                Run("cat .mcp.json", ["cat", ".mcp.json"]),
                "The server lists its tools without a credential:",
                Run(
                    "python3 tools/mcp_snapshot.py --check",
                    [python, "tools/mcp_snapshot.py", "--check"],
                ),
            ],
            ["Sign in from your agent for the tools that need an account."],
        ),
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("names", nargs="*", help="Casts to build (default: all)")
    parser.add_argument(
        "--gif-only",
        action="store_true",
        help="Do not run anything; render GIFs from the existing casts",
    )
    parser.add_argument("--no-gif", action="store_true", help="Write the casts only")
    args = parser.parse_args(argv)

    if args.gif_only:
        for cast_path in sorted(DEMO_DIR.glob("*.cast")):
            if not args.names or cast_path.stem in args.names:
                print(f"rendered {render_gif(cast_path).relative_to(REPO_ROOT)}")
        return 0

    with tempfile.TemporaryDirectory(prefix="kaggle-cast-") as temp:
        scratch = Path(temp).resolve()
        replacements = {
            str(scratch): "/tmp/kaggle-cast",
            str(REPO_ROOT): "./kaggle-skill",
            str(Path.home()): "~",
        }
        known = casts(scratch)
        unknown = set(args.names) - {cast.name for cast in known}
        if unknown:
            parser.error(f"unknown cast: {', '.join(sorted(unknown))}")
        for cast in known:
            if args.names and cast.name not in args.names:
                continue
            events = build_events(cast, replacements)
            if events is None:
                continue
            path = write_cast(cast, events)
            print(
                f"wrote {path.relative_to(REPO_ROOT)} ({len(events)} events, {events[-1][0]:.0f}s)"
            )
            if not args.no_gif:
                print(f"rendered {render_gif(path).relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
