"""Boundary markers for Kaggle-supplied text.

Everything Kaggle returns that a person outside this skill can author (page
bodies, titles, team names, file names, forum posts, CLI error text) is data,
not instructions. Scripts print it inside a block like::

    <untrusted-content-3f9a1c2b source="kaggle-mcp" tool="list_competition_pages">
    ...
    </untrusted-content-3f9a1c2b>

The tag name carries a random suffix chosen per block, so the content cannot
close its own block: it does not know the suffix. As a second layer, anything
in the content that looks like one of these tags is defanged, and JSON output
escapes ``<`` and ``>`` so no markup survives inside it.
"""

from __future__ import annotations

import html
import json
import re
import secrets
import sys
from typing import IO, Any

TAG = "untrusted-content"

_MARKER_RE = re.compile(r"<(\s*/?\s*)untrusted-content", re.IGNORECASE)
# C0 controls other than tab, newline and carriage return, plus DEL.
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def new_nonce() -> str:
    """Return the random suffix for one block."""
    return secrets.token_hex(4)


def neutralize(text: str) -> str:
    """Defang tag lookalikes and drop control characters in raw text."""
    text = _CONTROL_RE.sub("", text)
    return _MARKER_RE.sub(lambda m: "&lt;" + m.group(1) + TAG, text)


def dumps(obj: Any, *, indent: int | None = None, sort_keys: bool = False) -> str:
    """Serialize to JSON with ``<`` and ``>`` escaped.

    The result is still valid JSON and parses back to the same value.
    """
    text = json.dumps(obj, indent=indent, sort_keys=sort_keys)
    return text.replace("<", "\\u003c").replace(">", "\\u003e")


def _attr(value: Any) -> str:
    collapsed = " ".join(_CONTROL_RE.sub("", str(value)).split())
    return html.escape(collapsed, quote=True)


def open_tag(nonce: str, *, source: str, tool: str, **attrs: Any) -> str:
    """Build the opening tag. Attribute values are escaped."""
    parts = [f'source="{_attr(source)}"', f'tool="{_attr(tool)}"']
    for key, value in attrs.items():
        if value is None:
            continue
        parts.append(f'{key.replace("_", "-")}="{_attr(value)}"')
    return f"<{TAG}-{nonce} " + " ".join(parts) + ">"


def close_tag(nonce: str) -> str:
    return f"</{TAG}-{nonce}>"


class Block:
    """Context manager that prints one untrusted-content block.

    The closing tag is printed even when the body raises, so a failure never
    leaves a block open.
    """

    def __init__(self, *, source: str, tool: str, file: IO[str] | None = None, **attrs: Any):
        self.nonce = new_nonce()
        self._source = source
        self._tool = tool
        self._attrs = attrs
        self._file = file

    @property
    def file(self) -> IO[str]:
        return self._file if self._file is not None else sys.stdout

    def __enter__(self) -> "Block":
        print(
            open_tag(self.nonce, source=self._source, tool=self._tool, **self._attrs),
            file=self.file,
        )
        return self

    def write(self, text: str) -> None:
        """Print raw text inside the block."""
        text = neutralize(text)
        print(text, end="" if text.endswith("\n") else "\n", file=self.file)

    def write_json(self, obj: Any, *, indent: int | None = None, sort_keys: bool = False) -> None:
        """Print a JSON document inside the block."""
        print(dumps(obj, indent=indent, sort_keys=sort_keys), file=self.file)

    def __exit__(self, *exc_info: object) -> None:
        print(close_tag(self.nonce), file=self.file)


def emit_text(
    text: str, *, source: str, tool: str, file: IO[str] | None = None, **attrs: Any
) -> None:
    """Print raw text as one block."""
    with Block(source=source, tool=tool, file=file, **attrs) as block:
        block.write(text)


def emit_json(
    obj: Any,
    *,
    source: str,
    tool: str,
    indent: int | None = None,
    sort_keys: bool = False,
    file: IO[str] | None = None,
    **attrs: Any,
) -> None:
    """Print a JSON document as one block."""
    with Block(source=source, tool=tool, file=file, **attrs) as block:
        block.write_json(obj, indent=indent, sort_keys=sort_keys)


def main(argv: list[str] | None = None) -> int:
    """Run a local command and print its stdout as one untrusted block.

    Used by the shell wrappers for listings whose file names come from Kaggle::

        python3 shared/untrusted.py --source local --tool ls -- ls -la ./downloads
    """
    import argparse
    import subprocess

    parser = argparse.ArgumentParser(description="Wrap a command's output as untrusted content.")
    parser.add_argument("--source", default="local")
    parser.add_argument("--tool", required=True)
    parser.add_argument("cmd", nargs=argparse.REMAINDER, help="-- followed by the command")
    ns = parser.parse_args(argv)
    cmd = ns.cmd[1:] if ns.cmd[:1] == ["--"] else ns.cmd
    if not cmd:
        parser.error("no command given")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        print(f"error: command not found: {cmd[0]}", file=sys.stderr)
        return 127
    with Block(source=ns.source, tool=ns.tool) as block:
        if result.stdout:
            block.write(result.stdout)
    if result.stderr.strip():
        with Block(source=ns.source, tool=ns.tool, stream="stderr", file=sys.stderr) as block:
            block.write(result.stderr)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
