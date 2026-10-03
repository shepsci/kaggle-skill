"""Unit tests for skills/kaggle/shared/text.py."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from shared import text

HTML_PAGE = """<h2>Goal</h2>
<p>Predict <b>survival</b>. See the <a href="/c/titanic/data">Data page</a> and
<a href="https://example.org/x">this</a>.</p>
<ul><li>One</li><li>Two &amp; three</li></ul>
<ol><li>First</li><li>Second</li></ol>
<pre><b>Id,Survived</b>
892,0</pre>
<table><tr><th>Variable</th><th>Key</th></tr><tr><td>sex</td><td></td></tr></table>
<script>alert(1)</script><style>p {color: red}</style>
<p>Line one<br>line two <img src="x.png" alt="a chart"> <a href="javascript:alert(1)">bad</a></p>
"""


def test_html_becomes_markdown_like_text():
    out = text.to_text(HTML_PAGE)
    assert out.startswith("## Goal\n\nPredict **survival**. See the ")
    assert "[Data page](https://www.kaggle.com/c/titanic/data)" in out
    assert "[this](https://example.org/x)" in out
    assert "- One\n- Two & three" in out
    assert "1. First\n2. Second" in out
    assert "```\nId,Survived\n892,0\n```" in out
    assert "| Variable | Key |\n| sex |" in out
    assert "Line one\nline two [image: a chart] bad" in out
    assert "alert" not in out and "color" not in out and "<" not in out


def test_markdown_is_left_alone_apart_from_line_breaks():
    page = "## Prizes\n\n**Main** <br/>\nFirst: $9 <br>\n- item `List<int>`\n\n\n\nend"
    assert text.to_text(page) == "## Prizes\n\n**Main**\nFirst: $9\n- item `List<int>`\n\nend"


@pytest.mark.parametrize(
    "content, expected",
    [
        ("<h3>Goal</h3>\n<p>Predict.</p>", True),
        ("<p>one</p>", False),  # a single tag is not a page
        ("## Title\n\ntext <br> more", False),
        ("### Rules\n\n<p>a</p><p>b</p>", False),  # Markdown that embeds some HTML
        ("plain text\nwith lines", False),
        ("intro text <p>a</p><p>b</p>", True),
    ],
)
def test_is_html(content, expected):
    assert text.is_html(content) is expected


def test_empty_and_helper_functions():
    assert text.to_text("") == ""
    assert text.collapse("  a \n\t b  ") == "a b"
    assert text.shorten("abcdef", 4) == "abc…"
    assert text.shorten("abc", 4) == "abc"
    assert text.human_size(512) == "512 B"
    assert text.human_size("3258") == "3.3 KB"
    assert text.human_size(1_500_000_000) == "1.5 GB"
    assert text.human_size(None) == "?"
    assert text.absolute_url("/competitions/x") == "https://www.kaggle.com/competitions/x"
    assert text.absolute_url("https://a/b") == "https://a/b"
    assert text.absolute_url("") == ""


@pytest.mark.parametrize(
    "value",
    [
        "2026-10-22T23:59:00Z",
        "2026-10-22T23:59:00.604174100Z",  # nine fractional digits
        "2026-10-22T23:59:00.013Z",
        "2026-10-22T23:59:00",
        "2026-10-22T23:59:00+00:00",
    ],
)
def test_parse_time_accepts_kaggles_formats(value):
    parsed = text.parse_time(value)
    assert parsed is not None and parsed.tzinfo is not None
    assert parsed.replace(microsecond=0) == datetime(2026, 10, 22, 23, 59, tzinfo=timezone.utc)


def test_parse_time_rejects_other_values():
    assert text.parse_time("soon") is None
    assert text.parse_time("") is None
    assert text.parse_time(None) is None


def test_when_and_span():
    now = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)
    assert text.when("2026-10-22T23:59:00Z", now) == "2026-10-22 23:59 UTC (in 20 d 11 h)"
    assert text.when("2026-10-02T09:30:00Z", now) == "2026-10-02 09:30 UTC (2 h 30 min ago)"
    assert text.when(None, now) == "not given"
    assert text.when("garbage", now) == "garbage"
    assert text.span(timedelta(seconds=45)) == "45 s"
    assert text.span(timedelta(minutes=5, seconds=2)) == "5 min"
    assert text.day("2026-10-22T23:59:00Z") == "2026-10-22"
    assert text.day(None) == "-"
