"""Tests for Markdown and HTML rendering."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from geek42.models import NewsItem
from geek42.renderer import body_to_html, news_to_markdown, write_markdown


def _make_item(**kwargs: Any) -> NewsItem:
    defaults: dict[str, Any] = {
        "id": "2025-01-01-test",
        "title": "Test Item",
        "authors": ["Dev <dev@gentoo.org>"],
        "posted": date(2025, 1, 1),
        "body": "Test body content.",
    }
    defaults.update(kwargs)
    return NewsItem(**defaults)


def test_news_to_markdown_basic() -> None:
    item = _make_item()
    md = news_to_markdown(item)

    assert md.startswith("---\n")
    assert 'title: "Test Item"' in md
    assert "date: 2025-01-01" in md
    assert "Test body content." in md


def test_news_to_markdown_with_packages() -> None:
    item = _make_item(
        display_if_installed=["sys-apps/foo", "dev-libs/bar"],
        display_if_keyword=["amd64", "arm64"],
    )
    md = news_to_markdown(item)

    assert "packages:" in md
    assert '  - "sys-apps/foo"' in md
    assert "keywords:" in md
    assert '  - "amd64"' in md


def test_news_to_markdown_with_source() -> None:
    item = _make_item(source="gentoo")
    md = news_to_markdown(item)
    assert 'source: "gentoo"' in md


def test_body_to_html_paragraphs() -> None:
    body = "First paragraph.\n\nSecond paragraph."
    html = body_to_html(body)

    assert "<p>" in html
    assert "First paragraph." in html
    assert "Second paragraph." in html


def test_body_to_html_autolinks_urls() -> None:
    body = "Visit https://wiki.gentoo.org/wiki/Test for details."
    html = body_to_html(body)

    assert "https://wiki.gentoo.org/wiki/Test" in html
    assert "<a" in html or "href" in html


def test_write_markdown(tmp_path: Path) -> None:
    item = _make_item()
    path = write_markdown(item, tmp_path / "md")

    assert path.exists()
    assert path.name == "2025-01-01-test.md"
    content = path.read_text()
    assert "Test Item" in content
