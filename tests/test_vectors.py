"""Parametrized tests over test_vectors/ sample news files."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from geek42.parser import parse_news_file
from geek42.renderer import body_to_html

VECTORS_DIR = Path(__file__).parent.parent / "test_vectors"

# -- Valid news file vectors --

VALID_VECTORS = [
    ("news/valid-format2.en.txt", "FlexiBLAS Migration", date(2025, 11, 30), 2),
    ("news/valid-format1.en.txt", "Old Format News", date(2017, 3, 2), 1),
    ("news/unicode-body.en.txt", "Unicode Support", date(2026, 1, 15), 1),
    ("news/multiple-authors.en.txt", "Multi Author Item", date(2026, 3, 1), 1),
    ("news/all-optional-headers.en.txt", "Full Headers", date(2026, 2, 1), 3),
    ("news/minimal.en.txt", "Minimal", date(2026, 1, 1), 1),
]


@pytest.mark.parametrize(
    ("filename", "expected_title", "expected_date", "expected_revision"),
    VALID_VECTORS,
    ids=[v[0] for v in VALID_VECTORS],
)
def test_valid_vector_parses(
    filename: str,
    expected_title: str,
    expected_date: date,
    expected_revision: int,
) -> None:
    path = VECTORS_DIR / filename
    item = parse_news_file(path)
    assert item.title == expected_title
    assert item.posted == expected_date
    assert item.revision == expected_revision
    assert len(item.body) > 0


def test_format2_has_multiple_authors() -> None:
    item = parse_news_file(VECTORS_DIR / "news/multiple-authors.en.txt")
    assert len(item.authors) == 3
    assert "Alice" in item.authors[0]


def test_all_optional_headers_parsed() -> None:
    item = parse_news_file(VECTORS_DIR / "news/all-optional-headers.en.txt")
    assert item.display_if_installed == ["sys-devel/gcc"]
    assert "amd64" in item.display_if_keyword
    assert "arm64" in item.display_if_keyword
    assert item.display_if_profile == ["default/linux/amd64/23.0"]
    assert len(item.translators) == 1


def test_unicode_body_renders() -> None:
    item = parse_news_file(VECTORS_DIR / "news/unicode-body.en.txt")
    html = body_to_html(item.body)
    assert isinstance(html, str)
    assert len(html) > 0


# -- XSS vectors: dangerous elements must be stripped --

XSS_VECTORS = [
    ("xss/script-in-body.en.txt", "<script>"),
    ("xss/event-handler.en.txt", "onerror"),
    ("xss/javascript-url.en.txt", "javascript:"),
]


@pytest.mark.parametrize(
    ("filename", "forbidden"),
    XSS_VECTORS,
    ids=[v[0] for v in XSS_VECTORS],
)
def test_xss_vector_stripped(filename: str, forbidden: str) -> None:
    """Dangerous HTML elements must not appear in body_to_html output."""
    item = parse_news_file(VECTORS_DIR / filename)
    html = body_to_html(item.body)
    assert forbidden not in html.lower(), f"Found {forbidden!r} in rendered HTML: {html}"
