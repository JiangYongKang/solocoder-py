from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, List, Optional


def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AuditLogEntry:
    index: int
    event_type: str
    subject: str
    target: str
    timestamp: float
    details: Any = None
    previous_hash: str = ""
    hash: str = ""

    def content_for_hash(self) -> str:
        parts = [
            str(self.index),
            self.event_type,
            self.subject,
            self.target,
            str(self.timestamp),
            str(self.details) if self.details is not None else "",
            self.previous_hash,
        ]
        return "|".join(parts)

    def compute_hash(self) -> str:
        return compute_hash(self.content_for_hash())


@dataclass
class VerificationResult:
    index: int
    valid: bool
    expected_hash: str = ""
    actual_hash: str = ""
    message: str = ""
    is_propagated_failure: bool = False
    anchor_check_performed: bool = False


@dataclass
class ChainState:
    length: int
    genesis_hash: str
    chain_tip_hash: str
    hashes: List[str] = field(default_factory=list)


@dataclass
class VerificationReport:
    is_valid: bool
    total_entries: int
    passed_ranges: List[tuple] = field(default_factory=list)
    failed_ranges: List[tuple] = field(default_factory=list)
    tampered_indices: List[int] = field(default_factory=list)
    results: List[VerificationResult] = field(default_factory=list)
    first_tampered_index: Optional[int] = None

    def summary(self) -> str:
        if self.total_entries == 0:
            return "Audit log is empty, nothing to verify."
        if self.is_valid:
            return f"All {self.total_entries} entries verified successfully."
        tampered = ", ".join(str(i) for i in self.tampered_indices)
        return (
            f"Verification FAILED: {len(self.tampered_indices)} tampered entries "
            f"(indices: {tampered}). First tampered at index {self.first_tampered_index}."
        )
