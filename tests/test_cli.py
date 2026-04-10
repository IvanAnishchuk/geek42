"""Tests for the CLI interface."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from geek42.cli import app
from geek42.models import NewsSource, SiteConfig
from geek42.site import pull_source

runner = CliRunner()


def _write_config(path: Path, site_config: SiteConfig) -> None:
    """Write a TOML config file from a SiteConfig."""
    lines = [
        f'title = "{site_config.title}"',
        f'description = "{site_config.description}"',
        f'base_url = "{site_config.base_url}"',
        f'author = "{site_config.author}"',
        f'output_dir = "{site_config.output_dir}"',
        f'data_dir = "{site_config.data_dir}"',
        f'language = "{site_config.language}"',
        "",
    ]
    if site_config.sources:
        for source in site_config.sources:
            lines += [
                "[[sources]]",
                f'name = "{source.name}"',
                f'url = "{source.url}"',
                f'branch = "{source.branch}"',
                "",
            ]
    else:
        lines.append("sources = []")
    path.write_text("\n".join(lines), encoding="utf-8")


# -- init --


def test_init_creates_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert (tmp_path / "geek42.toml").exists()
    content = (tmp_path / "geek42.toml").read_text()
    assert "[[sources]]" in content
    assert 'url = "."' in content


def test_init_refuses_overwrite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "geek42.toml").write_text("existing")
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert (tmp_path / "geek42.toml").read_text() == "existing"


def test_init_custom_path(tmp_path: Path) -> None:
    cfg_path = tmp_path / "custom.toml"
    result = runner.invoke(app, ["init", "--config", str(cfg_path)])
    assert result.exit_code == 0
    assert cfg_path.exists()


# -- pull --


def test_pull(tmp_path: Path, site_config: SiteConfig) -> None:
    cfg_path = tmp_path / "geek42.toml"
    _write_config(cfg_path, site_config)
    result = runner.invoke(app, ["pull", "--config", str(cfg_path)])
    assert result.exit_code == 0
    assert "OK" in result.output


def test_pull_bad_url(tmp_path: Path) -> None:
    cfg = SiteConfig(
        sources=[NewsSource(name="bad", url="/nonexistent/repo.git", branch="main")],
        data_dir=tmp_path / "data",
    )
    cfg_path = tmp_path / "geek42.toml"
    _write_config(cfg_path, cfg)
    result = runner.invoke(app, ["pull", "--config", str(cfg_path)])
    # Should not crash, just report error
    assert result.exit_code == 0


# -- build --


def test_build_with_pull(tmp_path: Path, site_config: SiteConfig) -> None:
    cfg_path = tmp_path / "geek42.toml"
    _write_config(cfg_path, site_config)
    result = runner.invoke(app, ["build", "--config", str(cfg_path)])
    assert result.exit_code == 0
    assert "Done" in result.output
    assert site_config.output_dir.exists()


def test_build_no_pull(tmp_path: Path, site_config: SiteConfig) -> None:
    cfg_path = tmp_path / "geek42.toml"
    _write_config(cfg_path, site_config)
    # Pre-pull so repos exist
    for source in site_config.sources:
        pull_source(source, site_config.data_dir)
    result = runner.invoke(app, ["build", "--no-pull", "--config", str(cfg_path)])
    assert result.exit_code == 0
    assert "Done" in result.output


def test_build_no_items_exits_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    cfg = SiteConfig(
        sources=[],
        data_dir=tmp_path / "data",
        output_dir=tmp_path / "out",
    )
    cfg_path = tmp_path / "geek42.toml"
    _write_config(cfg_path, cfg)
    result = runner.invoke(app, ["build", "--no-pull", "--config", str(cfg_path)])
    assert result.exit_code == 1


# -- list --


def test_list_news(tmp_path: Path, site_config: SiteConfig) -> None:
    cfg_path = tmp_path / "geek42.toml"
    _write_config(cfg_path, site_config)
    for source in site_config.sources:
        pull_source(source, site_config.data_dir)
    result = runner.invoke(app, ["list", "--config", str(cfg_path)])
    assert result.exit_code == 0
    assert "FlexiBLAS" in result.output


def test_list_filter_source(tmp_path: Path, site_config: SiteConfig) -> None:
    cfg_path = tmp_path / "geek42.toml"
    _write_config(cfg_path, site_config)
    for source in site_config.sources:
        pull_source(source, site_config.data_dir)
    result = runner.invoke(app, ["list", "--source", "nonexistent", "--config", str(cfg_path)])
    assert result.exit_code == 1


def test_list_with_limit(tmp_path: Path, site_config: SiteConfig) -> None:
    cfg_path = tmp_path / "geek42.toml"
    _write_config(cfg_path, site_config)
    for source in site_config.sources:
        pull_source(source, site_config.data_dir)
    result = runner.invoke(app, ["list", "--limit", "1", "--config", str(cfg_path)])
    assert result.exit_code == 0


def test_list_no_items(tmp_path: Path) -> None:
    cfg = SiteConfig(sources=[], data_dir=tmp_path / "data")
    cfg_path = tmp_path / "geek42.toml"
    _write_config(cfg_path, cfg)
    result = runner.invoke(app, ["list", "--config", str(cfg_path)])
    assert result.exit_code == 1


# -- read --


def test_read_item(tmp_path: Path, site_config: SiteConfig) -> None:
    cfg_path = tmp_path / "geek42.toml"
    _write_config(cfg_path, site_config)
    for source in site_config.sources:
        pull_source(source, site_config.data_dir)
    result = runner.invoke(app, ["read", "flexiblas", "--config", str(cfg_path)])
    assert result.exit_code == 0
    assert "FlexiBLAS" in result.output
    assert "Sam James" in result.output
    assert "packages:" in result.output
    assert "amd64" in result.output


def test_read_marks_as_read(tmp_path: Path, site_config: SiteConfig) -> None:
    cfg_path = tmp_path / "geek42.toml"
    _write_config(cfg_path, site_config)
    for source in site_config.sources:
        pull_source(source, site_config.data_dir)

    runner.invoke(app, ["read", "flexiblas", "--config", str(cfg_path)])

    read_file = site_config.data_dir / "read.txt"
    assert read_file.exists()
    assert "flexiblas-migration" in read_file.read_text()


def test_read_item_not_found(tmp_path: Path, site_config: SiteConfig) -> None:
    cfg_path = tmp_path / "geek42.toml"
    _write_config(cfg_path, site_config)
    for source in site_config.sources:
        pull_source(source, site_config.data_dir)
    result = runner.invoke(app, ["read", "nonexistent-item", "--config", str(cfg_path)])
    assert result.exit_code == 1


# -- read-new --


def test_read_new_shows_unread(tmp_path: Path, site_config: SiteConfig) -> None:
    cfg_path = tmp_path / "geek42.toml"
    _write_config(cfg_path, site_config)
    for source in site_config.sources:
        pull_source(source, site_config.data_dir)

    result = runner.invoke(app, ["read-new", "--config", str(cfg_path)])
    assert result.exit_code == 0
    assert "2 unread" in result.output
    assert "FlexiBLAS" in result.output
    assert "Old Format" in result.output


def test_read_new_marks_all_read(tmp_path: Path, site_config: SiteConfig) -> None:
    cfg_path = tmp_path / "geek42.toml"
    _write_config(cfg_path, site_config)
    for source in site_config.sources:
        pull_source(source, site_config.data_dir)

    runner.invoke(app, ["read-new", "--config", str(cfg_path)])

    # Second call should have nothing unread
    result = runner.invoke(app, ["read-new", "--config", str(cfg_path)])
    assert result.exit_code == 0
    assert "No unread" in result.output


def test_read_new_nothing_unread(tmp_path: Path, site_config: SiteConfig) -> None:
    cfg_path = tmp_path / "geek42.toml"
    _write_config(cfg_path, site_config)
    for source in site_config.sources:
        pull_source(source, site_config.data_dir)

    # Mark everything as read first
    from geek42.tracker import ReadTracker

    tracker = ReadTracker(site_config.data_dir)
    tracker.mark_read("2025-11-30-flexiblas-migration", "2017-03-02-old-format")

    result = runner.invoke(app, ["read-new", "--config", str(cfg_path)])
    assert result.exit_code == 0
    assert "No unread" in result.output


# -- list --new --


def test_list_new_flag(tmp_path: Path, site_config: SiteConfig) -> None:
    cfg_path = tmp_path / "geek42.toml"
    _write_config(cfg_path, site_config)
    for source in site_config.sources:
        pull_source(source, site_config.data_dir)

    # All items are unread initially
    result = runner.invoke(app, ["list", "--new", "--config", str(cfg_path)])
    assert result.exit_code == 0
    assert "FlexiBLAS" in result.output


def test_list_new_after_reading(tmp_path: Path, site_config: SiteConfig) -> None:
    cfg_path = tmp_path / "geek42.toml"
    _write_config(cfg_path, site_config)
    for source in site_config.sources:
        pull_source(source, site_config.data_dir)

    # Read one item
    runner.invoke(app, ["read", "flexiblas", "--config", str(cfg_path)])

    # List --new should only show the other
    result = runner.invoke(app, ["list", "--new", "--config", str(cfg_path)])
    assert result.exit_code == 0
    assert "FlexiBLAS" not in result.output
    assert "Old Format" in result.output


def test_list_shows_unread_marker(tmp_path: Path, site_config: SiteConfig) -> None:
    cfg_path = tmp_path / "geek42.toml"
    _write_config(cfg_path, site_config)
    for source in site_config.sources:
        pull_source(source, site_config.data_dir)

    result = runner.invoke(app, ["list", "--config", str(cfg_path)])
    assert result.exit_code == 0
    assert "unread" in result.output


# -- _load_config --


def test_load_config_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When no config file exists, defaults are used."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["list"])
    # Will fail with exit 1 (no items) but should not crash
    assert result.exit_code == 1


# -- lint --

_VALID_NEWS = (
    "Title: Test\nAuthor: Dev <d@g.org>\n"
    "Posted: 2025-01-01\nRevision: 1\nNews-Item-Format: 2.0\n\nBody text."
)


def test_lint_file_clean(tmp_path: Path) -> None:
    d = tmp_path / "2025-01-01-test"
    d.mkdir()
    f = d / "2025-01-01-test.en.txt"
    f.write_text(_VALID_NEWS)
    result = runner.invoke(app, ["lint", str(f)])
    assert result.exit_code == 0
    assert "0 error(s)" in result.output


def test_lint_file_with_errors(tmp_path: Path) -> None:
    d = tmp_path / "2025-01-01-bad"
    d.mkdir()
    f = d / "2025-01-01-bad.en.txt"
    f.write_text("Title: Bad\n\n")  # missing headers + empty body
    result = runner.invoke(app, ["lint", str(f)])
    assert result.exit_code == 1


def test_lint_directory(news_repo: Path) -> None:
    result = runner.invoke(app, ["lint", str(news_repo)])
    assert result.exit_code == 0 or result.exit_code == 1
    assert "error(s)" in result.output


def test_lint_strict_fails_on_warnings(tmp_path: Path) -> None:
    d = tmp_path / "2025-01-01-warn"
    d.mkdir()
    f = d / "2025-01-01-warn.en.txt"
    # Valid but with a long body line (>72 chars) -> warning
    long = "x" * 80
    f.write_text(f"{_VALID_NEWS.rstrip()}\n{long}\n")
    result = runner.invoke(app, ["lint", "--strict", str(f)])
    assert result.exit_code == 1


def test_lint_nonexistent_path(tmp_path: Path) -> None:
    result = runner.invoke(app, ["lint", str(tmp_path / "nope")])
    assert result.exit_code == 1


# -- new --


def _fake_editor_that_fills_template(path_str: str) -> int:
    """Simulate an editor that fills in the template with valid content."""
    from datetime import date as d

    p = Path(path_str)
    today = d.today().isoformat()
    p.write_text(
        f"Title: My Test News\n"
        f"Author: Test Dev <test@example.org>\n"
        f"Posted: {today}\n"
        f"Revision: 1\n"
        f"News-Item-Format: 2.0\n"
        f"\n"
        f"This is my new news item body.\n",
        encoding="utf-8",
    )
    return 0


def test_new_creates_item(
    tmp_path: Path, site_config: SiteConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path = tmp_path / "geek42.toml"
    _write_config(cfg_path, site_config)
    for source in site_config.sources:
        pull_source(source, site_config.data_dir)

    # Monkeypatch open_in_editor to simulate editing
    import geek42.compose as compose_mod

    def mock_editor(path: Path, editor: str) -> int:
        return _fake_editor_that_fills_template(str(path))

    monkeypatch.setattr(compose_mod, "open_in_editor", mock_editor)

    result = runner.invoke(app, ["new", "--config", str(cfg_path)])
    assert result.exit_code == 0
    assert "Created" in result.output


def test_new_editor_failure(
    tmp_path: Path, site_config: SiteConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path = tmp_path / "geek42.toml"
    _write_config(cfg_path, site_config)
    for source in site_config.sources:
        pull_source(source, site_config.data_dir)

    import geek42.compose as compose_mod

    def mock_editor(path: Path, editor: str) -> int:
        return 1

    monkeypatch.setattr(compose_mod, "open_in_editor", mock_editor)

    result = runner.invoke(app, ["new", "--config", str(cfg_path)])
    assert result.exit_code == 1


def test_new_no_sources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = SiteConfig(sources=[], data_dir=tmp_path / "data")
    cfg_path = tmp_path / "geek42.toml"
    _write_config(cfg_path, cfg)
    result = runner.invoke(app, ["new", "--config", str(cfg_path)])
    assert result.exit_code == 1


def test_new_source_not_pulled(tmp_path: Path, site_config: SiteConfig) -> None:
    # Don't pull — repo dir won't exist
    cfg_path = tmp_path / "geek42.toml"
    _write_config(cfg_path, site_config)
    result = runner.invoke(app, ["new", "--config", str(cfg_path)])
    assert result.exit_code == 1


def test_new_unknown_source(tmp_path: Path, site_config: SiteConfig) -> None:
    cfg_path = tmp_path / "geek42.toml"
    _write_config(cfg_path, site_config)
    result = runner.invoke(app, ["new", "--source", "nonexistent", "--config", str(cfg_path)])
    assert result.exit_code == 1


# -- revise --


def test_revise_bumps_revision(
    tmp_path: Path, site_config: SiteConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path = tmp_path / "geek42.toml"
    _write_config(cfg_path, site_config)
    for source in site_config.sources:
        pull_source(source, site_config.data_dir)

    import geek42.compose as compose_mod

    def mock_editor(path: Path, editor: str) -> int:
        # Just accept the bumped revision as-is (it's already valid)
        return 0

    monkeypatch.setattr(compose_mod, "open_in_editor", mock_editor)

    result = runner.invoke(app, ["revise", "flexiblas", "--config", str(cfg_path)])
    assert result.exit_code == 0
    assert "Updated" in result.output

    # Verify revision was bumped in the actual file
    repo_dir = site_config.data_dir / "repos" / site_config.sources[0].name
    item_file = (
        repo_dir / "2025-11-30-flexiblas-migration" / "2025-11-30-flexiblas-migration.en.txt"
    )
    content = item_file.read_text()
    assert "Revision: 3" in content  # was 2 in fixture


def test_revise_item_not_found(tmp_path: Path, site_config: SiteConfig) -> None:
    cfg_path = tmp_path / "geek42.toml"
    _write_config(cfg_path, site_config)
    for source in site_config.sources:
        pull_source(source, site_config.data_dir)
    result = runner.invoke(app, ["revise", "nonexistent-item", "--config", str(cfg_path)])
    assert result.exit_code == 1


# -- local source tests --


def test_new_local_source(tmp_path: Path, news_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """geek42 new works with a local source (no pull required)."""
    monkeypatch.chdir(news_repo)
    cfg = SiteConfig(
        sources=[NewsSource(name="local", url=".")],
        data_dir=news_repo / ".geek42",
    )
    cfg_path = news_repo / "geek42.toml"
    _write_config(cfg_path, cfg)

    import geek42.compose as compose_mod

    def mock_editor(path: Path, editor: str) -> int:
        return _fake_editor_that_fills_template(str(path))

    monkeypatch.setattr(compose_mod, "open_in_editor", mock_editor)

    result = runner.invoke(app, ["new", "--config", str(cfg_path)])
    assert result.exit_code == 0
    assert "Created" in result.output

    # Item should be placed in the current directory, not .geek42/repos/
    from datetime import date

    today = date.today().isoformat()
    item_dir = news_repo / f"{today}-my-test-news"
    assert item_dir.is_dir()


def test_build_local_source(news_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """geek42 build --no-pull works with a local source."""
    monkeypatch.chdir(news_repo)
    cfg = SiteConfig(
        sources=[NewsSource(name="local", url=".")],
        output_dir=news_repo / "_site",
        data_dir=news_repo / ".geek42",
    )
    cfg_path = news_repo / "geek42.toml"
    _write_config(cfg_path, cfg)

    result = runner.invoke(app, ["build", "--no-pull", "--config", str(cfg_path)])
    assert result.exit_code == 0
    assert "Done" in result.output
    assert (news_repo / "_site" / "index.html").exists()


def test_pull_skips_local(news_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """geek42 pull silently skips local sources."""
    monkeypatch.chdir(news_repo)
    cfg = SiteConfig(
        sources=[NewsSource(name="local", url=".")],
        data_dir=news_repo / ".geek42",
    )
    cfg_path = news_repo / "geek42.toml"
    _write_config(cfg_path, cfg)

    result = runner.invoke(app, ["pull", "--config", str(cfg_path)])
    assert result.exit_code == 0
    # Should not attempt any git operations
    assert "Error" not in result.output


def test_revise_editor_failure(
    tmp_path: Path, site_config: SiteConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path = tmp_path / "geek42.toml"
    _write_config(cfg_path, site_config)
    for source in site_config.sources:
        pull_source(source, site_config.data_dir)

    import geek42.compose as compose_mod

    def mock_editor(path: Path, editor: str) -> int:
        return 1

    monkeypatch.setattr(compose_mod, "open_in_editor", mock_editor)

    result = runner.invoke(app, ["revise", "flexiblas", "--config", str(cfg_path)])
    assert result.exit_code == 1
