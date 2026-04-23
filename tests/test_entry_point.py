"""Tests for the geek42 entry point and error boundary."""

from __future__ import annotations

from typer.testing import CliRunner

from geek42.cli import app

runner = CliRunner()


def test_help_output() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "GLEP 42" in result.output


def test_main_module_exists() -> None:
    from importlib.util import find_spec

    spec = find_spec("geek42.__main__")
    assert spec is not None


def test_console_script(script_runner) -> None:  # noqa: ANN001
    """Verify the installed ``geek42`` entry point works."""
    result = script_runner.run(["geek42", "--help"])
    assert result.success
    assert "GLEP 42" in result.stdout


def test_error_boundary_catches_geek42_error() -> None:
    """Verify main() catches Geek42Error and exits cleanly."""
    result = runner.invoke(app, ["read", "nonexistent-item-that-does-not-exist-xyz"])
    assert result.exit_code == 1
