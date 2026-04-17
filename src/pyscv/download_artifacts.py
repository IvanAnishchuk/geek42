"""Download distribution artifacts from GitHub Release or PyPI.

Downloads only distribution files (.whl, .tar.gz) to dist/.
Does not touch proofs/ or perform any transformations.
"""

from __future__ import annotations

import tempfile
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Annotated
from urllib.parse import urljoin, urlparse

import httpx
import typer
from pydantic import BaseModel
from rich.console import Console

from pyscv.config import PyscvConfig

console = Console()

DEFAULT_EXTENSIONS = (".whl", ".tar.gz")

ALLOWED_HOSTS = frozenset(
    {
        "api.github.com",
        "github.com",
        "objects.githubusercontent.com",
        "release-assets.githubusercontent.com",
        "pypi.org",
        "test.pypi.org",
        "files.pythonhosted.org",
        "test-files.pythonhosted.org",
    }
)

GH_API_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


# -- API response models ---------------------------------------------------


class GhReleaseAsset(BaseModel):
    name: str
    browser_download_url: str


class PypiFileInfo(BaseModel):
    filename: str
    url: str


# -- Download helpers ------------------------------------------------------


def _validate_url(url: str) -> None:
    """Validate that a URL uses HTTPS and an allowed host."""
    parsed = urlparse(url)
    if parsed.scheme != "https":
        msg = f"Refusing non-HTTPS URL: {url}"
        raise ValueError(msg)
    if parsed.hostname not in ALLOWED_HOSTS:
        msg = f"Refusing URL from unexpected host {parsed.hostname}: {url}"
        raise ValueError(msg)


def _safe_filename(name: str) -> str:
    """Validate filename has no path traversal components."""
    safe = PurePosixPath(name).name
    if safe != name or ".." in name or "/" in name or "\\" in name:
        msg = f"Refusing unsafe filename: {name!r}"
        raise ValueError(msg)
    return safe


MAX_REDIRECTS = 5


def _resolve_url(url: str, timeout: float = 30) -> str:
    """Validate URL, follow redirect chain (each hop validated), return final URL."""
    _validate_url(url)
    for _ in range(MAX_REDIRECTS):
        resp = httpx.head(url, follow_redirects=False, timeout=timeout)
        if not resp.is_redirect:
            return url
        # urljoin handles both absolute and relative Location headers:
        # absolute → returned as-is, relative → resolved against current url
        url = urljoin(url, str(resp.headers["location"]))
        _validate_url(url)
    msg = f"Too many redirects (>{MAX_REDIRECTS}) starting from {url}"
    raise ValueError(msg)


def fetch_gh_release_assets(config: PyscvConfig, tag: str) -> list[GhReleaseAsset]:
    """Fetch asset list from GitHub Releases API."""
    url = _resolve_url(f"https://api.github.com/repos/{config.repo_slug}/releases/tags/{tag}")
    resp = httpx.get(url, timeout=30, follow_redirects=False, headers=GH_API_HEADERS)
    resp.raise_for_status()
    raw_assets = resp.json().get("assets", [])
    return [GhReleaseAsset.model_validate(a) for a in raw_assets]


def fetch_pypi_release_files(config: PyscvConfig, version: str) -> list[PypiFileInfo]:
    """Fetch file list from PyPI JSON API."""
    url = _resolve_url(f"{config.pypi_base_url}/pypi/{config.package_name}/{version}/json")
    resp = httpx.get(url, timeout=30, follow_redirects=False)
    resp.raise_for_status()
    raw_files = resp.json().get("urls", [])
    return [PypiFileInfo.model_validate(f) for f in raw_files]


def atomic_download(url: str, dest: Path) -> None:
    """Download a file atomically — write to temp dir then replace.

    Validates URL and all redirect destinations before downloading.
    """
    final_url = _resolve_url(url)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=dest.parent) as tmpdir:
        tmp_file = Path(tmpdir) / dest.name
        with httpx.stream("GET", final_url, timeout=60, follow_redirects=False) as stream:
            stream.raise_for_status()
            with tmp_file.open("wb") as fh:
                for chunk in stream.iter_bytes():
                    fh.write(chunk)
        tmp_file.replace(dest)


# -- Source downloaders ----------------------------------------------------


def download_from_gh(
    config: PyscvConfig,
    version: str,
    extensions: tuple[str, ...],
    *,
    force: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    """Download artifacts from GitHub Release via API + httpx."""
    assert config.dist_dir is not None  # noqa: S101 — type narrowing, checked by validate_required
    tag = config.tag(version)
    try:
        assets = fetch_gh_release_assets(config, tag)
    except httpx.HTTPError as exc:
        console.print(f"[red]ERROR: failed to fetch GitHub Release {tag}: {exc}[/]")
        return 1

    if not dry_run:
        config.dist_dir.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    skipped = 0
    for asset in assets:
        try:
            name = _safe_filename(asset.name)
        except ValueError as exc:
            console.print(f"  [red]FAIL[/] {asset.name}: {exc}")
            return 1
        if not any(name.endswith(ext) for ext in extensions):
            if verbose:
                console.print(f"  [dim]skip {name} (not a dist file)[/]")
            continue

        dest = config.dist_dir / name

        if dry_run:
            if dest.exists() and not force:
                console.print(f"  [yellow]exists[/] {name}")
                skipped += 1
            else:
                console.print(f"  [green]download[/] {name}")
                downloaded += 1
            continue

        if dest.exists() and not force:
            if verbose:
                console.print(f"  [dim]skip {name} (exists)[/]")
            skipped += 1
            continue

        if verbose:
            console.print(f"  [dim]downloading {name}...[/]")
        try:
            atomic_download(asset.browser_download_url, dest)
        except (httpx.HTTPError, ValueError, OSError) as exc:
            console.print(f"  [red]FAIL[/] {name}: {exc}")
            return 1
        console.print(f"  [green]OK[/] {name}")
        downloaded += 1

    action = "would be downloaded" if dry_run else "downloaded"
    summary = f"{downloaded} {action}"
    if skipped:
        summary += f", {skipped} skipped"
    console.print(f"\n[bold]{summary}[/] from {tag}")
    return 0


def download_from_pypi(
    config: PyscvConfig,
    version: str,
    extensions: tuple[str, ...],
    *,
    force: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    """Download artifacts from PyPI (or TestPyPI if configured)."""
    assert config.dist_dir is not None  # noqa: S101 — type narrowing, checked by validate_required
    try:
        files = fetch_pypi_release_files(config, version)
    except httpx.HTTPError as exc:
        console.print(f"[red]ERROR: failed to fetch from {config.pypi_label}: {exc}[/]")
        return 1

    if not dry_run:
        config.dist_dir.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    skipped = 0
    for file_info in files:
        try:
            filename = _safe_filename(file_info.filename)
        except ValueError as exc:
            console.print(f"  [red]FAIL[/] {file_info.filename}: {exc}")
            return 1
        if not any(filename.endswith(ext) for ext in extensions):
            if verbose:
                console.print(f"  [dim]skip {filename} (not matching extensions)[/]")
            continue

        dest = config.dist_dir / filename

        if dry_run:
            if dest.exists() and not force:
                console.print(f"  [yellow]exists[/] {filename}")
                skipped += 1
            else:
                console.print(f"  [green]download[/] {filename}")
                downloaded += 1
            continue

        if dest.exists() and not force:
            if verbose:
                console.print(f"  [dim]skip {filename} (exists)[/]")
            skipped += 1
            continue

        if verbose:
            console.print(f"  [dim]downloading {filename}...[/]")
        try:
            atomic_download(file_info.url, dest)
        except (httpx.HTTPError, ValueError, OSError) as exc:
            console.print(f"  [red]FAIL[/] {filename}: {exc}")
            return 1
        console.print(f"  [green]OK[/] {filename}")
        downloaded += 1

    action = "would be downloaded" if dry_run else "downloaded"
    summary = f"{downloaded} {action}"
    if skipped:
        summary += f", {skipped} skipped"
    console.print(f"\n[bold]{summary}[/] from {config.pypi_label}")
    return 0


# -- CLI -------------------------------------------------------------------


class Source(StrEnum):
    gh = "gh"
    pypi = "pypi"


app = typer.Typer(add_completion=False)


@app.command()
def main(
    version: Annotated[
        str | None,
        typer.Argument(help="Version to download (e.g. 0.4.2a10). Default: from pyproject.toml."),
    ] = None,
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
    pyproject: Annotated[
        Path,
        typer.Option(help="Path to pyproject.toml."),
    ] = Path("pyproject.toml"),
) -> None:
    """Download distribution artifacts from GitHub Release or PyPI."""
    try:
        config = PyscvConfig.from_pyproject(pyproject)
    except ValueError as exc:
        console.print(f"[red]ERROR: {exc}[/]")
        raise typer.Exit(1) from exc

    config = config.with_overrides(version=version)
    try:
        config.validate_required()
    except ValueError as exc:
        console.print(f"[red]ERROR: {exc}[/]")
        raise typer.Exit(1) from exc

    extensions = tuple(ext) if ext else DEFAULT_EXTENSIONS

    if config.use_testpypi and source == Source.pypi:
        console.print(
            "[bold yellow]WARNING: using TestPyPI (use-testpypi = true in pyproject.toml)[/]"
        )

    source_label = config.pypi_label if source == Source.pypi else source.value
    console.print(
        f"[bold]Downloading {config.package_name} {config.version}[/] from [cyan]{source_label}[/]"
        + (" [yellow](dry run)[/]" if dry_run else "")
    )

    if source == Source.gh:
        code = download_from_gh(
            config, config.version, extensions, force=force, dry_run=dry_run, verbose=verbose
        )
    else:
        code = download_from_pypi(
            config, config.version, extensions, force=force, dry_run=dry_run, verbose=verbose
        )

    raise typer.Exit(code)
