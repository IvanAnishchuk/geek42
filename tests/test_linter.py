"""Tests for the GLEP 42 news file linter."""

from __future__ import annotations

from pathlib import Path

from geek42.linter import Severity, lint_news_file, lint_repo

VALID_NEWS = """\
Title: Valid News Item
Author: Dev One <dev@gentoo.org>
Posted: 2025-06-15
Revision: 1
News-Item-Format: 2.0

This is a perfectly valid news item body.
It wraps at reasonable line lengths.
"""

FORMAT1_VALID = """\
Title: Old Format Item
Author: Dev <dev@gentoo.org>
Content-Type: text/plain
Posted: 2017-01-01
Revision: 1
News-Item-Format: 1.0

Old format body text.
"""

# Minimal valid headers to keep test strings short
_H = "Title: T\nAuthor: D <d@g>\nPosted: 2025-01-01\nRevision: 1\nNews-Item-Format: 2.0"


def _write_news(tmp_path: Path, item_id: str, content: str) -> Path:
    d = tmp_path / item_id
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{item_id}.en.txt"
    p.write_text(content)
    return p


# -- Valid files produce no errors --


def test_valid_file_no_errors(tmp_path: Path) -> None:
    p = _write_news(tmp_path, "2025-06-15-valid", VALID_NEWS)
    diags = lint_news_file(p)
    errors = [d for d in diags if d.severity == Severity.error]
    assert errors == []


def test_format1_valid(tmp_path: Path) -> None:
    p = _write_news(tmp_path, "2017-01-01-old", FORMAT1_VALID)
    diags = lint_news_file(p)
    errors = [d for d in diags if d.severity == Severity.error]
    assert errors == []


# -- E001: Missing required headers --


def test_missing_title(tmp_path: Path) -> None:
    content = (
        "Author: Dev <d@g.org>\nPosted: 2025-01-01\nRevision: 1\nNews-Item-Format: 2.0\n\nBody."
    )
    p = _write_news(tmp_path, "2025-01-01-no-title", content)
    diags = lint_news_file(p)
    codes = [(d.severity, d.code) for d in diags]
    assert (Severity.error, "001") in codes


def test_missing_posted(tmp_path: Path) -> None:
    content = "Title: Test\nAuthor: Dev <d@g.org>\nRevision: 1\nNews-Item-Format: 2.0\n\nBody."
    p = _write_news(tmp_path, "2025-01-01-no-posted", content)
    diags = lint_news_file(p)
    assert any(d.code == "001" and "Posted" in d.message for d in diags)


def test_missing_multiple_headers(tmp_path: Path) -> None:
    content = "Title: Test\n\nBody only."
    p = _write_news(tmp_path, "2025-01-01-minimal", content)
    diags = lint_news_file(p)
    missing = [d for d in diags if d.code == "001"]
    assert len(missing) >= 3


# -- E002: Invalid date --


def test_invalid_date(tmp_path: Path) -> None:
    h = _H.replace("Posted: 2025-01-01", "Posted: not-a-date")
    p = _write_news(tmp_path, "2025-01-01-bad-date", f"{h}\n\nBody.")
    diags = lint_news_file(p)
    assert any(d.code == "002" for d in diags)


# -- E003: Invalid revision --


def test_invalid_revision_not_int(tmp_path: Path) -> None:
    h = _H.replace("Revision: 1", "Revision: abc")
    p = _write_news(tmp_path, "2025-01-01-bad-rev", f"{h}\n\nBody.")
    diags = lint_news_file(p)
    assert any(d.code == "003" for d in diags)


def test_invalid_revision_zero(tmp_path: Path) -> None:
    h = _H.replace("Revision: 1", "Revision: 0")
    p = _write_news(tmp_path, "2025-01-01-zero-rev", f"{h}\n\nBody.")
    diags = lint_news_file(p)
    assert any(d.code == "003" for d in diags)


# -- E004: Unknown format --


def test_unknown_format(tmp_path: Path) -> None:
    h = _H.replace("News-Item-Format: 2.0", "News-Item-Format: 9.9")
    p = _write_news(tmp_path, "2025-01-01-bad-fmt", f"{h}\n\nBody.")
    diags = lint_news_file(p)
    assert any(d.code == "004" for d in diags)


# -- E005: Format 1.0 missing Content-Type --


def test_format1_missing_content_type(tmp_path: Path) -> None:
    h = _H.replace("News-Item-Format: 2.0", "News-Item-Format: 1.0")
    p = _write_news(tmp_path, "2025-01-01-no-ct", f"{h}\n\nBody.")
    diags = lint_news_file(p)
    assert any(d.code == "005" for d in diags)


# -- E006: Empty body --


def test_empty_body(tmp_path: Path) -> None:
    p = _write_news(tmp_path, "2025-01-01-empty", f"{_H}\n\n")
    diags = lint_news_file(p)
    assert any(d.code == "006" for d in diags)


# -- E010: Malformed header line --


def test_malformed_header(tmp_path: Path) -> None:
    bad = _H.replace("Author: D <d@g>", "this is not a header")
    p = _write_news(tmp_path, "2025-01-01-malformed", f"{bad}\n\nBody.")
    diags = lint_news_file(p)
    assert any(d.code == "010" for d in diags)


# -- W001: Title too long --


def test_title_too_long(tmp_path: Path) -> None:
    h = _H.replace("Title: T", f"Title: {'A' * 60}")
    p = _write_news(tmp_path, "2025-01-01-long-title", f"{h}\n\nBody.")
    diags = lint_news_file(p)
    assert any(d.severity == Severity.warning and d.code == "001" for d in diags)


# -- W002: Body line too long --


def test_body_line_too_long(tmp_path: Path) -> None:
    p = _write_news(tmp_path, "2025-01-01-long-line", f"{_H}\n\n{'x' * 80}")
    diags = lint_news_file(p)
    assert any(d.severity == Severity.warning and d.code == "002" for d in diags)


# -- W003: Trailing whitespace --


def test_trailing_whitespace(tmp_path: Path) -> None:
    h = _H.replace("Author: D <d@g>", "Author: D <d@g>  ")
    p = _write_news(tmp_path, "2025-01-01-trailing", f"{h}\n\nBody.")
    diags = lint_news_file(p)
    assert any(d.severity == Severity.warning and d.code == "003" for d in diags)


# -- W004: Author format --


def test_author_bad_format(tmp_path: Path) -> None:
    h = _H.replace("Author: D <d@g>", "Author: just-a-name")
    p = _write_news(tmp_path, "2025-01-01-bad-author", f"{h}\n\nBody.")
    diags = lint_news_file(p)
    assert any(d.severity == Severity.warning and d.code == "004" for d in diags)


# -- W005: File name mismatch --


def test_filename_mismatch(tmp_path: Path) -> None:
    d = tmp_path / "2025-01-01-correct-name"
    d.mkdir()
    p = d / "2025-01-01-wrong-name.en.txt"
    p.write_text(VALID_NEWS)
    diags = lint_news_file(p)
    assert any(d.severity == Severity.warning and d.code == "005" for d in diags)


# -- lint_repo --


def test_lint_repo(tmp_path: Path) -> None:
    _write_news(tmp_path, "2025-06-15-valid", VALID_NEWS)
    _write_news(tmp_path, "2025-01-01-empty-body", f"{_H}\n\n")
    diags = lint_repo(tmp_path)
    assert any(d.code == "006" for d in diags)


def test_lint_repo_missing_file(tmp_path: Path) -> None:
    (tmp_path / "2025-01-01-missing").mkdir()
    diags = lint_repo(tmp_path)
    assert any(d.code == "008" for d in diags)


def test_lint_repo_bad_dirname(tmp_path: Path) -> None:
    (tmp_path / "not-a-valid-id").mkdir()
    diags = lint_repo(tmp_path)
    assert any(d.severity == Severity.warning and d.code == "006" for d in diags)


def test_lint_repo_skips_dotdirs(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    _write_news(tmp_path, "2025-06-15-valid", VALID_NEWS)
    diags = lint_repo(tmp_path)
    assert not any(".git" in d.file for d in diags)


# -- Diagnostic __str__ --


def test_diagnostic_str(tmp_path: Path) -> None:
    h = _H.replace("Posted: 2025-01-01", "Posted: not-a-date")
    p = _write_news(tmp_path, "2025-01-01-str-test", f"{h}\n\nBody.")
    diags = lint_news_file(p)
    date_diag = next(d for d in diags if d.code == "002")
    s = str(date_diag)
    assert "E002" in s
    assert "not-a-date" in s
