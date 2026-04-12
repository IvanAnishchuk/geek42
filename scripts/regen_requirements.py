"""Regenerate requirements.txt, requirements-dev.txt, and badges from uv.lock.

Both requirements files are hash-pinned against uv.lock for reproducible,
verifiable installs. Badge JSON files are shields.io endpoint format,
committed to the repo so README badges auto-update on push.

Usage:
    uv run python scripts/regen_requirements.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
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


def _locked_version(lock_text: str, package: str) -> str | None:
    """Extract a package version from uv.lock text."""
    match = re.search(rf'^name = "{package}"\nversion = "(.+?)"', lock_text, re.MULTILINE)
    return match.group(1) if match else None


def _make_badge(label: str, message: str, color: str = "blue") -> dict:
    """Create a shields.io endpoint badge JSON object."""
    return {"schemaVersion": 1, "label": label, "message": message, "color": color}


def regen_badges() -> dict[str, str]:
    """Generate badge JSON files from uv.lock and pyproject.toml."""
    badges_dir = REPO_ROOT / "badges"
    badges_dir.mkdir(exist_ok=True)

    lock_text = (REPO_ROOT / "uv.lock").read_text(encoding="utf-8")
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    badges: dict[str, str] = {}

    # Tool versions from uv.lock
    for pkg, color in [
        ("uv", "DE5FE9"),
        ("ruff", "D7FF64"),
        ("ty", "D7FF64"),
    ]:
        version = _locked_version(lock_text, pkg)
        if version:
            badge = _make_badge(pkg, f"v{version}", color)
            path = badges_dir / f"{pkg}.json"
            path.write_text(json.dumps(badge, indent=2) + "\n", encoding="utf-8")
            badges[pkg] = version

    # Python version from pyproject.toml requires-python
    requires_python = pyproject.get("project", {}).get("requires-python", "")
    if requires_python:
        badge = _make_badge("python", requires_python, "3776AB")
        (badges_dir / "python.json").write_text(
            json.dumps(badge, indent=2) + "\n", encoding="utf-8"
        )
        badges["python"] = requires_python

    return badges


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

    # Regenerate badge JSON files
    badges = regen_badges()

    console.print()
    console.print("[bold green]Done[/]")
    console.print(f"  requirements.txt:     [cyan]{prod}[/] packages")
    console.print(f"  requirements-dev.txt: [cyan]{dev}[/] packages")
    if badges:
        summary = ", ".join(f"{k} {v}" for k, v in badges.items())
        console.print(f"  badges:               [cyan]{summary}[/]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
