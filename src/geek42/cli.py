"""CLI interface for geek42 using Typer + Rich."""

from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

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

DEFAULT_CONFIG = """\
title = "Gentoo News"
description = "Gentoo Linux News Items"
base_url = "https://example.github.io/gentoo-news"
author = "Gentoo Developers"
output_dir = "_site"
data_dir = ".geek42"
language = "en"

[[sources]]
name = "gentoo"
url = "https://anongit.gentoo.org/git/data/glep42-news-gentoo.git"
branch = "master"

# Add more sources:
# [[sources]]
# name = "overlay-news"
# url = "https://example.org/overlay-news.git"
# branch = "main"
"""


def _load_config(config_path: Path) -> SiteConfig:
    if config_path.exists():
        with open(config_path, "rb") as f:
            return SiteConfig(**tomllib.load(f))
    return SiteConfig()


@app.command()
def init(config: ConfigOption = Path("geek42.toml")) -> None:
    """Create a default geek42.toml configuration file."""
    if config.exists():
        err_console.print(f"[yellow]Already exists:[/] {config}")
        return
    config.write_text(DEFAULT_CONFIG, encoding="utf-8")
    console.print(f"[green]Created[/] {config}")


@app.command()
def pull(config: ConfigOption = Path("geek42.toml")) -> None:
    """Clone or update news source repositories."""
    cfg = _load_config(config)
    for source in cfg.sources:
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
) -> None:
    """Build the static site."""
    cfg = _load_config(config)
    do_pull = not no_pull

    if do_pull:
        console.print("[bold]Pulling sources...[/]")
        for source in cfg.sources:
            console.print(f"  {source.name}...", end=" ")
            try:
                pull_source(source, cfg.data_dir)
                console.print("[green]OK[/]")
            except subprocess.CalledProcessError as e:
                err_console.print(f"[red]Failed:[/] {e}")

    console.print("[bold]Collecting news items...[/]")
    items = collect_items(cfg, pull=False)
    if not items:
        err_console.print("[yellow]No news items found.[/] Run 'geek42 pull' first.")
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
) -> None:
    """List news items in the terminal."""
    from .tracker import ReadTracker

    cfg = _load_config(config)
    tracker = ReadTracker(cfg.data_dir)
    items = collect_items(cfg, pull=False)
    if source:
        items = [i for i in items if i.source == source]
    if new:
        items = tracker.unread(items)
    if not items:
        if new:
            err_console.print("[yellow]No unread items.[/]")
        else:
            err_console.print("[yellow]No news items.[/] Run 'geek42 pull' first.")

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
) -> None:
    """Read a specific news item in the terminal (marks it as read)."""
    from .tracker import ReadTracker

    cfg = _load_config(config)
    items = collect_items(cfg, pull=False)
    matches = [i for i in items if item_id in i.id]
    if not matches:
        err_console.print(f"[red]No item matching[/] '{item_id}'")
        raise typer.Exit(1)
    item = matches[0]
    _render_item(item)

    tracker = ReadTracker(cfg.data_dir)
    tracker.mark_read(item.id)


@app.command("read-new")
def read_new(
    config: ConfigOption = Path("geek42.toml"),
) -> None:
    """Read all unread news items, marking each as read."""
    from .tracker import ReadTracker

    cfg = _load_config(config)
    tracker = ReadTracker(cfg.data_dir)
    items = collect_items(cfg, pull=False)
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


@app.command()
def new(
    source: Annotated[
        str | None, typer.Option("--source", "-s", help="Target source name.")
    ] = None,
    editor: Annotated[str | None, typer.Option("--editor", "-e", help="Editor command.")] = None,
    config: ConfigOption = Path("geek42.toml"),
) -> None:
    """Create a new GLEP 42 news item (opens $EDITOR)."""
    from .compose import (
        edit_and_lint,
        generate_template,
        get_editor,
        make_temp_copy,
        place_news_item,
    )
    from .linter import Severity

    cfg = _load_config(config)
    ed = get_editor(editor)

    # Resolve target source repo
    src_obj = _resolve_source(cfg, source)
    repo_dir = cfg.data_dir / "repos" / src_obj.name
    if not repo_dir.is_dir():
        err_console.print("[red]Source not pulled.[/] Run 'geek42 pull' first.")
        raise typer.Exit(1)

    template = generate_template()
    tmp = make_temp_copy(template, prefix="geek42-new-")

    try:
        while True:
            ok, diags = edit_and_lint(tmp, ed)
            if not diags and not ok:
                err_console.print("[red]Editor exited with error.[/]")
                raise typer.Exit(1)

            for d in diags:
                style = "red" if d.severity == Severity.error else "yellow"
                console.print(f"[{style}]{d}[/]")

            if ok:
                break

            if not typer.confirm("Errors found. Re-edit?", default=True):
                err_console.print("[yellow]Aborted.[/]")
                raise typer.Exit(1)

        final = place_news_item(tmp, repo_dir, language=cfg.language)
        console.print(f"[green]Created[/] {final}")
    except ValueError as e:
        err_console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1) from None
    finally:
        if tmp.exists():
            tmp.unlink()


@app.command()
def revise(
    item_id: str,
    editor: Annotated[str | None, typer.Option("--editor", "-e", help="Editor command.")] = None,
    config: ConfigOption = Path("geek42.toml"),
) -> None:
    """Revise an existing news item (bump revision, open $EDITOR)."""
    import shutil

    from .compose import edit_and_lint, find_item_file, get_editor, prepare_revision
    from .linter import Severity

    cfg = _load_config(config)
    ed = get_editor(editor)

    item_path = find_item_file(item_id, cfg.data_dir, cfg.sources, cfg.language)
    if item_path is None:
        err_console.print(f"[red]No item matching[/] '{item_id}'")
        raise typer.Exit(1)

    console.print(f"Revising [bold]{item_path.parent.name}[/]")
    tmp = prepare_revision(item_path)

    try:
        while True:
            ok, diags = edit_and_lint(tmp, ed)
            if not diags and not ok:
                err_console.print("[red]Editor exited with error.[/]")
                raise typer.Exit(1)

            for d in diags:
                style = "red" if d.severity == Severity.error else "yellow"
                console.print(f"[{style}]{d}[/]")

            if ok:
                break

            if not typer.confirm("Errors found. Re-edit?", default=True):
                err_console.print("[yellow]Aborted.[/]")
                raise typer.Exit(1)

        shutil.copy2(tmp, item_path)
        console.print(f"[green]Updated[/] {item_path}")
    finally:
        if tmp.exists():
            tmp.unlink()


def _resolve_source(cfg: SiteConfig, name: str | None = None) -> NewsSource:
    """Resolve a source by name, or default to the first one."""
    if name:
        matches = [s for s in cfg.sources if s.name == name]
        if not matches:
            err_console.print(f"[red]Unknown source:[/] {name}")
            raise typer.Exit(1)
        return matches[0]
    if cfg.sources:
        return cfg.sources[0]
    err_console.print("[red]No sources configured.[/]")
    raise typer.Exit(1)


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


def main() -> None:
    app()
