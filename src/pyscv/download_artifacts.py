"""Download distribution artifacts from GitHub Release or PyPI.

Downloads only distribution files (.whl, .tar.gz) to dist/.
Does not touch proofs/ or perform any transformations.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import httpx
from rich.console import Console

from pyscv.config import PyscvConfig

console = Console()

DEFAULT_EXTENSIONS = (".whl", ".tar.gz")


# -- Download helpers ------------------------------------------------------


def fetch_gh_release_assets(config: PyscvConfig, tag: str) -> list[dict]:
    """Fetch asset list from GitHub Releases API."""
    url = f"https://api.github.com/repos/{config.repo_slug}/releases/tags/{tag}"
    resp = httpx.get(url, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    return resp.json().get("assets", [])


def fetch_pypi_release_files(config: PyscvConfig, version: str) -> list[dict]:
    """Fetch file list from PyPI JSON API."""
    url = f"{config.pypi_base_url}/pypi/{config.package_name}/{version}/json"
    resp = httpx.get(url, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    return resp.json().get("urls", [])


def atomic_download(url: str, dest: Path) -> None:
    """Download a file atomically — write to temp dir then rename."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=dest.parent) as tmpdir:
        tmp_file = Path(tmpdir) / dest.name
        with httpx.stream("GET", url, timeout=60, follow_redirects=True) as stream:
            stream.raise_for_status()
            with tmp_file.open("wb") as fh:
                for chunk in stream.iter_bytes():
                    fh.write(chunk)
        tmp_file.rename(dest)


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
    tag = config.tag(version)
    try:
        assets = fetch_gh_release_assets(config, tag)
    except httpx.HTTPError as exc:
        console.print(f"[red]ERROR: GitHub Release {tag} not found: {exc}[/]")
        return 1

    if not dry_run:
        config.dist_dir.mkdir(exist_ok=True)
    count = 0
    for asset in assets:
        name = asset["name"]
        if not any(name.endswith(ext) for ext in extensions):
            if verbose:
                console.print(f"  [dim]skip {name} (not a dist file)[/]")
            continue

        dest = config.dist_dir / name

        if dry_run:
            status = "[yellow]exists[/]" if dest.exists() and not force else "[green]download[/]"
            console.print(f"  {status} {name}")
            count += 1
            continue

        if dest.exists() and not force:
            if verbose:
                console.print(f"  [dim]skip {name} (exists)[/]")
            continue

        download_url = asset["browser_download_url"]
        if verbose:
            console.print(f"  [dim]downloading {name}...[/]")
        try:
            atomic_download(download_url, dest)
        except httpx.HTTPError as exc:
            console.print(f"  [red]FAIL[/] {name}: {exc}")
            return 1
        console.print(f"  [green]OK[/] {name}")
        count += 1

    action = "would be downloaded" if dry_run else "downloaded"
    console.print(f"\n[bold]{count}[/] artifact(s) {action} from {tag}")
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
    try:
        files = fetch_pypi_release_files(config, version)
    except httpx.HTTPError as exc:
        console.print(f"[red]ERROR: could not fetch from {config.pypi_label}: {exc}[/]")
        return 1

    if not dry_run:
        config.dist_dir.mkdir(exist_ok=True)
    count = 0
    for file_info in files:
        filename = file_info["filename"]
        if not any(filename.endswith(ext) for ext in extensions):
            if verbose:
                console.print(f"  [dim]skip {filename} (not matching extensions)[/]")
            continue

        dest = config.dist_dir / filename

        if dry_run:
            status = "[yellow]exists[/]" if dest.exists() and not force else "[green]download[/]"
            console.print(f"  {status} {filename}")
            count += 1
            continue

        if dest.exists() and not force:
            if verbose:
                console.print(f"  [dim]skip {filename} (exists)[/]")
            continue

        download_url = file_info["url"]
        if verbose:
            console.print(f"  [dim]downloading {filename}...[/]")
        try:
            atomic_download(download_url, dest)
        except httpx.HTTPError as exc:
            console.print(f"  [red]FAIL[/] {filename}: {exc}")
            return 1
        console.print(f"  [green]OK[/] {filename}")
        count += 1

    action = "would be downloaded" if dry_run else "downloaded"
    console.print(f"\n[bold]{count}[/] artifact(s) {action} from {config.pypi_label}")
    return 0
