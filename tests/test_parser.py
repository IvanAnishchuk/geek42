"""Tests for GLEP 42 parser."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from geek42.errors import InvalidHeaderValueError, MissingHeaderError, ParseError
from geek42.parser import (
    parse_markdown_file,
    parse_news_file,
    scan_markdown_dir,
    scan_repo,
    update_markdown_frontmatter,
    update_news_header,
)

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


# -- exception paths --


def test_parse_missing_title_raises(tmp_path: Path) -> None:
    item_dir = tmp_path / "2025-01-01-no-title"
    item_dir.mkdir()
    f = item_dir / "2025-01-01-no-title.en.txt"
    f.write_text("Author: D <d@g>\nPosted: 2025-01-01\nRevision: 1\nNews-Item-Format: 2.0\n\nBody.")
    with pytest.raises(MissingHeaderError) as exc_info:
        parse_news_file(f)
    assert exc_info.value.header == "Title"
    assert exc_info.value.path == f


def test_parse_missing_posted_raises(tmp_path: Path) -> None:
    item_dir = tmp_path / "2025-01-01-no-posted"
    item_dir.mkdir()
    f = item_dir / "2025-01-01-no-posted.en.txt"
    f.write_text("Title: T\nAuthor: D <d@g>\nRevision: 1\nNews-Item-Format: 2.0\n\nBody.")
    with pytest.raises(MissingHeaderError) as exc_info:
        parse_news_file(f)
    assert exc_info.value.header == "Posted"


def test_parse_invalid_posted_date(tmp_path: Path) -> None:
    item_dir = tmp_path / "2025-01-01-bad-date"
    item_dir.mkdir()
    f = item_dir / "2025-01-01-bad-date.en.txt"
    f.write_text(
        "Title: T\nAuthor: D <d@g>\nPosted: not-a-date\nRevision: 1\nNews-Item-Format: 2.0\n\nBody."
    )
    with pytest.raises(InvalidHeaderValueError) as exc_info:
        parse_news_file(f)
    assert exc_info.value.header == "Posted"
    assert exc_info.value.value == "not-a-date"


def test_parse_invalid_revision(tmp_path: Path) -> None:
    item_dir = tmp_path / "2025-01-01-bad-rev"
    item_dir.mkdir()
    f = item_dir / "2025-01-01-bad-rev.en.txt"
    f.write_text(
        "Title: T\nAuthor: D <d@g>\nPosted: 2025-01-01\nRevision: abc\n"
        "News-Item-Format: 2.0\n\nBody."
    )
    with pytest.raises(InvalidHeaderValueError) as exc_info:
        parse_news_file(f)
    assert exc_info.value.header == "Revision"
    assert exc_info.value.value == "abc"


def test_parse_news_file_str_message(tmp_path: Path) -> None:
    """ParseError __str__ includes the file path for context."""
    item_dir = tmp_path / "2025-01-01-no-title"
    item_dir.mkdir()
    f = item_dir / "2025-01-01-no-title.en.txt"
    f.write_text("Author: D <d@g>\nPosted: 2025-01-01\n\nBody.")
    with pytest.raises(MissingHeaderError) as exc_info:
        parse_news_file(f)
    assert "no-title.en.txt" in str(exc_info.value)
    assert "Title" in str(exc_info.value)


# -- Markdown parser --


def test_parse_markdown_basic(tmp_path: Path) -> None:
    f = tmp_path / "2026-04-15-test.md"
    f.write_text('---\ntitle: "Test Post"\ndate: 2026-04-15\nauthors: "Dev <d@g>"\n---\n\nBody.\n')

    item = parse_markdown_file(f)
    assert item.id == "2026-04-15-test"
    assert item.title == "Test Post"
    assert item.posted == date(2026, 4, 15)
    assert item.authors == ["Dev <d@g>"]
    assert item.body == "Body."
    assert item.item_type == "news"


def test_parse_markdown_advisory(tmp_path: Path) -> None:
    f = tmp_path / "2026-05-01-vuln.md"
    f.write_text(
        '---\ntitle: "Fix"\ndate: 2026-05-01\nauthors: "Dev <d@g>"\n'
        'item_type: "advisory"\nadvisory_severity: "high"\n'
        'advisory_cves:\n  - "CVE-2026-12345"\n'
        'advisory_affected:\n  - "<0.5.0"\n'
        'advisory_fixed: "0.5.0"\n'
        'packages:\n  - "dev-python/geek42"\n---\n\nVuln details.\n'
    )

    item = parse_markdown_file(f)
    assert item.item_type == "advisory"
    assert item.advisory_severity == "high"
    assert item.advisory_cves == ["CVE-2026-12345"]
    assert item.advisory_affected == ["<0.5.0"]
    assert item.advisory_fixed == "0.5.0"
    assert item.display_if_installed == ["dev-python/geek42"]


def test_parse_markdown_roundtrip(tmp_path: Path) -> None:
    """Write with news_to_markdown, read back — fields should match."""
    from geek42.renderer import news_to_markdown

    from .conftest import make_item

    original = make_item(
        id="2026-01-01-rt",
        title="Round Trip",
        authors=["A <a@b>"],
        posted=date(2026, 1, 1),
        body="Paragraph one.\n\nParagraph two.",
        display_if_installed=["cat/pkg"],
        display_if_keyword=["amd64"],
        item_type="advisory",
        advisory_severity="medium",
        advisory_cves=["CVE-2026-00001"],
        advisory_fixed="1.2.3",
    )
    md = news_to_markdown(original)
    f = tmp_path / f"{original.id}.md"
    f.write_text(md)

    parsed = parse_markdown_file(f)
    assert parsed.title == original.title
    assert parsed.posted == original.posted
    assert parsed.revision == original.revision
    assert parsed.display_if_installed == original.display_if_installed
    assert parsed.display_if_keyword == original.display_if_keyword
    assert parsed.item_type == original.item_type
    assert parsed.advisory_severity == original.advisory_severity
    assert parsed.advisory_cves == original.advisory_cves
    assert parsed.advisory_fixed == original.advisory_fixed
    assert parsed.body == original.body


def test_parse_markdown_missing_fence(tmp_path: Path) -> None:
    f = tmp_path / "bad.md"
    f.write_text("no frontmatter here")
    with pytest.raises(ParseError):
        parse_markdown_file(f)


def test_parse_markdown_missing_title(tmp_path: Path) -> None:
    f = tmp_path / "bad.md"
    f.write_text("---\ndate: 2026-01-01\n---\nBody.")
    with pytest.raises(MissingHeaderError):
        parse_markdown_file(f)


def test_parse_markdown_missing_date(tmp_path: Path) -> None:
    f = tmp_path / "bad.md"
    f.write_text('---\ntitle: "T"\n---\nBody.')
    with pytest.raises(MissingHeaderError):
        parse_markdown_file(f)


def test_scan_markdown_dir(tmp_path: Path) -> None:
    (tmp_path / "post1.md").write_text('---\ntitle: "A"\ndate: 2026-01-01\nauthors: "X"\n---\nA\n')
    (tmp_path / "post2.md").write_text('---\ntitle: "B"\ndate: 2026-01-02\nauthors: "Y"\n---\nB\n')
    (tmp_path / "not-md.txt").write_text("ignored")

    items = scan_markdown_dir(tmp_path, source="test", item_type="blog")
    assert len(items) == 2
    assert all(i.item_type == "blog" for i in items)
    assert all(i.source == "test" for i in items)


def test_scan_markdown_dir_skips_bad_files(tmp_path: Path) -> None:
    good = '---\ntitle: "OK"\ndate: 2026-01-01\nauthors: "X"\n---\nBody\n'
    (tmp_path / "good.md").write_text(good)
    (tmp_path / "bad.md").write_text("no frontmatter")

    items = scan_markdown_dir(tmp_path)
    assert len(items) == 1


def test_scan_markdown_dir_nonexistent() -> None:
    items = scan_markdown_dir(Path("/nonexistent/path"))
    assert items == []


def test_scan_markdown_dir_preserves_explicit_type(tmp_path: Path) -> None:
    """If frontmatter has item_type, it should NOT be overridden by default."""
    (tmp_path / "adv.md").write_text(
        '---\ntitle: "X"\ndate: 2026-01-01\nauthors: "A"\nitem_type: "advisory"\n---\nBody\n'
    )
    items = scan_markdown_dir(tmp_path, item_type="blog")
    assert len(items) == 1
    assert items[0].item_type == "advisory"


# -- Header write-back --


def test_update_news_header_adds_new(tmp_path: Path) -> None:
    item_dir = tmp_path / "2026-01-01-test"
    item_dir.mkdir()
    f = item_dir / "2026-01-01-test.en.txt"
    f.write_text("Title: Test\nAuthor: A <a@b>\nPosted: 2026-01-01\n\nBody.\n")

    update_news_header(f, "Issue-URL", "https://github.com/x/y/issues/1")

    text = f.read_text()
    assert "Issue-URL: https://github.com/x/y/issues/1" in text
    # Should be before the blank line
    lines = text.split("\n")
    blank_idx = next(i for i, ln in enumerate(lines) if ln.strip() == "")
    issue_idx = next(i for i, ln in enumerate(lines) if "Issue-URL" in ln)
    assert issue_idx < blank_idx


def test_update_news_header_replaces_existing(tmp_path: Path) -> None:
    item_dir = tmp_path / "2026-01-01-test"
    item_dir.mkdir()
    f = item_dir / "2026-01-01-test.en.txt"
    f.write_text("Title: Test\nIssue-URL: old\nPosted: 2026-01-01\n\nBody.\n")

    update_news_header(f, "Issue-URL", "new-url")

    text = f.read_text()
    assert "Issue-URL: new-url" in text
    assert "old" not in text


def test_update_markdown_frontmatter_adds_new(tmp_path: Path) -> None:
    f = tmp_path / "test.md"
    f.write_text('---\ntitle: "Test"\ndate: 2026-01-01\n---\n\nBody.\n')

    update_markdown_frontmatter(f, "issue_url", "https://github.com/x/y/issues/1")

    text = f.read_text()
    assert 'issue_url: "https://github.com/x/y/issues/1"' in text
    # Should be within frontmatter (before closing ---)
    lines = text.split("\n")
    fences = [i for i, ln in enumerate(lines) if ln.strip() == "---"]
    issue_idx = next(i for i, ln in enumerate(lines) if "issue_url" in ln)
    assert fences[0] < issue_idx < fences[1]


def test_update_markdown_frontmatter_replaces_existing(tmp_path: Path) -> None:
    f = tmp_path / "test.md"
    f.write_text('---\ntitle: "Test"\nissue_url: "old"\n---\n\nBody.\n')

    update_markdown_frontmatter(f, "issue_url", "new-url")

    text = f.read_text()
    assert 'issue_url: "new-url"' in text
    assert "old" not in text
