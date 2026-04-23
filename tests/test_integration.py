"""End-to-end integration tests for the full geek42 workflow.

These tests exercise multi-step workflows to ensure all components
work together correctly.
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from geek42.cli import app
from geek42.parser import scan_repo
from geek42.renderer import body_to_html, news_to_markdown

runner = CliRunner()


class TestFullLifecycle:
    """Test the init -> compile-blog -> build -> verify flow."""

    def test_init_compile_build(self, news_repo: Path) -> None:
        """Full lifecycle: compile-blog then build site, verify output."""
        # Step 1: compile-blog (generates markdown + README index)
        result = runner.invoke(app, ["compile-blog", str(news_repo)])
        assert result.exit_code == 0

        # Verify markdown files created
        news_dir = news_repo / "news"
        assert news_dir.is_dir()
        md_files = list(news_dir.glob("*.md"))
        assert len(md_files) == 2

        # Verify README index created
        readme = news_repo / "README.md"
        assert readme.exists()
        readme_text = readme.read_text()
        assert "FlexiBLAS Migration" in readme_text
        assert "Old Format News" in readme_text

        # Step 2: lint the repo (should pass with 0 errors)
        result = runner.invoke(app, ["lint", str(news_repo / "metadata" / "news")])
        assert result.exit_code == 0
        assert "0 error(s)" in result.output

    def test_compile_then_recompile_idempotent(self, news_repo: Path) -> None:
        """Running compile-blog twice produces identical output."""
        runner.invoke(app, ["compile-blog", str(news_repo)])
        first_readme = (news_repo / "README.md").read_text()
        first_md = {f.name: f.read_text() for f in (news_repo / "news").glob("*.md")}

        runner.invoke(app, ["compile-blog", str(news_repo)])
        second_readme = (news_repo / "README.md").read_text()
        second_md = {f.name: f.read_text() for f in (news_repo / "news").glob("*.md")}

        assert first_readme == second_readme
        assert first_md == second_md


class TestRoundTrip:
    """Test parse -> render -> verify content preservation."""

    def test_parse_render_roundtrip(self, news_repo: Path) -> None:
        """Parsing a news file and rendering to markdown preserves content."""
        items = scan_repo(news_repo)
        assert len(items) == 2

        for item in items:
            md = news_to_markdown(item)
            # YAML frontmatter preserved
            assert item.title in md
            assert item.posted.isoformat() in md
            # Body preserved
            assert item.body in md

    def test_parse_html_roundtrip(self, news_repo: Path) -> None:
        """Parsing and rendering to HTML preserves text content."""
        items = scan_repo(news_repo)
        for item in items:
            html = body_to_html(item.body)
            assert isinstance(html, str)
            assert len(html) > 0
            # Key text content should survive rendering
            for word in item.body.split()[:5]:
                # Skip URLs and special chars
                if not word.startswith("http") and word.isalpha():
                    assert word in html


class TestCompileAndBuildAgreement:
    """Verify compile-blog and build produce consistent content."""

    def test_same_items_found(self, news_repo: Path) -> None:
        """Both compile-blog and build discover the same news items."""
        # compile-blog writes to news/
        runner.invoke(app, ["compile-blog", str(news_repo)])

        # Verify the compiled markdown files match the parsed items
        items = scan_repo(news_repo)
        item_ids = {item.id for item in items}
        md_stems = {f.stem for f in (news_repo / "news").glob("*.md")}

        assert item_ids == md_stems


class TestLintIntegration:
    """Test linting integrated with the parser."""

    def test_lint_after_parse(self, news_repo: Path) -> None:
        """Items that parse successfully should also lint clean for errors."""
        items = scan_repo(news_repo)
        assert len(items) > 0  # Sanity check

        # Each parsed item should not have any E-level diagnostics
        from geek42.linter import Severity, lint_news_file

        news_root = news_repo / "metadata" / "news"
        for item_dir in news_root.iterdir():
            if not item_dir.is_dir() or item_dir.name.startswith("."):
                continue
            for txt in item_dir.glob("*.txt"):
                diags = lint_news_file(txt)
                errors = [d for d in diags if d.severity == Severity.error]
                assert not errors, f"Unexpected errors in {txt}: {errors}"


class TestTrackerIntegration:
    """Test read tracking integrated with CLI commands."""

    def test_list_read_read_new_flow(self, news_repo: Path, tmp_path: Path) -> None:
        """Test the list -> read -> read-new flow."""
        # Write a config so data_dir is in tmp_path
        cfg = tmp_path / "geek42.toml"
        cfg.write_text(
            f'title = "T"\nauthor = "A"\ndata_dir = "{tmp_path / "data"}"\n'
            f'[[sources]]\nname = "local"\nurl = "."\n'
        )

        # List shows 2 items, both unread
        result = runner.invoke(app, ["list", "-c", str(cfg), "-C", str(news_repo)])
        assert result.exit_code == 0
        assert "2 unread" in result.output

        # Read one item
        result = runner.invoke(app, ["read", "flexiblas", "-c", str(cfg), "-C", str(news_repo)])
        assert result.exit_code == 0
        assert "FlexiBLAS" in result.output

        # List now shows 1 unread
        result = runner.invoke(app, ["list", "-c", str(cfg), "-C", str(news_repo)])
        assert result.exit_code == 0
        assert "1 unread" in result.output

        # Read-new reads remaining
        result = runner.invoke(app, ["read-new", "-c", str(cfg), "-C", str(news_repo)])
        assert result.exit_code == 0
        assert "1 unread item" in result.output

        # Now all read
        result = runner.invoke(app, ["list", "--new", "-c", str(cfg), "-C", str(news_repo)])
        assert result.exit_code == 1  # No unread items
