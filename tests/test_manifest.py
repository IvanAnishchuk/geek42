"""Tests for Manifest generation and verification — including gemato parity."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

import geek42.manifest as manifest_mod
from geek42.manifest import generate_manifest, manifest_path, verify_manifest

from .conftest import SAMPLE_NEWS_FORMAT2

_GEMATO = shutil.which("gemato")
_requires_gemato = pytest.mark.skipif(not _GEMATO, reason="gemato not installed")


# -- helpers ------------------------------------------------------------------


def _make_repo(tmp_path: Path) -> Path:
    """Minimal news repo."""
    root = tmp_path / "repo"
    news = root / "metadata" / "news" / "2025-11-30-flexiblas-migration"
    news.mkdir(parents=True)
    (news / "2025-11-30-flexiblas-migration.en.txt").write_text(SAMPLE_NEWS_FORMAT2)
    (root / "geek42.toml").write_text('title = "Test"\n')
    (root / "README.md").write_text("# Test\n")
    return root


def _make_nested_repo(tmp_path: Path) -> Path:
    """News repo with nested dirs, multiple items, dotfiles, extra files."""
    root = tmp_path / "repo"

    # Two news items
    for slug in ("2025-01-01-alpha", "2025-06-15-beta-update"):
        d = root / "metadata" / "news" / slug
        d.mkdir(parents=True)
        (d / f"{slug}.en.txt").write_text(
            f"Title: {slug}\nAuthor: D <d@g>\nPosted: {slug[:10]}\n"
            f"Revision: 1\nNews-Item-Format: 2.0\n\nBody.\n"
        )

    # Top-level files
    (root / "geek42.toml").write_text('title = "Nested"\n')
    (root / "README.md").write_text("# Nested\n")

    # Compiled blog output
    news_dir = root / "news"
    news_dir.mkdir()
    (news_dir / "2025-01-01-alpha.md").write_text("compiled\n")
    (news_dir / "2025-06-15-beta-update.md").write_text("compiled\n")

    # Deeper non-news directory
    sub = root / "docs" / "guides"
    sub.mkdir(parents=True)
    (sub / "quickstart.md").write_text("guide\n")

    # Dotfiles / dotdirs (should be excluded)
    (root / ".gitignore").write_text("_site/\n")
    dotdir = root / ".git-fake"
    dotdir.mkdir()
    (dotdir / "config").write_text("gitdata\n")

    # metadata/layout.conf
    (root / "metadata" / "layout.conf").write_text("repo-name = test\n")

    return root


def _data_lines(text: str) -> list[str]:
    """Extract and sort DATA lines from a Manifest (or decompressed .gz)."""
    return sorted(ln for ln in text.splitlines() if ln.startswith("DATA "))


def _data_paths(text: str) -> list[str]:
    """Extract sorted file paths from DATA lines."""
    return sorted(ln.split()[1] for ln in text.splitlines() if ln.startswith("DATA "))


def _py_generate(root: Path) -> None:
    """Force the pure-Python fallback regardless of gemato availability."""
    manifest_mod._py_create(root)


# -- generation ---------------------------------------------------------------


def test_generate_creates_manifest(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    ok = generate_manifest(root)
    assert ok
    mf = manifest_path(root)
    assert mf.exists()
    text = mf.read_text()
    assert "BLAKE2B" in text
    assert "SHA512" in text
    # Top-level files are DATA entries; news items are in sub-Manifests
    assert "README.md" in text


def test_generate_empty_repo(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    root.mkdir()
    generate_manifest(root)
    mf = manifest_path(root)
    if mf.exists():
        assert "DATA " not in mf.read_text()


def test_manifest_covers_all_non_dot_files(tmp_path: Path) -> None:
    root = _make_nested_repo(tmp_path)
    _py_generate(root)
    text = manifest_path(root).read_text()
    paths = _data_paths(text)

    # Should include
    assert "geek42.toml" in paths
    assert "README.md" in paths
    assert "metadata/news/2025-01-01-alpha/2025-01-01-alpha.en.txt" in paths
    assert "metadata/news/2025-06-15-beta-update/2025-06-15-beta-update.en.txt" in paths
    assert "news/2025-01-01-alpha.md" in paths
    assert "docs/guides/quickstart.md" in paths
    assert "metadata/layout.conf" in paths

    # Should exclude
    assert not any(".git" in p for p in paths)
    assert not any("Manifest" in p for p in paths)


def test_manifest_skips_manifest_files(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    # Create a stray Manifest.old
    (root / "Manifest.old").write_text("stale\n")
    _py_generate(root)
    text = manifest_path(root).read_text()
    assert "Manifest" not in _data_paths(text)


# -- verification -------------------------------------------------------------


def test_verify_ok(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    generate_manifest(root)
    assert verify_manifest(root) == []


def test_verify_detects_modification(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    generate_manifest(root)
    (root / "README.md").write_text("TAMPERED\n")
    assert verify_manifest(root)


def test_verify_detects_missing_file(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    generate_manifest(root)
    (root / "README.md").unlink()
    assert verify_manifest(root)


def test_verify_no_manifest(tmp_path: Path) -> None:
    root = tmp_path / "nomanifest"
    root.mkdir()
    assert verify_manifest(root)


def test_verify_nested_repo(tmp_path: Path) -> None:
    root = _make_nested_repo(tmp_path)
    generate_manifest(root)
    assert verify_manifest(root) == []


def test_verify_nested_tamper_deep_file(tmp_path: Path) -> None:
    root = _make_nested_repo(tmp_path)
    generate_manifest(root)
    (root / "docs" / "guides" / "quickstart.md").write_text("EVIL\n")
    assert verify_manifest(root)


# -- gemato parity tests (nested) --------------------------------------------


@_requires_gemato
def test_py_fallback_passes_gemato_verify(tmp_path: Path) -> None:
    """Our pure-Python flat Manifest must pass ``gemato verify``."""
    root = _make_nested_repo(tmp_path)
    _py_generate(root)

    result = subprocess.run(
        [_GEMATO, "verify", str(root)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr


@_requires_gemato
def test_gemato_ebuild_profile_produces_sub_manifests(tmp_path: Path) -> None:
    """``gemato create --profile ebuild`` must produce compressed sub-Manifests."""
    root = _make_nested_repo(tmp_path)
    subprocess.run(
        [_GEMATO, "create", "--profile", "ebuild", str(root)],
        check=True, capture_output=True,
    )
    # Root Manifest references compressed sub-Manifests
    text = manifest_path(root).read_text()
    assert "MANIFEST metadata/Manifest.gz" in text or "MANIFEST metadata/" in text

    # Sub-Manifests exist as .gz
    gz_files = list(root.rglob("Manifest.gz"))
    assert gz_files, "expected at least one Manifest.gz"


@_requires_gemato
def test_gemato_ebuild_profile_passes_our_verify(tmp_path: Path) -> None:
    """Hierarchical Manifests from --profile ebuild must pass our verify."""
    root = _make_nested_repo(tmp_path)
    subprocess.run(
        [_GEMATO, "create", "--profile", "ebuild", str(root)],
        check=True, capture_output=True,
    )
    # Our verify should handle MANIFEST entries and .gz decompression
    errors = manifest_mod._py_verify(root)
    assert errors == []


@_requires_gemato
def test_generate_uses_ebuild_profile(tmp_path: Path) -> None:
    """generate_manifest() with gemato must use --profile ebuild."""
    root = _make_nested_repo(tmp_path)
    generate_manifest(root)

    # Should have compressed sub-Manifests
    gz_files = list(root.rglob("Manifest.gz"))
    assert gz_files, "expected Manifest.gz files (ebuild profile)"

    # And gemato must verify it
    result = subprocess.run(
        [_GEMATO, "verify", str(root)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr


@_requires_gemato
def test_gemato_detects_tamper_after_generate(tmp_path: Path) -> None:
    root = _make_nested_repo(tmp_path)
    generate_manifest(root)
    (root / "docs" / "guides" / "quickstart.md").write_text("EVIL\n")

    result = subprocess.run(
        [_GEMATO, "verify", str(root)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0


@_requires_gemato
def test_our_verify_detects_tamper_on_ebuild_profile(tmp_path: Path) -> None:
    """Our Python verify must catch tampering in the hierarchical structure."""
    root = _make_nested_repo(tmp_path)
    subprocess.run(
        [_GEMATO, "create", "--profile", "ebuild", str(root)],
        check=True, capture_output=True,
    )
    (root / "docs" / "guides" / "quickstart.md").write_text("EVIL\n")
    errors = manifest_mod._py_verify(root)
    assert errors


@_requires_gemato
def test_simple_repo_gemato_verify(tmp_path: Path) -> None:
    """Smoke test: generate_manifest on minimal repo passes gemato verify."""
    root = _make_repo(tmp_path)
    generate_manifest(root)

    result = subprocess.run(
        [_GEMATO, "verify", str(root)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
