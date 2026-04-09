"""Compose and revise GLEP 42 news items via $EDITOR."""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path

from .errors import EmptyTitleError, SlugDerivationError
from .linter import Diagnostic, Severity, lint_news_file

_GIT = shutil.which("git")


def get_editor(override: str | None = None) -> str:
    """Resolve editor: --editor flag > $VISUAL > $EDITOR > vi."""
    if override:
        return override
    return os.environ.get("VISUAL") or os.environ.get("EDITOR") or "vi"


def _git_config(key: str) -> str | None:
    if _GIT is None:
        return None
    try:
        result = subprocess.run(  # noqa: S603  # fixed args, key is a literal from our code
            [_GIT, "config", "--get", key],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return result.stdout.strip() or None


def infer_author() -> str:
    """Infer author from git config user.name / user.email."""
    name = _git_config("user.name") or "Your Name"
    email = _git_config("user.email") or "your@email.org"
    return f"{name} <{email}>"


def title_to_slug(title: str, max_len: int = 20) -> str:
    """Convert a title to a GLEP 42 short-name slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if len(slug) > max_len:
        slug = slug[:max_len].rsplit("-", 1)[0]
    return slug


def generate_template(author: str | None = None) -> str:
    """Generate a new GLEP 42 news item template."""
    today = date.today().isoformat()
    if author is None:
        author = infer_author()
    return (
        f"Title: \n"
        f"Author: {author}\n"
        f"Posted: {today}\n"
        f"Revision: 1\n"
        f"News-Item-Format: 2.0\n"
        f"\n"
        f"Write your news item body here.\n"
        f"\n"
        f"Wrap lines at 72 characters. Separate paragraphs with\n"
        f"blank lines.\n"
    )


def open_in_editor(path: Path, editor: str) -> int:
    """Open a file in the user's editor. Returns the exit code.

    The editor command comes from a trusted source (CLI flag or the
    user's own $VISUAL/$EDITOR environment variable). We intentionally
    do not validate it further — the user is authorizing execution.
    """
    cmd = shlex.split(editor) + [str(path)]
    return subprocess.run(cmd, check=False).returncode  # noqa: S603


def edit_and_lint(path: Path, editor: str) -> tuple[bool, list[Diagnostic]]:
    """Open file in editor, then lint it.

    Returns (success, diagnostics). success=True means no errors.
    """
    rc = open_in_editor(path, editor)
    if rc != 0:
        return False, []
    diags = lint_news_file(path)
    errors = [d for d in diags if d.severity == Severity.error]
    return len(errors) == 0, diags


def make_temp_copy(content: str, prefix: str = "geek42-") -> Path:
    """Write content to a named temp file. Caller must clean up."""
    fd, tmp = tempfile.mkstemp(suffix=".txt", prefix=prefix)
    os.close(fd)
    p = Path(tmp)
    p.write_text(content, encoding="utf-8")
    return p


def place_news_item(src: Path, repo_dir: Path, language: str = "en") -> Path:
    """Parse a composed file, derive its item ID, and place it in the repo.

    :raises EmptyTitleError: The parsed file has an empty Title.
    :raises SlugDerivationError: A valid slug cannot be derived from the title.
    :returns: The final path under ``repo_dir``.
    """
    from .parser import parse_news_file

    item = parse_news_file(src)
    if not item.title.strip():
        raise EmptyTitleError

    slug = title_to_slug(item.title)
    if not slug:
        raise SlugDerivationError(item.title)

    item_id = f"{item.posted.isoformat()}-{slug}"
    target_dir = repo_dir / item_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / f"{item_id}.{language}.txt"
    shutil.copy2(src, target_file)
    return target_file


def prepare_revision(item_path: Path) -> Path:
    """Copy a news file to a temp file with bumped revision and today's date.

    Returns the temp file path. Caller must clean up.
    """
    from .parser import parse_news_file

    item = parse_news_file(item_path)
    text = item_path.read_text(encoding="utf-8")

    # Bump revision
    text = text.replace(
        f"Revision: {item.revision}",
        f"Revision: {item.revision + 1}",
        1,
    )
    # Update Posted date
    text = text.replace(
        f"Posted: {item.posted.isoformat()}",
        f"Posted: {date.today().isoformat()}",
        1,
    )
    return make_temp_copy(text, prefix="geek42-revise-")


def find_item_file(
    item_id: str, data_dir: Path, sources: list, language: str = "en"
) -> Path | None:
    """Find the file path for a news item across all sources."""
    for source in sources:
        repo_dir = data_dir / "repos" / source.name
        if not repo_dir.is_dir():
            continue
        # Exact match first
        candidate = repo_dir / item_id / f"{item_id}.{language}.txt"
        if candidate.exists():
            return candidate
        # Substring match
        for entry in repo_dir.iterdir():
            if entry.is_dir() and item_id in entry.name:
                f = entry / f"{entry.name}.{language}.txt"
                if f.exists():
                    return f
    return None
