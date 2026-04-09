"""Track read/unread state for news items."""

from __future__ import annotations

from pathlib import Path

from .models import NewsItem


class ReadTracker:
    """Persists read item IDs to a plain text file in the data directory."""

    def __init__(self, data_dir: Path) -> None:
        self.path = data_dir / "read.txt"
        self._ids: set[str] | None = None

    @property
    def read_ids(self) -> set[str]:
        if self._ids is None:
            if self.path.exists():
                text = self.path.read_text(encoding="utf-8").strip()
                self._ids = set(text.splitlines()) if text else set()
            else:
                self._ids = set()
        return self._ids

    def is_read(self, item_id: str) -> bool:
        return item_id in self.read_ids

    def mark_read(self, *item_ids: str) -> None:
        self.read_ids.update(item_ids)
        self._save()

    def unread(self, items: list[NewsItem]) -> list[NewsItem]:
        return [i for i in items if not self.is_read(i.id)]

    def count_unread(self, items: list[NewsItem]) -> int:
        return sum(1 for i in items if not self.is_read(i.id))

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            "\n".join(sorted(self.read_ids)) + "\n",
            encoding="utf-8",
        )
