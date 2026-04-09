"""Tests for GLEP 42 parser."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from geek42.parser import parse_news_file, scan_repo

from .conftest import SAMPLE_NEWS_FORMAT1, SAMPLE_NEWS_FORMAT2


def test_parse_format2(tmp_path: Path) -> None:
    item_dir = tmp_path / "2025-11-30-flexiblas-migration"
    item_dir.mkdir()
    news_file = item_dir / "2025-11-30-flexiblas-migration.en.txt"
    news_file.write_text(SAMPLE_NEWS_FORMAT2)

    item = parse_news_file(news_file, source="gentoo")

    assert item.id == "2025-11-30-flexiblas-migration"
    assert item.title == "FlexiBLAS Migration"
    assert item.authors == ["Sam James <sam@gentoo.org>", "Ada Lovelace <ada@example.org>"]
    assert item.posted == date(2025, 11, 30)
    assert item.revision == 2
    assert item.news_item_format == "2.0"
    assert item.content_type is None
    assert item.display_if_installed == ["app-eselect/eselect-blas", "sci-libs/flexiblas"]
    assert item.display_if_keyword == ["amd64"]
    assert item.display_if_profile == ["default/linux/amd64/23.0"]
    assert item.language == "en"
    assert item.source == "gentoo"
    assert "FlexiBLAS migration" in item.body
    assert "https://wiki.gentoo.org/wiki/FlexiBLAS" in item.body


def test_parse_format1(tmp_path: Path) -> None:
    item_dir = tmp_path / "2017-03-02-old-format"
    item_dir.mkdir()
    news_file = item_dir / "2017-03-02-old-format.en.txt"
    news_file.write_text(SAMPLE_NEWS_FORMAT1)

    item = parse_news_file(news_file)

    assert item.title == "Old Format News"
    assert item.news_item_format == "1.0"
    assert item.content_type == "text/plain"
    assert item.revision == 1
    assert item.display_if_installed == []
    assert item.display_if_keyword == []
    assert "older format 1.0" in item.body


def test_parse_language_extraction(tmp_path: Path) -> None:
    item_dir = tmp_path / "2025-01-01-test"
    item_dir.mkdir()
    news_file = item_dir / "2025-01-01-test.de.txt"
    news_file.write_text(
        "Title: German News\nAuthor: Dev <d@g.org>\nPosted: 2025-01-01\n"
        "Revision: 1\nNews-Item-Format: 2.0\n\nDeutsch body."
    )

    item = parse_news_file(news_file)
    assert item.language == "de"


def test_scan_repo(news_repo: Path) -> None:
    items = scan_repo(news_repo, source="test")

    assert len(items) == 2
    ids = {i.id for i in items}
    assert "2025-11-30-flexiblas-migration" in ids
    assert "2017-03-02-old-format" in ids
    for item in items:
        assert item.source == "test"


def test_scan_repo_skips_non_news_dirs(news_repo: Path) -> None:
    # .git-stuff and README should not produce items
    items = scan_repo(news_repo)
    assert all(i.id.startswith("20") for i in items)


def test_scan_repo_skips_malformed(news_repo: Path) -> None:
    bad_dir = news_repo / "2025-06-01-broken"
    bad_dir.mkdir()
    (bad_dir / "2025-06-01-broken.en.txt").write_text("not valid at all\n\x00\x01")

    items = scan_repo(news_repo)
    # Should still get the 2 valid items, broken one skipped
    assert len(items) == 2
