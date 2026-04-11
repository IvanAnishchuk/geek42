"""geek42 — GLEP 42 Gentoo news to static blog converter.

Public API. Importing from this top-level module is the supported way
to consume geek42 from other Python code; the submodule layout is an
implementation detail and may change between releases.

Example::

    from geek42 import NewsItem, NewsSource, SiteConfig, parse_news_file

    item = parse_news_file(Path("2025-11-30-foo/2025-11-30-foo.en.txt"))
    print(item.title, item.posted)
"""

from __future__ import annotations

from .blog import compile_news
from .errors import (
    ComposeError,
    ConfigError,
    EditorFailedError,
    EmptyTitleError,
    Geek42Error,
    GematoNotFoundError,
    GitNotFoundError,
    InvalidHeaderValueError,
    ItemNotFoundError,
    MissingHeaderError,
    NoSourcesConfiguredError,
    ParseError,
    SlugDerivationError,
    SourceNotFoundError,
    SourceNotPulledError,
    SystemDependencyError,
)
from .feeds import generate_atom, generate_rss
from .linter import Diagnostic, Severity, lint_news_file, lint_repo
from .manifest import generate_manifest, verify_manifest
from .models import NewsItem, NewsSource, SiteConfig
from .parser import NEWS_SUBDIR, parse_news_file, resolve_news_root, scan_repo
from .renderer import body_to_html, news_to_markdown, write_markdown
from .scaffold import scaffold
from .tracker import ReadTracker

__version__ = "0.4.2a3"

__all__ = [
    "ComposeError",
    "compile_news",
    "ConfigError",
    "Diagnostic",
    "EditorFailedError",
    "EmptyTitleError",
    "GematoNotFoundError",
    "Geek42Error",
    "GitNotFoundError",
    "InvalidHeaderValueError",
    "ItemNotFoundError",
    "MissingHeaderError",
    "NewsItem",
    "NewsSource",
    "NoSourcesConfiguredError",
    "ParseError",
    "ReadTracker",
    "Severity",
    "SiteConfig",
    "SlugDerivationError",
    "SourceNotFoundError",
    "SourceNotPulledError",
    "SystemDependencyError",
    "__version__",
    "body_to_html",
    "generate_atom",
    "generate_rss",
    "lint_news_file",
    "lint_repo",
    "generate_manifest",
    "NEWS_SUBDIR",
    "news_to_markdown",
    "parse_news_file",
    "resolve_news_root",
    "scaffold",
    "scan_repo",
    "verify_manifest",
    "write_markdown",
]
