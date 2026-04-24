"""Compile news items, blog posts, and advisories into a readable in-repo blog.

Running :func:`compile_news` on a news repository will:

1. Parse every news item (from ``metadata/news/``), blog post (from
   ``metadata/posts/``), and advisory (from ``metadata/glsa/``).
2. Write (or overwrite) a compiled Markdown file per item in the output
   directory (repo root by default, or a subdirectory via ``news_dir``).
3. Update a fenced section in ``README.md`` with a chronological index.

This is designed to be called as a **pre-commit hook** so that the
generated Markdown and index are always in sync with the source items.
The result is a GitHub repo that doubles as a readable, cloneable blog
— no build step required for readers.

Pre-commit hook configuration example (for a news repo)::

    # .pre-commit-config.yaml
    repos:
      - repo: local
        hooks:
          - id: compile-blog
            name: geek42 compile-blog
            entry: uv run geek42 compile-blog
            language: system
            always_run: true
            pass_filenames: false
"""

from __future__ import annotations

import re
from pathlib import Path

from .advisory import glsa_filename, news_to_glsa_xml
from .models import NewsItem
from .parser import _ID_RE, scan_markdown_dir, scan_repo
from .renderer import news_to_markdown

_INDEX_START = "<!-- geek42:news-index:start -->"
_INDEX_END = "<!-- geek42:news-index:end -->"
_INDEX_RE = re.compile(
    re.escape(_INDEX_START) + r".*?" + re.escape(_INDEX_END),
    re.DOTALL,
)


def _escape_md_table(text: str) -> str:
    """Escape characters that break Markdown table cells or link syntax."""
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("[", "\\[").replace("]", "\\]")


def _render_index(items: list[NewsItem], news_dir: str) -> str:
    """Build the Markdown index block (including sentinel comments)."""
    lines = [
        _INDEX_START,
        "## News",
        "",
        "| Date | Title | Author |",
        "|------|-------|--------|",
    ]
    for item in items:
        author = item.authors[0].split("<")[0].strip() if item.authors else ""
        safe_title = _escape_md_table(item.title)
        safe_author = _escape_md_table(author)
        if news_dir:
            link = f"[{safe_title}]({news_dir}/{item.id}.md)"
        else:
            link = f"[{safe_title}]({item.id}.md)"
        lines.append(f"| {item.posted} | {link} | {safe_author} |")
    lines += ["", _INDEX_END]
    return "\n".join(lines)


def _update_readme(readme_path: Path, items: list[NewsItem], news_dir: str) -> bool:
    """Insert or replace the news index in the README.

    Returns ``True`` if the file was changed, ``False`` if unchanged.
    If the README does not exist, it is created with just the index.
    If the sentinel markers are missing, the index is appended.
    """
    index_block = _render_index(items, news_dir)

    if not readme_path.exists():
        readme_path.write_text(index_block + "\n", encoding="utf-8")
        return True

    text = readme_path.read_text(encoding="utf-8")

    if _INDEX_RE.search(text):
        new_text = _INDEX_RE.sub(index_block, text)
    else:
        new_text = text.rstrip("\n") + "\n\n" + index_block + "\n"

    if new_text == text:
        return False

    readme_path.write_text(new_text, encoding="utf-8")
    return True


def compile_news(
    repo_root: Path,
    *,
    news_dir: str = "news",
    readme: str = "README.md",
    language: str = "en",
) -> int:
    """Compile all content sources in *repo_root* into a blog.

    Scans three source directories under ``metadata/``:

    - ``metadata/news/`` — GLEP 42 ``.txt`` news items
    - ``metadata/posts/`` — Markdown blog posts
    - ``metadata/glsa/`` — Markdown advisory sources

    Compiled Markdown is written to *news_dir* (default ``"news"``).
    When *news_dir* is empty, compiled files are placed at the repo root.

    :param repo_root: Path to the news repository.
    :param news_dir: Output directory for compiled Markdown (empty = repo root).
    :param readme: README filename to update with the news index.
    :param language: Preferred language for news item selection.
    :returns: Number of items compiled.
    """
    # Collect from all three sources
    items: list[NewsItem] = []
    items.extend(scan_repo(repo_root, language=language))
    items.extend(scan_markdown_dir(repo_root / "metadata" / "posts", item_type="blog"))
    items.extend(scan_markdown_dir(repo_root / "metadata" / "glsa", item_type="advisory"))
    items.sort(key=lambda x: (x.posted, x.id), reverse=True)

    # Resolve output directory
    out = repo_root / news_dir if news_dir else repo_root
    out.mkdir(parents=True, exist_ok=True)

    # Remove stale compiled .md files
    current_ids = {item.id for item in items}
    for existing_md in out.glob("*.md"):
        # When writing to repo root, only clean up date-prefixed files
        # to avoid touching README.md, CONTRIBUTING.md, etc.
        if not news_dir and not _ID_RE.match(existing_md.stem):
            continue
        if existing_md.stem not in current_ids:
            existing_md.unlink()

    # Write compiled Markdown
    for item in items:
        md_path = out / f"{item.id}.md"
        md_path.write_text(news_to_markdown(item), encoding="utf-8")

    # Write GLSA XML for advisory items
    glsa_dir = repo_root / "metadata" / "glsa"
    advisory_ids = set()
    for item in items:
        if item.item_type == "advisory":
            glsa_dir.mkdir(parents=True, exist_ok=True)
            xml_path = glsa_dir / glsa_filename(item)
            xml_path.write_text(news_to_glsa_xml(item), encoding="utf-8")
            advisory_ids.add(glsa_filename(item))

    # Remove stale GLSA XML files (only glsa-*.xml, not source .md files)
    if glsa_dir.is_dir():
        for existing_xml in glsa_dir.glob("glsa-*.xml"):
            if existing_xml.name not in advisory_ids:
                existing_xml.unlink()

    # Determine link prefix for README index
    link_prefix = news_dir if news_dir else ""

    # Update the README index
    _update_readme(repo_root / readme, items, link_prefix)

    return len(items)
