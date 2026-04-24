"""Tests for GitHub integration module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from geek42.github import (
    GhNotFoundError,
    PublishError,
    _require_gh,
    create_issue,
    create_release,
    find_issue,
    update_issue,
)

from .conftest import make_item


@pytest.fixture
def _mock_gh(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure _GH is set to a known value for tests."""
    monkeypatch.setattr("geek42.github._GH", "/usr/bin/gh")


def _fake_run(stdout: str = "", stderr: str = "", returncode: int = 0):
    """Create a mock subprocess result."""
    from subprocess import CompletedProcess

    return CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class TestRequireGh:
    def test_raises_when_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("geek42.github._GH", None)
        with pytest.raises(GhNotFoundError):
            _require_gh()

    def test_returns_path(self, _mock_gh: None) -> None:
        assert _require_gh() == "/usr/bin/gh"


class TestFindIssue:
    @pytest.mark.usefixtures("_mock_gh")
    def test_found(self, tmp_path: Path) -> None:
        with patch("geek42.github._run_gh", return_value=_fake_run('[{"number": 42}]')):
            assert find_issue("owner/repo", "2026-05-01-test", tmp_path) == 42

    @pytest.mark.usefixtures("_mock_gh")
    def test_not_found(self, tmp_path: Path) -> None:
        with patch("geek42.github._run_gh", return_value=_fake_run("[]")):
            assert find_issue("owner/repo", "2026-05-01-test", tmp_path) is None

    @pytest.mark.usefixtures("_mock_gh")
    def test_gh_error(self, tmp_path: Path) -> None:
        with patch("geek42.github._run_gh", return_value=_fake_run(returncode=1)):
            assert find_issue("owner/repo", "2026-05-01-test", tmp_path) is None


class TestCreateIssue:
    @pytest.mark.usefixtures("_mock_gh")
    def test_success(self, tmp_path: Path) -> None:
        item = make_item(title="Test News")
        url = "https://github.com/owner/repo/issues/1"
        with patch("geek42.github._run_gh", return_value=_fake_run(url)):
            result = create_issue("owner/repo", item, tmp_path)
        assert result == url

    @pytest.mark.usefixtures("_mock_gh")
    def test_with_base_url(self, tmp_path: Path) -> None:
        item = make_item(id="2026-01-01-x", title="Test")
        with patch("geek42.github._run_gh", return_value=_fake_run("url")) as mock:
            create_issue("owner/repo", item, tmp_path, base_url="https://blog.example.com")
        call_args = mock.call_args[0][0]
        body_idx = call_args.index("--body") + 1
        assert "blog.example.com" in call_args[body_idx]

    @pytest.mark.usefixtures("_mock_gh")
    def test_failure_raises(self, tmp_path: Path) -> None:
        item = make_item()
        with (
            patch("geek42.github._run_gh", return_value=_fake_run(stderr="denied", returncode=1)),
            pytest.raises(PublishError),
        ):
            create_issue("owner/repo", item, tmp_path)

    @pytest.mark.usefixtures("_mock_gh")
    def test_advisory_gets_label(self, tmp_path: Path) -> None:
        item = make_item(item_type="advisory")
        with patch("geek42.github._run_gh", return_value=_fake_run("url")) as mock:
            create_issue("owner/repo", item, tmp_path)
        call_args = mock.call_args[0][0]
        assert "--label" in call_args
        assert "advisory" in call_args


class TestUpdateIssue:
    @pytest.mark.usefixtures("_mock_gh")
    def test_success(self, tmp_path: Path) -> None:
        item = make_item(body="Updated body.")
        with patch("geek42.github._run_gh", return_value=_fake_run()):
            update_issue("owner/repo", 42, item, tmp_path)

    @pytest.mark.usefixtures("_mock_gh")
    def test_failure_raises(self, tmp_path: Path) -> None:
        item = make_item()
        with (
            patch("geek42.github._run_gh", return_value=_fake_run(stderr="err", returncode=1)),
            pytest.raises(PublishError),
        ):
            update_issue("owner/repo", 42, item, tmp_path)


class TestCreateRelease:
    @pytest.mark.usefixtures("_mock_gh")
    def test_success(self, tmp_path: Path) -> None:
        item = make_item(id="2026-05-01-fix", title="Fix")
        url = "https://github.com/owner/repo/releases/tag/news/2026-05-01-fix"
        with patch("geek42.github._run_gh", return_value=_fake_run(url)):
            result = create_release("owner/repo", item, tmp_path)
        assert result == url

    @pytest.mark.usefixtures("_mock_gh")
    def test_failure_raises(self, tmp_path: Path) -> None:
        item = make_item()
        with (
            patch("geek42.github._run_gh", return_value=_fake_run(stderr="err", returncode=1)),
            pytest.raises(PublishError),
        ):
            create_release("owner/repo", item, tmp_path)
