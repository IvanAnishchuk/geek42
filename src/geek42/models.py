"""Pydantic models for GLEP 42 news items and configuration."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from pydantic import BaseModel, Field


class NewsItem(BaseModel):
    """A single GLEP 42 news item."""

    id: str
    title: str
    authors: list[str]
    posted: date
    revision: int = 1
    news_item_format: str = "2.0"
    content_type: str | None = None
    translators: list[str] = Field(default_factory=list)
    display_if_installed: list[str] = Field(default_factory=list)
    display_if_keyword: list[str] = Field(default_factory=list)
    display_if_profile: list[str] = Field(default_factory=list)
    body: str
    language: str = "en"
    source: str = ""


class NewsSource(BaseModel):
    """A git repository containing GLEP 42 news items."""

    name: str
    url: str
    branch: str = "master"


class SiteConfig(BaseModel):
    """Configuration for the static site generator."""

    title: str = "Gentoo News"
    description: str = "Gentoo Linux News Items"
    base_url: str = "https://example.github.io/gentoo-news"
    author: str = "Gentoo Developers"
    sources: list[NewsSource] = Field(
        default_factory=lambda: [
            NewsSource(
                name="gentoo",
                url="https://anongit.gentoo.org/git/data/glep42-news-gentoo.git",
            )
        ]
    )
    output_dir: Path = Path("_site")
    data_dir: Path = Path(".geek42")
    language: str = "en"
