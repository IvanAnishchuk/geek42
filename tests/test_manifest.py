"""Tests for Manifest generation and verification via gemato."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from geek42.manifest import (
    generate_manifest,
    manifest_path,
    verify_manifest,
)

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

    for slug in ("2025-01-01-alpha", "2025-06-15-beta-update"):
        d = root / "metadata" / "news" / slug
        d.mkdir(parents=True)
        (d / f"{slug}.en.txt").write_text(
            f"Title: {slug}\nAuthor: D <d@g>\nPosted: {slug[:10]}\n"
            f"Revision: 1\nNews-Item-Format: 2.0\n\nBody.\n"
        )

    (root / "geek42.toml").write_text('title = "Nested"\n')
    (root / "README.md").write_text("# Nested\n")

    news_dir = root / "news"
    news_dir.mkdir()
    (news_dir / "2025-01-01-alpha.md").write_text("compiled\n")
    (news_dir / "2025-06-15-beta-update.md").write_text("compiled\n")

    sub = root / "docs" / "guides"
    sub.mkdir(parents=True)
    (sub / "quickstart.md").write_text("guide\n")

    (root / ".gitignore").write_text("_site/\n")
    dotdir = root / ".git-fake"
    dotdir.mkdir()
    (dotdir / "config").write_text("gitdata\n")

    (root / "metadata" / "layout.conf").write_text("repo-name = test\n")

    return root


# -- generation ---------------------------------------------------------------


@_requires_gemato
def test_generate_creates_manifest(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    ok = generate_manifest(root)
    assert ok
    mf = manifest_path(root)
    assert mf.exists()
    text = mf.read_text()
    assert "BLAKE2B" in text
    assert "SHA512" in text
    assert "README.md" in text


@_requires_gemato
def test_generate_creates_sub_manifests(tmp_path: Path) -> None:
    root = _make_nested_repo(tmp_path)
    generate_manifest(root)

    # Root references sub-Manifests (uncompressed with high watermark)
    text = manifest_path(root).read_text()
    assert "MANIFEST" in text

    # Sub-directory Manifests exist
    sub_manifests = sorted(
        p.relative_to(root) for p in root.rglob("Manifest") if p != manifest_path(root)
    )
    assert sub_manifests, "expected sub-Manifest files"


@_requires_gemato
def test_generate_covers_all_non_dot_files(tmp_path: Path) -> None:
    """All non-dotfiles must be covered somewhere in the Manifest tree."""
    root = _make_nested_repo(tmp_path)
    generate_manifest(root)

    # gemato verify would fail if any file is uncovered
    assert _GEMATO is not None
    result = subprocess.run(
        [_GEMATO, "verify", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@_requires_gemato
def test_generate_skips_dotfiles(tmp_path: Path) -> None:
    root = _make_nested_repo(tmp_path)
    generate_manifest(root)
    text = manifest_path(root).read_text()
    assert ".git" not in text
    assert ".gitignore" not in text


# -- verification -------------------------------------------------------------


@_requires_gemato
def test_verify_ok(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    generate_manifest(root)
    assert verify_manifest(root) == []


@_requires_gemato
def test_verify_nested_ok(tmp_path: Path) -> None:
    root = _make_nested_repo(tmp_path)
    generate_manifest(root)
    assert verify_manifest(root) == []


@_requires_gemato
def test_verify_detects_modification(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    generate_manifest(root)
    (root / "README.md").write_text("TAMPERED\n")
    assert verify_manifest(root)


@_requires_gemato
def test_verify_detects_deep_modification(tmp_path: Path) -> None:
    root = _make_nested_repo(tmp_path)
    generate_manifest(root)
    (root / "docs" / "guides" / "quickstart.md").write_text("EVIL\n")
    assert verify_manifest(root)


@_requires_gemato
def test_verify_detects_missing_file(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    generate_manifest(root)
    (root / "README.md").unlink()
    assert verify_manifest(root)


@_requires_gemato
def test_verify_no_manifest(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    root.mkdir()
    assert verify_manifest(root)


# -- matches real gentoo structure -------------------------------------------


@_requires_gemato
def test_structure_matches_gentoo(tmp_path: Path) -> None:
    """Our Manifest tree must have the same shape as the Gentoo portage repo."""
    root = _make_nested_repo(tmp_path)
    generate_manifest(root)

    # Root Manifest: DATA + IGNORE + MANIFEST entries
    text = manifest_path(root).read_text()
    has_data = any(ln.startswith("DATA ") for ln in text.splitlines())
    has_manifest = any(ln.startswith("MANIFEST ") for ln in text.splitlines())
    has_ignore = any(ln.startswith("IGNORE ") for ln in text.splitlines())
    assert has_data, "root should have DATA entries for top-level files"
    assert has_manifest, "root should have MANIFEST entries for subdirs"
    assert has_ignore, "root should have IGNORE entries (ebuild profile)"

    # Sub-Manifests exist (uncompressed with high compress-watermark)
    assert (root / "metadata" / "Manifest").exists() or (root / "metadata" / "Manifest.gz").exists()
    metadata_news = root / "metadata" / "news"
    assert (metadata_news / "Manifest").exists() or (metadata_news / "Manifest.gz").exists()


@_requires_gemato
def test_gemato_verify_matches_gemato_create(tmp_path: Path) -> None:
    """A Manifest we generate must be identical to one gemato creates."""
    root = _make_nested_repo(tmp_path)

    # Our generate (which calls gemato create --profile ebuild)
    generate_manifest(root)
    our_root = manifest_path(root).read_text()

    # Regenerate with gemato directly (should be idempotent)
    assert _GEMATO is not None
    subprocess.run(
        [_GEMATO, "create", "--profile", "ebuild", str(root)],
        check=True,
        capture_output=True,
    )
    their_root = manifest_path(root).read_text()

    assert our_root == their_root


# -- error handling -----------------------------------------------------------


def test_gemato_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import geek42.manifest as mod

    monkeypatch.setattr(mod, "_gemato", lambda: (_ for _ in ()).throw(RuntimeError("no gemato")))
    with pytest.raises(RuntimeError, match="no gemato"):
        generate_manifest(tmp_path)
