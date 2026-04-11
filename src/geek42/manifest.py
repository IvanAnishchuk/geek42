"""Gemato-compatible Manifest generation and verification.

Delegates to ``gemato`` (a project dependency) using the same flags
as the Gentoo overlay workflow::

    gemato update --sign --profile ebuild \\
        --hashes "BLAKE2B SHA512" --timestamp \\
        --compress-watermark 999999999 -q .

    gemato verify --require-signed-manifest \\
        --openpgp-key metadata/key.asc .
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .errors import GematoNotFoundError

_HASHES = "BLAKE2B SHA512"
_COMPRESS_WATERMARK = "999999999"


def _gemato() -> str:
    """Return the absolute path to ``gemato``."""
    path = shutil.which("gemato")
    if path is None:
        raise GematoNotFoundError
    return path


# -- public API ---------------------------------------------------------------


def manifest_path(root: Path) -> Path:
    """Return the canonical Manifest location (``root / Manifest``)."""
    return root / "Manifest"


def generate_manifest(root: Path, *, signing_key: str = "") -> bool:
    """Create or update the Manifest tree and optionally sign.

    Uses the same flags as the Gentoo overlay gemato-sign pre-commit
    hook: ``--profile ebuild``, ``--hashes "BLAKE2B SHA512"``,
    ``--timestamp``, ``--compress-watermark 999999999``.

    When *signing_key* is non-empty the top-level Manifest is signed.
    """
    gemato = _gemato()
    mf = manifest_path(root)

    # First run needs "create"; subsequent runs use "update"
    sub = "update" if mf.exists() else "create"
    args = [
        gemato,
        sub,
        "--profile",
        "ebuild",
        "--hashes",
        _HASHES,
        "--timestamp",
        "--compress-watermark",
        _COMPRESS_WATERMARK,
        "-q",
    ]
    if signing_key:
        args += ["--sign", "--openpgp-id", signing_key]
    args.append(str(root))

    result = subprocess.run(  # noqa: S603
        args,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def verify_manifest(root: Path, *, key_file: str = "metadata/key.asc") -> list[str]:
    """Verify the Manifest tree.

    If ``metadata/key.asc`` exists, signature verification is required.
    Returns a list of error strings (empty = OK).
    """
    gemato = _gemato()
    args = [gemato, "verify"]

    key_path = root / key_file
    if key_path.exists():
        args += ["--require-signed-manifest", "--openpgp-key", str(key_path), "--no-refresh-keys"]

    args += ["--keep-going", str(root)]

    result = subprocess.run(  # noqa: S603
        args,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return []
    errors = [
        line.strip() for line in result.stderr.splitlines() if line.strip() and "ERROR" in line
    ]
    return errors or [result.stderr.strip() or f"gemato exited {result.returncode}"]
