#!/usr/bin/env python3
"""Record a real Claude Code session with the plugin loaded, for the demos.

    python3 tools/record_session.py agent-brief "What is the metric of ...?"
    python3 tools/record_session.py agent-submit "Submit ./submission.csv to ..." --workdir ~/demo

Starts `claude -p` with this checkout loaded as the plugin, lets the agent run
the skill's commands, and writes what happened to docs/demo/sessions/<name>.json:
the question, each command with the start of its output, and the agent's
answer, as they were. tools/build_casts.py then turns the file into a cast
and a GIF.

After a recording the tool lists every number in the answer that no command
printed, so that a made-up figure is caught before the session is committed.

Only the lines a demo shows are kept from each output, with a count of the
rest: ten lines, or six for a command that prints someone's text (a writeup,
a topic, a page), which is the title, the author and the address. The whole
output would put other people's writing, and the contact details some of
them include, into this repository.

The session runs on your Claude Code subscription. The tool refuses to start
when an API key is set or when `claude auth status` does not show a
subscription login: a demo must never be billed to the Claude API.

Nothing can be written to Kaggle: the session runs with
KAGGLE_SKILL_READ_ONLY=1, and the agent may run only the skill's entry point.
Kaggle MCP servers are switched off, so the agent uses the skill's commands.

The skill's commands see no Kaggle credential: they run with HOME set to an
empty folder (through CLAUDE_ENV_FILE, which Claude Code sources before each
shell command) and without KAGGLE_* variables, so a demo shows what a new
user gets and no account data. --with-credential keeps your credential, for
a command that needs one (listing competitions); the session then runs with
KAGGLE_SKILL_HIDE_ACCOUNT=1, which leaves your entries and ranks out of the
output. Read the file before committing it all the same.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_casts import clean, shorten  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO_ROOT / "skills" / "kaggle"
SESSIONS_DIR = REPO_ROOT / "docs" / "demo" / "sessions"
# Claude Code gives each session a scratch folder with a long path.
SCRATCH_RE = re.compile(r"(?:/private)?/tmp/claude-\d+/[^\s\"']*?/scratchpad")
SHOWN_LINES = 10
# Commands whose output is someone's text: only its heading is kept.
PROSE_COMMANDS = {"writeup": 6, "topic": 6, "pages": 6, "hackathon": 6}
API_VARIABLES = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
)


def claude_binary() -> str:
    found = os.environ.get("CLAUDE_BIN") or shutil.which("claude")
    if not found:
        raise SystemExit("error: `claude` is not on PATH; set CLAUDE_BIN to its path")
    return found


def check_subscription(claude: str) -> None:
    """Stop unless the CLI is signed in with a subscription and no API key is set."""
    set_variables = [name for name in API_VARIABLES if os.environ.get(name)]
    if set_variables:
        raise SystemExit(f"error: {', '.join(set_variables)} is set; demos never use the API")
    result = subprocess.run([claude, "auth", "status"], capture_output=True, text=True, check=False)
    try:
        status = json.loads(result.stdout)
    except ValueError:
        raise SystemExit("error: could not read `claude auth status`") from None
    if not status.get("loggedIn") or status.get("authMethod") != "claude.ai":
        raise SystemExit(
            "error: the CLI is not signed in with a Claude subscription. "
            "Run: claude auth login --claudeai"
        )


def session_env(empty_home: Path | None) -> dict[str, str]:
    """The session's environment: read-only, and with no Kaggle credential unless asked."""
    env = {key: value for key, value in os.environ.items() if not key.startswith("KAGGLE_")}
    env["KAGGLE_SKILL_READ_ONLY"] = "1"
    # Your entries and ranks stay out of a demo even when a credential is used.
    env["KAGGLE_SKILL_HIDE_ACCOUNT"] = "1"
    if empty_home is not None:
        # Claude Code keeps its own sign-in under the real HOME; only the shell
        # commands the agent runs get the empty one.
        env_file = empty_home / "session-env.sh"
        env_file.write_text(f"export HOME={shlex.quote(str(empty_home))}\n", encoding="utf-8")
        env["CLAUDE_ENV_FILE"] = str(env_file)
    return env


def run_session(
    claude: str,
    question: str,
    workdir: Path,
    model: str | None,
    env: dict[str, str],
    stream: Path | None = None,
) -> list[dict]:
    entry = SKILL_DIR / "scripts" / "kaggle_skill.py"
    command = [
        claude,
        "-p",
        question,
        "--plugin-dir",
        str(REPO_ROOT),
        "--strict-mcp-config",
        "--output-format",
        "stream-json",
        "--verbose",
        "--max-turns",
        "12",
        "--no-session-persistence",
        "--allowedTools",
        f"Bash(python3 {entry}:*)",
        "Skill",
        "Read",
        "Glob",
        "Grep",
    ]
    if model:
        command += ["--model", model]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=workdir,
        env=env,
        stdin=subprocess.DEVNULL,
        timeout=900,
        check=False,
    )
    if stream is not None:
        # The whole stream, for looking into a run. Keep it out of the repository.
        stream.write_text(result.stdout, encoding="utf-8")
    events = []
    for line in result.stdout.splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            continue
    if result.returncode != 0 or not events:
        raise SystemExit(f"error: the session failed (exit {result.returncode})")
    return events


def _blocks(event: dict) -> list[dict]:
    content = (event.get("message") or {}).get("content")
    return [block for block in content or [] if isinstance(block, dict)]


def _text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
    return ""


def to_session(
    events: list[dict],
    name: str,
    title: str,
    question: str,
    workdir: Path,
    shown_lines: int = SHOWN_LINES,
    answer_lines: int | None = None,
) -> dict:
    """The session file: the commands that ran, their output, and the answer."""
    # Hook events come first; the init event carries the model and the version.
    init = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), {})
    commands: dict[str, str] = {}
    outputs: dict[str, str] = {}
    for event in events:
        for block in _blocks(event):
            if block.get("type") == "tool_use" and block.get("name") == "Bash":
                commands[block["id"]] = str((block.get("input") or {}).get("command", ""))
            elif block.get("type") == "tool_result":
                outputs[str(block.get("tool_use_id"))] = _text(block.get("content"))
    result = next((e for e in reversed(events) if e.get("type") == "result"), {})
    answer = str(result.get("result") or "").strip()
    if not answer:
        raise SystemExit("error: the session ended without an answer")
    unsupported = unsupported_numbers(answer, list(outputs.values()))
    if unsupported:
        print(
            "check these numbers by hand: the answer has them, no command printed them: "
            + ", ".join(unsupported),
            file=sys.stderr,
        )

    def short(text: str) -> str:
        # The skill's folder, the working folder and the session's scratch folder
        # are shortened, as in the other demos.
        text = text.replace(f"{SKILL_DIR}/", "")
        return SCRATCH_RE.sub("/tmp/scratch", text).replace(str(workdir), ".")

    steps = [
        step(short(command), short(outputs.get(tool_id, "")), shown_lines)
        for tool_id, command in commands.items()
        if "kaggle_skill.py" in command
    ]
    version = init.get("claude_code_version") or "?"
    model = init.get("model") or "?"
    session = {
        "name": name,
        "title": title,
        "recorded": datetime.date.today().isoformat(),
        "agent": f"Claude Code {version} ({model})",
        "agent_short": "Claude",
        "question": question,
        "steps": steps,
        "answer": answer,
    }
    if answer_lines:
        # The demo shows this many lines of the answer; the file keeps all of it.
        session["answer_show_lines"] = answer_lines
    return session


_NUMBER_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _digits(number: str) -> str:
    return re.sub(r"\D", "", number)


def unsupported_numbers(answer: str, outputs: list[str]) -> list[str]:
    """Numbers in the answer that no command printed: a prompt to check, not a verdict.

    A number of three digits or more counts as supported when a number in the
    output has the same digits or starts with them (the answer may round
    103253 to 103k, or 2026-11-02 to "Nov 2"). Anything this lists has to be
    looked up by a person before the session is committed.
    """
    printed = {_digits(found) for output in outputs for found in _NUMBER_RE.findall(output)}
    missing = []
    for found in _NUMBER_RE.findall(answer):
        digits = _digits(found)
        if len(digits) < 3 or digits in printed:
            continue
        if not any(number.startswith(digits) for number in printed):
            missing.append(found)
    return list(dict.fromkeys(missing))


def step(command: str, output: str, shown_lines: int = SHOWN_LINES) -> dict:
    """One command with the part of its output a demo shows."""
    words = command.split("kaggle_skill.py", 1)[1].split()
    limit = PROSE_COMMANDS.get(words[0] if words else "", shown_lines)
    kept = shorten(clean(output), limit, 200)
    return {"command": command, "output": kept, "show_lines": len(kept.splitlines())}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("name", help="File name in docs/demo/sessions/, without .json")
    parser.add_argument("question", help="The question, as a person would type it")
    parser.add_argument("--title", help="Title of the cast")
    parser.add_argument("--workdir", default=".", help="Folder the session runs in")
    parser.add_argument("--model", help="Model for the session (default: the CLI's)")
    parser.add_argument(
        "--show-lines",
        type=int,
        default=SHOWN_LINES,
        metavar="N",
        help=f"Lines kept from each command's output (default: {SHOWN_LINES})",
    )
    parser.add_argument(
        "--answer-lines",
        type=int,
        metavar="N",
        help="Lines of the answer the demo shows (default: all); the file keeps the whole answer",
    )
    parser.add_argument(
        "--stream",
        metavar="PATH",
        help="Also save the whole event stream here, with every full output; not for committing",
    )
    parser.add_argument(
        "--from-stream",
        metavar="PATH",
        help="Build the session file from a stream saved with --stream; starts no session",
    )
    parser.add_argument(
        "--with-credential",
        action="store_true",
        help="Let the skill's commands use your Kaggle credential (read the output first)",
    )
    args = parser.parse_args(argv)

    workdir = Path(args.workdir).expanduser().resolve()
    if args.from_stream:
        lines = Path(args.from_stream).expanduser().read_text(encoding="utf-8").splitlines()
        events = [json.loads(line) for line in lines if line.startswith("{")]
    else:
        claude = claude_binary()
        check_subscription(claude)
        with tempfile.TemporaryDirectory(prefix="kaggle-demo-home-") as empty:
            env = session_env(None if args.with_credential else Path(empty))
            stream = Path(args.stream).expanduser() if args.stream else None
            events = run_session(claude, args.question, workdir, args.model, env, stream)
    session = to_session(
        events,
        args.name,
        args.title or f"kaggle-skill - {args.name}",
        args.question,
        workdir,
        args.show_lines,
        args.answer_lines,
    )
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    target = SESSIONS_DIR / f"{args.name}.json"
    target.write_text(json.dumps(session, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {target.relative_to(REPO_ROOT)}: {len(session['steps'])} commands")
    if args.with_credential:
        print("Read it before committing it: the output can hold account details.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
