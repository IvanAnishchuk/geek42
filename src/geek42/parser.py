"""Parse GLEP 42 news item files and Markdown with YAML frontmatter."""

from __future__ import annotations

import contextlib
import json
import re
from datetime import date
from pathlib import Path

from .errors import InvalidHeaderValueError, MissingHeaderError, ParseError
from .models import NewsItem

_HEADER_RE = re.compile(r"^([A-Za-z][A-Za-z0-9-]*)\s*:\s*(.*)")
_ID_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9+_-]+$")

REQUIRED_HEADERS: tuple[str, ...] = ("Title", "Author", "Posted")

#: Default subdirectory for news items inside a portage-style repository.
NEWS_SUBDIR = Path("metadata") / "news"


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


def update_news_header(path: Path, key: str, value: str) -> None:
    """Add or update a header in a GLEP 42 ``.txt`` file.

    Inserts the header before the blank line separating headers from
    body.  If the header already exists, its value is replaced.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    new_line = f"{key}: {value}"

    # Check if header already exists and replace it
    for i, line in enumerate(lines):
        m = _HEADER_RE.match(line)
        if m and m.group(1) == key:
            lines[i] = new_line
            path.write_text("\n".join(lines), encoding="utf-8")
            return

    # Insert before the first blank line (header/body separator)
    for i, line in enumerate(lines):
        if line.strip() == "":
            lines.insert(i, new_line)
            path.write_text("\n".join(lines), encoding="utf-8")
            return

    # No blank line found — append to end of headers
    lines.append(new_line)
    path.write_text("\n".join(lines), encoding="utf-8")


def update_markdown_frontmatter(path: Path, key: str, value: str) -> None:
    """Add or update a field in Markdown YAML frontmatter."""
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")

    if not lines or lines[0].strip() != "---":
        return

    # Find closing fence
    end_fence = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_fence = i
            break
    if end_fence is None:
        return

    new_line = f'{key}: "{value}"'

    # Check if key already exists in frontmatter and replace
    for i in range(1, end_fence):
        if re.match(rf"^{re.escape(key)}\s*:", lines[i]):
            lines[i] = new_line
            path.write_text("\n".join(lines), encoding="utf-8")
            return

    # Insert before closing fence
    lines.insert(end_fence, new_line)
    path.write_text("\n".join(lines), encoding="utf-8")


def resolve_news_root(repo_path: Path) -> Path:
    """Return the directory containing news item directories.

    Checks ``repo_path / metadata/news`` first (standard portage layout).
    Falls back to ``repo_path`` itself (dedicated news-only repos like
    ``glep42-news-gentoo.git``).
    """
    candidate = repo_path / NEWS_SUBDIR
    return candidate if candidate.is_dir() else repo_path


def scan_repo(repo_path: Path, source: str = "", language: str = "en") -> list[NewsItem]:
    """Scan a repository directory for all parseable news items.

    Looks in ``metadata/news/`` first, falling back to the repo root
    for dedicated news repositories. Directories that do not match the
    GLEP 42 identifier pattern are skipped silently. Malformed news
    files (raising :class:`ParseError`) are also skipped so a single
    bad item does not break a build.
    """
    news_root = resolve_news_root(repo_path)
    items: list[NewsItem] = []
    for entry in sorted(news_root.iterdir()):
        if not entry.is_dir() or not _ID_RE.match(entry.name):
            continue
        news_file = entry / f"{entry.name}.{language}.txt"
        if not news_file.exists() and language != "en":
            news_file = entry / f"{entry.name}.en.txt"
        if news_file.exists():
            with contextlib.suppress(ParseError, OSError):
                items.append(parse_news_file(news_file, source=source))
    return items


# ---------------------------------------------------------------------------
# Markdown with YAML frontmatter
# ---------------------------------------------------------------------------

_FENCE = "---"


def _yaml_unquote(value: str) -> str:
    """Unquote a YAML string value.

    Handles JSON-quoted strings (produced by :func:`renderer._yaml_str`)
    and bare values.
    """
    stripped = value.strip()
    if stripped.startswith('"') and stripped.endswith('"'):
        return json.loads(stripped)
    return stripped


def parse_markdown_file(path: Path, source: str = "") -> NewsItem:
    """Parse a Markdown file with YAML frontmatter into a :class:`NewsItem`.

    The frontmatter format matches the output of
    :func:`renderer.news_to_markdown`.

    :param path: Path to a ``.md`` file.
    :param source: Logical source name stored on the returned item.
    :raises ParseError: If the file cannot be parsed.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")

    # Find frontmatter fences
    if not lines or lines[0].strip() != _FENCE:
        raise ParseError(path, "missing opening frontmatter fence")

    end_fence = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == _FENCE:
            end_fence = i
            break
    if end_fence is None:
        raise ParseError(path, "missing closing frontmatter fence")

    # Parse frontmatter lines into a dict
    fm: dict[str, str | list[str]] = {}
    current_key = ""
    for line in lines[1:end_fence]:
        if line.startswith("  - "):
            # List item continuation
            current_val = fm.get(current_key)
            if current_key and isinstance(current_val, list):
                current_val.append(_yaml_unquote(line[4:]))
            continue
        m = re.match(r"^([a-z_]+)\s*:\s*(.*)", line)
        if m:
            key, value = m.group(1), m.group(2).strip()
            current_key = key
            if not value:
                # Start of a list
                fm[key] = []
            else:
                fm[key] = _yaml_unquote(value)

    body = "\n".join(lines[end_fence + 1 :]).strip()

    # Extract fields with defaults
    title = str(fm.get("title", ""))
    if not title:
        raise MissingHeaderError(path, "title")

    posted_raw = str(fm.get("date", ""))
    if not posted_raw:
        raise MissingHeaderError(path, "date")
    try:
        posted = date.fromisoformat(posted_raw)
    except ValueError as exc:
        raise InvalidHeaderValueError(path, "date", posted_raw) from exc

    revision = 1
    rev_raw = fm.get("revision")
    if rev_raw is not None:
        try:
            revision = int(str(rev_raw))
        except (ValueError, TypeError) as exc:
            raise InvalidHeaderValueError(path, "revision", str(rev_raw)) from exc

    # Authors: stored as comma-separated string in frontmatter
    authors_raw = fm.get("authors", "")
    if isinstance(authors_raw, str) and authors_raw:
        authors = [a.strip() for a in authors_raw.split(",") if a.strip()]
    elif isinstance(authors_raw, list):
        authors = authors_raw
    else:
        authors = []

    packages = fm.get("packages", [])
    if isinstance(packages, str):
        packages = [packages]
    keywords = fm.get("keywords", [])
    if isinstance(keywords, str):
        keywords = [keywords]

    # Advisory fields
    advisory_cves = fm.get("advisory_cves", [])
    if isinstance(advisory_cves, str):
        advisory_cves = [advisory_cves]
    advisory_affected = fm.get("advisory_affected", [])
    if isinstance(advisory_affected, str):
        advisory_affected = [advisory_affected]

    return NewsItem(
        id=path.stem,
        title=title,
        authors=authors,
        posted=posted,
        revision=revision,
        body=body,
        source=source or str(fm.get("source", "")),
        display_if_installed=packages,
        display_if_keyword=keywords,
        item_type=str(fm.get("item_type", "news")),
        advisory_severity=str(fm.get("advisory_severity", "")),
        advisory_cves=advisory_cves,
        advisory_affected=advisory_affected,
        advisory_fixed=str(fm.get("advisory_fixed", "")),
    )


def scan_markdown_dir(dir_path: Path, source: str = "", item_type: str = "blog") -> list[NewsItem]:
    """Scan a directory for Markdown files with YAML frontmatter.

    :param dir_path: Directory to scan.
    :param source: Logical source name for all items.
    :param item_type: Default ``item_type`` if not set in frontmatter.
    :returns: Sorted list of parsed items.
    """
    if not dir_path.is_dir():
        return []

    items: list[NewsItem] = []
    for md_file in sorted(dir_path.glob("*.md")):
        with contextlib.suppress(ParseError, OSError, json.JSONDecodeError):
            item = parse_markdown_file(md_file, source=source)
            # Apply default item_type if not explicitly set in frontmatter
            if item.item_type == "news" and item_type != "news":
                item = item.model_copy(update={"item_type": item_type})
            items.append(item)
    items.sort(key=lambda x: (x.posted, x.id))
    return items
