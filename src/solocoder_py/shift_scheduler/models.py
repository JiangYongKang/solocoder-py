from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional


class SwapRequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EFFECTIVE = "effective"


class GapType(str, Enum):
    UNCOVERED = "uncovered"
    DUPLICATE = "duplicate"


@dataclass(frozen=True)
class StaffId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("StaffId cannot be empty")

    def __str__(self) -> str:
        return self.value


@dataclass
class Staff:
    staff_id: StaffId
    name: str

    def __post_init__(self) -> None:
        if self.staff_id is None:
            raise ValueError("staff_id cannot be None")
        if not self.name or not self.name.strip():
            raise ValueError("name cannot be empty")


@dataclass
class ShiftAssignment:
    shift_date: date
    staff_id: StaffId

    def __post_init__(self) -> None:
        if self.shift_date is None:
            raise ValueError("shift_date cannot be None")
        if self.staff_id is None:
            raise ValueError("staff_id cannot be None")


@dataclass
class SwapRequest:
    request_id: str
    requester_id: StaffId
    responder_id: StaffId
    requester_date: date
    responder_date: date
    status: SwapRequestStatus = SwapRequestStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not self.request_id or not self.request_id.strip():
            raise ValueError("request_id cannot be empty")
        if self.requester_id is None:
            raise ValueError("requester_id cannot be None")
        if self.responder_id is None:
            raise ValueError("responder_id cannot be None")
        if self.requester_date is None:
            raise ValueError("requester_date cannot be None")
        if self.responder_date is None:
            raise ValueError("responder_date cannot be None")
        if self.requester_id == self.responder_id:
            raise ValueError("Cannot swap shifts with yourself")

    def approve(self) -> None:
        if self.status != SwapRequestStatus.PENDING:
            raise ValueError("Swap request is not pending")
        self.status = SwapRequestStatus.APPROVED
        self.processed_at = datetime.now()

    def reject(self) -> None:
        if self.status != SwapRequestStatus.PENDING:
            raise ValueError("Swap request is not pending")
        self.status = SwapRequestStatus.REJECTED
        self.processed_at = datetime.now()

    def mark_effective(self) -> None:
        if self.status != SwapRequestStatus.APPROVED:
            raise ValueError("Swap request must be approved before marking effective")
        self.status = SwapRequestStatus.EFFECTIVE

    @property
    def is_pending(self) -> bool:
        return self.status == SwapRequestStatus.PENDING

    @property
    def is_approved(self) -> bool:
        return self.status == SwapRequestStatus.APPROVED

    @property
    def is_rejected(self) -> bool:
        return self.status == SwapRequestStatus.REJECTED

    @property
    def is_effective(self) -> bool:
        return self.status == SwapRequestStatus.EFFECTIVE


@dataclass
class GapReport:
    gap_type: GapType
    shift_date: date
    staff_ids: List[StaffId] = field(default_factory=list)
    message: str = ""

    def __post_init__(self) -> None:
        if self.shift_date is None:
            raise ValueError("shift_date cannot be None")

    @property
    def is_uncovered(self) -> bool:
        return self.gap_type == GapType.UNCOVERED

    @property
    def is_duplicate(self) -> bool:
        return self.gap_type == GapType.DUPLICATE


@dataclass
class ValidationResult:
    is_valid: bool
    gaps: List[GapReport] = field(default_factory=list)

    @property
    def uncovered_count(self) -> int:
        return sum(1 for g in self.gaps if g.is_uncovered)

    @property
    def duplicate_count(self) -> int:
        return sum(1 for g in self.gaps if g.is_duplicate)
