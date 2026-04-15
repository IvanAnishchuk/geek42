"""Regenerate shields.io badge JSON files from uv.lock and pyproject.toml.

Badge files live under badges/ and are committed to the repo so README
badges auto-update when tool versions change.

Usage:
    uv run python scripts/regen_badges.py
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


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
    badges = regen_badges()
    if badges:
        summary = ", ".join(f"{k} {v}" for k, v in badges.items())
        print(f"Regenerated badges: {summary}")
    else:
        print("No badges generated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
