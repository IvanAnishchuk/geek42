"""Regenerate requirements.txt and requirements-dev.txt from uv.lock.

Both files are hash-pinned against uv.lock for reproducible, verifiable
installs. They are committed to the repo and CI verifies they stay in
sync with pyproject.toml / uv.lock.

Usage:
    uv run python scripts/regen_requirements.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from rich.console import Console

console = Console()
REPO_ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str], *, description: str) -> None:
    console.print(f"[bold blue]→[/] {description}")
    result = subprocess.run(  # noqa: S603 — args are list literals, no shell
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        console.print(f"[bold red]✗[/] Command failed: {' '.join(cmd)}")
        if result.stdout:
            console.print(result.stdout)
        if result.stderr:
            console.print(result.stderr)
        sys.exit(result.returncode)


def pkg_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(
        1 for line in path.read_text(encoding="utf-8").splitlines() if line and line[0].isalpha()
    )


def main() -> int:
    run(
        ["uv", "lock"],
        description="uv lock (refresh lockfile if pyproject.toml changed)",
    )

    run(
        [
            "uv",
            "export",
            "--format",
            "requirements-txt",
            "--no-emit-project",
            "--no-dev",
            "--output-file",
            "requirements.txt",
        ],
        description="Exporting requirements.txt (prod only, hash-pinned)",
    )

    run(
        [
            "uv",
            "export",
            "--format",
            "requirements-txt",
            "--no-emit-project",
            "--output-file",
            "requirements-dev.txt",
        ],
        description="Exporting requirements-dev.txt (prod + dev, hash-pinned)",
    )

    prod = pkg_count(REPO_ROOT / "requirements.txt")
    dev = pkg_count(REPO_ROOT / "requirements-dev.txt")

    console.print()
    console.print("[bold green]Done[/]")
    console.print(f"  requirements.txt:     [cyan]{prod}[/] packages")
    console.print(f"  requirements-dev.txt: [cyan]{dev}[/] packages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
