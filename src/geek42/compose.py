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
from .models import NewsSource

_GIT = shutil.which("git")


def get_editor(override: str | None = None) -> str:
    """Resolve which editor command to invoke.

    Resolution order: ``override`` argument → ``$VISUAL`` → ``$EDITOR``
    → fallback ``vi``. The result may contain arguments
    (e.g. ``"code --wait"``) which the caller will split with
    :func:`shlex.split`.
    """
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
    """Build an author string from local git config.

    Reads ``user.name`` and ``user.email`` from the user's git config
    and formats them as ``"Name <email>"``. Returns sensible
    placeholder values when git is unavailable or unconfigured so the
    template still parses.
    """
    name = _git_config("user.name") or "Your Name"
    email = _git_config("user.email") or "your@email.org"
    return f"{name} <{email}>"


def title_to_slug(title: str, max_len: int = 20) -> str:
    """Convert a free-form title to a GLEP 42 short-name slug.

    Lowercases, replaces every run of non-alphanumeric characters with
    a single hyphen, strips leading/trailing hyphens, and truncates at
    a word boundary if longer than ``max_len`` (default 20, the GLEP 42
    recommended maximum).

    Returns an empty string when no slug-worthy characters are present.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if len(slug) > max_len:
        slug = slug[:max_len].rsplit("-", 1)[0]
    return slug


def generate_template(author: str | None = None) -> str:
    """Return a fresh GLEP 42 news item template ready for the editor.

    The template has today's date and either the supplied or
    git-inferred author already filled in. The user only needs to set
    a Title and write the body.
    """
    if author is None:
        author = infer_author()
    today = date.today().isoformat()
    return (
        "Title: \n"
        f"Author: {author}\n"
        f"Posted: {today}\n"
        "Revision: 1\n"
        "News-Item-Format: 2.0\n"
        "\n"
        "Write your news item body here.\n"
        "\n"
        "Wrap lines at 72 characters. Separate paragraphs with\n"
        "blank lines.\n"
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
    """Write ``content`` to a fresh ``.txt`` temp file and return its path.

    The caller is responsible for unlinking the file. Use a ``try/finally``
    block to guarantee cleanup even if the editor or linter raises.
    """
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
    """Stage an existing news item for revision in a temp file.

    Reads the item, bumps the ``Revision:`` header by one, replaces
    the ``Posted:`` date with today, and writes the result to a fresh
    temp file. The original file is left untouched until the caller
    copies the edited temp file back over it.

    :returns: Path to the temp file. Caller must unlink it.
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
    item_id: str,
    data_dir: Path,
    sources: list[NewsSource],
    language: str = "en",
    *,
    root_dir: Path | None = None,
) -> Path | None:
    """Locate the file backing a news item by ID across all configured sources.

    The lookup is exact-match first, then falls back to substring match
    on directory names — letting users invoke ``geek42 read flexiblas``
    instead of typing the full ``2025-11-30-flexiblas-migration``.

    :param item_id: Either a full GLEP 42 identifier or a substring.
    :param data_dir: The geek42 data dir containing ``repos/<name>/``.
    :param sources: Configured news sources (only the ``name`` is used).
    :param language: ``en`` etc. — picks the right ``{id}.{lang}.txt``.
    :param root_dir: Base directory for local sources (default: cwd).
    :returns: The path to the news file, or ``None`` if no match.
    """
    _root = (root_dir or Path(".")).resolve()
    for source in sources:
        repo_dir = _root if source.is_local else data_dir / "repos" / source.name
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
