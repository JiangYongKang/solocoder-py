from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from .states import CoordinatorDecision


@dataclass
class DecisionLogEntry:
    transaction_id: str
    decision: CoordinatorDecision
    participant_ids: List[str]
    timestamp: datetime = field(default_factory=datetime.now)
    executed: bool = False


class DecisionLog:
    def __init__(self) -> None:
        self._entries: Dict[str, DecisionLogEntry] = {}

    def record_decision(
        self,
        transaction_id: str,
        decision: CoordinatorDecision,
        participant_ids: List[str],
    ) -> DecisionLogEntry:
        entry = DecisionLogEntry(
            transaction_id=transaction_id,
            decision=decision,
            participant_ids=list(participant_ids),
        )
        self._entries[transaction_id] = entry
        return entry

    def mark_executed(self, transaction_id: str) -> None:
        entry = self._entries.get(transaction_id)
        if entry is not None:
            entry.executed = True

    def get_entry(self, transaction_id: str) -> Optional[DecisionLogEntry]:
        return self._entries.get(transaction_id)

    def get_pending_entries(self) -> List[DecisionLogEntry]:
        return [e for e in self._entries.values() if not e.executed]

    def has_entry(self, transaction_id: str) -> bool:
        return transaction_id in self._entries

    def clear(self) -> None:
        self._entries.clear()

    def count(self) -> int:
        return len(self._entries)
