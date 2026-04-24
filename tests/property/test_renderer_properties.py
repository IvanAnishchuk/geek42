"""Property-based tests for the renderer module."""

from __future__ import annotations

from datetime import date

from bs4 import BeautifulSoup
from hypothesis import given, settings
from hypothesis import strategies as st

from geek42.models import NewsItem
from geek42.renderer import _yaml_str, body_to_html, news_to_markdown

# -- Strategies --

_news_item = st.builds(
    NewsItem,
    id=st.from_regex(r"20[0-9]{2}-[01][0-9]-[0-3][0-9]-[a-z-]{3,20}", fullmatch=True),
    title=st.text(min_size=1, max_size=50).filter(lambda t: t.strip() and "\n" not in t),
    authors=st.lists(
        st.from_regex(r"[A-Z][a-z]+ <[a-z]+@[a-z]+\.[a-z]+>", fullmatch=True),
        min_size=1,
        max_size=3,
    ),
    posted=st.dates(min_value=date(2000, 1, 1), max_value=date(2099, 12, 31)),
    revision=st.integers(min_value=1, max_value=99),
    body=st.text(min_size=1, max_size=200).filter(lambda t: t.strip()),
)


# -- Properties --


@given(value=st.text(min_size=0, max_size=200))
@settings(deadline=2000, max_examples=100)
def test_yaml_str_always_quoted(value: str) -> None:
    """_yaml_str always returns a double-quoted string."""
    result = _yaml_str(value)
    assert result.startswith('"')
    assert result.endswith('"')


@given(item=_news_item)
@settings(deadline=2000, max_examples=50)
def test_news_to_markdown_has_frontmatter(item: NewsItem) -> None:
    """news_to_markdown always produces YAML frontmatter."""
    md = news_to_markdown(item)
    assert md.startswith("---\n")
    assert md.count("---") >= 2
    assert f"date: {item.posted.isoformat()}" in md


@given(body=st.text(min_size=0, max_size=500))
@settings(deadline=2000, max_examples=100)
def test_body_to_html_returns_string(body: str) -> None:
    """body_to_html always returns a string for any input."""
    result = body_to_html(body)
    assert isinstance(result, str)


@given(body=st.text(min_size=0, max_size=500))
@settings(deadline=2000, max_examples=100)
def test_body_to_html_no_dangerous_elements(body: str) -> None:
    """Sanitized output must not contain dangerous HTML elements or attributes."""
    result = body_to_html(body)
    soup = BeautifulSoup(result, "html.parser")
    # No <script> or <iframe> elements in the parsed DOM
    assert soup.find("script") is None
    assert soup.find("iframe") is None
    # No event-handler attributes on any element
    for tag in soup.find_all(True):
        for attr in tag.attrs:
            assert not attr.startswith("on"), f"event handler {attr} found on <{tag.name}>"
