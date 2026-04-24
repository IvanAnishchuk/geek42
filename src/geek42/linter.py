"""Linter for GLEP 42 news item files."""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel

_HEADER_RE = re.compile(r"^([A-Za-z][A-Za-z0-9-]*)\s*:\s*(.*)")
_ID_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9+_-]+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_AUTHOR_RE = re.compile(r"^.+\s+<[^>]+>$")

REQUIRED_HEADERS = ("Title", "Author", "Posted", "Revision", "News-Item-Format")
KNOWN_FORMATS = ("1.0", "2.0")
MAX_TITLE_LEN = 50
MAX_LINE_LEN = 72


class Severity(StrEnum):
    error = "error"
    warning = "warning"


class Diagnostic(BaseModel):
    """A single lint diagnostic."""

    file: str
    line: int | None = None
    severity: Severity
    code: str
    message: str

    def __str__(self) -> str:
        loc = self.file
        if self.line is not None:
            loc += f":{self.line}"
        return f"{loc}: {self.severity.value[0].upper()}{self.code} {self.message}"


def _diag(
    name: str,
    sev: Severity,
    code: str,
    msg: str,
    line: int | None = None,
) -> Diagnostic:
    return Diagnostic(file=name, line=line, severity=sev, code=code, message=msg)


def lint_news_file(path: Path) -> list[Diagnostic]:  # noqa: C901 — validation with many independent checks is inherently complex
    """Lint a single GLEP 42 news file. Returns a list of diagnostics."""
    diags: list[Diagnostic] = []
    name = str(path)
    E = Severity.error
    W = Severity.warning

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        return [_diag(name, E, "001", f"Cannot read file: {e}")]
    except UnicodeDecodeError as e:
        return [_diag(name, E, "001", f"Cannot decode file as UTF-8: {e}")]

    lines = text.split("\n")

    # Parse headers
    headers: dict[str, list[tuple[int, str]]] = {}
    body_start = len(lines)
    found_blank = False

    for i, line in enumerate(lines):
        if line.strip() == "":
            body_start = i + 1
            found_blank = True
            break
        m = _HEADER_RE.match(line)
        if m:
            key, value = m.group(1), m.group(2).strip()
            headers.setdefault(key, []).append((i + 1, value))
        else:
            diags.append(_diag(name, E, "010", f"Malformed header: {line!r}", i + 1))

    # E001: Required headers
    for hdr in REQUIRED_HEADERS:
        if hdr not in headers:
            diags.append(_diag(name, E, "001", f"Missing required header: {hdr}"))

    # E002: Posted date format
    for lineno, val in headers.get("Posted", []):
        if not _DATE_RE.match(val):
            diags.append(_diag(name, E, "002", f"Invalid date: {val!r} (want YYYY-MM-DD)", lineno))

    # E003: Revision must be a positive integer
    for lineno, val in headers.get("Revision", []):
        try:
            rev = int(val)
        except ValueError:
            diags.append(_diag(name, E, "003", f"Invalid revision: {val!r}", lineno))
        else:
            if rev < 1:
                diags.append(_diag(name, E, "003", f"Invalid revision: {val!r}", lineno))

    # E004: Unknown format version
    for lineno, val in headers.get("News-Item-Format", []):
        if val not in KNOWN_FORMATS:
            diags.append(_diag(name, E, "004", f"Unknown format: {val!r}", lineno))

    # E005: Format 1.0 requires Content-Type
    fmt_vals = [v for _, v in headers.get("News-Item-Format", [])]
    if "1.0" in fmt_vals and "Content-Type" not in headers:
        diags.append(_diag(name, E, "005", "Format 1.0 requires Content-Type"))

    # E006: Empty body
    body_lines = lines[body_start:]
    body_text = "\n".join(body_lines).strip()
    if not body_text:
        diags.append(_diag(name, E, "006", "Empty body"))

    # E007: No blank line separating headers from body
    if not found_blank and body_text:
        diags.append(_diag(name, E, "007", "No blank line between headers and body"))

    # W001: Title too long
    for lineno, val in headers.get("Title", []):
        if len(val) > MAX_TITLE_LEN:
            msg = f"Title exceeds {MAX_TITLE_LEN} chars ({len(val)})"
            diags.append(_diag(name, W, "001", msg, lineno))

    # W002: Body line too long
    for i, line in enumerate(body_lines, start=body_start + 1):
        if len(line) > MAX_LINE_LEN:
            msg = f"Line exceeds {MAX_LINE_LEN} chars ({len(line)})"
            diags.append(_diag(name, W, "002", msg, i))

    # W003: Trailing whitespace
    for i, line in enumerate(lines, start=1):
        if line != line.rstrip():
            diags.append(_diag(name, W, "003", "Trailing whitespace", i))

    # W004: Author format
    for lineno, val in headers.get("Author", []):
        if not _AUTHOR_RE.match(val):
            msg = f"Author not in 'Name <email>' format: {val!r}"
            diags.append(_diag(name, W, "004", msg, lineno))

    # W005: File name vs directory name mismatch
    expected = path.parent.name
    actual = path.stem.rsplit(".", 1)[0] if "." in path.stem else path.stem
    if actual != expected:
        diags.append(_diag(name, W, "005", f"File stem {actual!r} != dir {expected!r}"))

    return diags


def lint_repo(repo_path: Path, language: str = "en") -> list[Diagnostic]:
    """Lint all news items in a repository directory."""
    from .parser import resolve_news_root

    news_root = resolve_news_root(repo_path)
    all_diags: list[Diagnostic] = []

    for entry in sorted(news_root.iterdir()):
        if not entry.is_dir():
            continue
        if not _ID_RE.match(entry.name):
            if not entry.name.startswith("."):
                msg = f"Bad directory name: {entry.name!r}"
                all_diags.append(_diag(str(entry), Severity.warning, "006", msg))
            continue
        news_file = entry / f"{entry.name}.{language}.txt"
        if not news_file.exists():
            msg = f"Missing {entry.name}.{language}.txt"
            all_diags.append(_diag(str(entry), Severity.error, "008", msg))
            continue
        all_diags.extend(lint_news_file(news_file))

    return all_diags
