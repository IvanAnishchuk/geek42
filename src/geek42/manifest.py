"""Gemato-compatible Manifest generation and verification.

The ``Manifest`` lives at the repository root and covers every file
in the tree, exactly as ``gemato create --hashes "BLAKE2B SHA512"``
produces.  When gemato is available on ``$PATH`` it is used directly;
otherwise a pure-Python fallback generates / verifies the same format.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path

_HASHES = "BLAKE2B SHA512"
_GEMATO = shutil.which("gemato")

# -- public helpers -----------------------------------------------------------


def manifest_path(root: Path) -> Path:
    """Return the canonical Manifest location (``root / Manifest``)."""
    return root / "Manifest"


# -- generation ---------------------------------------------------------------


def generate_manifest(root: Path) -> bool:
    """Create or update the root ``Manifest``.

    Uses ``gemato create`` when available, falls back to pure Python.
    Returns True when a Manifest was written.
    """
    if _GEMATO:
        return _gemato_create(root)
    return _py_create(root)


def _gemato_create(root: Path) -> bool:
    result = subprocess.run(  # noqa: S603
        [_GEMATO, "create", "--hashes", _HASHES, str(root)],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _py_create(root: Path) -> bool:
    lines: list[str] = []
    for f in sorted(root.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(root)
        if str(rel) == "Manifest":
            continue
        if any(p.startswith(".") for p in rel.parts):
            continue
        size, b2, s5 = _hash_file(f)
        lines.append(f"DATA {rel} {size} BLAKE2B {b2} SHA512 {s5}")
    if not lines:
        return False
    manifest_path(root).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


# -- verification -------------------------------------------------------------


def verify_manifest(root: Path) -> list[str]:
    """Verify the Manifest.  Returns a list of errors (empty = OK).

    Delegates to ``gemato verify`` when available, otherwise checks
    each ``DATA`` entry with pure Python.
    """
    if _GEMATO:
        return _gemato_verify(root)
    return _py_verify(root)


def _gemato_verify(root: Path) -> list[str]:
    result = subprocess.run(  # noqa: S603
        [_GEMATO, "verify", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return []
    # Parse gemato's error output into a list
    errors = [
        line.strip()
        for line in result.stderr.splitlines()
        if line.strip() and "ERROR" in line
    ]
    return errors or [result.stderr.strip() or f"gemato exited {result.returncode}"]


def _py_verify(root: Path) -> list[str]:
    mf = manifest_path(root)
    if not mf.exists():
        return ["Manifest file not found"]

    text = mf.read_text(encoding="utf-8")
    errors: list[str] = []

    for line in text.splitlines():
        if not line.startswith("DATA "):
            continue
        parts = line.split()
        if len(parts) < 7:
            errors.append(f"malformed line: {line}")
            continue

        rel_path = parts[1]
        expected_size = int(parts[2])
        target = root / rel_path

        if not target.exists():
            errors.append(f"missing: {rel_path}")
            continue

        size, b2, s5 = _hash_file(target)
        if size != expected_size:
            errors.append(f"size mismatch: {rel_path} ({size} != {expected_size})")
        hashes = dict(zip(parts[3::2], parts[4::2], strict=False))
        if "BLAKE2B" in hashes and hashes["BLAKE2B"] != b2:
            errors.append(f"BLAKE2B mismatch: {rel_path}")
        if "SHA512" in hashes and hashes["SHA512"] != s5:
            errors.append(f"SHA512 mismatch: {rel_path}")

    return errors


# -- internal -----------------------------------------------------------------


def _hash_file(path: Path) -> tuple[int, str, str]:
    data = path.read_bytes()
    return (
        len(data),
        hashlib.blake2b(data).hexdigest(),
        hashlib.sha512(data).hexdigest(),
    )
