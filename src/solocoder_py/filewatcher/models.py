from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional


class ChangeType(str, Enum):
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


@dataclass
class FileEvent:
    change_type: ChangeType
    path: Path
    timestamp: datetime
    old_path: Optional[Path] = None

    def __post_init__(self) -> None:
        self.path = Path(self.path)
        if self.old_path is not None:
            self.old_path = Path(self.old_path)
        if not isinstance(self.timestamp, datetime):
            raise ValueError("timestamp must be a datetime object")
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=timezone.utc)

    @classmethod
    def created(cls, path: Path | str, timestamp: Optional[datetime] = None) -> "FileEvent":
        return cls(
            change_type=ChangeType.CREATED,
            path=Path(path),
            timestamp=timestamp or datetime.now(timezone.utc),
        )

    @classmethod
    def modified(cls, path: Path | str, timestamp: Optional[datetime] = None) -> "FileEvent":
        return cls(
            change_type=ChangeType.MODIFIED,
            path=Path(path),
            timestamp=timestamp or datetime.now(timezone.utc),
        )

    @classmethod
    def deleted(cls, path: Path | str, timestamp: Optional[datetime] = None) -> "FileEvent":
        return cls(
            change_type=ChangeType.DELETED,
            path=Path(path),
            timestamp=timestamp or datetime.now(timezone.utc),
        )

    @classmethod
    def renamed(
        cls,
        old_path: Path | str,
        new_path: Path | str,
        timestamp: Optional[datetime] = None,
    ) -> "FileEvent":
        return cls(
            change_type=ChangeType.RENAMED,
            path=Path(new_path),
            timestamp=timestamp or datetime.now(timezone.utc),
            old_path=Path(old_path),
        )

    @property
    def is_rename(self) -> bool:
        return self.change_type == ChangeType.RENAMED and self.old_path is not None
