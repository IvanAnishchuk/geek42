"""Download distribution artifacts from GitHub Release or PyPI.

Downloads only distribution files (.whl, .tar.gz) to dist/.
Does not touch proofs/ or perform any transformations.

Usage:
    uv run python scripts/download_artifacts.py 0.4.2a10
    uv run python scripts/download_artifacts.py 0.4.2a10 --source pypi
    uv run python scripts/download_artifacts.py 0.4.2a10 --dry-run
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from pyscv.config import PyscvConfig
from pyscv.download_artifacts import (
    DEFAULT_EXTENSIONS,
    download_from_gh,
    download_from_pypi,
)

app = typer.Typer(add_completion=False)
console = Console()


class Source(StrEnum):
    gh = "gh"
    pypi = "pypi"


@app.command()
def main(
    version: Annotated[
        str,
        typer.Argument(help="Version to download (e.g. 0.4.2a10). Default: from pyproject.toml."),
    ] = "",
    source: Annotated[
        Source,
        typer.Option(help="Download source."),
    ] = Source.gh,
    ext: Annotated[
        list[str] | None,
        typer.Option(help="File extensions to download (repeatable)."),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing files."),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Show what would be downloaded."),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show detailed progress."),
    ] = False,
) -> None:
    """Download distribution artifacts from GitHub Release or PyPI."""
    repo_root = Path(__file__).resolve().parent.parent
    try:
        config = PyscvConfig.from_pyproject(repo_root / "pyproject.toml")
    except ValueError as exc:
        console.print(f"[red]ERROR: {exc}[/]")
        raise typer.Exit(1) from exc

    ver = version or config.version
    extensions = tuple(ext) if ext else DEFAULT_EXTENSIONS

    if config.use_testpypi and source == Source.pypi:
        console.print(
            "[bold yellow]WARNING: using TestPyPI (use-testpypi = true in pyproject.toml)[/]"
        )

    source_label = config.pypi_label if source == Source.pypi else source.value
    console.print(
        f"[bold]Downloading {config.package_name} {ver}[/] from [cyan]{source_label}[/]"
        + (" [yellow](dry run)[/]" if dry_run else "")
    )

    if source == Source.gh:
        code = download_from_gh(
            config, ver, extensions, force=force, dry_run=dry_run, verbose=verbose
        )
    else:
        code = download_from_pypi(
            config, ver, extensions, force=force, dry_run=dry_run, verbose=verbose
        )

    raise typer.Exit(code)


if __name__ == "__main__":
    app()
