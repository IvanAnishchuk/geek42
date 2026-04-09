"""Convert news items to Markdown and HTML."""

from __future__ import annotations

import re
from pathlib import Path

import markdown as md

from .models import NewsItem

_URL_RE = re.compile(r"(https?://[^\s<>)\]]+)")


def news_to_markdown(item: NewsItem) -> str:
    """Convert a NewsItem to a Markdown string with YAML frontmatter."""
    lines = [
        "---",
        f'title: "{item.title}"',
        f"date: {item.posted.isoformat()}",
        f"revision: {item.revision}",
    ]
    if item.authors:
        authors = ", ".join(item.authors)
        lines.append(f'authors: "{authors}"')
    if item.source:
        lines.append(f'source: "{item.source}"')
    if item.display_if_installed:
        lines.append("packages:")
        for pkg in item.display_if_installed:
            lines.append(f'  - "{pkg}"')
    if item.display_if_keyword:
        lines.append("keywords:")
        for kw in item.display_if_keyword:
            lines.append(f'  - "{kw}"')
    lines += ["---", "", item.body, ""]
    return "\n".join(lines)


def body_to_html(body: str) -> str:
    """Convert plain-text body to HTML with auto-linked URLs."""
    text = _URL_RE.sub(r"<\1>", body)
    return md.markdown(text, extensions=["smarty"])


def write_markdown(item: NewsItem, output_dir: Path) -> Path:
    """Write a news item as a .md file with YAML frontmatter."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{item.id}.md"
    path.write_text(news_to_markdown(item), encoding="utf-8")
    return path
