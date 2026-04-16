"""Check that pyproject.toml and __init__.py versions match.

Usage:
    uv run python scripts/check_version.py
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"
INIT_PY = REPO_ROOT / "src" / "geek42" / "__init__.py"


def get_pyproject_version() -> str:
    try:
        data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
        return data["project"]["version"]
    except (FileNotFoundError, tomllib.TOMLDecodeError, KeyError) as exc:
        msg = f"could not read version from {PYPROJECT}: {exc}"
        raise ValueError(msg) from exc


def get_init_version() -> str | None:
    for line in INIT_PY.read_text(encoding="utf-8").splitlines():
        match = re.match(r"""^__version__\s*=\s*['"](.+?)['"]""", line)
        if match:
            return match.group(1)
    return None


def main() -> int:
    try:
        pyproject_ver = get_pyproject_version()
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    init_ver = get_init_version()

    if init_ver is None:
        print(f"ERROR: could not find __version__ in {INIT_PY}", file=sys.stderr)
        return 1

    if pyproject_ver != init_ver:
        print("ERROR: version mismatch", file=sys.stderr)
        print(f"  pyproject.toml: {pyproject_ver}", file=sys.stderr)
        print(f"  __init__.py:    {init_ver}", file=sys.stderr)
        return 1

    print(f"Version consistent: {pyproject_ver}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
