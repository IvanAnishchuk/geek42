"""Convert news items to Markdown and HTML."""

from __future__ import annotations

import json
import re
from pathlib import Path

import markdown as md

from .models import NewsItem

_URL_RE = re.compile(r"(https?://[^\s<>)\]]+)")


def _yaml_str(value: str) -> str:
    """Return a YAML-safe double-quoted string.

    JSON double-quoted strings are a strict subset of YAML double-quoted
    strings, so ``json.dumps`` gives us safe quoting and escaping for
    any Unicode input without pulling in a YAML dependency.
    """
    return json.dumps(value, ensure_ascii=False)


def news_to_markdown(item: NewsItem) -> str:
    """Convert a :class:`NewsItem` to a Markdown string with YAML frontmatter."""
    lines = [
        "---",
        f"title: {_yaml_str(item.title)}",
        f"date: {item.posted.isoformat()}",
        f"revision: {item.revision}",
    ]
    if item.authors:
        lines.append(f"authors: {_yaml_str(', '.join(item.authors))}")
    if item.source:
        lines.append(f"source: {_yaml_str(item.source)}")
    if item.display_if_installed:
        lines.append("packages:")
        lines.extend(f"  - {_yaml_str(pkg)}" for pkg in item.display_if_installed)
    if item.display_if_keyword:
        lines.append("keywords:")
        lines.extend(f"  - {_yaml_str(kw)}" for kw in item.display_if_keyword)
    lines += ["---", "", item.body, ""]
    return "\n".join(lines)


def body_to_html(body: str) -> str:
    """Convert plain-text body to HTML with auto-linked URLs."""
    text = _URL_RE.sub(r"<\1>", body)
    return md.markdown(text, extensions=["smarty"])


def write_markdown(item: NewsItem, output_dir: Path) -> Path:
    """Write a news item to ``{output_dir}/{item.id}.md``.

    Creates ``output_dir`` if it does not exist. The file is written
    in UTF-8 with YAML frontmatter followed by the body.

    :returns: The full path of the file just written.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{item.id}.md"
    path.write_text(news_to_markdown(item), encoding="utf-8")
    return path
