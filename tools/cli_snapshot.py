#!/usr/bin/env python3
"""Compare the Kaggle CLI's command tree with the committed snapshot.

    python3 tools/cli_snapshot.py --check     # exit 1 and list the changes if it differs
    python3 tools/cli_snapshot.py --update    # rewrite the snapshot from the installed CLI

Walks `kaggle <command> --help` for every command and records the long option
names. Help needs no credentials and no network. The snapshot is what the
docs tests check documented commands against.
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
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = REPO_ROOT / "tests" / "fixtures" / "cli_help_snapshot.json"
MAX_DEPTH = 6


def _help(kaggle: str, path: list[str], env: dict[str, str]) -> str:
    result = subprocess.run(
        [kaggle, *path, "--help"], capture_output=True, text=True, env=env, timeout=120, check=False
    )
    return result.stdout + result.stderr


def _choices(text: str) -> list[str]:
    """Subcommand names from the usage line: ``{list,files,get} ...``."""
    usage = text.split("\n\n")[0].replace("\n", " ")
    names: list[str] = []
    for group in re.finditer(r"\{([a-zA-Z0-9_,\-]+)\}\s*\.\.\.", usage):
        names = group.group(1).split(",")
    return names


def _flags(text: str) -> list[str]:
    return sorted(set(re.findall(r"(?<![\w-])(--[a-z][a-z0-9-]+)", text)) - {"--help"})


def _usage_path(text: str) -> list[str]:
    """The command path argparse prints: ``usage: kaggle kernels pull [-h]`` -> kernels, pull.

    A parent's optional positional can sit in the middle
    (``kaggle competitions pages [competition] list [-h]``); it is dropped.
    """
    first = text.split("\n", 1)[0]
    if not first.startswith("usage: kaggle"):
        return []
    head = first[len("usage: kaggle") :].split("[-h]", 1)[0]
    head = re.sub(r"\[[^\]]*\]|\{[^}]*\}", " ", head)
    tokens = head.split()
    return tokens if all(re.fullmatch(r"[a-z][a-z0-9-]*", t) for t in tokens) else []


def walk(kaggle: str) -> tuple[dict[str, list[str]], dict[str, str]]:
    """Return ``(commands, aliases)``.

    ``commands`` maps each command path to its long options, for example
    ``{"competitions submit": ["--file", ...]}``. ``aliases`` maps an alias
    path to the command it stands for (``{"c": "competitions", "kernels get":
    "kernels pull"}``). The usage line tells them apart: help for an alias
    prints the real command's name. A name the CLI lists but cannot run is
    left out.
    """
    with tempfile.TemporaryDirectory() as home:
        env = {
            k: v
            for k, v in os.environ.items()
            if not k.startswith("KAGGLE_") and k not in ("VERBOSE", "VERBOSE_OUTPUT")
        }
        env.update(HOME=home, COLUMNS="250")
        commands: dict[str, list[str]] = {}
        aliases: dict[str, str] = {}

        def visit(path: list[str], text: str, depth: int) -> None:
            if path:
                commands[" ".join(path)] = _flags(text)
            if depth >= MAX_DEPTH:
                return
            for name in _choices(text):
                child = [*path, name]
                child_text = _help(kaggle, child, env)
                real = _usage_path(child_text)
                if real == child:
                    visit(child, child_text, depth + 1)
                elif len(real) == len(child) and real[:-1] == path:
                    aliases[" ".join(child)] = " ".join(real)

        visit([], _help(kaggle, [], env), 0)
        return dict(sorted(commands.items())), dict(sorted(aliases.items()))


def resolve(
    tokens: list[str], commands: dict[str, list[str]], aliases: dict[str, str]
) -> tuple[str | None, int]:
    """Longest command at the start of ``tokens``, with aliases expanded.

    Returns ``(command path, number of tokens it used)``, or ``(None, 0)``.
    """
    path: list[str] = []
    best: tuple[str | None, int] = (None, 0)
    for index, token in enumerate(tokens):
        candidate = " ".join([*path, token])
        candidate = aliases.get(candidate, candidate)
        if candidate not in commands:
            break
        path = candidate.split()
        best = (candidate, index + 1)
    return best


def cli_version(kaggle: str) -> str:
    result = subprocess.run(
        [kaggle, "--version"], capture_output=True, text=True, timeout=60, check=False
    )
    match = re.search(r"\d+\.\d+\.\d+\S*", result.stdout + result.stderr)
    return match.group(0) if match else "unknown"


def diff(old: dict, new: dict) -> list[str]:
    """Differences between two snapshots (``{"commands": ..., "aliases": ...}``)."""
    changes: list[str] = []
    before, after = old["commands"], new["commands"]
    for name in sorted(set(after) - set(before)):
        changes.append(f"added command: kaggle {name}")
    for name in sorted(set(before) - set(after)):
        changes.append(f"removed command: kaggle {name}")
    for name in sorted(set(before) & set(after)):
        added = sorted(set(after[name]) - set(before[name]))
        removed = sorted(set(before[name]) - set(after[name]))
        if added:
            changes.append(f"kaggle {name}: new options {' '.join(added)}")
        if removed:
            changes.append(f"kaggle {name}: removed options {' '.join(removed)}")
    old_aliases, new_aliases = old.get("aliases", {}), new.get("aliases", {})
    for name in sorted(set(new_aliases) - set(old_aliases)):
        changes.append(f"added alias: kaggle {name} -> kaggle {new_aliases[name]}")
    for name in sorted(set(old_aliases) - set(new_aliases)):
        changes.append(f"removed alias: kaggle {name}")
    return changes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Compare; exit 1 on any difference")
    mode.add_argument("--update", action="store_true", help="Rewrite the snapshot")
    parser.add_argument(
        "--kaggle",
        default=os.environ.get("KAGGLE_CLI_BIN") or shutil.which("kaggle") or "kaggle",
        help="Path of the kaggle executable",
    )
    args = parser.parse_args(argv)

    try:
        version = cli_version(args.kaggle)
        commands, aliases = walk(args.kaggle)
    except FileNotFoundError:
        print("error: kaggle executable not found", file=sys.stderr)
        return 2
    if not commands:
        print("error: could not read the CLI's help", file=sys.stderr)
        return 2
    live = {"kaggle_version": version, "commands": commands, "aliases": aliases}

    if args.update:
        SNAPSHOT.write_text(json.dumps(live, indent=1) + "\n")
        print(
            f"wrote {SNAPSHOT.relative_to(REPO_ROOT)} "
            f"({len(commands)} commands, {len(aliases)} aliases, kaggle {version})"
        )
        return 0

    committed = json.loads(SNAPSHOT.read_text())
    changes = diff(committed, live)
    if not changes:
        print(f"kaggle {version} matches the snapshot ({len(commands)} commands)")
        return 0
    print(
        f"kaggle {version} differs from the snapshot taken with "
        f"kaggle {committed.get('kaggle_version')}:"
    )
    print("\n".join(changes))
    return 1


if __name__ == "__main__":
    sys.exit(main())
