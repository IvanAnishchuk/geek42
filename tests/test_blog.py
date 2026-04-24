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


# -- Three-source compilation --


def test_compile_with_blog_posts(news_repo: Path) -> None:
    posts_dir = news_repo / "metadata" / "posts"
    posts_dir.mkdir(parents=True)
    (posts_dir / "2026-04-15-thoughts.md").write_text(
        '---\ntitle: "My Thoughts"\ndate: 2026-04-15\nauthors: "Test"\n---\n\nBlog content.\n'
    )

    count = compile_news(news_repo)
    assert count == 3  # 2 news + 1 blog post

    md = (news_repo / "news" / "2026-04-15-thoughts.md").read_text()
    assert "My Thoughts" in md
    assert 'item_type: "blog"' in md


def test_compile_with_advisories(news_repo: Path) -> None:
    glsa_dir = news_repo / "metadata" / "glsa"
    glsa_dir.mkdir(parents=True)
    (glsa_dir / "2026-05-01-vuln.md").write_text(
        '---\ntitle: "Security Fix"\ndate: 2026-05-01\nauthors: "Test"\n'
        'item_type: "advisory"\nadvisory_severity: "high"\n'
        'advisory_cves:\n  - "CVE-2026-99999"\npackages:\n  - "dev-python/geek42"\n'
        "---\n\nFix a vulnerability.\n"
    )

    count = compile_news(news_repo)
    assert count == 3  # 2 news + 1 advisory

    # Compiled Markdown in news/
    md = (news_repo / "news" / "2026-05-01-vuln.md").read_text()
    assert 'item_type: "advisory"' in md
    assert 'advisory_severity: "high"' in md

    # GLSA XML generated
    xml_files = list(glsa_dir.glob("glsa-*.xml"))
    assert len(xml_files) == 1
    xml = xml_files[0].read_text()
    assert "Security Fix" in xml
    assert "CVE-2026-99999" in xml


def test_compile_removes_stale_glsa_xml(news_repo: Path) -> None:
    glsa_dir = news_repo / "metadata" / "glsa"
    glsa_dir.mkdir(parents=True)

    # Create an advisory
    (glsa_dir / "2026-05-01-vuln.md").write_text(
        '---\ntitle: "Fix"\ndate: 2026-05-01\nauthors: "T"\nitem_type: "advisory"\n---\n\nBody.\n'
    )
    compile_news(news_repo)
    assert len(list(glsa_dir.glob("glsa-*.xml"))) == 1

    # Remove the source advisory
    (glsa_dir / "2026-05-01-vuln.md").unlink()
    compile_news(news_repo)

    # Stale XML should be cleaned up
    assert len(list(glsa_dir.glob("glsa-*.xml"))) == 0


def test_compile_to_repo_root(news_repo: Path) -> None:
    # Write a README to preserve
    (news_repo / "README.md").write_text("# My Blog\n\nWelcome.\n")

    count = compile_news(news_repo, news_dir="")
    assert count == 2

    # Compiled .md files at root
    assert (news_repo / "2025-11-30-flexiblas-migration.md").exists()
    assert (news_repo / "2017-03-02-old-format.md").exists()

    # README preserved, index appended
    readme = (news_repo / "README.md").read_text()
    assert readme.startswith("# My Blog\n")
    assert "Welcome." in readme
    assert _INDEX_START in readme
    # Links should be relative (no subdirectory prefix)
    assert "(2025-11-30-flexiblas-migration.md)" in readme


def test_compile_root_safe_cleanup(news_repo: Path) -> None:
    """Stale cleanup at root only removes date-prefixed .md files."""
    compile_news(news_repo, news_dir="")

    # Create non-date-prefixed .md file (should NOT be deleted)
    (news_repo / "CONTRIBUTING.md").write_text("# Contributing\n")
    # Create stale date-prefixed .md file (should be deleted)
    (news_repo / "2020-01-01-removed.md").write_text("stale")

    compile_news(news_repo, news_dir="")

    assert (news_repo / "CONTRIBUTING.md").exists()
    assert not (news_repo / "2020-01-01-removed.md").exists()
