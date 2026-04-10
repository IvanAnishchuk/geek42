"""Gemato-compatible Manifest generation and verification.

Produces ``Manifest`` files containing BLAKE2B and SHA512 checksums
for every news item file, following the Gentoo Manifest 2 format.
Signing uses ``gpg`` for clear-text signatures, which gemato can
verify transparently.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from .parser import NEWS_SUBDIR


def _hash_file(path: Path) -> tuple[int, str, str]:
    """Return (size, blake2b_hex, sha512_hex) for *path*."""
    data = path.read_bytes()
    b2 = hashlib.blake2b(data).hexdigest()
    s5 = hashlib.sha512(data).hexdigest()
    return len(data), b2, s5


def generate_manifest(root: Path) -> str:
    """Build a Manifest string covering all news item files under *root*.

    The output uses Gentoo's Manifest 2 ``DATA`` entries with BLAKE2B
    and SHA512 checksums, compatible with ``gemato verify``.
    """
    news_root = root / NEWS_SUBDIR
    if not news_root.is_dir():
        return ""

    lines: list[str] = []
    for item_dir in sorted(news_root.iterdir()):
        if not item_dir.is_dir():
            continue
        for f in sorted(item_dir.iterdir()):
            if not f.is_file():
                continue
            rel = f.relative_to(root)
            size, b2, s5 = _hash_file(f)
            lines.append(f"DATA {rel} {size} BLAKE2B {b2} SHA512 {s5}")

    return "\n".join(lines) + "\n" if lines else ""


def verify_manifest(root: Path) -> list[str]:
    """Check every ``DATA`` entry in the Manifest against disk.

    Returns a list of error strings (empty means all OK).
    """
    manifest_path = root / "Manifest"
    if not manifest_path.exists():
        return ["Manifest file not found"]

    text = manifest_path.read_text(encoding="utf-8")
    errors: list[str] = []

    for line in text.splitlines():
        # Skip PGP armour and blank lines
        if not line.startswith("DATA "):
            continue
        parts = line.split()
        # DATA path size BLAKE2B hash SHA512 hash
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
        # Check whichever hashes are present
        hashes = dict(zip(parts[3::2], parts[4::2], strict=False))
        if "BLAKE2B" in hashes and hashes["BLAKE2B"] != b2:
            errors.append(f"BLAKE2B mismatch: {rel_path}")
        if "SHA512" in hashes and hashes["SHA512"] != s5:
            errors.append(f"SHA512 mismatch: {rel_path}")

    return errors
