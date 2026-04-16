"""Tests for pyscv.download_artifacts and pyscv.config."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest

from pyscv.config import PyscvConfig
from pyscv.download_artifacts import (
    atomic_download,
    download_from_gh,
    download_from_pypi,
    fetch_gh_release_assets,
    fetch_pypi_release_files,
)

# -- Fixtures --------------------------------------------------------------


@pytest.fixture()
def config(tmp_path: Path) -> PyscvConfig:
    return PyscvConfig(
        package_name="testpkg",
        version="1.0.0",
        repo_slug="owner/repo",
        tag_prefix="v",
        dist_dir=tmp_path / "dist",
    )


@pytest.fixture()
def gh_assets() -> list[dict]:
    return [
        {"name": "pkg-1.0.0.whl", "browser_download_url": "https://gh.example/pkg-1.0.0.whl"},
        {"name": "pkg-1.0.0.tar.gz", "browser_download_url": "https://gh.example/pkg-1.0.0.tar.gz"},
        {"name": "pkg-1.0.0-SHA256SUMS.txt", "browser_download_url": "https://gh.example/sums"},
        {"name": "pkg-1.0.0.whl.sigstore.json", "browser_download_url": "https://gh.example/sig"},
    ]


@pytest.fixture()
def pypi_files() -> list[dict]:
    return [
        {"filename": "pkg-1.0.0.whl", "url": "https://pypi.example/pkg-1.0.0.whl"},
        {"filename": "pkg-1.0.0.tar.gz", "url": "https://pypi.example/pkg-1.0.0.tar.gz"},
    ]


@pytest.fixture()
def no_network_gh(monkeypatch, gh_assets):
    """Replace fetch_gh_release_assets with a fake returning gh_assets."""
    monkeypatch.setattr(
        "pyscv.download_artifacts.fetch_gh_release_assets",
        lambda *_a, **_kw: gh_assets,
    )


@pytest.fixture()
def no_network_pypi(monkeypatch, pypi_files):
    """Replace fetch_pypi_release_files with a fake returning pypi_files."""
    monkeypatch.setattr(
        "pyscv.download_artifacts.fetch_pypi_release_files",
        lambda *_a, **_kw: pypi_files,
    )


@pytest.fixture()
def fake_download(monkeypatch):
    """Replace atomic_download: records calls, creates empty dest files."""
    calls: list[tuple[str, Path]] = []

    def _download(url: str, dest: Path) -> None:
        calls.append((url, dest))
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"fake")

    monkeypatch.setattr("pyscv.download_artifacts.atomic_download", _download)
    return calls


# -- PyscvConfig.from_pyproject --------------------------------------------


@pytest.fixture()
def minimal_pyproject(tmp_path: Path) -> Path:
    """Write a minimal pyproject.toml and return its path."""
    p = tmp_path / "pyproject.toml"
    p.write_text(
        '[project]\nname = "mypkg"\nversion = "2.3.4"\n'
        "[project.urls]\n"
        '[tool.pyscv]\nrepo-slug = "me/mypkg"\ntag-prefix = "release-"\n'
        "use-testpypi = true\n"
    )
    return p


@pytest.fixture()
def bare_pyproject(tmp_path: Path) -> Path:
    """pyproject.toml with no [tool.pyscv] section."""
    p = tmp_path / "pyproject.toml"
    p.write_text('[project]\nname = "bare"\nversion = "0.1"\n')
    return p


def test_from_pyproject_parses_all_fields(minimal_pyproject):
    cfg = PyscvConfig.from_pyproject(minimal_pyproject)
    assert cfg.package_name == "mypkg"
    assert cfg.version == "2.3.4"
    assert cfg.repo_slug == "me/mypkg"
    assert cfg.tag_prefix == "release-"
    assert cfg.use_testpypi is True
    assert cfg.dist_dir == minimal_pyproject.parent / "dist"


def test_from_pyproject_defaults_without_pyscv(bare_pyproject):
    cfg = PyscvConfig.from_pyproject(bare_pyproject)
    assert cfg.package_name == "bare"
    assert cfg.repo_slug == ""
    assert cfg.tag_prefix == "v"
    assert cfg.use_testpypi is False


@pytest.mark.parametrize(
    ("use_testpypi", "expected_url", "expected_label"),
    [
        (False, "https://pypi.org", "PyPI"),
        (True, "https://test.pypi.org", "TestPyPI"),
    ],
)
def test_pypi_url_and_label(use_testpypi, expected_url, expected_label):
    cfg = PyscvConfig(package_name="x", version="1", repo_slug="o/r", use_testpypi=use_testpypi)
    assert cfg.pypi_base_url == expected_url
    assert cfg.pypi_label == expected_label


@pytest.mark.parametrize(
    ("prefix", "version", "override", "expected"),
    [
        ("v", "1.0", None, "v1.0"),
        ("v", "1.0", "2.0", "v2.0"),
        ("release-", "3.0a1", None, "release-3.0a1"),
    ],
)
def test_tag_formatting(prefix, version, override, expected):
    cfg = PyscvConfig(package_name="x", version=version, repo_slug="o/r", tag_prefix=prefix)
    assert cfg.tag(override) == expected


# -- fetch_gh_release_assets -----------------------------------------------


def test_fetch_gh_builds_correct_url(monkeypatch, config):
    captured = {}

    def fake_get(url, **kw):
        captured["url"] = url
        resp = MagicMock()
        resp.json.return_value = {"assets": []}
        return resp

    monkeypatch.setattr("pyscv.download_artifacts.httpx.get", fake_get)
    fetch_gh_release_assets(config, "v1.0.0")
    assert captured["url"] == "https://api.github.com/repos/owner/repo/releases/tags/v1.0.0"


def test_fetch_gh_returns_assets(monkeypatch, config):
    resp = MagicMock()
    resp.json.return_value = {"assets": [{"name": "a.whl"}, {"name": "b.tar.gz"}]}
    monkeypatch.setattr("pyscv.download_artifacts.httpx.get", lambda *a, **kw: resp)
    assert len(fetch_gh_release_assets(config, "v1")) == 2


def test_fetch_gh_propagates_http_error(monkeypatch, config):
    def explode(*_a, **_kw):
        raise httpx.HTTPStatusError(
            "boom", request=MagicMock(), response=MagicMock(status_code=404)
        )

    monkeypatch.setattr("pyscv.download_artifacts.httpx.get", explode)
    with pytest.raises(httpx.HTTPStatusError):
        fetch_gh_release_assets(config, "v99")


# -- fetch_pypi_release_files ----------------------------------------------


def test_fetch_pypi_uses_configured_base_url(monkeypatch):
    cfg = PyscvConfig(package_name="mypkg", version="1", repo_slug="o/r", use_testpypi=True)
    captured = {}

    def fake_get(url, **kw):
        captured["url"] = url
        resp = MagicMock()
        resp.json.return_value = {"urls": []}
        return resp

    monkeypatch.setattr("pyscv.download_artifacts.httpx.get", fake_get)
    fetch_pypi_release_files(cfg, "1.0")
    assert captured["url"] == "https://test.pypi.org/pypi/mypkg/1.0/json"


def test_fetch_pypi_returns_files(monkeypatch, config):
    resp = MagicMock()
    resp.json.return_value = {"urls": [{"filename": "x.whl"}, {"filename": "x.tar.gz"}]}
    monkeypatch.setattr("pyscv.download_artifacts.httpx.get", lambda *a, **kw: resp)
    assert len(fetch_pypi_release_files(config, "1")) == 2


def test_fetch_pypi_propagates_http_error(monkeypatch, config):
    def explode(*_a, **_kw):
        raise httpx.HTTPStatusError(
            "boom", request=MagicMock(), response=MagicMock(status_code=404)
        )

    monkeypatch.setattr("pyscv.download_artifacts.httpx.get", explode)
    with pytest.raises(httpx.HTTPStatusError):
        fetch_pypi_release_files(config, "99")


# -- download_from_gh -----------------------------------------------------


def test_gh_dry_run_creates_nothing(config, no_network_gh):
    assert download_from_gh(config, "1.0.0", (".whl", ".tar.gz"), dry_run=True) == 0
    assert not config.dist_dir.exists()


@pytest.mark.parametrize(
    ("extensions", "expected_count"),
    [
        ((".whl",), 1),
        ((".tar.gz",), 1),
        ((".whl", ".tar.gz"), 2),
        ((".zip",), 0),
    ],
)
def test_gh_filters_by_extension(config, no_network_gh, fake_download, extensions, expected_count):
    assert download_from_gh(config, "1.0.0", extensions) == 0
    assert len(fake_download) == expected_count


def test_gh_skips_existing_without_force(config, no_network_gh, fake_download):
    config.dist_dir.mkdir(parents=True)
    (config.dist_dir / "pkg-1.0.0.whl").write_bytes(b"old")
    assert download_from_gh(config, "1.0.0", (".whl", ".tar.gz")) == 0
    assert len(fake_download) == 1
    assert fake_download[0][1].name == "pkg-1.0.0.tar.gz"


def test_gh_force_overwrites_existing(config, no_network_gh, fake_download):
    config.dist_dir.mkdir(parents=True)
    (config.dist_dir / "pkg-1.0.0.whl").write_bytes(b"old")
    assert download_from_gh(config, "1.0.0", (".whl", ".tar.gz"), force=True) == 0
    assert len(fake_download) == 2


def test_gh_verbose_logs_skips_and_progress(config, no_network_gh, fake_download):
    config.dist_dir.mkdir(parents=True)
    (config.dist_dir / "pkg-1.0.0.whl").write_bytes(b"old")
    assert download_from_gh(config, "1.0.0", (".whl", ".tar.gz"), verbose=True) == 0
    assert len(fake_download) == 1  # tar.gz only, whl skipped


def test_gh_download_failure_returns_1(config, no_network_gh, monkeypatch):
    def failing_download(_url, _dest):
        raise httpx.HTTPStatusError(
            "fail", request=MagicMock(), response=MagicMock(status_code=500)
        )

    monkeypatch.setattr("pyscv.download_artifacts.atomic_download", failing_download)
    assert download_from_gh(config, "1.0.0", (".whl",)) == 1


def test_gh_dry_run_shows_exists_status(config, no_network_gh):
    config.dist_dir.mkdir(parents=True)
    (config.dist_dir / "pkg-1.0.0.whl").write_bytes(b"old")
    assert download_from_gh(config, "1.0.0", (".whl", ".tar.gz"), dry_run=True) == 0


def test_gh_returns_1_on_fetch_error(monkeypatch, config):
    def explode(*_a, **_kw):
        raise httpx.HTTPStatusError(
            "nope", request=MagicMock(), response=MagicMock(status_code=404)
        )

    monkeypatch.setattr("pyscv.download_artifacts.fetch_gh_release_assets", explode)
    assert download_from_gh(config, "99", (".whl",)) == 1


# -- download_from_pypi ---------------------------------------------------


def test_pypi_dry_run_creates_nothing(config, no_network_pypi):
    assert download_from_pypi(config, "1.0.0", (".whl", ".tar.gz"), dry_run=True) == 0
    assert not config.dist_dir.exists()


@pytest.mark.parametrize(
    ("extensions", "expected_count"),
    [
        ((".whl",), 1),
        ((".tar.gz",), 1),
        ((".whl", ".tar.gz"), 2),
        ((".zip",), 0),
    ],
)
def test_pypi_filters_by_extension(
    config, no_network_pypi, fake_download, extensions, expected_count
):
    assert download_from_pypi(config, "1.0.0", extensions) == 0
    assert len(fake_download) == expected_count


def test_pypi_skips_existing_without_force(config, no_network_pypi, fake_download):
    config.dist_dir.mkdir(parents=True)
    (config.dist_dir / "pkg-1.0.0.whl").write_bytes(b"old")
    assert download_from_pypi(config, "1.0.0", (".whl", ".tar.gz")) == 0
    assert len(fake_download) == 1


def test_pypi_verbose_logs_skips_and_progress(config, no_network_pypi, fake_download):
    config.dist_dir.mkdir(parents=True)
    (config.dist_dir / "pkg-1.0.0.whl").write_bytes(b"old")
    assert download_from_pypi(config, "1.0.0", (".whl", ".tar.gz"), verbose=True) == 0
    assert len(fake_download) == 1


def test_pypi_verbose_logs_non_matching_extensions(config, no_network_pypi, fake_download):
    assert download_from_pypi(config, "1.0.0", (".zip",), verbose=True) == 0
    assert len(fake_download) == 0


def test_pypi_force_overwrites(config, no_network_pypi, fake_download):
    config.dist_dir.mkdir(parents=True)
    (config.dist_dir / "pkg-1.0.0.whl").write_bytes(b"old")
    assert download_from_pypi(config, "1.0.0", (".whl", ".tar.gz"), force=True) == 0
    assert len(fake_download) == 2


def test_pypi_download_failure_returns_1(config, no_network_pypi, monkeypatch):
    def failing_download(_url, _dest):
        raise httpx.HTTPStatusError(
            "fail", request=MagicMock(), response=MagicMock(status_code=500)
        )

    monkeypatch.setattr("pyscv.download_artifacts.atomic_download", failing_download)
    assert download_from_pypi(config, "1.0.0", (".whl",)) == 1


def test_pypi_dry_run_shows_exists_status(config, no_network_pypi):
    config.dist_dir.mkdir(parents=True)
    (config.dist_dir / "pkg-1.0.0.whl").write_bytes(b"old")
    assert download_from_pypi(config, "1.0.0", (".whl", ".tar.gz"), dry_run=True) == 0


def test_pypi_returns_1_on_fetch_error(monkeypatch, config):
    def explode(*_a, **_kw):
        raise httpx.HTTPStatusError(
            "nope", request=MagicMock(), response=MagicMock(status_code=404)
        )

    monkeypatch.setattr("pyscv.download_artifacts.fetch_pypi_release_files", explode)
    assert download_from_pypi(config, "99", (".whl",)) == 1


# -- atomic_download -------------------------------------------------------


def test_atomic_download_writes_complete_file(tmp_path, monkeypatch):
    dest = tmp_path / "output.whl"
    mock_stream = MagicMock()
    mock_stream.__enter__ = MagicMock(return_value=mock_stream)
    mock_stream.__exit__ = MagicMock(return_value=False)
    mock_stream.raise_for_status = MagicMock()
    mock_stream.iter_bytes.return_value = [b"chunk1", b"chunk2"]

    monkeypatch.setattr("pyscv.download_artifacts.httpx.stream", lambda *a, **kw: mock_stream)
    atomic_download("https://example.com/f.whl", dest)
    assert dest.read_bytes() == b"chunk1chunk2"


def test_atomic_download_no_partial_on_status_error(tmp_path, monkeypatch):
    dest = tmp_path / "output.whl"
    mock_stream = MagicMock()
    mock_stream.__enter__ = MagicMock(return_value=mock_stream)
    mock_stream.__exit__ = MagicMock(return_value=False)
    mock_stream.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500", request=MagicMock(), response=MagicMock(status_code=500)
    )

    monkeypatch.setattr("pyscv.download_artifacts.httpx.stream", lambda *_a, **_kw: mock_stream)
    with pytest.raises(httpx.HTTPStatusError):
        atomic_download("https://example.com/f.whl", dest)
    assert not dest.exists()


def test_atomic_download_no_partial_on_stream_error(tmp_path, monkeypatch):
    """If iter_bytes fails mid-write, dest must not exist."""
    dest = tmp_path / "output.whl"

    def exploding_iter():
        yield b"partial"
        raise ConnectionError

    mock_stream = MagicMock()
    mock_stream.__enter__ = MagicMock(return_value=mock_stream)
    mock_stream.__exit__ = MagicMock(return_value=False)
    mock_stream.raise_for_status = MagicMock()
    mock_stream.iter_bytes = exploding_iter

    monkeypatch.setattr("pyscv.download_artifacts.httpx.stream", lambda *_a, **_kw: mock_stream)
    with pytest.raises(ConnectionError):
        atomic_download("https://example.com/f.whl", dest)
    assert not dest.exists()
