"""Property-based tests for the GLEP 42 parser and related functions."""

from __future__ import annotations

import re
import tempfile
from datetime import date
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from geek42.compose import title_to_slug
from geek42.parser import parse_news_file
from geek42.renderer import body_to_html

# -- Strategies --

_valid_date = st.dates(min_value=date(2000, 1, 1), max_value=date(2099, 12, 31))

_valid_title = (
    st.text(
        alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z"), max_codepoint=0x7E),
        min_size=1,
        max_size=50,
    )
    .map(lambda t: t.strip())
    .filter(lambda t: len(t) > 0 and "\n" not in t)
)

_valid_author = st.from_regex(r"[A-Z][a-z]+ [A-Z][a-z]+ <[a-z]+@[a-z]+\.[a-z]+>", fullmatch=True)

_valid_revision = st.integers(min_value=1, max_value=999)

_body_text = st.text(min_size=1, max_size=500).filter(lambda t: t.strip())


def _build_news_file(title: str, author: str, posted: date, revision: int, body: str) -> str:
    return (
        f"Title: {title}\n"
        f"Author: {author}\n"
        f"Posted: {posted.isoformat()}\n"
        f"Revision: {revision}\n"
        "News-Item-Format: 2.0\n"
        f"\n{body}\n"
    )


# -- Properties --


@given(
    title=_valid_title,
    author=_valid_author,
    posted=_valid_date,
    revision=_valid_revision,
    body=_body_text,
)
@settings(deadline=2000, max_examples=50)
def test_valid_news_file_roundtrips(
    title: str, author: str, posted: date, revision: int, body: str
) -> None:
    """A correctly structured news file always parses without error."""
    content = _build_news_file(title, author, posted, revision, body)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".en.txt", delete=False) as f:
        f.write(content)
        f.flush()
        item = parse_news_file(Path(f.name))

    assert item.title == title
    assert item.posted == posted
    assert item.revision == revision
    assert len(item.body) > 0


@given(body=st.text(min_size=0, max_size=1000))
@settings(deadline=2000, max_examples=100)
def test_body_to_html_never_raises(body: str) -> None:
    """body_to_html should never raise on arbitrary Unicode input."""
    result = body_to_html(body)
    assert isinstance(result, str)


@given(body=st.text(min_size=0, max_size=500))
@settings(deadline=2000, max_examples=100)
def test_body_to_html_never_contains_script(body: str) -> None:
    """body_to_html output must never contain <script> tags."""
    result = body_to_html(body)
    assert "<script" not in result.lower()


@given(title=st.text(min_size=1, max_size=100).filter(lambda t: t.strip()))
@settings(deadline=2000, max_examples=100)
def test_title_to_slug_valid_chars(title: str) -> None:
    """title_to_slug always produces a string with only [a-z0-9-] or empty."""
    slug = title_to_slug(title)
    if slug:
        assert re.fullmatch(r"[a-z0-9-]+", slug), f"Bad slug: {slug!r} from {title!r}"
        assert len(slug) <= 50
