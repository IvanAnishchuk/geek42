"""Static site builder — orchestrates pulling, parsing, rendering."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import jinja2

from .errors import GitNotFoundError
from .feeds import generate_atom, generate_rss
from .models import NewsItem, NewsSource, SiteConfig
from .parser import scan_repo
from .renderer import body_to_html, write_markdown

# Resolve git to an absolute path once at import time. This avoids S607
# (partial executable path) and ensures we fail fast if git is missing.
_GIT = shutil.which("git")


def _require_git() -> str:
    """Return the absolute path to ``git``, or raise :class:`GitNotFoundError`."""
    if _GIT is None:
        raise GitNotFoundError
    return _GIT


def pull_source(source: NewsSource, data_dir: Path, *, root_dir: Path | None = None) -> Path:
    """Clone or update a news source git repository."""
    if source.is_local:
        return (root_dir or Path(".")).resolve()
    git = _require_git()
    repo_dir = data_dir / "repos" / source.name
    if (repo_dir / ".git").is_dir():
        subprocess.run(  # noqa: S603  # args are fixed literals + validated paths
            [git, "-C", str(repo_dir), "pull", "--ff-only"],
            check=True,
            capture_output=True,
        )
    else:
        repo_dir.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(  # noqa: S603  # args are fixed literals + config-provided URL
            [git, "clone", "--depth=1", "-b", source.branch, source.url, str(repo_dir)],
            check=True,
            capture_output=True,
        )
    return repo_dir


def collect_items(
    config: SiteConfig, *, pull: bool = False, root_dir: Path | None = None
) -> list[NewsItem]:
    """Collect news items from all configured sources, sorted newest first.

    If ``pull`` is true, each source is cloned/updated before scanning;
    sources that fail to pull but have a cached clone are still scanned
    from the cache. Sources with no cache are silently skipped.
    """
    _root = (root_dir or Path(".")).resolve()
    all_items: list[NewsItem] = []
    for source in config.sources:
        if source.is_local:
            repo_dir = _root
        else:
            repo_dir = config.data_dir / "repos" / source.name
            if pull:
                try:
                    pull_source(source, config.data_dir)
                except subprocess.CalledProcessError:
                    if not repo_dir.is_dir():
                        continue
        if not repo_dir.is_dir():
            continue
        items = scan_repo(repo_dir, source=source.name, language=config.language)
        all_items.extend(items)
    all_items.sort(key=lambda x: (x.posted, x.id), reverse=True)
    return all_items


def build_site(config: SiteConfig, items: list[NewsItem]) -> int:
    """Build the full static site from pre-collected items. Returns item count."""
    if not items:
        return 0

    output = config.output_dir
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    # Markdown exports
    md_dir = output / "markdown"
    for item in items:
        write_markdown(item, md_dir)

    # Jinja2 templates
    template_dir = Path(__file__).parent / "templates"
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(template_dir)),
        autoescape=True,
    )

    # Render posts
    posts_dir = output / "posts"
    posts_dir.mkdir()
    post_tmpl = env.get_template("post.html.j2")
    for item in items:
        html_body = body_to_html(item.body)
        html = post_tmpl.render(item=item, body_html=html_body, config=config, root="..")
        (posts_dir / f"{item.id}.html").write_text(html, encoding="utf-8")

    # Render index
    index_tmpl = env.get_template("index.html.j2")
    (output / "index.html").write_text(
        index_tmpl.render(items=items, config=config, root="."),
        encoding="utf-8",
    )

    # Feeds
    (output / "rss.xml").write_text(generate_rss(items, config), encoding="utf-8")
    (output / "atom.xml").write_text(generate_atom(items, config), encoding="utf-8")

    # Static assets
    css_src = template_dir / "style.css"
    if css_src.exists():
        shutil.copy2(css_src, output / "style.css")

    return len(items)
