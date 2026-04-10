"""CLI interface for geek42 using Typer + Rich."""

from __future__ import annotations

import shutil
import subprocess
import tomllib
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .errors import (
    EditorFailedError,
    Geek42Error,
    GitNotFoundError,
    ItemNotFoundError,
    NoSourcesConfiguredError,  # noqa: F401  # re-exported for typing
    SourceNotFoundError,
    SourceNotPulledError,
)
from .models import NewsItem, NewsSource, SiteConfig
from .site import build_site, collect_items, pull_source

app = typer.Typer(
    name="geek42",
    help="GLEP 42 news to static blog converter.",
    no_args_is_help=True,
)
console = Console()
err_console = Console(stderr=True)

ConfigOption = Annotated[Path, typer.Option("--config", "-c", help="Config file path.")]
DirectoryOption = Annotated[
    Path | None, typer.Option("--directory", "-C", help="Working directory.")
]

DEFAULT_CONFIG = """\
title = "{title}"
author = "{author}"
description = "News Items"
base_url = ""
output_dir = "_site"
data_dir = ".geek42"
language = "en"

# OpenPGP key ID for Manifest signing (used by `geek42 sign`):
# signing_key = "0xABCD1234"

[[sources]]
name = "local"
url = "."

# To read news from remote repositories, add more sources:
# [[sources]]
# name = "gentoo"
# url = "https://anongit.gentoo.org/git/data/glep42-news-gentoo.git"
# branch = "master"
"""


def _load_config(config_path: Path, directory: Path | None = None) -> SiteConfig:
    if directory is not None and not config_path.is_absolute():
        config_path = directory / config_path
    if config_path.exists():
        with open(config_path, "rb") as f:
            cfg = SiteConfig(**tomllib.load(f))
    else:
        cfg = SiteConfig()
    if directory is not None:
        if not cfg.data_dir.is_absolute():
            cfg.data_dir = directory / cfg.data_dir
        if not cfg.output_dir.is_absolute():
            cfg.output_dir = directory / cfg.output_dir
    return cfg


@app.command()
def init(
    config: ConfigOption = Path("geek42.toml"),
    directory: DirectoryOption = None,
    title: Annotated[str, typer.Option("--title", "-t", help="Site title.")] = "My News",
    bare: Annotated[bool, typer.Option("--bare", help="Only create geek42.toml.")] = False,
) -> None:
    """Scaffold a new GLEP 42 news repository.

    Creates the standard directory layout with pre-commit hooks, CI
    workflow, and tool configuration. Use --bare to create only
    geek42.toml (old behaviour).
    """
    from .compose import infer_author

    root = (directory or Path(".")).resolve()
    author = infer_author()

    if bare:
        cfg_path = root / config if not config.is_absolute() else config
        if cfg_path.exists():
            err_console.print(f"[yellow]Already exists:[/] {cfg_path}")
            return
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        content = DEFAULT_CONFIG.format(title=title, author=author)
        cfg_path.write_text(content, encoding="utf-8")
        console.print(f"[green]Created[/] {cfg_path}")
    else:
        from .scaffold import scaffold

        created = scaffold(root, title=title, author=author)
        if created:
            for f in created:
                console.print(f"  [green]+[/] {f.relative_to(root)}")
            console.print(f"\n[green]{len(created)} file(s) created.[/]")
        else:
            err_console.print("[yellow]All files already exist.[/]")


@app.command()
def pull(
    config: ConfigOption = Path("geek42.toml"),
    directory: DirectoryOption = None,
) -> None:
    """Clone or update news source repositories."""
    cfg = _load_config(config, directory)
    for source in cfg.sources:
        if source.is_local:
            continue
        console.print(f"Pulling [bold]{source.name}[/] ({source.url})...")
        try:
            pull_source(source, cfg.data_dir)
            console.print("  [green]OK[/]")
        except subprocess.CalledProcessError as e:
            err_console.print(f"  [red]Error:[/] {e}")


@app.command()
def build(
    config: ConfigOption = Path("geek42.toml"),
    no_pull: Annotated[bool, typer.Option("--no-pull", help="Skip pulling sources.")] = False,
    directory: DirectoryOption = None,
) -> None:
    """Build the static site."""
    cfg = _load_config(config, directory)
    root_dir = directory.resolve() if directory is not None else None
    do_pull = not no_pull

    if do_pull:
        remote_sources = [s for s in cfg.sources if not s.is_local]
        if remote_sources:
            console.print("[bold]Pulling sources...[/]")
            for source in remote_sources:
                console.print(f"  {source.name}...", end=" ")
                try:
                    pull_source(source, cfg.data_dir)
                    console.print("[green]OK[/]")
                except subprocess.CalledProcessError as e:
                    err_console.print(f"[red]Failed:[/] {e}")

    console.print("[bold]Collecting news items...[/]")
    items = collect_items(cfg, pull=False, root_dir=root_dir)
    if not items:
        err_console.print("[yellow]No news items found.[/]")
        raise typer.Exit(1)

    console.print("[bold]Building site...[/]")
    count = build_site(cfg, items)
    console.print(f"[green]Done.[/] {count} posts -> {cfg.output_dir}/")


@app.command("list")
def list_news(
    config: ConfigOption = Path("geek42.toml"),
    source: Annotated[str | None, typer.Option("--source", "-s", help="Filter by source.")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max items.")] = 20,
    new: Annotated[bool, typer.Option("--new", help="Show only unread items.")] = False,
    directory: DirectoryOption = None,
) -> None:
    """List news items in the terminal."""
    from .tracker import ReadTracker

    cfg = _load_config(config, directory)
    root_dir = directory.resolve() if directory is not None else None
    tracker = ReadTracker(cfg.data_dir)
    items = collect_items(cfg, pull=False, root_dir=root_dir)
    if source:
        items = [i for i in items if i.source == source]
    if new:
        items = tracker.unread(items)
    if not items:
        if new:
            err_console.print("[yellow]No unread items.[/]")
        else:
            err_console.print("[yellow]No news items.[/]")

        raise typer.Exit(1)

    n_unread = tracker.count_unread(items)
    title = f"News Items ({n_unread} unread)" if n_unread else "News Items"

    table = Table(title=title, show_lines=False)
    table.add_column("", no_wrap=True, width=3)
    table.add_column("Date", style="cyan", no_wrap=True)
    table.add_column("Title", style="bold")
    table.add_column("Source", style="dim")
    table.add_column("ID", style="dim")

    for item in items[:limit]:
        marker = "[green]*[/]" if not tracker.is_read(item.id) else ""
        table.add_row(marker, str(item.posted), item.title, item.source, item.id)

    console.print(table)


def _render_item(item: NewsItem) -> None:
    """Render a single NewsItem to the console."""
    meta_lines = [
        f"[cyan]{', '.join(item.authors)}[/]",
        f"[dim]{item.posted}  rev {item.revision}  [{item.source}][/]",
    ]
    if item.display_if_installed:
        meta_lines.append(f"[dim]packages: {', '.join(item.display_if_installed)}[/]")
    if item.display_if_keyword:
        meta_lines.append(f"[dim]keywords: {', '.join(item.display_if_keyword)}[/]")

    console.print()
    console.print(
        Panel(
            "\n".join(meta_lines),
            title=f"[bold]{item.title}[/]",
            border_style="blue",
        )
    )
    console.print()
    console.print(item.body)
    console.print()


@app.command()
def read(
    item_id: str,
    config: ConfigOption = Path("geek42.toml"),
    directory: DirectoryOption = None,
) -> None:
    """Read a specific news item in the terminal (marks it as read)."""
    from .tracker import ReadTracker

    cfg = _load_config(config, directory)
    root_dir = directory.resolve() if directory is not None else None
    items = collect_items(cfg, pull=False, root_dir=root_dir)
    matches = [i for i in items if item_id in i.id]
    if not matches:
        raise ItemNotFoundError(item_id)
    item = matches[0]
    _render_item(item)

    tracker = ReadTracker(cfg.data_dir)
    tracker.mark_read(item.id)


@app.command("read-new")
def read_new(
    config: ConfigOption = Path("geek42.toml"),
    directory: DirectoryOption = None,
) -> None:
    """Read all unread news items, marking each as read."""
    from .tracker import ReadTracker

    cfg = _load_config(config, directory)
    root_dir = directory.resolve() if directory is not None else None
    tracker = ReadTracker(cfg.data_dir)
    items = collect_items(cfg, pull=False, root_dir=root_dir)
    unread = tracker.unread(items)

    if not unread:
        console.print("[dim]No unread news items.[/]")
        return

    console.print(f"[bold]{len(unread)} unread item(s)[/]\n")

    for i, item in enumerate(unread):
        if i > 0:
            console.print(f"[dim]{'─' * 60}[/]")
        _render_item(item)
        tracker.mark_read(item.id)


def _run_editor_loop(tmp: Path, editor: str) -> None:
    """Open ``tmp`` in ``editor`` until it lints clean or the user aborts.

    Lint diagnostics are printed after each edit. If errors remain,
    the user is prompted to re-edit (default yes). On abort, raises
    :class:`typer.Exit`. On editor failure (non-zero exit and no
    diagnostics produced), raises :class:`EditorFailedError`.
    """
    from .compose import edit_and_lint
    from .linter import Severity

    while True:
        ok, diags = edit_and_lint(tmp, editor)
        if not diags and not ok:
            raise EditorFailedError(editor, returncode=1)

        for d in diags:
            style = "red" if d.severity == Severity.error else "yellow"
            console.print(f"[{style}]{d}[/]")

        if ok:
            return

        if not typer.confirm("Errors found. Re-edit?", default=True):
            err_console.print("[yellow]Aborted.[/]")
            raise typer.Exit(1)


@app.command()
def new(
    source: Annotated[
        str | None, typer.Option("--source", "-s", help="Target source name.")
    ] = None,
    editor: Annotated[str | None, typer.Option("--editor", "-e", help="Editor command.")] = None,
    config: ConfigOption = Path("geek42.toml"),
    directory: DirectoryOption = None,
) -> None:
    """Create a new GLEP 42 news item (opens $EDITOR)."""
    from .compose import generate_template, get_editor, make_temp_copy, place_news_item

    cfg = _load_config(config, directory)
    ed = get_editor(editor)

    # Resolve target directory
    if directory is not None:
        repo_dir = directory.resolve()
    else:
        src_obj = _resolve_source(cfg, source)
        if src_obj.is_local:
            repo_dir = Path(".").resolve()
        else:
            repo_dir = cfg.data_dir / "repos" / src_obj.name
            if not repo_dir.is_dir():
                raise SourceNotPulledError(src_obj.name)

    template = generate_template()
    tmp = make_temp_copy(template, prefix="geek42-new-")

    try:
        _run_editor_loop(tmp, ed)
        final = place_news_item(tmp, repo_dir, language=cfg.language)
        console.print(f"[green]Created[/] {final}")
    finally:
        if tmp.exists():
            tmp.unlink()


@app.command()
def revise(
    item_id: str,
    editor: Annotated[str | None, typer.Option("--editor", "-e", help="Editor command.")] = None,
    config: ConfigOption = Path("geek42.toml"),
    directory: DirectoryOption = None,
) -> None:
    """Revise an existing news item (bump revision, open $EDITOR)."""
    from .compose import find_item_file, get_editor, prepare_revision

    cfg = _load_config(config, directory)
    root_dir = directory.resolve() if directory is not None else None
    ed = get_editor(editor)

    item_path = find_item_file(item_id, cfg.data_dir, cfg.sources, cfg.language, root_dir=root_dir)
    if item_path is None:
        raise ItemNotFoundError(item_id)

    console.print(f"Revising [bold]{item_path.parent.name}[/]")
    tmp = prepare_revision(item_path)

    try:
        _run_editor_loop(tmp, ed)
        shutil.copy2(tmp, item_path)
        console.print(f"[green]Updated[/] {item_path}")
    finally:
        if tmp.exists():
            tmp.unlink()


def _resolve_source(cfg: SiteConfig, name: str | None = None) -> NewsSource:
    """Resolve a source by name, or default to the first one.

    :raises SourceNotFoundError: ``name`` is given but doesn't match.
    :raises NoSourcesConfiguredError: No sources in the config at all.
    """
    if name:
        matches = [s for s in cfg.sources if s.name == name]
        if not matches:
            raise SourceNotFoundError(name)
        return matches[0]
    if cfg.sources:
        return cfg.sources[0]
    raise NoSourcesConfiguredError


@app.command("compile-blog")
def compile_blog(
    path: Annotated[Path, typer.Argument(help="Root of a GLEP 42 news repository.")] = Path("."),
    news_dir: Annotated[
        str, typer.Option("--news-dir", "-d", help="Output directory for Markdown files.")
    ] = "news",
    readme: Annotated[str, typer.Option("--readme", help="README file to update.")] = "README.md",
    language: Annotated[str, typer.Option("--language", "-l", help="Preferred language.")] = "en",
) -> None:
    """Compile news items into Markdown files and update the README index.

    Designed to run as a pre-commit hook so the repo doubles as a blog.
    """
    from .blog import compile_news

    root = path.resolve()
    count = compile_news(root, news_dir=news_dir, readme=readme, language=language)
    if count:
        console.print(f"[green]Compiled[/] {count} news item(s) -> {news_dir}/")
    else:
        console.print("[yellow]No news items found.[/]")


@app.command()
def lint(
    path: Annotated[Path, typer.Argument(help="Path to a news file or repository directory.")],
    strict: Annotated[bool, typer.Option("--strict", help="Treat warnings as errors.")] = False,
) -> None:
    """Lint GLEP 42 news files for errors and style issues."""
    from .linter import Severity, lint_news_file, lint_repo

    if path.is_file():
        diags = lint_news_file(path)
    elif path.is_dir():
        diags = lint_repo(path)
    else:
        err_console.print(f"[red]Not found:[/] {path}")
        raise typer.Exit(1)

    errors = [d for d in diags if d.severity == Severity.error]
    warnings = [d for d in diags if d.severity == Severity.warning]

    for d in diags:
        style = "red" if d.severity == Severity.error else "yellow"
        console.print(f"[{style}]{d}[/]")

    if diags:
        console.print()
    console.print(f"{len(errors)} error(s), {len(warnings)} warning(s)")

    if errors or (strict and warnings):
        raise typer.Exit(1)


# -- sign / verify --


@app.command()
def sign(
    key: Annotated[str | None, typer.Option("--key", "-k", help="OpenPGP key ID.")] = None,
    config: ConfigOption = Path("geek42.toml"),
    directory: DirectoryOption = None,
) -> None:
    """Regenerate the Manifest tree and optionally sign it.

    Uses the same gemato flags as the Gentoo overlay workflow.
    The key comes from --key or ``signing_key`` in geek42.toml.
    """
    from .manifest import generate_manifest

    cfg = _load_config(config, directory)
    root = (directory or Path(".")).resolve()
    signing_key = key or cfg.signing_key or ""

    ok = generate_manifest(root, signing_key=signing_key)
    if not ok:
        err_console.print("[red]gemato update failed[/]")
        raise typer.Exit(1)

    if signing_key:
        console.print(f"[green]Manifest updated and signed[/] with key {signing_key}")
    else:
        console.print("[green]Manifest updated.[/]")


@app.command()
def verify(
    directory: DirectoryOption = None,
) -> None:
    """Verify the Manifest tree (checksums and signature).

    Delegates entirely to ``gemato verify``, which handles the
    hierarchical compressed sub-Manifests and OpenPGP signatures.
    """
    from .manifest import manifest_path, verify_manifest

    root = (directory or Path(".")).resolve()

    if not manifest_path(root).exists():
        err_console.print("[yellow]No Manifest found.[/]")
        raise typer.Exit(0)

    errors = verify_manifest(root)
    if errors:
        for e in errors:
            err_console.print(f"  [red]✗[/] {e}")
        raise typer.Exit(1)
    console.print("[green]Verified.[/]")


# -- commit / push / deploy-status helpers --


def _git(
    args: list[str],
    root: Path,
    *,
    capture_output: bool = False,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run a git command rooted at *root*. Returns the CompletedProcess."""
    git = shutil.which("git")
    if git is None:
        raise GitNotFoundError
    return subprocess.run(  # noqa: S603
        [git, "-C", str(root), *args],
        text=True,
        capture_output=capture_output,
        check=check,
    )


def _detect_news_changes(root: Path) -> tuple[list[str], list[str], list[str]]:
    """Return (added, modified, deleted) item IDs from ``git status``."""
    from .parser import NEWS_SUBDIR

    result = _git(
        ["status", "--porcelain", "--", str(NEWS_SUBDIR)],
        root,
        capture_output=True,
        check=False,
    )
    added: list[str] = []
    modified: list[str] = []
    deleted: list[str] = []
    seen: set[str] = set()

    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        status, filepath = line[:2], line[3:]
        parts = Path(filepath).parts
        try:
            idx = list(parts).index("news")
        except ValueError:
            continue
        if idx + 1 >= len(parts):
            continue
        item_id = parts[idx + 1]
        if item_id in seen:
            continue
        seen.add(item_id)

        if "?" in status or "A" in status:
            added.append(item_id)
        elif "D" in status:
            deleted.append(item_id)
        else:
            modified.append(item_id)

    return added, modified, deleted


def _news_commit_message(added: list[str], modified: list[str], deleted: list[str]) -> str:
    """Generate a Conventional Commits message from news changes."""
    if len(added) == 1 and not modified and not deleted:
        return f"feat(news): add {added[0]}"
    if len(modified) == 1 and not added and not deleted:
        return f"fix(news): revise {modified[0]}"
    if len(deleted) == 1 and not added and not modified:
        return f"chore(news): remove {deleted[0]}"
    parts: list[str] = []
    if added:
        parts.append(f"add {len(added)}")
    if modified:
        parts.append(f"revise {len(modified)}")
    if deleted:
        parts.append(f"remove {len(deleted)}")
    return f"feat(news): {', '.join(parts)} item(s)"


@app.command()
def commit(
    message: Annotated[str | None, typer.Option("--message", "-m", help="Commit message.")] = None,
    config: ConfigOption = Path("geek42.toml"),
    directory: DirectoryOption = None,
) -> None:
    """Stage news items, compile blog, and commit.

    Runs compile-blog before committing so that generated Markdown and
    the README index are included in the same commit. Updates the
    Manifest when ``signing_key`` is set in the config. When --message
    is omitted a Conventional Commits message is derived from the
    changed news items (like ``pkgdev commit``).
    """
    from .blog import compile_news
    from .manifest import generate_manifest
    from .parser import NEWS_SUBDIR

    cfg = _load_config(config, directory)
    root = (directory or Path(".")).resolve()

    added, modified, deleted = _detect_news_changes(root)
    if not added and not modified and not deleted:
        err_console.print("[yellow]Nothing to commit.[/]")
        raise typer.Exit(0)

    # Compile blog so the pre-commit hook is a no-op
    compile_news(root, language=cfg.language)

    # Regenerate Manifest checksums
    generate_manifest(root)

    # Stage news items, compiled output, and Manifest
    for p in (str(NEWS_SUBDIR), "news", "README.md", "Manifest"):
        if (root / p).exists():
            _git(["add", p], root, capture_output=True, check=False)

    if message is None:
        message = _news_commit_message(added, modified, deleted)

    result = _git(["commit", "-m", message], root, capture_output=True, check=False)
    if result.returncode == 0:
        console.print(f"[green]Committed:[/] {message}")
    else:
        # Pre-commit may have modified files — re-stage and retry once
        for p in (str(NEWS_SUBDIR), "news", "README.md"):
            if (root / p).exists():
                _git(["add", p], root, capture_output=True, check=False)
        result = _git(["commit", "-m", message], root, capture_output=True, check=False)
        if result.returncode == 0:
            console.print(f"[green]Committed:[/] {message}")
        else:
            err_console.print(f"[red]Commit failed:[/]\n{result.stderr.strip()}")
            raise typer.Exit(1)


@app.command()
def push(
    directory: DirectoryOption = None,
) -> None:
    """Push commits to the remote repository."""
    root = (directory or Path(".")).resolve()
    # Let git write progress directly to the terminal
    result = _git(["push"], root, check=False)
    if result.returncode != 0:
        raise typer.Exit(1)


@app.command("deploy-status")
def deploy_status(
    directory: DirectoryOption = None,
) -> None:
    """Check GitHub Pages build and CI status on main."""
    import json as json_mod

    gh = shutil.which("gh")
    if gh is None:
        err_console.print("[red]gh CLI not found in PATH[/]")
        raise typer.Exit(1)

    root = (directory or Path(".")).resolve()

    def _gh(args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603
            [gh, *args], capture_output=True, text=True, check=False, cwd=str(root)
        )

    # Resolve owner/repo
    nwo_r = _gh(["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"])
    if nwo_r.returncode != 0:
        err_console.print("[red]Could not detect GitHub repository.[/]")
        raise typer.Exit(1)
    nwo = nwo_r.stdout.strip()
    console.print(f"[bold]{nwo}[/]\n")

    # Pages info
    pages_r = _gh(["api", f"repos/{nwo}/pages"])
    if pages_r.returncode == 0:
        pages = json_mod.loads(pages_r.stdout)
        url = pages.get("html_url", "N/A")
        status = pages.get("status", "unknown")
        style = "green" if status == "built" else "yellow"
        console.print(f"  [bold]Pages:[/] {url}")
        console.print(f"  [bold]Status:[/] [{style}]{status}[/]")

        # Latest build
        builds_r = _gh(["api", f"repos/{nwo}/pages/builds?per_page=1"])
        if builds_r.returncode == 0:
            builds = json_mod.loads(builds_r.stdout)
            if builds:
                b = builds[0]
                bstatus = b.get("status", "unknown")
                created = b.get("created_at", "")[:16].replace("T", " ")
                sha = (b.get("commit") or "")[:7]
                bstyle = (
                    "green" if bstatus == "built" else "yellow" if bstatus == "building" else "red"
                )
                console.print(f"  [bold]Build:[/]  [{bstyle}]{bstatus}[/] {created} ({sha})")
    else:
        console.print("  [yellow]GitHub Pages not configured.[/]")

    # Latest CI run on main
    ci_r = _gh(
        [
            "run",
            "list",
            "--branch",
            "main",
            "--limit",
            "1",
            "--json",
            "status,conclusion,displayTitle,headSha",
        ]
    )
    if ci_r.returncode == 0:
        runs = json_mod.loads(ci_r.stdout)
        if runs:
            run = runs[0]
            conclusion = run.get("conclusion") or run.get("status", "unknown")
            title = run.get("displayTitle", "")
            sha = run.get("headSha", "")[:7]
            if conclusion == "success":
                icon, cstyle = "✓", "green"
            elif conclusion in ("failure", "cancelled"):
                icon, cstyle = "✗", "red"
            else:
                icon, cstyle = "…", "yellow"
            console.print(f"  [bold]CI:[/]    [{cstyle}]{icon} {conclusion}[/] {title} ({sha})")

    console.print()


def main() -> None:
    """Entry point. Catches Geek42Error at the boundary and formats it."""
    try:
        app()
    except Geek42Error as exc:
        err_console.print(f"[red]Error:[/] {exc}")
        raise typer.Exit(1) from exc
