"""Track read/unread state for news items.

The tracker is a thin wrapper around a plain text file containing one
read item ID per line. It is intentionally simple — no database, no
JSON, no locking — because the geek42 CLI is single-process and
read-mostly. Race conditions across concurrent invocations are
acknowledged and considered acceptable for this use case.
"""

from __future__ import annotations

from pathlib import Path

from .models import NewsItem


class ReadTracker:
    """Persists the set of read item IDs to ``{data_dir}/read.txt``.

    The set is loaded lazily on first access and cached on the
    instance. Subsequent reads do not touch disk; mutations are
    persisted immediately. Construct a new instance per command
    invocation to pick up changes from other processes.
    """

    def __init__(self, data_dir: Path) -> None:
        """Bind the tracker to ``{data_dir}/read.txt`` (not yet read)."""
        self.path = data_dir / "read.txt"
        self._ids: set[str] | None = None

    @property
    def read_ids(self) -> set[str]:
        """The set of item IDs marked as read.

        Lazily loaded on first access. The returned set is the live
        cache; mutating it directly will not be persisted.
        Use :meth:`mark_read` to persist changes.
        """
        if self._ids is None:
            if self.path.exists():
                text = self.path.read_text(encoding="utf-8").strip()
                self._ids = set(text.splitlines()) if text else set()
            else:
                self._ids = set()
        return self._ids

    def is_read(self, item_id: str) -> bool:
        """Return whether ``item_id`` has been marked as read."""
        return item_id in self.read_ids

    def mark_read(self, *item_ids: str) -> None:
        """Mark one or more item IDs as read and persist immediately."""
        self.read_ids.update(item_ids)
        self._save()

    def unread(self, items: list[NewsItem]) -> list[NewsItem]:
        """Return only the items in ``items`` that are not yet read."""
        return [i for i in items if not self.is_read(i.id)]

    def count_unread(self, items: list[NewsItem]) -> int:
        """Return the number of items in ``items`` that are not yet read."""
        return sum(1 for i in items if not self.is_read(i.id))

    def _save(self) -> None:
        """Write the current ID set back to disk, sorted, one per line."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            "\n".join(sorted(self.read_ids)) + "\n",
            encoding="utf-8",
        )


def _cov_test_branches(x: int) -> str:
    """Nested if/elif/else — some branches taken, some not."""
    if x > 10:
        if x > 100:
            return "big"
        return "medium"
    elif x > 0:
        return "small"
    else:
        return "zero"


def _cov_test_ternary(x: int) -> int:
    """Ternary on a single line — partial branch, line is 'covered'."""
    return x if x > 0 else -x


def _cov_test_short_circuit(a: bool, b: bool) -> str:
    """Short-circuit boolean — hidden branch when first operand decides."""
    if a and b:
        return "both"
    return "nope"


def _cov_test_comprehension(items: list[int]) -> list[int]:
    """Comprehension with filter — branch inside the filter expression."""
    return [x for x in items if x > 0]


def _cov_test_try_except(x: int) -> str:
    """Try/except where except never fires."""
    try:
        return str(100 // x)
    except ZeroDivisionError:
        return "inf"


def _cov_test_or_default(val: str | None) -> str:
    """Or-default pattern — implicit branch."""
    return val or "default"
