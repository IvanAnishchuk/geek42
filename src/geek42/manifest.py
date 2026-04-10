"""Gemato-compatible Manifest generation and verification.

Uses ``gemato create --profile ebuild`` to produce the same
hierarchical Manifest structure as the Gentoo portage tree:

- Root ``Manifest`` with ``DATA``, ``IGNORE``, and ``MANIFEST`` entries
- Compressed ``Manifest.gz`` sub-Manifests in each subdirectory
- ``TIMESTAMP`` entries when signing

When gemato is not available, a flat pure-Python fallback is used
that gemato can still verify.
"""

from __future__ import annotations

import gzip
import hashlib
import shutil
import subprocess
from pathlib import Path

_GEMATO = shutil.which("gemato")

# -- public helpers -----------------------------------------------------------


def manifest_path(root: Path) -> Path:
    """Return the canonical Manifest location (``root / Manifest``)."""
    return root / "Manifest"


# -- generation ---------------------------------------------------------------


def generate_manifest(root: Path) -> bool:
    """Create or update the Manifest tree.

    Uses ``gemato create --profile ebuild`` for the hierarchical
    compressed Manifest structure matching Gentoo repos.  Falls back
    to a flat pure-Python Manifest when gemato is absent.
    """
    if _GEMATO:
        return _gemato_create(root)
    return _py_create(root)


def _gemato_create(root: Path) -> bool:
    result = subprocess.run(  # noqa: S603
        [_GEMATO, "create", "--profile", "ebuild", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _py_create(root: Path) -> bool:
    """Flat fallback — single root Manifest with DATA entries.

    This is verifiable by gemato but lacks the hierarchical compressed
    sub-Manifests.  Install gemato for full Gentoo-repo parity.
    """
    lines: list[str] = []
    for f in sorted(root.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(root)
        if rel.name.startswith("Manifest"):
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
    """Verify the Manifest tree.  Returns a list of errors (empty = OK).

    Delegates to ``gemato verify`` when available (handles compressed
    sub-Manifests, signatures, etc.).  Falls back to pure-Python
    verification of DATA entries in the root Manifest.
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
    errors = [
        line.strip()
        for line in result.stderr.splitlines()
        if line.strip() and "ERROR" in line
    ]
    return errors or [result.stderr.strip() or f"gemato exited {result.returncode}"]


def _py_verify(root: Path) -> list[str]:
    """Verify DATA entries in the root Manifest and any .gz sub-Manifests."""
    mf = manifest_path(root)
    if not mf.exists():
        return ["Manifest file not found"]

    errors: list[str] = []
    _verify_manifest_text(mf.read_text(encoding="utf-8"), root, errors)

    return errors


def _verify_manifest_text(text: str, base: Path, errors: list[str]) -> None:
    """Verify all DATA and MANIFEST entries in a Manifest body."""
    for line in text.splitlines():
        if line.startswith("DATA "):
            _verify_data_line(line, base, errors)
        elif line.startswith("MANIFEST "):
            _verify_sub_manifest(line, base, errors)


def _verify_data_line(line: str, base: Path, errors: list[str]) -> None:
    parts = line.split()
    if len(parts) < 7:
        errors.append(f"malformed line: {line}")
        return

    rel_path = parts[1]
    expected_size = int(parts[2])
    target = base / rel_path

    if not target.exists():
        errors.append(f"missing: {rel_path}")
        return

    size, b2, s5 = _hash_file(target)
    if size != expected_size:
        errors.append(f"size mismatch: {rel_path} ({size} != {expected_size})")
    hashes = dict(zip(parts[3::2], parts[4::2], strict=False))
    if "BLAKE2B" in hashes and hashes["BLAKE2B"] != b2:
        errors.append(f"BLAKE2B mismatch: {rel_path}")
    if "SHA512" in hashes and hashes["SHA512"] != s5:
        errors.append(f"SHA512 mismatch: {rel_path}")


def _verify_sub_manifest(line: str, base: Path, errors: list[str]) -> None:
    """Verify a MANIFEST entry and recurse into the referenced sub-Manifest."""
    parts = line.split()
    if len(parts) < 3:
        return
    rel_path = parts[1]
    target = base / rel_path

    if not target.exists():
        errors.append(f"missing sub-Manifest: {rel_path}")
        return

    # Verify the sub-Manifest file's own checksums
    _verify_data_line(line.replace("MANIFEST ", "DATA ", 1), base, errors)

    # Recurse into the sub-Manifest contents
    sub_base = target.parent
    if rel_path.endswith(".gz"):
        sub_text = gzip.decompress(target.read_bytes()).decode("utf-8")
    else:
        sub_text = target.read_text(encoding="utf-8")
    _verify_manifest_text(sub_text, sub_base, errors)


# -- internal -----------------------------------------------------------------


def _hash_file(path: Path) -> tuple[int, str, str]:
    data = path.read_bytes()
    return (
        len(data),
        hashlib.blake2b(data).hexdigest(),
        hashlib.sha512(data).hexdigest(),
    )
