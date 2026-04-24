"""GitHub integration via the ``gh`` CLI.

Wraps ``gh`` for creating issues and releases linked to news items.
Follows the same subprocess pattern as :mod:`geek42.manifest`.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .errors import Geek42Error, SystemDependencyError
from .models import NewsItem
from .renderer import news_to_markdown

_GH = shutil.which("gh")


class GhNotFoundError(SystemDependencyError):
    """The gh CLI is not on PATH."""

    def __init__(self) -> None:
        super().__init__("gh CLI not found in PATH (install from https://cli.github.com)")


class PublishError(Geek42Error):
    """Failed to publish a news item to GitHub."""

    def __init__(self, action: str, detail: str = "") -> None:
        msg = f"publish failed: {action}"
        if detail:
            msg += f": {detail}"
        super().__init__(msg)


def _require_gh() -> str:
    if _GH is None:
        raise GhNotFoundError
    return _GH


def _check_gh(result: subprocess.CompletedProcess[str], action: str) -> None:
    """Raise :class:`PublishError` if a ``gh`` command failed."""
    if result.returncode != 0:
        raise PublishError(action, result.stderr.strip())


def _run_gh(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    gh = _require_gh()
    return subprocess.run(  # noqa: S603 — args are list literals, no shell
        [gh, *args], capture_output=True, text=True, check=False, cwd=str(cwd)
    )


def find_issue(repo: str, item_id: str, cwd: Path) -> int | None:
    """Find an existing GitHub issue for a news item by searching titles.

    :returns: Issue number, or ``None`` if not found.
    """
    result = _run_gh(
        ["issue", "list", "--repo", repo, "--search", f"{item_id} in:title", "--json", "number"],
        cwd,
    )
    if result.returncode != 0:
        return None
    issues = json.loads(result.stdout)
    return issues[0]["number"] if issues else None


def create_issue(repo: str, item: NewsItem, cwd: Path, base_url: str = "") -> str:
    """Create a GitHub issue for a news item. Returns the issue URL.

    The issue body contains the news item content and a link to the
    blog post when *base_url* is set.
    """
    body_parts = [item.body]
    if base_url:
        post_url = f"{base_url.rstrip('/')}/posts/{item.id}.html"
        body_parts.append(f"\n---\n[Read on blog]({post_url})")

    label = item.item_type if item.item_type != "news" else ""
    args = [
        "issue",
        "create",
        "--repo",
        repo,
        "--title",
        f"[{item.item_type}] {item.title}",
        "--body",
        "\n".join(body_parts),
    ]
    if label:
        args.extend(["--label", label])

    result = _run_gh(args, cwd)
    _check_gh(result, "create issue")
    return result.stdout.strip()


def update_issue(repo: str, issue_number: int, item: NewsItem, cwd: Path) -> None:
    """Update an existing issue's body (e.g. after a revision)."""
    result = _run_gh(
        [
            "issue",
            "edit",
            str(issue_number),
            "--repo",
            repo,
            "--body",
            item.body,
        ],
        cwd,
    )
    _check_gh(result, f"update issue #{issue_number}")


def create_release(repo: str, item: NewsItem, cwd: Path) -> str:
    """Create a git tag and GitHub release for a news item.

    Tag format: ``news/{item.id}``.

    :returns: The release URL.
    """
    tag = f"news/{item.id}"
    md_body = news_to_markdown(item)

    result = _run_gh(
        [
            "release",
            "create",
            tag,
            "--repo",
            repo,
            "--title",
            item.title,
            "--notes",
            md_body,
        ],
        cwd,
    )
    _check_gh(result, f"create release {tag}")
    return result.stdout.strip()
