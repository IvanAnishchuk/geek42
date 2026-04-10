"""Tests for the blog compilation module."""

from __future__ import annotations

from pathlib import Path

from geek42.blog import _INDEX_END, _INDEX_START, compile_news


def test_compile_news_creates_markdown_files(news_repo: Path) -> None:
    count = compile_news(news_repo)

    assert count == 2
    news_dir = news_repo / "news"
    assert news_dir.is_dir()

    md_files = sorted(f.name for f in news_dir.glob("*.md"))
    assert "2017-03-02-old-format.md" in md_files
    assert "2025-11-30-flexiblas-migration.md" in md_files


def test_compile_news_markdown_has_frontmatter(news_repo: Path) -> None:
    compile_news(news_repo)

    md = (news_repo / "news" / "2025-11-30-flexiblas-migration.md").read_text()
    assert md.startswith("---\n")
    assert "title:" in md
    assert "FlexiBLAS Migration" in md
    assert "date: 2025-11-30" in md


def test_compile_news_creates_readme_index(news_repo: Path) -> None:
    compile_news(news_repo)

    readme = (news_repo / "README.md").read_text()
    assert _INDEX_START in readme
    assert _INDEX_END in readme
    assert "FlexiBLAS Migration" in readme
    assert "Old Format News" in readme
    assert "news/2025-11-30-flexiblas-migration.md" in readme


def test_compile_news_updates_existing_readme(news_repo: Path) -> None:
    readme_path = news_repo / "README.md"
    readme_path.write_text(
        "# My News Repo\n\nSome intro text.\n",
        encoding="utf-8",
    )

    compile_news(news_repo)

    readme = readme_path.read_text()
    assert readme.startswith("# My News Repo\n")
    assert "Some intro text." in readme
    assert _INDEX_START in readme
    assert "FlexiBLAS Migration" in readme


def test_compile_news_replaces_existing_index(news_repo: Path) -> None:
    readme_path = news_repo / "README.md"
    readme_path.write_text(
        f"# News\n\n{_INDEX_START}\nold index\n{_INDEX_END}\n\nFooter.\n",
        encoding="utf-8",
    )

    compile_news(news_repo)

    readme = readme_path.read_text()
    assert "old index" not in readme
    assert "FlexiBLAS Migration" in readme
    assert "Footer." in readme


def test_compile_news_is_idempotent(news_repo: Path) -> None:
    compile_news(news_repo)
    readme_after_first = (news_repo / "README.md").read_text()
    md_after_first = (news_repo / "news" / "2025-11-30-flexiblas-migration.md").read_text()

    compile_news(news_repo)
    readme_after_second = (news_repo / "README.md").read_text()
    md_after_second = (news_repo / "news" / "2025-11-30-flexiblas-migration.md").read_text()

    assert readme_after_first == readme_after_second
    assert md_after_first == md_after_second


def test_compile_news_removes_stale_markdown(news_repo: Path) -> None:
    compile_news(news_repo)

    # Create a stale file that doesn't correspond to any news item
    stale = news_repo / "news" / "2020-01-01-removed-item.md"
    stale.write_text("stale content")

    compile_news(news_repo)

    assert not stale.exists()
    assert (news_repo / "news" / "2025-11-30-flexiblas-migration.md").exists()


def test_compile_news_empty_repo(tmp_path: Path) -> None:
    count = compile_news(tmp_path)

    assert count == 0
    readme = (tmp_path / "README.md").read_text()
    assert _INDEX_START in readme
    assert "| Date | Title | Author |" in readme


def test_compile_news_custom_dirs(news_repo: Path) -> None:
    compile_news(news_repo, news_dir="blog", readme="INDEX.md")

    assert (news_repo / "blog").is_dir()
    assert (news_repo / "blog" / "2025-11-30-flexiblas-migration.md").exists()

    index = (news_repo / "INDEX.md").read_text()
    assert "blog/2025-11-30-flexiblas-migration.md" in index


def test_compile_news_index_sorted_newest_first(news_repo: Path) -> None:
    compile_news(news_repo)

    readme = (news_repo / "README.md").read_text()
    flexiblas_pos = readme.index("FlexiBLAS")
    old_pos = readme.index("Old Format")
    assert flexiblas_pos < old_pos
