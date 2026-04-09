"""Tests for the static site builder."""

from __future__ import annotations

from geek42.models import NewsItem, NewsSource, SiteConfig
from geek42.site import build_site, collect_items, pull_source


def test_pull_source(site_config: SiteConfig) -> None:
    source = site_config.sources[0]
    repo_dir = pull_source(source, site_config.data_dir)

    assert repo_dir.is_dir()
    assert (repo_dir / ".git").is_dir()


def test_collect_items_with_pull(site_config: SiteConfig) -> None:
    items = collect_items(site_config, pull=True)

    assert len(items) == 2
    assert all(isinstance(i, NewsItem) for i in items)
    # Should be sorted newest first
    assert items[0].posted >= items[1].posted


def test_collect_items_without_pull(site_config: SiteConfig) -> None:
    # First pull to make repos available
    for source in site_config.sources:
        pull_source(source, site_config.data_dir)

    items = collect_items(site_config, pull=False)
    assert len(items) == 2


def test_collect_items_empty_without_repos(site_config: SiteConfig) -> None:
    items = collect_items(site_config, pull=False)
    assert items == []


def test_build_site_creates_output(site_config: SiteConfig) -> None:
    items = collect_items(site_config, pull=True)
    count = build_site(site_config, items)

    assert count == 2
    output = site_config.output_dir
    assert (output / "index.html").exists()
    assert (output / "rss.xml").exists()
    assert (output / "atom.xml").exists()
    assert (output / "style.css").exists()
    assert (output / "posts").is_dir()


def test_build_site_creates_posts(site_config: SiteConfig) -> None:
    items = collect_items(site_config, pull=True)
    build_site(site_config, items)

    posts = list(site_config.output_dir.glob("posts/*.html"))
    assert len(posts) == 2

    html = (site_config.output_dir / "posts" / "2025-11-30-flexiblas-migration.html").read_text()
    assert "FlexiBLAS Migration" in html
    assert "Sam James" in html
    assert "schema.org" in html


def test_build_site_creates_markdown_exports(site_config: SiteConfig) -> None:
    items = collect_items(site_config, pull=True)
    build_site(site_config, items)

    md_files = list(site_config.output_dir.glob("markdown/*.md"))
    assert len(md_files) == 2


def test_build_site_empty_items(site_config: SiteConfig) -> None:
    count = build_site(site_config, [])
    assert count == 0


def test_build_site_index_contains_all_items(site_config: SiteConfig) -> None:
    items = collect_items(site_config, pull=True)
    build_site(site_config, items)

    index_html = (site_config.output_dir / "index.html").read_text()
    assert "FlexiBLAS Migration" in index_html
    assert "Old Format News" in index_html


def test_build_site_rss_valid(site_config: SiteConfig) -> None:
    import xml.etree.ElementTree as ET

    items = collect_items(site_config, pull=True)
    build_site(site_config, items)

    rss = ET.parse(site_config.output_dir / "rss.xml")
    root = rss.getroot()
    assert root.tag == "rss"
    channel = root.find("channel")
    assert channel is not None
    assert len(channel.findall("item")) == 2


def test_pull_source_updates_existing(site_config: SiteConfig) -> None:
    """Pulling an already-cloned repo should do a git pull (update path)."""
    source = site_config.sources[0]
    # First clone
    pull_source(source, site_config.data_dir)
    # Second pull — hits the "already exists" branch
    repo_dir = pull_source(source, site_config.data_dir)
    assert (repo_dir / ".git").is_dir()


def test_collect_items_pull_failure_skips(site_config: SiteConfig) -> None:
    """If pull fails and no local repo exists, the source is skipped."""
    site_config.sources = [NewsSource(name="broken", url="/nonexistent/repo", branch="main")]
    items = collect_items(site_config, pull=True)
    assert items == []


def test_collect_items_pull_failure_uses_cached(site_config: SiteConfig) -> None:
    """If pull fails but a local repo exists, use the cached copy."""
    # First, successfully pull
    items_before = collect_items(site_config, pull=True)
    assert len(items_before) == 2

    # Now break the source URL but keep the local repo
    site_config.sources[0].url = "/nonexistent/broken"
    items_after = collect_items(site_config, pull=True)
    assert len(items_after) == 2


def test_build_site_rebuilds_existing_output(site_config: SiteConfig) -> None:
    """Building twice should clean and rebuild the output directory."""
    items = collect_items(site_config, pull=True)

    # First build
    build_site(site_config, items)
    assert (site_config.output_dir / "index.html").exists()

    # Create a stale file
    (site_config.output_dir / "stale.txt").write_text("old")

    # Second build should remove stale file
    build_site(site_config, items)
    assert not (site_config.output_dir / "stale.txt").exists()
    assert (site_config.output_dir / "index.html").exists()
