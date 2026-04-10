"""Compile GLEP 42 news items into a readable in-repo blog.

Running :func:`compile_news` on a GLEP 42 news repository will:

1. Parse every news item (from ``metadata/news/`` or repo root).
2. Write (or overwrite) a Markdown file per item in ``news/``.
3. Update a fenced section in ``README.md`` with a chronological index.

This is designed to be called as a **pre-commit hook** so that the
generated Markdown and index are always in sync with the source
news items. The result is a GitHub repo that doubles as a readable,
cloneable blog — no build step required for readers.

Pre-commit hook configuration example (for a GLEP 42 news repo)::

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

from .models import NewsItem
from .parser import scan_repo
from .renderer import news_to_markdown

_INDEX_START = "<!-- geek42:news-index:start -->"
_INDEX_END = "<!-- geek42:news-index:end -->"
_INDEX_RE = re.compile(
    re.escape(_INDEX_START) + r".*?" + re.escape(_INDEX_END),
    re.DOTALL,
)


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
        link = f"[{item.title}]({news_dir}/{item.id}.md)"
        lines.append(f"| {item.posted} | {link} | {author} |")
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
    """Compile all GLEP 42 news items in *repo_root* into a blog.

    :param repo_root: Path to the GLEP 42 news repository.
    :param news_dir: Directory name (relative to *repo_root*) for Markdown output.
    :param readme: README filename to update with the news index.
    :param language: Preferred language for news item selection.
    :returns: Number of news items compiled.
    """
    items = scan_repo(repo_root, language=language)
    items.sort(key=lambda x: (x.posted, x.id), reverse=True)

    # Write individual Markdown files
    out = repo_root / news_dir
    out.mkdir(parents=True, exist_ok=True)

    # Remove stale .md files that no longer correspond to a news item
    current_ids = {item.id for item in items}
    for existing_md in out.glob("*.md"):
        if existing_md.stem not in current_ids:
            existing_md.unlink()

    for item in items:
        md_path = out / f"{item.id}.md"
        md_path.write_text(news_to_markdown(item), encoding="utf-8")

    # Update the README index
    _update_readme(repo_root / readme, items, news_dir)

    return len(items)
