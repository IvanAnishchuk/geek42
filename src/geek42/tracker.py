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
