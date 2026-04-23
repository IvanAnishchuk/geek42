"""Tests for CLI commands that previously had zero coverage.

Covers: compile-blog, lint (directory mode), sign, verify, commit, push,
deploy-status.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from geek42.cli import app

runner = CliRunner()


# -- compile-blog --


class TestCompileBlog:
    def test_creates_markdown(self, news_repo: Path) -> None:
        result = runner.invoke(app, ["compile-blog", str(news_repo)])
        assert result.exit_code == 0
        assert "Compiled" in result.output
        assert "2" in result.output  # 2 news items
        # Verify markdown files were created
        news_dir = news_repo / "news"
        md_files = list(news_dir.glob("*.md"))
        assert len(md_files) == 2

    def test_empty_repo(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["compile-blog", str(tmp_path)])
        assert result.exit_code == 0
        assert "No news items found" in result.output

    def test_custom_dirs(self, news_repo: Path) -> None:
        result = runner.invoke(
            app,
            [
                "compile-blog",
                str(news_repo),
                "--news-dir",
                "posts",
                "--readme",
                "INDEX.md",
            ],
        )
        assert result.exit_code == 0
        assert (news_repo / "posts").is_dir()
        assert (news_repo / "INDEX.md").exists()


# -- lint (supplement existing tests) --


class TestLintExtended:
    def test_lint_directory(self, news_repo: Path) -> None:
        result = runner.invoke(app, ["lint", str(news_repo / "metadata" / "news")])
        assert result.exit_code == 0
        assert "error(s)" in result.output

    def test_lint_strict_on_clean_file(self, news_repo: Path) -> None:
        # The sample format 2.0 file may have warnings but no errors
        f = (
            news_repo
            / "metadata"
            / "news"
            / "2025-11-30-flexiblas-migration"
            / "2025-11-30-flexiblas-migration.en.txt"
        )
        result = runner.invoke(app, ["lint", str(f)])
        assert "0 error(s)" in result.output

    def test_lint_nonexistent_path(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["lint", str(tmp_path / "nope.txt")])
        assert result.exit_code == 1
        assert "Not found" in result.output


# -- sign --


class TestSign:
    def test_sign_success(self, news_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        with patch("geek42.manifest.generate_manifest", return_value=True) as mock_gen:
            monkeypatch.chdir(news_repo)
            result = runner.invoke(app, ["sign"])
            assert result.exit_code == 0
            assert "Manifest updated" in result.output
            mock_gen.assert_called_once()

    def test_sign_with_key(self, news_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        with patch("geek42.manifest.generate_manifest", return_value=True):
            monkeypatch.chdir(news_repo)
            result = runner.invoke(app, ["sign", "--key", "0xDEADBEEF"])
            assert result.exit_code == 0
            assert "signed" in result.output
            assert "0xDEADBEEF" in result.output

    def test_sign_failure(self, news_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        with patch("geek42.manifest.generate_manifest", return_value=False):
            monkeypatch.chdir(news_repo)
            result = runner.invoke(app, ["sign"])
            assert result.exit_code == 1
            assert "failed" in result.output

    def test_sign_key_from_config(self, news_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # Write config with signing_key
        cfg = news_repo / "geek42.toml"
        cfg.write_text(
            'title = "T"\nauthor = "A"\nsigning_key = "0xCONFIG"\n'
            '[[sources]]\nname = "local"\nurl = "."\n'
        )
        with patch("geek42.manifest.generate_manifest", return_value=True) as mock_gen:
            monkeypatch.chdir(news_repo)
            result = runner.invoke(app, ["sign"])
            assert result.exit_code == 0
            assert "0xCONFIG" in result.output
            # Verify the signing_key was passed to generate_manifest
            call_kwargs = mock_gen.call_args
            assert call_kwargs[1]["signing_key"] == "0xCONFIG"


# -- verify --


class TestVerify:
    def test_verify_no_manifest(self, news_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(news_repo)
        # No Manifest file exists, should exit 0 with message
        result = runner.invoke(app, ["verify"])
        assert result.exit_code == 0
        assert "No Manifest found" in result.output

    def test_verify_success(self, news_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # Create a Manifest file so the check passes
        (news_repo / "Manifest").write_text("dummy")
        monkeypatch.chdir(news_repo)
        with patch("geek42.manifest.verify_manifest", return_value=[]):
            result = runner.invoke(app, ["verify"])
            assert result.exit_code == 0
            assert "Verified" in result.output

    def test_verify_errors(self, news_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        (news_repo / "Manifest").write_text("dummy")
        monkeypatch.chdir(news_repo)
        with patch(
            "geek42.manifest.verify_manifest",
            return_value=["ERROR: hash mismatch for foo.txt"],
        ):
            result = runner.invoke(app, ["verify"])
            assert result.exit_code == 1


# -- commit --


class TestCommit:
    def test_commit_no_changes(self, git_news_repo: Path) -> None:
        result = runner.invoke(app, ["commit", "-C", str(git_news_repo)])
        assert result.exit_code == 0
        assert "Nothing to commit" in result.output

    def test_commit_auto_message(self, git_news_repo: Path) -> None:
        # Add a new news item to trigger auto-message generation
        new_dir = git_news_repo / "metadata" / "news" / "2026-04-01-test-commit"
        new_dir.mkdir()
        (new_dir / "2026-04-01-test-commit.en.txt").write_text(
            "Title: Test Commit\nAuthor: Dev <d@g.org>\nPosted: 2026-04-01\n"
            "Revision: 1\nNews-Item-Format: 2.0\n\nBody."
        )
        # Mock generate_manifest so we don't need gemato
        with patch("geek42.manifest.generate_manifest"):
            result = runner.invoke(app, ["commit", "-C", str(git_news_repo)])
            assert result.exit_code == 0
            assert "Committed" in result.output
            assert "feat(news)" in result.output

    def test_commit_custom_message(self, git_news_repo: Path) -> None:
        new_dir = git_news_repo / "metadata" / "news" / "2026-04-02-custom"
        new_dir.mkdir()
        (new_dir / "2026-04-02-custom.en.txt").write_text(
            "Title: Custom\nAuthor: Dev <d@g.org>\nPosted: 2026-04-02\n"
            "Revision: 1\nNews-Item-Format: 2.0\n\nBody."
        )
        with patch("geek42.manifest.generate_manifest"):
            result = runner.invoke(app, ["commit", "-C", str(git_news_repo), "-m", "my custom msg"])
            assert result.exit_code == 0
            assert "my custom msg" in result.output


# -- push --


class TestPush:
    def test_push_success(self, git_news_repo: Path) -> None:
        with patch("geek42.cli._git") as mock_git:
            mock_git.return_value = MagicMock(returncode=0)
            result = runner.invoke(app, ["push", "-C", str(git_news_repo)])
            assert result.exit_code == 0

    def test_push_failure(self, git_news_repo: Path) -> None:
        with patch("geek42.cli._git") as mock_git:
            mock_git.return_value = MagicMock(returncode=1)
            result = runner.invoke(app, ["push", "-C", str(git_news_repo)])
            assert result.exit_code == 1


# -- deploy-status --


class TestDeployStatus:
    def test_no_gh(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        with patch("geek42.cli.shutil.which", return_value=None):
            result = runner.invoke(app, ["deploy-status"])
            assert result.exit_code == 1
            assert "gh CLI not found" in result.output

    def test_no_repo(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        mock_result = MagicMock(returncode=1, stdout="", stderr="")
        with (
            patch("geek42.cli.shutil.which", return_value="/usr/bin/gh"),
            patch("geek42.cli.subprocess.run", return_value=mock_result),
        ):
            result = runner.invoke(app, ["deploy-status"])
            assert result.exit_code == 1
            assert "Could not detect" in result.output

    def test_pages_configured(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        import json

        def mock_run(args: list[str], **kwargs: object) -> MagicMock:
            cmd = " ".join(args)
            r = MagicMock()
            r.returncode = 0
            if "nameWithOwner" in cmd:
                r.stdout = "owner/repo\n"
            elif "/pages/builds" in cmd:
                r.stdout = json.dumps(
                    [
                        {
                            "status": "built",
                            "created_at": "2026-04-01T12:00:00Z",
                            "commit": "abc1234def",
                        }
                    ]
                )
            elif "/pages" in cmd:
                r.stdout = json.dumps(
                    {"html_url": "https://owner.github.io/repo", "status": "built"}
                )
            elif "run" in cmd:
                r.stdout = json.dumps(
                    [
                        {
                            "conclusion": "success",
                            "displayTitle": "Test CI",
                            "headSha": "abc1234def5678",
                        }
                    ]
                )
            else:
                r.stdout = ""
            return r

        with (
            patch("geek42.cli.shutil.which", return_value="/usr/bin/gh"),
            patch("geek42.cli.subprocess.run", side_effect=mock_run),
        ):
            result = runner.invoke(app, ["deploy-status"])
            assert result.exit_code == 0
            assert "owner/repo" in result.output
            assert "Pages" in result.output

    def test_no_pages(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        import json

        def mock_run(args: list[str], **kwargs: object) -> MagicMock:
            cmd = " ".join(args)
            r = MagicMock()
            if "nameWithOwner" in cmd:
                r.returncode = 0
                r.stdout = "owner/repo\n"
            elif "/pages" in cmd:
                r.returncode = 1
                r.stdout = ""
            elif "run" in cmd:
                r.returncode = 0
                r.stdout = json.dumps([])
            else:
                r.returncode = 0
                r.stdout = ""
            return r

        with (
            patch("geek42.cli.shutil.which", return_value="/usr/bin/gh"),
            patch("geek42.cli.subprocess.run", side_effect=mock_run),
        ):
            result = runner.invoke(app, ["deploy-status"])
            assert result.exit_code == 0
            assert "not configured" in result.output


# -- init (scaffold path, non-bare) --


class TestInitScaffold:
    def test_init_scaffold(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["init", "-C", str(tmp_path)])
        assert result.exit_code == 0
        assert "file(s) created" in result.output
        assert (tmp_path / "geek42.toml").exists()

    def test_init_scaffold_existing(self, tmp_path: Path) -> None:
        # Run twice — second time should say "already exist"
        runner.invoke(app, ["init", "-C", str(tmp_path)])
        result = runner.invoke(app, ["init", "-C", str(tmp_path)])
        assert "already exist" in result.output.lower() or "Already exist" in result.output
