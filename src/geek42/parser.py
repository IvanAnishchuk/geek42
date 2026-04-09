"""Parse GLEP 42 news item files."""

from __future__ import annotations

import contextlib
import re
from datetime import date
from pathlib import Path

from .errors import InvalidHeaderValueError, MissingHeaderError, ParseError
from .models import NewsItem

_HEADER_RE = re.compile(r"^([A-Za-z][A-Za-z0-9-]*)\s*:\s*(.*)")
_ID_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9+_-]+$")

REQUIRED_HEADERS: tuple[str, ...] = ("Title", "Author", "Posted")


def parse_news_file(path: Path, source: str = "") -> NewsItem:
    """Parse a single GLEP 42 news file into a :class:`NewsItem`.

    :param path: Path to the ``{id}.{lang}.txt`` file.
    :param source: Logical source name (e.g. ``"gentoo"``), stored on
        the returned item.
    :raises MissingHeaderError: A required header is missing.
    :raises InvalidHeaderValueError: A header has an unparseable value.
    """
    text = path.read_text(encoding="utf-8")
    headers: dict[str, list[str]] = {}
    lines = text.split("\n")
    body_start = len(lines)

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
    for required in REQUIRED_HEADERS:
        if required not in headers:
            raise MissingHeaderError(path, required)

    # Parse the Posted date — we know the header exists at this point
    posted_raw = headers["Posted"][0]
    try:
        posted = date.fromisoformat(posted_raw)
    except ValueError as exc:
        raise InvalidHeaderValueError(path, "Posted", posted_raw) from exc

    # Parse the Revision number if present; default to 1
    revision = 1
    if "Revision" in headers:
        revision_raw = headers["Revision"][0]
        try:
            revision = int(revision_raw)
        except ValueError as exc:
            raise InvalidHeaderValueError(path, "Revision", revision_raw) from exc

    # Extract language from filename: {id}.{lang}.txt
    language = "en"
    if "." in path.stem:
        language = path.stem.rsplit(".", 1)[1]

    return NewsItem(
        id=path.parent.name,
        title=headers["Title"][0],
        authors=headers["Author"],
        posted=posted,
        revision=revision,
        news_item_format=headers.get("News-Item-Format", ["1.0"])[0],
        content_type=headers["Content-Type"][0] if "Content-Type" in headers else None,
        translators=headers.get("Translator", []),
        display_if_installed=headers.get("Display-If-Installed", []),
        display_if_keyword=headers.get("Display-If-Keyword", []),
        display_if_profile=headers.get("Display-If-Profile", []),
        body=body,
        language=language,
        source=source,
    )


def scan_repo(repo_path: Path, source: str = "", language: str = "en") -> list[NewsItem]:
    """Scan a repository directory for all parseable news items.

    Directories that do not match the GLEP 42 identifier pattern are
    skipped silently. Malformed news files (raising :class:`ParseError`)
    are also skipped so a single bad item does not break a build.
    """
    items: list[NewsItem] = []
    for entry in sorted(repo_path.iterdir()):
        if not entry.is_dir() or not _ID_RE.match(entry.name):
            continue
        news_file = entry / f"{entry.name}.{language}.txt"
        if not news_file.exists() and language != "en":
            news_file = entry / f"{entry.name}.en.txt"
        if news_file.exists():
            with contextlib.suppress(ParseError, OSError):
                items.append(parse_news_file(news_file, source=source))
    return items
