"""Generate a versioned ebuild by copying the -9999 template.

The -9999 ebuild uses a PV conditional to switch between live git
and PyPI sources, so a renamed copy works as-is for any version.

Usage:
    uv run python scripts/gen_ebuild.py [VERSION]
    uv run python scripts/gen_ebuild.py 0.4.2a7
    uv run python scripts/gen_ebuild.py          # auto-detects from __init__.py
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EBUILD_DIR = REPO_ROOT / "packaging" / "gentoo" / "app-text" / "geek42"
TEMPLATE = EBUILD_DIR / "geek42-9999.ebuild"

# PEP 440 to Gentoo version mapping
PEP440_TO_GENTOO = {
    "a": "_alpha",
    "b": "_beta",
    "c": "_rc",
}


def pep440_to_gentoo(version: str) -> str:
    """Convert PEP 440 version to Gentoo version format."""
    for suffix, replacement in PEP440_TO_GENTOO.items():
        match = re.match(rf"^(.+?){suffix}(\d+)$", version)
        if match:
            return f"{match.group(1)}{replacement}{match.group(2)}"
    return version


def get_version() -> str:
    if len(sys.argv) > 1:
        return sys.argv[1].removeprefix("v")
    init = REPO_ROOT / "src" / "geek42" / "__init__.py"
    for line in init.read_text().splitlines():
        if line.startswith("__version__"):
            return line.split('"')[1]
    print("Could not detect version. Pass it as an argument.")
    msg = "Could not detect version from __init__.py or CLI argument"
    raise ValueError(msg)


def _validate_version(version: str) -> None:
    """Reject versions with path separators or other unsafe characters."""
    if not re.match(r"^[0-9]+(\.[0-9]+)*(a|b|c|rc|dev)?[0-9]*$", version):
        print(f"Error: invalid version format: {version}")
        sys.exit(1)


def main() -> int:
    try:
        version = get_version()
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1
    _validate_version(version)
    gentoo_version = pep440_to_gentoo(version)

    if not TEMPLATE.exists():
        print(f"Error: template not found: {TEMPLATE}")
        return 1

    output_dir = REPO_ROOT / "dist" / "gentoo" / "dev-python" / "geek42"
    output_dir.mkdir(parents=True, exist_ok=True)

    output = output_dir / f"geek42-{gentoo_version}.ebuild"
    shutil.copy2(TEMPLATE, output)
    print(f"Generated {output.relative_to(REPO_ROOT)}")

    # Copy metadata.xml for overlay use
    metadata = EBUILD_DIR / "metadata.xml"
    if metadata.exists():
        shutil.copy2(metadata, output_dir / "metadata.xml")
        print(f"  Copied  {metadata.name}")

    print(f"  PEP 440: {version}")
    print(f"  Gentoo:  {gentoo_version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
