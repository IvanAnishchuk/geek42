"""Tests for the read/unread tracker."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from geek42.models import NewsItem
from geek42.tracker import ReadTracker, _coverage_test_noop


def _item(item_id: str) -> NewsItem:
    return NewsItem(
        id=item_id,
        title=f"Item {item_id}",
        authors=["Dev <d@g>"],
        posted=date(2025, 1, 1),
        body="body",
    )


def test_empty_tracker(tmp_path: Path) -> None:
    tracker = ReadTracker(tmp_path)
    assert tracker.read_ids == set()
    assert not tracker.is_read("anything")


def test_mark_read(tmp_path: Path) -> None:
    tracker = ReadTracker(tmp_path)
    tracker.mark_read("2025-01-01-foo")
    assert tracker.is_read("2025-01-01-foo")
    assert not tracker.is_read("2025-01-01-bar")


def test_mark_read_persists(tmp_path: Path) -> None:
    tracker1 = ReadTracker(tmp_path)
    tracker1.mark_read("item-a", "item-b")

    # New tracker instance reads from disk
    tracker2 = ReadTracker(tmp_path)
    assert tracker2.is_read("item-a")
    assert tracker2.is_read("item-b")


def test_mark_read_idempotent(tmp_path: Path) -> None:
    tracker = ReadTracker(tmp_path)
    tracker.mark_read("item-a")
    tracker.mark_read("item-a")
    assert (tmp_path / "read.txt").read_text().count("item-a") == 1


def test_unread(tmp_path: Path) -> None:
    tracker = ReadTracker(tmp_path)
    items = [_item("a"), _item("b"), _item("c")]
    tracker.mark_read("a", "c")

    unread = tracker.unread(items)
    assert len(unread) == 1
    assert unread[0].id == "b"


def test_count_unread(tmp_path: Path) -> None:
    tracker = ReadTracker(tmp_path)
    items = [_item("a"), _item("b"), _item("c")]
    tracker.mark_read("b")

    assert tracker.count_unread(items) == 2


def test_unread_all_read(tmp_path: Path) -> None:
    tracker = ReadTracker(tmp_path)
    items = [_item("a"), _item("b")]
    tracker.mark_read("a", "b")

    assert tracker.unread(items) == []
    assert tracker.count_unread(items) == 0


def test_unread_none_read(tmp_path: Path) -> None:
    tracker = ReadTracker(tmp_path)
    items = [_item("a"), _item("b")]

    assert len(tracker.unread(items)) == 2
    assert tracker.count_unread(items) == 2


def test_creates_data_dir(tmp_path: Path) -> None:
    nested = tmp_path / "deep" / "nested"
    tracker = ReadTracker(nested)
    tracker.mark_read("item")
    assert (nested / "read.txt").exists()


# -- Temporary: test coverage annotations (will revert) --------------------


def test_coverage_noop_partial() -> None:
    """Only cover some branches to test partial coverage annotations."""
    assert _coverage_test_noop(50) == "medium"
    assert _coverage_test_noop(5) == "small"
