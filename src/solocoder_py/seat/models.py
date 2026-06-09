from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SeatState(str, Enum):
    AVAILABLE = "available"
    RESERVED = "reserved"
    OCCUPIED = "occupied"


@dataclass(frozen=True)
class SeatId:
    row: int
    column: int

    def __post_init__(self) -> None:
        if self.row < 0:
            raise ValueError("row cannot be negative")
        if self.column < 0:
            raise ValueError("column cannot be negative")

    def __str__(self) -> str:
        return f"R{self.row}C{self.column}"


@dataclass
class Seat:
    seat_id: SeatId
    state: SeatState = SeatState.AVAILABLE
    reserved_by: Optional[str] = None
    reserved_at: Optional[float] = None
    occupied_by: Optional[str] = None

    def __post_init__(self) -> None:
        if self.seat_id is None:
            raise ValueError("seat_id cannot be None")

    @property
    def is_available(self) -> bool:
        return self.state == SeatState.AVAILABLE

    @property
    def is_reserved(self) -> bool:
        return self.state == SeatState.RESERVED

    @property
    def is_occupied(self) -> bool:
        return self.state == SeatState.OCCUPIED

    def is_reserved_by(self, user_id: str) -> bool:
        return self.state == SeatState.RESERVED and self.reserved_by == user_id

    def is_occupied_by(self, user_id: str) -> bool:
        return self.state == SeatState.OCCUPIED and self.occupied_by == user_id

    def reserve(self, user_id: str, now: float) -> None:
        if self.state != SeatState.AVAILABLE:
            raise ValueError(f"Seat is not available")
        if not user_id:
            raise ValueError("user_id cannot be empty")
        self.state = SeatState.RESERVED
        self.reserved_by = user_id
        self.reserved_at = now

    def cancel_reservation(self, user_id: str) -> None:
        if self.state != SeatState.RESERVED:
            raise ValueError("Seat is not reserved")
        if self.reserved_by != user_id:
            raise ValueError("Reservation does not belong to this user")
        self.state = SeatState.AVAILABLE
        self.reserved_by = None
        self.reserved_at = None

    def confirm_occupancy(self, user_id: str) -> None:
        if self.state != SeatState.RESERVED:
            raise ValueError("Seat is not reserved")
        if self.reserved_by != user_id:
            raise ValueError("Reservation does not belong to this user")
        self.state = SeatState.OCCUPIED
        self.occupied_by = user_id
        self.reserved_by = None
        self.reserved_at = None

    def force_release(self) -> None:
        self.state = SeatState.AVAILABLE
        self.reserved_by = None
        self.reserved_at = None
        self.occupied_by = None

    def is_reservation_expired(self, now: float, timeout_seconds: float) -> bool:
        if self.state != SeatState.RESERVED:
            return False
        if self.reserved_at is None:
            return False
        return (now - self.reserved_at) >= timeout_seconds
