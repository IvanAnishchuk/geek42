"""Parse GLEP 42 news item files."""

from __future__ import annotations

import contextlib
import re
from datetime import date
from pathlib import Path

from .models import NewsItem

_HEADER_RE = re.compile(r"^([A-Za-z][A-Za-z0-9-]*)\s*:\s*(.*)")
_ID_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9+_-]+$")


def parse_news_file(path: Path, source: str = "") -> NewsItem:
    """Parse a single GLEP 42 news file into a NewsItem."""
    text = path.read_text(encoding="utf-8")
    headers: dict[str, list[str]] = {}
    lines = text.split("\n")
    body_start = 0

    for i, line in enumerate(lines):
        if line.strip() == "":
            body_start = i + 1
            break
        m = _HEADER_RE.match(line)
        if m:
            key, value = m.group(1), m.group(2).strip()
            headers.setdefault(key, []).append(value)

    body = "\n".join(lines[body_start:]).strip()

    # Validate required headers
    for required in ("Title", "Posted"):
        if required not in headers:
            raise ValueError(f"Missing required header '{required}' in {path}")

    # Extract language from filename: {id}.{lang}.txt
    lang = "en"
    stem = path.stem
    parts = stem.rsplit(".", 1)
    if len(parts) == 2:
        lang = parts[1]

    return NewsItem(
        id=path.parent.name,
        title=headers.get("Title", ["Untitled"])[0],
        authors=headers.get("Author", ["Unknown"]),
        posted=date.fromisoformat(headers.get("Posted", ["1970-01-01"])[0]),
        revision=int(headers.get("Revision", ["1"])[0]),
        news_item_format=headers.get("News-Item-Format", ["1.0"])[0],
        content_type=headers.get("Content-Type", [None])[0],
        translators=headers.get("Translator", []),
        display_if_installed=headers.get("Display-If-Installed", []),
        display_if_keyword=headers.get("Display-If-Keyword", []),
        display_if_profile=headers.get("Display-If-Profile", []),
        body=body,
        language=lang,
        source=source,
    )


def scan_repo(repo_path: Path, source: str = "", language: str = "en") -> list[NewsItem]:
    """Scan a repository directory for all news items."""
    items: list[NewsItem] = []
    for entry in sorted(repo_path.iterdir()):
        if not entry.is_dir() or not _ID_RE.match(entry.name):
            continue
        news_file = entry / f"{entry.name}.{language}.txt"
        if not news_file.exists() and language != "en":
            news_file = entry / f"{entry.name}.en.txt"
        if news_file.exists():
            with contextlib.suppress(Exception):
                items.append(parse_news_file(news_file, source=source))
    return items
