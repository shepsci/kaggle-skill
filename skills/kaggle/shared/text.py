"""Turn Kaggle content into text that is cheap to read.

Kaggle stores a competition page as Markdown or, for older competitions, as
HTML. ``to_text`` leaves Markdown as it is, apart from ``<br>`` line breaks,
and turns an HTML page into Markdown-like text: headings, lists, links, code
and tables survive, the tags do not.

Nothing here makes text safe to follow. The result is still written by a
competition host or a participant, and callers print it inside an
untrusted-content block.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser

KAGGLE_BASE = "https://www.kaggle.com"

_BLOCK_CLOSE_RE = re.compile(r"</(p|div|h[1-6]|ul|ol|li|table|tr|td|th|pre)\s*>", re.IGNORECASE)
_MARKDOWN_LINE_RE = re.compile(r"^(#{1,6}\s?\S|[-*+] \S|\d+\. \S)", re.MULTILINE)
_BR_RE = re.compile(r"[ \t]*<br\s*/?>[ \t]*\n?", re.IGNORECASE)
_BLANK_LINES_RE = re.compile(r"\n{3,}")
_SPACE_RE = re.compile(r"[ \t\r\f\v\n]+")

_SKIPPED = {"script", "style", "noscript", "template", "head", "title", "svg", "math"}
_BLOCKS = {
    "p",
    "div",
    "section",
    "article",
    "header",
    "footer",
    "main",
    "aside",
    "figure",
    "figcaption",
    "blockquote",
    "ul",
    "ol",
    "table",
    "details",
    "summary",
    "form",
    "dl",
    "dt",
    "dd",
}
_HEADINGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}
_LINK_SCHEMES = ("http://", "https://", "mailto:")


def is_html(content: str) -> bool:
    """True when the content is an HTML page and not Markdown with a few tags in it."""
    if len(_BLOCK_CLOSE_RE.findall(content)) < 2:
        return False
    return content.lstrip().startswith("<") or not _MARKDOWN_LINE_RE.search(content)


class _Converter(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.out: list[str] = []
        self.skip_depth = 0
        self.pre_depth = 0
        self.lists: list[list] = []  # [kind, next number]
        self.links: list[tuple[int, str]] = []

    # -- output helpers ------------------------------------------------------

    def _emit(self, text: str) -> None:
        if text:
            self.out.append(text)

    def _break(self, lines: int = 2) -> None:
        self.out.append("\n" * lines)

    def _mark(self, marker: str) -> None:
        """Emphasis markers, except inside a code block, where they would be shown."""
        if not self.pre_depth:
            self.out.append(marker)

    def _href(self, attrs: list[tuple[str, str | None]]) -> str:
        href = (dict(attrs).get("href") or "").strip()
        if href.startswith("/") and not href.startswith("//"):
            return self.base_url + href
        return href if href.lower().startswith(_LINK_SCHEMES) else ""

    # -- parser callbacks ----------------------------------------------------

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIPPED:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag in _HEADINGS:
            self._break()
            self._emit("#" * _HEADINGS[tag] + " ")
        elif tag in _BLOCKS:
            self._break()
            if tag in ("ul", "ol"):
                self.lists.append([tag, 1])
        elif tag == "br":
            self._break(1)
        elif tag == "hr":
            self._break()
            self._emit("---")
            self._break()
        elif tag == "li":
            self._break(1)
            indent = "  " * max(len(self.lists) - 1, 0)
            if self.lists and self.lists[-1][0] == "ol":
                self._emit(f"{indent}{self.lists[-1][1]}. ")
                self.lists[-1][1] += 1
            else:
                self._emit(f"{indent}- ")
        elif tag == "pre":
            self.pre_depth += 1
            self._break()
            self._emit("```\n")
        elif tag == "code":
            if not self.pre_depth:
                self._emit("`")
        elif tag in ("strong", "b"):
            self._mark("**")
        elif tag in ("em", "i"):
            self._mark("*")
        elif tag == "a":
            self.links.append((len(self.out), self._href(attrs)))
        elif tag == "img":
            alt = (dict(attrs).get("alt") or "").strip()
            if alt:
                self._emit(f"[image: {alt}]")
        elif tag == "tr":
            self._break(1)
            self._emit("| ")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag in _SKIPPED:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIPPED:
            self.skip_depth = max(self.skip_depth - 1, 0)
            return
        if self.skip_depth:
            return
        if tag in _HEADINGS:
            self._break()
        elif tag in _BLOCKS:
            if tag in ("ul", "ol") and self.lists:
                self.lists.pop()
            self._break()
        elif tag == "pre":
            self.pre_depth = max(self.pre_depth - 1, 0)
            self._emit("\n```")
            self._break()
        elif tag == "code":
            if not self.pre_depth:
                self._emit("`")
        elif tag in ("strong", "b"):
            self._mark("**")
        elif tag in ("em", "i"):
            self._mark("*")
        elif tag == "a" and self.links:
            start, href = self.links.pop()
            label = "".join(self.out[start:]).strip()
            del self.out[start:]
            if href and label and label != href:
                self._emit(f"[{label}]({href})")
            else:
                self._emit(label or href)
        elif tag in ("td", "th"):
            self._emit(" | ")

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        if self.pre_depth:
            self._emit(data)
            return
        text = _SPACE_RE.sub(" ", data)
        if text == " " and (not self.out or self.out[-1].endswith(("\n", " "))):
            return
        if self.out and self.out[-1].endswith("\n"):
            text = text.lstrip(" ")
        self._emit(text)


def _tidy(text: str) -> str:
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    return _BLANK_LINES_RE.sub("\n\n", "\n".join(lines)).strip()


def html_to_text(content: str, base_url: str = KAGGLE_BASE) -> str:
    """Convert an HTML fragment to Markdown-like text."""
    converter = _Converter(base_url)
    converter.feed(content)
    converter.close()
    return _tidy("".join(converter.out))


def to_text(content: str, base_url: str = KAGGLE_BASE) -> str:
    """Readable text for a page that may be HTML or Markdown."""
    if not content:
        return ""
    if is_html(content):
        return html_to_text(content, base_url)
    return _tidy(_BR_RE.sub("\n", content))


def collapse(text: str) -> str:
    """The text on one line, with single spaces."""
    return _SPACE_RE.sub(" ", text or "").strip()


_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_EMPHASIS_RE = re.compile(r"(\*\*|__|`)")


def plain(text: str) -> str:
    """Markdown read as plain words: images dropped, links as their text, no ** or `."""
    text = _IMAGE_RE.sub("", text)
    text = _LINK_RE.sub(r"\1", text)
    return _EMPHASIS_RE.sub("", text)


def shorten(text: str, limit: int) -> str:
    """Cut ``text`` to ``limit`` characters, ending with an ellipsis when cut."""
    text = text or ""
    if limit <= 0 or len(text) <= limit:
        return text
    return text[: max(limit - 1, 0)].rstrip() + "…"


def human_size(size: int | float | str | None) -> str:
    """A byte count as ``512 B``, ``3.2 KB``, ``1.5 GB``."""
    try:
        value = float(size)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "?"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(value) < 1000 or unit == "TB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1000
    return "?"


def absolute_url(url: str | None, base_url: str = KAGGLE_BASE) -> str:
    """A Kaggle URL with its host: ``/competitions/x`` becomes ``https://www.kaggle.com/...``."""
    url = (url or "").strip()
    if not url or url.lower().startswith(("http://", "https://")):
        return url
    return base_url + (url if url.startswith("/") else "/" + url)


# -- time -------------------------------------------------------------------

_FRACTION_RE = re.compile(r"\.(\d+)")


def parse_time(value: object) -> datetime | None:
    """Parse the timestamps Kaggle returns: ``2026-10-22T23:59:00Z``, with or
    without fractional seconds (up to nine digits) and with or without a zone.
    A value without a zone is taken as UTC. Returns None for anything else."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    # datetime.fromisoformat accepts at most six fractional digits.
    text = _FRACTION_RE.sub(lambda m: "." + m.group(1)[:6].ljust(6, "0"), text, count=1)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def span(delta: timedelta) -> str:
    """A duration in its two largest units: ``20 d 3 h``, ``3 h 12 min``, ``45 s``."""
    seconds = int(abs(delta.total_seconds()))
    days, rest = divmod(seconds, 86400)
    hours, rest = divmod(rest, 3600)
    minutes, secs = divmod(rest, 60)
    if days:
        return f"{days} d {hours} h"
    if hours:
        return f"{hours} h {minutes} min"
    if minutes:
        return f"{minutes} min"
    return f"{secs} s"


def when(value: object, now: datetime | None = None) -> str:
    """A timestamp with its distance from now: ``2026-10-22 23:59 UTC (in 20 d 3 h)``."""
    moment = parse_time(value)
    if moment is None:
        return str(value) if value else "not given"
    now = now or now_utc()
    stamp = moment.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    distance = span(moment - now)
    return f"{stamp} (in {distance})" if moment > now else f"{stamp} ({distance} ago)"


def day(value: object) -> str:
    """The date part of a timestamp, or ``-``."""
    moment = parse_time(value)
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%d") if moment else "-"
