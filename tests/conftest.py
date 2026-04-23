"""Shared fixtures for geek42 tests."""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from geek42.models import NewsItem, NewsSource, SiteConfig

SAMPLE_NEWS_FORMAT2 = """\
Title: FlexiBLAS Migration
Author: Sam James <sam@gentoo.org>
Author: Ada Lovelace <ada@example.org>
Posted: 2025-11-30
Revision: 2
News-Item-Format: 2.0
Display-If-Installed: app-eselect/eselect-blas
Display-If-Installed: sci-libs/flexiblas
Display-If-Keyword: amd64
Display-If-Profile: default/linux/amd64/23.0

This is about the FlexiBLAS migration.

Users should update their systems. More info at
https://wiki.gentoo.org/wiki/FlexiBLAS

Steps:
1. Sync your repo
2. Update world
"""

SAMPLE_NEWS_FORMAT1 = """\
Title: Old Format News
Author: Old Dev <old@gentoo.org>
Content-Type: text/plain
Posted: 2017-03-02
Revision: 1
News-Item-Format: 1.0

This is an older format 1.0 news item.
It has a Content-Type header.
"""


@pytest.fixture(autouse=True)
def _isolate_git_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent tests from using the user's global git config or signing keys."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", "/dev/null")
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Test")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "test@test.invalid")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Test")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "test@test.invalid")
    monkeypatch.delenv("GPG_AGENT_INFO", raising=False)
    monkeypatch.delenv("SSH_AUTH_SOCK", raising=False)


def make_item(**kwargs: Any) -> NewsItem:
    """Create a NewsItem with sensible defaults. Override any field via kwargs."""
    defaults: dict[str, Any] = {
        "id": "2025-01-01-test",
        "title": "Test Item",
        "authors": ["Dev <dev@gentoo.org>"],
        "posted": date(2025, 1, 1),
        "body": "Test body content.",
    }
    defaults.update(kwargs)
    return NewsItem(**defaults)


@pytest.fixture
def news_repo(tmp_path: Path) -> Path:
    """Create a mock GLEP 42 news repo with sample items in metadata/news/."""
    news_root = tmp_path / "metadata" / "news"
    news_root.mkdir(parents=True)

    # Format 2.0 item
    item1_dir = news_root / "2025-11-30-flexiblas-migration"
    item1_dir.mkdir()
    (item1_dir / "2025-11-30-flexiblas-migration.en.txt").write_text(SAMPLE_NEWS_FORMAT2)

    # Format 1.0 item
    item2_dir = news_root / "2017-03-02-old-format"
    item2_dir.mkdir()
    (item2_dir / "2017-03-02-old-format.en.txt").write_text(SAMPLE_NEWS_FORMAT1)

    # Non-news directory (should be skipped)
    (tmp_path / "README").write_text("This is a news repo")
    (tmp_path / ".git-stuff").mkdir()

    return tmp_path


@pytest.fixture
def git_news_repo(news_repo: Path) -> Path:
    """Like news_repo but initialized as a git repository."""
    subprocess.run(["git", "init", str(news_repo)], check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(news_repo),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@test.invalid",
            "commit",
            "--allow-empty",
            "-m",
            "init",
            "--no-gpg-sign",
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "-C", str(news_repo), "add", "-A"], check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(news_repo),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@test.invalid",
            "commit",
            "-m",
            "add news",
            "--no-gpg-sign",
        ],
        check=True,
        capture_output=True,
    )
    return news_repo


@pytest.fixture
def site_config(tmp_path: Path, git_news_repo: Path) -> SiteConfig:
    """A SiteConfig pointing at the mock git repo."""
    branch_result = subprocess.run(
        ["git", "-C", str(git_news_repo), "branch", "--show-current"],
        check=True,
        capture_output=True,
        text=True,
    )
    branch = branch_result.stdout.strip()
    return SiteConfig(
        title="Test News",
        description="Test news site",
        base_url="https://test.example.com",
        author="Test Author",
        sources=[
            NewsSource(name="test", url=str(git_news_repo), branch=branch),
        ],
        output_dir=tmp_path / "output",
        data_dir=tmp_path / "data",
    )


@pytest.fixture
def local_site_config(news_repo: Path) -> SiteConfig:
    """A SiteConfig with a local source pointing at news_repo via url='.'."""
    return SiteConfig(
        title="Test News",
        description="Test news site",
        base_url="https://test.example.com",
        author="Test Author",
        sources=[NewsSource(name="local", url=".")],
        output_dir=news_repo / "_site",
        data_dir=news_repo / ".geek42",
    )
