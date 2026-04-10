"""Pydantic models for GLEP 42 news items and runtime configuration."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from pydantic import BaseModel, Field


class NewsItem(BaseModel):
    """A single GLEP 42 news item parsed from disk."""

    id: str = Field(
        description="GLEP 42 identifier — directory name in the form YYYY-MM-DD-short-name.",
    )
    title: str = Field(description="Headline of the news item (max 50 chars per GLEP 42).")
    authors: list[str] = Field(
        description="One or more authors in the form 'Name <email>'.",
    )
    posted: date = Field(description="Publication date (UTC).")
    revision: int = Field(
        default=1,
        description="Revision number; incremented on each substantive edit.",
    )
    news_item_format: str = Field(
        default="2.0",
        description="GLEP 42 format version. Known values: '1.0', '2.0'.",
    )
    content_type: str | None = Field(
        default=None,
        description="MIME type from format 1.0; absent in format 2.0.",
    )
    translators: list[str] = Field(
        default_factory=list,
        description="Translators for non-English variants, 'Name <email>'.",
    )
    display_if_installed: list[str] = Field(
        default_factory=list,
        description="Package atoms — show only if any are installed.",
    )
    display_if_keyword: list[str] = Field(
        default_factory=list,
        description="Architecture keywords — show only on matching arches.",
    )
    display_if_profile: list[str] = Field(
        default_factory=list,
        description="Profile paths — show only on matching profiles.",
    )
    body: str = Field(description="Plain-text body, paragraphs separated by blank lines.")
    language: str = Field(
        default="en",
        description="IETF language tag from the filename suffix.",
    )
    source: str = Field(
        default="",
        description="Logical name of the source repo (set by scan_repo).",
    )


class NewsSource(BaseModel):
    """A git repository configured as a source of GLEP 42 news items."""

    name: str = Field(
        description="Logical name used as the local cache directory and on the site.",
    )
    url: str = Field(
        default=".",
        description='Git URL, or "." for the current directory (local source).',
    )
    branch: str = Field(
        default="master",
        description="Branch to clone and follow (ignored for local sources).",
    )

    @property
    def is_local(self) -> bool:
        """True when this source points at the current directory (no pull needed)."""
        return self.url == "."


class SiteConfig(BaseModel):
    """Top-level geek42 configuration loaded from ``geek42.toml``."""

    title: str = Field(default="My News", description="Site title.")
    description: str = Field(
        default="News Items",
        description="Site description shown in feed metadata and the header.",
    )
    base_url: str = Field(
        default="",
        description="Public URL where the built site will be hosted; used in feeds.",
    )
    author: str = Field(
        default="",
        description="Default author shown in the Atom feed.",
    )
    sources: list[NewsSource] = Field(
        default_factory=lambda: [NewsSource(name="local", url=".")],
        description='News sources. Use url="." for the current repo (default).',
    )
    output_dir: Path = Field(
        default=Path("_site"),
        description="Where the static site is written by `geek42 build`.",
    )
    data_dir: Path = Field(
        default=Path(".geek42"),
        description="Where source repo clones and read/unread state are cached.",
    )
    language: str = Field(
        default="en",
        description="Preferred language for selecting translated news items.",
    )
