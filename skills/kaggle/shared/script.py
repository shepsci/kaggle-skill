"""What every script in this skill shares: exit codes, arguments, messages.

The exit codes are the table in SKILL.md:

    0    done (a dry run that changed nothing is also 0)
    1    Kaggle or the CLI reported a failure, or a notebook run failed
    2    wrong arguments, or a credential is needed and none works
    3    Kaggle denied permission for this account or role
    4    a status or a listing could not be read
    5    refused for safety
    124  timed out while waiting
    127  the Kaggle CLI or a Python package the command needs is not installed
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2
EXIT_NO_CREDENTIAL = 2
EXIT_DENIED = 3
EXIT_UNAVAILABLE = 4
EXIT_REFUSED = 5
EXIT_TIMEOUT = 124
EXIT_NOT_INSTALLED = 127

READ_ONLY_VAR = "KAGGLE_SKILL_READ_ONLY"
STATE_DIR_VAR = "KAGGLE_SKILL_DIR"
HIDE_ACCOUNT_VAR = "KAGGLE_SKILL_HIDE_ACCOUNT"
DEFAULT_STATE_DIR = ".kaggle-skill"

# One part of a Kaggle slug: it starts with a letter or digit, which rules out
# "..", option-looking values and anything with spaces or shell characters.
PART = r"[A-Za-z0-9][A-Za-z0-9._-]*"
# fullmatch, not match with "$": "$" also matches before a final line break.
_PART_RE = re.compile(PART)

PACKAGES = {
    "kaggle": "kaggle>=2.2.4",
    "kagglehub": "kagglehub>=1.0.2",
}
NO_CREDENTIAL_HELP = (
    "no Kaggle credential was found. Sign in with `kaggle auth login`, set KAGGLE_API_TOKEN, "
    "or save a token in ~/.kaggle/access_token (see modules/setup/README.md)"
)


def fail(message: str, code: int = EXIT_FAILED) -> int:
    """Print one ``error:`` line on standard error and return ``code``."""
    print(f"error: {message}", file=sys.stderr)
    return code


def warn(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


def missing_package(name: str, purpose: str = "") -> int:
    """Say which package is missing and how to install it. Returns exit code 127."""
    spec = PACKAGES.get(name, name)
    reason = f" (needed for {purpose})" if purpose else ""
    return fail(
        f"the Python package '{name}' is not installed{reason}. "
        f"Install it with: python3 -m pip install '{spec}'",
        EXIT_NOT_INSTALLED,
    )


def no_credential(what: str = "this command") -> int:
    """Say that a credential is needed. Returns exit code 2."""
    return fail(f"{what} needs a Kaggle account: {NO_CREDENTIAL_HELP}", EXIT_NO_CREDENTIAL)


# -- names ------------------------------------------------------------------


def competition_slug(value: str) -> str:
    """The competition slug from a slug or a Kaggle competition URL.

    Raises ValueError when the result is not a slug.
    """
    text = (value or "").strip()
    parsed = urlparse(text)
    path = parsed.path if parsed.scheme else text
    parts = [part for part in path.split("/") if part]
    slug = parts[0] if len(parts) == 1 else ""
    for marker in ("competitions", "c"):
        if marker in parts and parts.index(marker) + 1 < len(parts):
            slug = parts[parts.index(marker) + 1]
            break
    if not _PART_RE.fullmatch(slug):
        raise ValueError("the competition is not a slug such as titanic, or a competition URL")
    return slug


def is_handle(value: str, parts: int) -> bool:
    """True for ``parts`` slug parts joined by ``/``: owner/name is two parts."""
    return bool(re.fullmatch(rf"{PART}(/{PART}){{{parts - 1}}}", value or ""))


def positive_int(value: str) -> int:
    """argparse type: a whole number above zero."""
    try:
        number = int(value)
    except ValueError:
        number = 0
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a whole number above zero")
    return number


# -- arguments --------------------------------------------------------------


# What the positionals after the competition hold, for --help.
POSITIONAL_HELP = {
    "dir": "Folder to download into (default: ./downloads/<competition>)",
    "file": "The submission file",
    "message": "The submission message, if not given with -m",
}


def parse(parser: argparse.ArgumentParser, argv: list[str] | None = None) -> argparse.Namespace:
    """Parse, with positionals allowed after options: ``download titanic --unzip ./data``.

    Python 3.11 reads the positionals in one run before the first option and
    rejects the rest; parse_intermixed_args reads them wherever they are.
    """
    return parser.parse_intermixed_args(argv)


def add_competition(parser: argparse.ArgumentParser, *names: str) -> None:
    """Add the competition, as the first positional or as ``--competition``.

    ``names`` are further positionals that follow it. Read them all back with
    ``positionals``; a name that ends with ``?`` is optional.
    """
    parser.add_argument(
        "competition",
        nargs="?",
        help="Competition slug (titanic) or its URL",
    )
    for name in names:
        key = name.rstrip("?")
        parser.add_argument(key, nargs="?", help=POSITIONAL_HELP.get(key, key))
    parser.add_argument(
        "-c",
        "--competition",
        dest="competition_opt",
        metavar="COMPETITION",
        help="The same, as an option",
    )
    # The older spelling of --competition in competition_details.py.
    parser.add_argument("--slug", dest="competition_opt", help=argparse.SUPPRESS)


def positionals(parser: argparse.ArgumentParser, args: argparse.Namespace, *names: str) -> list:
    """The competition slug followed by the values of ``names``.

    When the competition came as ``--competition``, the positionals are one
    place to the left of where argparse put them, and are moved back.
    """
    keys = ["competition", *[name.rstrip("?") for name in names]]
    values = [getattr(args, key) for key in keys]
    if args.competition_opt:
        if values[0] == args.competition_opt:
            pass  # the same competition both ways
        elif values[-1] is None:
            values = [args.competition_opt, *values[:-1]]
        else:
            parser.error("the competition was given twice")
    if not values[0]:
        parser.error("name the competition: a slug such as titanic, or its URL")
    for name, value in zip(names, values[1:]):
        if value is None and not name.endswith("?"):
            parser.error(f"missing argument: {name}")
    try:
        values[0] = competition_slug(values[0])
    except ValueError as exc:
        parser.error(str(exc))
    return values


def add_json(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text")
    # Older spellings: --pretty indented the JSON that used to be the default.
    parser.add_argument("--pretty", action="store_true", help=argparse.SUPPRESS)


def add_full(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--full",
        action="store_true",
        help="Print everything the server returned, as JSON",
    )


def add_limit(parser: argparse.ArgumentParser, default: int, what: str = "rows") -> None:
    parser.add_argument(
        "--limit",
        type=positive_int,
        default=default,
        metavar="N",
        help=f"Print at most N {what} (default: {default})",
    )


def add_yes(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Do it. Without this flag the command only prints what it would do",
    )


# -- writes -----------------------------------------------------------------


def read_only() -> bool:
    """True when ``KAGGLE_SKILL_READ_ONLY`` forbids every write."""
    return os.environ.get(READ_ONLY_VAR, "").strip().lower() not in ("", "0", "false", "no")


def hide_account() -> bool:
    """True when ``KAGGLE_SKILL_HIDE_ACCOUNT`` asks to leave out your entries and ranks.

    For screen sharing and recordings: listings and briefs then show only what
    anyone would see. Commands that are about the account (status, the
    leaderboard's "you" row) are not affected.
    """
    return os.environ.get(HIDE_ACCOUNT_VAR, "").strip().lower() not in ("", "0", "false", "no")


def write_gate(
    yes: bool,
    *,
    action: str,
    details: list[tuple[str, str]],
    cost: str = "",
    target: str = "Kaggle",
    blocked: bool = False,
) -> int | None:
    """Print what a write would do, and decide whether it may happen.

    Returns None when the caller may go ahead: ``--yes`` was given and the
    read-only switch is off. Otherwise returns the exit code to stop with:
    0 after a dry run, 5 when the read-only switch refused a confirmed write.
    ``blocked`` means the caller already found a reason the write cannot
    happen: the plan is printed and ``--yes`` is not offered.
    """
    refused = yes and read_only() and not blocked
    if yes and not refused and not blocked:
        print(f"Confirmed with --yes: {action}")
        return None
    if refused:
        print(f"Refused: {READ_ONLY_VAR} is set, so nothing is sent to {target}.")
    else:
        print(f"Dry run. Nothing was sent to {target}.")
    width = max([len(label) for label, _ in details] + [len("action"), len("cost")]) + 1
    print(f"  {'action:':<{width}} {action}")
    for label, value in details:
        print(f"  {label + ':':<{width}} {value}")
    if cost:
        print(f"  {'cost:':<{width}} {cost}")
    if refused:
        return EXIT_REFUSED
    if blocked:
        print("This cannot be done as given. See the error above.")
    else:
        # The request that led here is not the yes: the user has not seen this plan.
        print("Show this to the user and wait for their yes. Then run it again with --yes.")
    return EXIT_OK


# -- local state ------------------------------------------------------------


def state_dir() -> Path:
    """Folder for the skill's local records: ``./.kaggle-skill`` or ``KAGGLE_SKILL_DIR``."""
    return Path(os.environ.get(STATE_DIR_VAR) or DEFAULT_STATE_DIR)


def write_state(path: Path, content: str, *, append: bool = False) -> Path:
    """Write to a file in the state folder without following links.

    A cloned repository can carry a ``.kaggle-skill`` folder with a link in
    it (``ledger.jsonl -> ~/.bashrc``), and a plain write would follow the
    link. Here a link on the way is an error (OSError), new folders are
    private (0700), and new files 0600. A ``KAGGLE_SKILL_DIR`` the user set
    is trusted as given; only what is below it is checked.
    """
    base = state_dir()
    below = path.relative_to(base).parts[:-1]
    if os.environ.get(STATE_DIR_VAR):
        base.mkdir(mode=0o700, parents=True, exist_ok=True)
        folder, parts = base, below
    else:
        folder, parts = Path(), (*base.parts, *below)
    for part in parts:
        folder = folder / part
        if folder.is_symlink():
            raise OSError(f"{folder} is a link; the skill does not write through links")
        if not folder.exists():
            folder.mkdir(mode=0o700)
    if path.is_symlink():
        raise OSError(f"{path} is a link; the skill does not write through links")
    flags = os.O_WRONLY | os.O_CREAT | (os.O_APPEND if append else os.O_TRUNC)
    descriptor = os.open(path, flags | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(descriptor, "a" if append else "w", encoding="utf-8") as handle:
        handle.write(content)
    return path
