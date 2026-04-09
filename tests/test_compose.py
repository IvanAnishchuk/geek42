"""Tests for the compose/revise module."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from geek42.compose import (
    find_item_file,
    generate_template,
    get_editor,
    infer_author,
    make_temp_copy,
    place_news_item,
    prepare_revision,
    title_to_slug,
)
from geek42.errors import EmptyTitleError, SlugDerivationError
from geek42.models import NewsSource

# -- get_editor --


def test_get_editor_override() -> None:
    assert get_editor("nano") == "nano"


def test_get_editor_visual(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VISUAL", "code --wait")
    monkeypatch.delenv("EDITOR", raising=False)
    assert get_editor() == "code --wait"


def test_get_editor_editor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VISUAL", raising=False)
    monkeypatch.setenv("EDITOR", "emacs")
    assert get_editor() == "emacs"


def test_get_editor_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VISUAL", raising=False)
    monkeypatch.delenv("EDITOR", raising=False)
    assert get_editor() == "vi"


# -- infer_author --


def test_infer_author() -> None:
    author = infer_author()
    # Should return "Name <email>" format
    assert "<" in author
    assert ">" in author


# -- title_to_slug --


def test_slug_basic() -> None:
    assert title_to_slug("FlexiBLAS Migration") == "flexiblas-migration"


def test_slug_special_chars() -> None:
    assert title_to_slug("GCC 14: What's New?") == "gcc-14-what-s-new"


def test_slug_truncation() -> None:
    slug = title_to_slug("a very long title that exceeds the limit", max_len=20)
    assert len(slug) <= 20
    assert not slug.endswith("-")


def test_slug_empty() -> None:
    assert title_to_slug("") == ""


def test_slug_numbers() -> None:
    assert title_to_slug("Python 3.13 Update") == "python-3-13-update"


# -- generate_template --


def test_generate_template_has_required_headers() -> None:
    tmpl = generate_template(author="Test Dev <test@gentoo.org>")
    assert "Title: " in tmpl
    assert "Author: Test Dev <test@gentoo.org>" in tmpl
    assert f"Posted: {date.today().isoformat()}" in tmpl
    assert "Revision: 1" in tmpl
    assert "News-Item-Format: 2.0" in tmpl


def test_generate_template_has_body_placeholder() -> None:
    tmpl = generate_template(author="X <x@x>")
    assert "Write your news item body here." in tmpl


def test_generate_template_infers_author() -> None:
    tmpl = generate_template()
    assert "Author: " in tmpl


# -- make_temp_copy --


def test_make_temp_copy() -> None:
    p = make_temp_copy("hello world", prefix="test-")
    try:
        assert p.exists()
        assert p.read_text() == "hello world"
        assert p.name.startswith("test-")
    finally:
        p.unlink()


# -- place_news_item --


def _valid_content(title: str = "Test News Item") -> str:
    today = date.today().isoformat()
    return (
        f"Title: {title}\n"
        f"Author: Dev <dev@gentoo.org>\n"
        f"Posted: {today}\n"
        f"Revision: 1\n"
        f"News-Item-Format: 2.0\n"
        f"\n"
        f"This is the body of the news item.\n"
    )


def test_place_news_item(tmp_path: Path) -> None:
    src = tmp_path / "draft.txt"
    src.write_text(_valid_content("FlexiBLAS Migration"))
    repo = tmp_path / "repo"
    repo.mkdir()

    result = place_news_item(src, repo)

    assert result.exists()
    assert "flexiblas-migration" in result.parent.name
    assert date.today().isoformat() in result.parent.name
    assert result.name.endswith(".en.txt")


def test_place_news_item_empty_title(tmp_path: Path) -> None:
    src = tmp_path / "draft.txt"
    src.write_text(_valid_content(""))
    repo = tmp_path / "repo"
    repo.mkdir()

    with pytest.raises(EmptyTitleError):
        place_news_item(src, repo)


def test_place_news_item_unslugable_title(tmp_path: Path) -> None:
    src = tmp_path / "draft.txt"
    # Title is all punctuation, won't produce a slug
    src.write_text(_valid_content("!@#$%^&*()"))
    repo = tmp_path / "repo"
    repo.mkdir()

    with pytest.raises(SlugDerivationError):
        place_news_item(src, repo)


# -- prepare_revision --


def test_prepare_revision(tmp_path: Path) -> None:
    item_dir = tmp_path / "2025-06-15-test"
    item_dir.mkdir()
    item_file = item_dir / "2025-06-15-test.en.txt"
    item_file.write_text(
        "Title: Test Item\n"
        "Author: Dev <dev@gentoo.org>\n"
        "Posted: 2025-06-15\n"
        "Revision: 2\n"
        "News-Item-Format: 2.0\n"
        "\n"
        "Original body.\n"
    )

    tmp = prepare_revision(item_file)
    try:
        content = tmp.read_text()
        assert "Revision: 3" in content
        assert f"Posted: {date.today().isoformat()}" in content
        assert "Original body." in content
        assert "Revision: 2" not in content
    finally:
        tmp.unlink()


# -- find_item_file --


def test_find_item_exact(tmp_path: Path) -> None:
    repo = tmp_path / "repos" / "test"
    item_dir = repo / "2025-01-01-foo"
    item_dir.mkdir(parents=True)
    f = item_dir / "2025-01-01-foo.en.txt"
    f.write_text("content")

    sources = [NewsSource(name="test", url="x", branch="main")]
    result = find_item_file("2025-01-01-foo", tmp_path, sources)
    assert result == f


def test_find_item_substring(tmp_path: Path) -> None:
    repo = tmp_path / "repos" / "test"
    item_dir = repo / "2025-01-01-foobar-baz"
    item_dir.mkdir(parents=True)
    f = item_dir / "2025-01-01-foobar-baz.en.txt"
    f.write_text("content")

    sources = [NewsSource(name="test", url="x", branch="main")]
    result = find_item_file("foobar", tmp_path, sources)
    assert result == f


def test_find_item_not_found(tmp_path: Path) -> None:
    sources = [NewsSource(name="test", url="x", branch="main")]
    assert find_item_file("nonexistent", tmp_path, sources) is None


def test_find_item_unpulled_source(tmp_path: Path) -> None:
    sources = [NewsSource(name="missing", url="x", branch="main")]
    assert find_item_file("anything", tmp_path, sources) is None
