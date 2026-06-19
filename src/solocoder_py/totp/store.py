from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .models import UserTotpRecord


@dataclass
class InMemoryTotpStore:
    records: dict[str, UserTotpRecord] = field(default_factory=dict)

    def get_record(self, user_id: str) -> Optional[UserTotpRecord]:
        return self.records.get(user_id)

    def store_record(self, user_id: str, record: UserTotpRecord) -> None:
        self.records[user_id] = record

    def delete_record(self, user_id: str) -> bool:
        if user_id in self.records:
            del self.records[user_id]
            return True
        return False

    def has_record(self, user_id: str) -> bool:
        return user_id in self.records

    def clear(self) -> None:
        self.records.clear()

    def __len__(self) -> int:
        return len(self.records)
