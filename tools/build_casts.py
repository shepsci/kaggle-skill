#!/usr/bin/env python3
"""Rebuild the demos in docs/demo/: asciinema casts and their GIFs.

    python3 tools/build_casts.py                 # every demo
    python3 tools/build_casts.py competition-brief vesuvius-top-writeups
    python3 tools/build_casts.py --gif-only      # re-render the GIFs from the casts
    python3 tools/build_casts.py --readme        # also refresh the demo blocks in README.md

There are two kinds of demo.

A command demo is a short list of commands. They are run for real and their
output goes into the cast, so it shows what the tools print today. Three
things are changed on the way, and only these: terminal colour codes are
removed, long output is cut with a line that says how much was left out, and
temporary folder paths are replaced by a short one.

A session demo is a recorded agent session, kept as a JSON file in
docs/demo/sessions/: the question a person asked, the commands the agent ran
with what they printed, and the agent's answer. Nothing is run when it is
rebuilt; the file is the recording.

The screen is 48 columns wide, so that the type stays about 11 pixels tall
when GitHub shrinks the image to a phone's width. Commands are typed and
output scrolls a few lines at a time.

Everything here reads. Nothing is submitted, published or installed into your
own agent configuration: the plugin installs run in throwaway config folders.

Needs: the Kaggle CLI and Pillow. Demos that need `claude` or `codex` are
skipped with a note when that program is not installed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
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

SESSIONS_DIR = DEMO_DIR / "sessions"
README = REPO_ROOT / "README.md"

# 48 columns of 20-pixel type are about 11 pixels tall on a 375-pixel phone.
COLS, ROWS = 48, 20
FONT_SIZE = 20
TYPING_CHUNK = 9  # characters per typing frame
SCROLL_LINES = 3  # lines of output per frame
ANSI_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


@dataclass
class Run:
    """One command: what is shown, what is run, and how much output to keep."""

    shown: str
    argv: list[str]
    max_lines: int = 14
    max_width: int = 200
    env: dict[str, str] = field(default_factory=dict)
    cwd: Path | None = None
    needs: str | None = None
    stderr: bool = False
    stdin: str | None = None
    # Run with an empty home folder and no Kaggle variables: the reader sees
    # what anyone gets, and nothing about the maintainer's account.
    anonymous: bool = False


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


BLOCK_OPEN_RE = re.compile(r"<untrusted-content-([0-9a-f]{8})[ >]")


def _closing_of_open_block(shown: list[str], rest: list[str]) -> str | None:
    """The closing tag, somewhere in ``rest``, of the block left open in ``shown``."""
    nonce = None
    for line in shown:
        opened = BLOCK_OPEN_RE.match(line)
        if opened:
            nonce = opened.group(1)
        elif line.startswith("</untrusted-content-"):
            nonce = None
    closing = f"</untrusted-content-{nonce}>"
    return closing if nonce and closing in rest else None


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
        # A cut inside a block still shows the block's closing tag, after the count.
        closing = _closing_of_open_block(lines[:max_lines], lines[max_lines:])
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
    if step.anonymous:
        env = {k: v for k, v in env.items() if not k.startswith("KAGGLE")}
        env["HOME"] = replacements["__anonymous_home__"]
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
        if not old.startswith("__"):
            output = output.replace(old, new)
    return shorten(output, step.max_lines, step.max_width)


class Recorder:
    """Collects asciinema events: typed commands, and output a few lines at a time."""

    def __init__(self) -> None:
        self.events: list[list] = []
        self.clock = 0.2

    def emit(self, text: str, pause: float) -> None:
        self.events.append([round(self.clock, 2), "o", text.replace("\n", "\r\n")])
        self.clock += pause

    def say(self, text: str, pause: float = 0.6) -> None:
        self.emit(text + "\n", pause)

    def type(self, text: str, prefix: str = "$ ") -> None:
        self.emit(prefix, 0.15)
        for start in range(0, len(text), TYPING_CHUNK):
            self.emit(text[start : start + TYPING_CHUNK], 0.07)
        self.emit("\n", 0.35)

    def scroll(self, text: str, pace: float = 0.16) -> None:
        lines = text.splitlines()
        for start in range(0, len(lines), SCROLL_LINES):
            self.emit("\n".join(lines[start : start + SCROLL_LINES]) + "\n", pace)


def build_events(cast: Cast, replacements: dict[str, str]) -> list[list] | None:
    """asciinema events for a command demo, or None when a needed program is missing."""
    rec = Recorder()
    rec.say("\n".join(cast.intro) + "\n", 0.8)
    for step in cast.steps:
        if isinstance(step, str):
            rec.say(step, 0.6)
            continue
        output = execute(step, replacements)
        if output is None:
            print(f"  skipped {cast.name}: `{step.needs}` is not installed", file=sys.stderr)
            return None
        rec.type(step.shown)
        rec.scroll(output)
        rec.emit("\n", 0.5)
    if cast.outro:
        rec.say("\n".join(cast.outro), 1.5)
    return rec.events


# ── recorded agent sessions ──────────────────────────────────────────────────


def wrap(text: str, width: int = COLS - 2, indent: str = "  ") -> str:
    """Wrap prose to the screen, keeping paragraphs and list lines apart."""
    import textwrap

    out: list[str] = []
    for paragraph in text.splitlines():
        if not paragraph.strip():
            out.append("")
            continue
        hanging = indent + ("  " if paragraph.lstrip().startswith(("- ", "* ")) else "")
        out += textwrap.wrap(
            paragraph.strip(), width=width, initial_indent=indent, subsequent_indent=hanging
        ) or [""]
    return "\n".join(out)


def load_session(path: Path) -> dict:
    session = json.loads(path.read_text(encoding="utf-8"))
    for key in ("name", "title", "recorded", "agent", "question", "steps", "answer"):
        if key not in session:
            raise ValueError(f"{path.name}: the session has no {key!r}")
    return session


def session_events(session: dict) -> list[list]:
    """asciinema events for a recorded agent session. Nothing is run."""
    rec = Recorder()
    rec.say("You", 0.3)
    rec.scroll(wrap(session["question"]), 0.35)
    rec.emit("\n", 0.9)
    for step in session["steps"]:
        rec.say(f"{session.get('agent_short', 'Agent')} runs", 0.3)
        rec.type(step["command"], prefix="  $ ")
        output = shorten(clean(step["output"]), int(step.get("show_lines", 10)), 200)
        rec.scroll("\n".join("  " + line for line in output.splitlines()))
        rec.emit("\n", 0.5)
    rec.say(session.get("agent_short", "Agent"), 0.3)
    # A terminal draws no bold: the markers would show as asterisks.
    answer = wrap(session["answer"].replace("**", "")).splitlines()
    limit = int(session.get("answer_show_lines") or len(answer))
    if len(answer) > limit:
        # A long answer is cut on screen; the session file holds all of it.
        answer = [*answer[:limit], f"  … ({len(answer) - limit} more lines in the session file)"]
    rec.scroll("\n".join(answer), 0.3)
    return rec.events


def session_commands(session: dict) -> list[str]:
    """The skill's commands a session ran, by name, in the order they first ran."""
    names: list[str] = []
    for step in session["steps"]:
        for name in re.findall(r"kaggle_skill\.py\s+([a-z][a-z-]*)", step["command"]):
            if name not in names:
                names.append(name)
        # `S=.../kaggle_skill.py; python3 $S validate ...` names the command after $S.
        for name in re.findall(r"\$S\s+([a-z][a-z-]*)", step["command"]):
            if name not in names:
                names.append(name)
    return names


def session_caption(session: dict, name: str) -> str:
    """One line under a session's GIF: when, in what, what ran, and where the rest is."""
    commands = " and ".join(f"`{command}`" for command in session_commands(session))
    return (
        f"A real session, recorded {session['recorded']} in {session['agent']}: the agent "
        f"ran {commands}, then answered. "
        f"[The whole answer](docs/demo/sessions/{name}.json), "
        f"[cast](docs/demo/{name}.cast)."
    )


def write_cast(name: str, title: str, events: list[list]) -> Path:
    header = {
        "version": 2,
        "width": COLS,
        "height": ROWS,
        "timestamp": int(time.time()),
        "idle_time_limit": 1.5,
        "env": {"SHELL": "/bin/bash", "TERM": "xterm-256color"},
        "title": title,
    }
    path = DEMO_DIR / f"{name}.cast"
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
BACKGROUND, TEXT, PROMPT, DIM = (13, 17, 23), (201, 209, 217), (126, 231, 135), (125, 133, 144)
ACCENT, BRIGHT = (240, 183, 92), (240, 246, 252)
SPEAKERS = ("You", "Agent", "Claude")


def _font(size: int = FONT_SIZE):
    from PIL import ImageFont

    for candidate in FONT_CANDIDATES:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def _printable(line: str) -> str:
    """Characters the monospace font draws at one cell each."""
    return "".join(ch for ch in line if ord(ch) < 0x2190 or 0x2500 <= ord(ch) < 0x2600)


def _screen_rows(text: str) -> list[tuple[str, tuple[int, int, int]]]:
    """What a terminal COLS wide shows for ``text``: wrapped rows with their colour."""
    rows: list[tuple[str, tuple[int, int, int]]] = []
    answering = False
    for line in text.replace("\r\n", "\n").split("\n"):
        printable = _printable(line)
        stripped = printable.strip()
        first = stripped.split(" ")[0] if stripped else ""
        if printable in SPEAKERS or (first in SPEAKERS and stripped.endswith("runs")):
            colour = ACCENT
            answering = printable in SPEAKERS
        elif stripped.startswith("$ "):
            colour, answering = PROMPT, False
        elif stripped.startswith(("<untrusted-content-", "</untrusted-content-", "… (")):
            colour = DIM
        elif answering:
            colour = BRIGHT
        else:
            colour = TEXT
        rows += [(row, colour) for row in _wrap_row(printable)]
    if rows and rows[-1][0] == "":
        rows.pop()
    return rows[-ROWS:]


# A short label near the left edge: `  metric:   value`, a list mark, a prompt.
_LABEL_RE = re.compile(r"^(\s{0,4}(?:[A-Za-z][\w ()]{0,16}:|[-*]|\d+\.|\$|#+|\[\d+\])\s+)\S")


def _wrap_row(line: str) -> list[str]:
    """Break a long line at spaces, with the continuation under the line's own text."""
    if len(line) <= COLS:
        return [line]
    lead = len(line) - len(line.lstrip(" "))
    label = _LABEL_RE.match(line)
    hang = min(len(label.group(1)) if label else lead, COLS // 2)
    rows: list[str] = []
    current = " " * lead
    for word in line[lead:].split(" "):
        gap = " " if current.strip() else ""
        if len(current) + len(gap) + len(word) <= COLS:
            current += gap + word
            continue
        label_only = label is not None and not rows and current.strip() == label.group(1).strip()
        if current.strip() and not label_only:
            rows.append(current.rstrip())
            current = " " * hang + word
        else:
            current += gap + word
        while len(current) > COLS:  # one word longer than the screen: a URL, a tag
            rows.append(current[:COLS])
            current = " " * hang + current[COLS:]
    rows.append(current)
    return rows


def _screen_lines(text: str) -> list[str]:
    """The rows of the screen as text."""
    return [row for row, _ in _screen_rows(text)]


def _palette():
    """One palette for every frame: the background, each text colour, and the
    shades between them that smooth the edges of the letters."""
    from PIL import Image

    colours = [BACKGROUND]
    for colour in (TEXT, PROMPT, DIM, ACCENT, BRIGHT):
        for step in range(1, 7):
            colours.append(tuple(int(b + (c - b) * step / 6) for b, c in zip(BACKGROUND, colour)))
    flat = [channel for colour in colours for channel in colour]
    image = Image.new("P", (1, 1))
    image.putpalette(flat + [0] * (768 - len(flat)))
    return image


def render_gif(cast_path: Path) -> Path:
    """Render a cast as an animated GIF: one frame per output event."""
    from PIL import Image, ImageDraw

    rows = cast_path.read_text(encoding="utf-8").splitlines()
    events = [json.loads(row) for row in rows[1:]]
    font = _font()
    cell_w = font.getlength("M")
    ascent, descent = font.getmetrics()
    cell_h = int((ascent + descent) * 1.12)
    pad = 18
    size = (int(COLS * cell_w) + 2 * pad, ROWS * cell_h + 2 * pad)

    palette = _palette()
    frames, durations = [], []
    shown = ""
    for index, (stamp, _, data) in enumerate(events):
        shown += data
        image = Image.new("RGB", size, BACKGROUND)
        draw = ImageDraw.Draw(image)
        for row, (line, colour) in enumerate(_screen_rows(shown)):
            draw.text((pad, pad + row * cell_h), line, font=font, fill=colour)
        frames.append(image.quantize(palette=palette, dither=Image.Dither.NONE))
        following = events[index + 1][0] if index + 1 < len(events) else stamp + 3.0
        durations.append(int(max(0.06, min(following - stamp, 2.0)) * 1000))
    durations[-1] = 3500

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
    skill_dir = REPO_ROOT / SKILL
    claude_env = {
        "HOME": str(scratch / "claude-home"),
        "CLAUDE_CONFIG_DIR": str(scratch / "claude-config"),
    }
    codex_env = {
        "HOME": str(scratch / "codex-home-user"),
        "CODEX_HOME": str(scratch / "codex-home"),
    }
    for folder in (*claude_env.values(), *codex_env.values(), str(scratch / "anonymous-home")):
        Path(folder).mkdir(parents=True, exist_ok=True)

    def command(arguments: str, **options) -> Run:
        """One of the skill's commands, run from the skill folder as an agent runs it."""
        return Run(
            f"python3 scripts/kaggle_skill.py {arguments}",
            [python, "scripts/kaggle_skill.py", *shlex.split(arguments)],
            cwd=skill_dir,
            anonymous=True,
            **options,
        )

    return [
        Cast(
            "competition-brief",
            "kaggle-skill - a competition on one screen",
            ["A competition on one screen.", "No credential, nothing installed."],
            [
                command("brief titanic", max_lines=18),
                command("pages titanic --page evaluation --max-chars 300", max_lines=16),
            ],
            ["The text inside each block is data from Kaggle."],
        ),
        Cast(
            "vesuvius-top-writeups",
            "kaggle-skill - solution writeups of the top teams",
            ["What did the top three teams do?", "No credential is used."],
            [
                command(
                    "solutions vesuvius-challenge-surface-detection --top 3 --preview",
                    max_lines=16,
                )
            ],
        ),
        Cast(
            "install-and-demo",
            "kaggle-skill - Claude Code install and first command",
            [
                "Install in Claude Code, then a first command.",
                "(from a local checkout, in a throwaway",
                " config folder)",
            ],
            [
                Run(
                    "claude plugin marketplace add ./kaggle-skill",
                    ["claude", "plugin", "marketplace", "add", str(REPO_ROOT)],
                    env=claude_env,
                    needs="claude",
                    stderr=True,
                    max_lines=6,
                ),
                Run(
                    "claude plugin install kaggle@shepsci",
                    ["claude", "plugin", "install", "kaggle@shepsci"],
                    env=claude_env,
                    needs="claude",
                    stderr=True,
                    max_lines=6,
                ),
                "The agent then runs the skill's commands:",
                command("brief titanic", max_lines=12),
            ],
        ),
        Cast(
            "codex-install",
            "kaggle-skill - Codex install",
            ["Install in Codex.", "(from a local checkout, in a throwaway", " CODEX_HOME)"],
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
                    max_lines=20,
                ),
            ],
        ),
    ]


def sessions() -> list[dict]:
    """The recorded agent sessions, in name order."""
    return [load_session(path) for path in sorted(SESSIONS_DIR.glob("*.json"))]


# ── the README's demo blocks ─────────────────────────────────────────────────

HERO_SESSION = "agent-brief"
DRY_RUN_SESSION = "agent-submit"
SOLUTIONS_SESSION = "agent-solutions"


def _replace_block(text: str, name: str, body: str) -> str:
    start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
    if start not in text or end not in text:
        raise ValueError(f"README.md has no {name} block")
    head, rest = text.split(start, 1)
    _, tail = rest.split(end, 1)
    return f"{head}{start}\n{body.strip()}\n{end}{tail}"


def readme_blocks(recorded: dict[str, dict]) -> dict[str, str]:
    """What goes between the markers in README.md, from the demos that exist."""
    hero = recorded.get(HERO_SESSION)
    if hero and (MEDIA_DIR / f"{HERO_SESSION}.gif").exists():
        hero_body = "\n".join(
            [
                f"> **You:** {hero['question']}",
                "",
                f"![The agent's answer, recorded](docs/demo/media/{HERO_SESSION}.gif)",
                "",
                session_caption(hero, HERO_SESSION),
            ]
        )
    else:
        hero_body = "\n".join(
            [
                "![A competition on one screen](docs/demo/media/competition-brief.gif)",
                "",
                "What the agent runs and what comes back. "
                "[Cast](docs/demo/competition-brief.cast).",
            ]
        )

    parts = ["## See it work", ""]
    dry_run = recorded.get(DRY_RUN_SESSION)
    if dry_run and (MEDIA_DIR / f"{DRY_RUN_SESSION}.gif").exists():
        parts += [
            f"> **You:** {dry_run['question']}",
            "",
            f"![A submission is a dry run first](docs/demo/media/{DRY_RUN_SESSION}.gif)",
            "",
            "The agent checks the file, shows the dry run, and asks before it submits. "
            + session_caption(dry_run, DRY_RUN_SESSION),
            "",
        ]
    solutions = recorded.get(SOLUTIONS_SESSION)
    if solutions and (MEDIA_DIR / f"{SOLUTIONS_SESSION}.gif").exists():
        parts += [
            f"> **You:** {solutions['question']}",
            "",
            f"![What the top teams did](docs/demo/media/{SOLUTIONS_SESSION}.gif)",
            "",
            session_caption(solutions, SOLUTIONS_SESSION),
            "",
        ]
    else:
        parts += [
            "Solution writeups of the top teams, by rank "
            "([cast](docs/demo/vesuvius-top-writeups.cast)):",
            "",
            "![Solution writeups of the top teams](docs/demo/media/vesuvius-top-writeups.gif)",
            "",
        ]
    parts += [
        "Install in Claude Code and run a first command ([cast](docs/demo/install-and-demo.cast)):",
        "",
        "![Install and first command](docs/demo/media/install-and-demo.gif)",
        "",
        "The sessions are recorded as they ran, with no Kaggle credential configured; the "
        "[demo library](docs/demo/README.md) says how each demo is made.",
    ]
    return {"hero": hero_body, "demos": "\n".join(parts)}


def update_readme() -> None:
    recorded = {session["name"]: session for session in sessions()}
    text = README.read_text(encoding="utf-8")
    for name, body in readme_blocks(recorded).items():
        text = _replace_block(text, name, body)
    README.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("names", nargs="*", help="Demos to build (default: all)")
    parser.add_argument(
        "--gif-only",
        action="store_true",
        help="Do not run anything; render GIFs from the existing casts",
    )
    parser.add_argument("--no-gif", action="store_true", help="Write the casts only")
    parser.add_argument(
        "--readme", action="store_true", help="Refresh the demo blocks in README.md as well"
    )
    args = parser.parse_args(argv)

    if args.gif_only:
        for cast_path in sorted(DEMO_DIR.glob("*.cast")):
            if not args.names or cast_path.stem in args.names:
                print(f"rendered {render_gif(cast_path).relative_to(REPO_ROOT)}")
        if args.readme:
            update_readme()
        return 0

    with tempfile.TemporaryDirectory(prefix="kaggle-cast-") as temp:
        scratch = Path(temp).resolve()
        replacements = {
            str(scratch): "/tmp/kaggle-cast",
            str(REPO_ROOT): "./kaggle-skill",
            str(Path.home()): "~",
            "__anonymous_home__": str(scratch / "anonymous-home"),
        }
        known = casts(scratch)
        recorded = sessions()
        names = {cast.name for cast in known} | {session["name"] for session in recorded}
        unknown = set(args.names) - names
        if unknown:
            parser.error(f"unknown demo: {', '.join(sorted(unknown))}")
        built: list[tuple[str, str, list[list]]] = []
        for cast in known:
            if args.names and cast.name not in args.names:
                continue
            events = build_events(cast, replacements)
            if events is not None:
                built.append((cast.name, cast.title, events))
        for session in recorded:
            if args.names and session["name"] not in args.names:
                continue
            built.append((session["name"], session["title"], session_events(session)))
        for name, title, events in built:
            path = write_cast(name, title, events)
            print(
                f"wrote {path.relative_to(REPO_ROOT)} ({len(events)} events, {events[-1][0]:.0f}s)"
            )
            if not args.no_gif:
                print(f"rendered {render_gif(path).relative_to(REPO_ROOT)}")
    if args.readme:
        update_readme()
    return 0


if __name__ == "__main__":
    sys.exit(main())
