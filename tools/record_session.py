#!/usr/bin/env python3
"""Record a real Claude Code session with the plugin loaded, for the demos.

    python3 tools/record_session.py agent-brief "What is the metric of ...?"
    python3 tools/record_session.py agent-submit "Submit ./submission.csv to ..." --workdir ~/demo

Starts `claude -p` with this checkout loaded as the plugin, lets the agent run
the skill's commands, and writes what happened to docs/demo/sessions/<name>.json:
the question, each command with its full output, and the agent's answer, as
they were. tools/build_casts.py then turns the file into a cast and a GIF.

The session runs on your Claude Code subscription. The tool refuses to start
when an API key is set or when `claude auth status` does not show a
subscription login: a demo must never be billed to the Claude API.

Nothing can be written to Kaggle: the session runs with
KAGGLE_SKILL_READ_ONLY=1, and the agent may run only the skill's entry point.
Kaggle MCP servers are switched off, so the agent uses the skill's commands.
Read the file before committing it: the output can hold account details.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO_ROOT / "skills" / "kaggle"
SESSIONS_DIR = REPO_ROOT / "docs" / "demo" / "sessions"
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


def run_session(claude: str, question: str, workdir: Path, model: str | None) -> list[dict]:
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
    env = {**os.environ, "KAGGLE_SKILL_READ_ONLY": "1"}
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


def to_session(events: list[dict], name: str, title: str, question: str, workdir: Path) -> dict:
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

    def short(text: str) -> str:
        # The skill's folder and the working folder are shortened, as in the other demos.
        text = text.replace(f"{SKILL_DIR}/", "")
        return text.replace(str(workdir), ".")

    steps = [
        {"command": short(command), "output": short(outputs.get(tool_id, "")), "show_lines": 10}
        for tool_id, command in commands.items()
        if "kaggle_skill.py" in command
    ]
    version = init.get("claude_code_version") or "?"
    model = init.get("model") or "?"
    return {
        "name": name,
        "title": title,
        "recorded": datetime.date.today().isoformat(),
        "agent": f"Claude Code {version} ({model})",
        "agent_short": "Claude",
        "question": question,
        "steps": steps,
        "answer": answer,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("name", help="File name in docs/demo/sessions/, without .json")
    parser.add_argument("question", help="The question, as a person would type it")
    parser.add_argument("--title", help="Title of the cast")
    parser.add_argument("--workdir", default=".", help="Folder the session runs in")
    parser.add_argument("--model", help="Model for the session (default: the CLI's)")
    args = parser.parse_args(argv)

    claude = claude_binary()
    check_subscription(claude)
    workdir = Path(args.workdir).expanduser().resolve()
    events = run_session(claude, args.question, workdir, args.model)
    session = to_session(
        events, args.name, args.title or f"kaggle-skill - {args.name}", args.question, workdir
    )
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    target = SESSIONS_DIR / f"{args.name}.json"
    target.write_text(json.dumps(session, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {target.relative_to(REPO_ROOT)}: {len(session['steps'])} commands")
    print("Read it before committing it: the output can hold account details.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
