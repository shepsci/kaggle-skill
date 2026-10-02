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

Text is printed as it is written: a dash stays a dash and an emoji stays an
emoji. The exception is what a reader cannot see. Control characters,
zero-width and bidirectional format characters, tag characters and private-use
code points are removed from text and written as ``\\uXXXX`` escapes in JSON,
because hidden text is one way to smuggle instructions past a person who
reviews the output.
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
# C0 controls other than tab, newline and carriage return.
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
# What a reader cannot see: DEL and the C1 controls, the soft hyphen, the
# Arabic letter mark, the Mongolian vowel separator, zero-width and
# bidirectional format characters, the byte-order mark, interlinear
# annotation marks, surrogates, private-use code points, tag characters and
# the variation-selector supplement.
_HIDDEN = (
    "\x7f-\x9f\u00ad\u061c\u180e\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff\ufff9-\ufffb"
    "\ud800-\udfff\ue000-\uf8ff\U000e0000-\U000e0fff\U000f0000-\U0010ffff"
)
_HIDDEN_RUN_RE = re.compile(f"[{_HIDDEN}]+")
_LINE_SEPARATOR_RE = re.compile("[\u2028\u2029]")
_JSON_ESCAPE_RE = re.compile(f"[<>\u2028\u2029{_HIDDEN}]")
# A run this long is not typography (a joiner in an emoji, a stray soft
# hyphen). It is replaced by a note instead of being dropped without a trace.
HIDDEN_RUN_NOTE_AT = 4


def new_nonce() -> str:
    """Return the random suffix for one block."""
    return secrets.token_hex(4)


def _hidden_note(match: re.Match[str]) -> str:
    count = len(match.group(0))
    return f"[{count} hidden characters removed]" if count >= HIDDEN_RUN_NOTE_AT else ""


def strip_hidden(text: str) -> str:
    """Remove control and invisible characters; note a long run of them."""
    text = _CONTROL_RE.sub("", text)
    text = _LINE_SEPARATOR_RE.sub("\n", text)
    return _HIDDEN_RUN_RE.sub(_hidden_note, text)


def neutralize(text: str) -> str:
    """Defang tag lookalikes and remove what cannot be seen in raw text."""
    # Hidden characters go first, so they cannot split a lookalike tag.
    return _MARKER_RE.sub(lambda m: "&lt;" + m.group(1) + TAG, strip_hidden(text))


def _json_escape(match: re.Match[str]) -> str:
    code = ord(match.group(0))
    if code > 0xFFFF:
        code -= 0x10000
        return f"\\u{0xD800 + (code >> 10):04x}\\u{0xDC00 + (code & 0x3FF):04x}"
    return f"\\u{code:04x}"


def dumps(
    obj: Any, *, indent: int | None = None, sort_keys: bool = False, ensure_ascii: bool = False
) -> str:
    """Serialize to JSON with ``<``, ``>`` and invisible characters escaped.

    Other text is left as written, so titles and names stay readable. The
    result is valid JSON and parses back to the same value.
    """
    text = json.dumps(obj, indent=indent, sort_keys=sort_keys, ensure_ascii=ensure_ascii)
    return _JSON_ESCAPE_RE.sub(_json_escape, text)


def _print(text: str, file: IO[str], *, end: str = "\n", ascii_text: Any = None) -> None:
    """Print, and fall back to escapes on a stream that cannot encode the text."""
    try:
        print(text, end=end, file=file)
    except UnicodeEncodeError:
        if ascii_text is not None:
            text = ascii_text()
        else:
            encoding = getattr(file, "encoding", None) or "ascii"
            text = text.encode(encoding, "backslashreplace").decode(encoding)
        print(text, end=end, file=file)


def _attr(value: Any) -> str:
    collapsed = " ".join(strip_hidden(str(value)).split())
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
        _print(text, self.file, end="" if text.endswith("\n") else "\n")

    def write_json(self, obj: Any, *, indent: int | None = None, sort_keys: bool = False) -> None:
        """Print a JSON document inside the block."""
        _print(
            dumps(obj, indent=indent, sort_keys=sort_keys),
            self.file,
            ascii_text=lambda: dumps(obj, indent=indent, sort_keys=sort_keys, ensure_ascii=True),
        )

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
