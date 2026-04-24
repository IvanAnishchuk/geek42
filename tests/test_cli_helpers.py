"""Tests for CLI helper functions (_detect_news_changes, _news_commit_message, _git)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from geek42.cli import _detect_news_changes, _git, _news_commit_message
from geek42.errors import GitNotFoundError

# -- _news_commit_message (pure logic, no mocking needed) --


class TestNewsCommitMessage:
    def test_single_add(self) -> None:
        msg = _news_commit_message(["2025-01-01-new-thing"], [], [])
        assert msg == "feat(news): add 2025-01-01-new-thing"

    def test_single_modify(self) -> None:
        msg = _news_commit_message([], ["2025-01-01-revised"], [])
        assert msg == "fix(news): revise 2025-01-01-revised"

    def test_single_delete(self) -> None:
        msg = _news_commit_message([], [], ["2025-01-01-removed"])
        assert msg == "chore(news): remove 2025-01-01-removed"

    def test_multiple_adds(self) -> None:
        msg = _news_commit_message(["a", "b", "c"], [], [])
        assert msg == "feat(news): add 3 item(s)"

    def test_mixed_changes(self) -> None:
        msg = _news_commit_message(["a"], ["b"], ["c"])
        assert msg == "feat(news): add 1, revise 1, remove 1 item(s)"

    def test_add_and_modify(self) -> None:
        msg = _news_commit_message(["a", "b"], ["c"], [])
        assert msg == "feat(news): add 2, revise 1 item(s)"

    def test_modify_and_delete(self) -> None:
        msg = _news_commit_message([], ["a"], ["b", "c"])
        assert msg == "feat(news): revise 1, remove 2 item(s)"


# -- _git --


class TestGit:
    def test_git_not_found_raises(self, tmp_path: Path) -> None:
        with patch("geek42.cli.shutil.which", return_value=None), pytest.raises(GitNotFoundError):
            _git(["status"], tmp_path)

    def test_git_runs_command(self, tmp_path: Path) -> None:
        result = _git(["status"], tmp_path, capture_output=True)
        # git status on a non-repo may fail, but it should not raise
        assert result.returncode is not None


# -- _detect_news_changes --


class TestDetectNewsChanges:
    def test_added_items(self, git_news_repo: Path) -> None:
        # Create a new untracked news item
        new_dir = git_news_repo / "metadata" / "news" / "2026-01-01-brand-new"
        new_dir.mkdir()
        (new_dir / "2026-01-01-brand-new.en.txt").write_text(
            "Title: Brand New\nAuthor: Dev <d@g.org>\nPosted: 2026-01-01\n"
            "Revision: 1\nNews-Item-Format: 2.0\n\nNew item body."
        )

        added, modified, deleted = _detect_news_changes(git_news_repo)
        assert "2026-01-01-brand-new" in added
        assert not modified
        assert not deleted

    def test_deleted_items(self, git_news_repo: Path) -> None:
        import subprocess

        # Remove a committed news item
        item_dir = git_news_repo / "metadata" / "news" / "2025-11-30-flexiblas-migration"
        subprocess.run(
            ["git", "-C", str(git_news_repo), "rm", "-rf", str(item_dir)],
            check=True,
            capture_output=True,
        )

        added, modified, deleted = _detect_news_changes(git_news_repo)
        assert "2025-11-30-flexiblas-migration" in deleted
        assert not added

    def test_modified_items(self, git_news_repo: Path) -> None:
        # Modify an existing tracked news file
        item_file = (
            git_news_repo
            / "metadata"
            / "news"
            / "2025-11-30-flexiblas-migration"
            / "2025-11-30-flexiblas-migration.en.txt"
        )
        item_file.write_text(item_file.read_text() + "\nAppended content.")
        import subprocess

        subprocess.run(
            ["git", "-C", str(git_news_repo), "add", str(item_file)],
            check=True,
            capture_output=True,
        )

        added, modified, deleted = _detect_news_changes(git_news_repo)
        assert "2025-11-30-flexiblas-migration" in modified

    def test_no_changes(self, git_news_repo: Path) -> None:
        added, modified, deleted = _detect_news_changes(git_news_repo)
        assert not added
        assert not modified
        assert not deleted

    def test_deduplicates_same_item(self, git_news_repo: Path) -> None:
        # Add two files to the same item directory
        item_dir = git_news_repo / "metadata" / "news" / "2026-02-01-multi"
        item_dir.mkdir()
        (item_dir / "2026-02-01-multi.en.txt").write_text(
            "Title: Multi\nAuthor: Dev <d@g.org>\nPosted: 2026-02-01\n"
            "Revision: 1\nNews-Item-Format: 2.0\n\nBody."
        )
        (item_dir / "2026-02-01-multi.de.txt").write_text(
            "Title: Multi DE\nAuthor: Dev <d@g.org>\nPosted: 2026-02-01\n"
            "Revision: 1\nNews-Item-Format: 2.0\n\nBody DE."
        )

        added, _, _ = _detect_news_changes(git_news_repo)
        assert added.count("2026-02-01-multi") == 1
