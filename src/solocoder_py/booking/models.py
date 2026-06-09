from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class BookingError(Exception):
    pass


class InsufficientCapacityError(BookingError):
    pass


class TimeSlotNotFoundError(BookingError):
    pass


class TimeSlotConflictError(BookingError):
    pass


class InvalidTimeRangeError(BookingError):
    pass


class BookingNotFoundError(BookingError):
    pass


class BookingStatus(str, Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


@dataclass
class TimeSlot:
    id: str
    start_time: datetime
    end_time: datetime
    capacity: int
    booked_count: int = 0

    def __post_init__(self) -> None:
        if self.start_time >= self.end_time:
            raise InvalidTimeRangeError(
                f"start_time must be before end_time: {self.start_time} >= {self.end_time}"
            )
        if self.capacity <= 0:
            raise InvalidTimeRangeError(
                f"capacity must be positive: {self.capacity}"
            )
        if self.booked_count < 0:
            raise InvalidTimeRangeError(
                f"booked_count cannot be negative: {self.booked_count}"
            )
        if self.booked_count > self.capacity:
            raise InsufficientCapacityError(
                f"booked_count cannot exceed capacity: {self.booked_count} > {self.capacity}"
            )

    @property
    def available_capacity(self) -> int:
        return self.capacity - self.booked_count

    def overlaps(self, other_start: datetime, other_end: datetime) -> bool:
        return self.start_time < other_end and other_start < self.end_time

    def reserve(self, quantity: int) -> None:
        if quantity <= 0:
            raise InvalidTimeRangeError("reserve quantity must be positive")
        if quantity > self.available_capacity:
            raise InsufficientCapacityError(
                f"Insufficient capacity in slot {self.id}: "
                f"requested {quantity}, available {self.available_capacity}"
            )
        self.booked_count += quantity

    def release(self, quantity: int) -> None:
        if quantity <= 0:
            raise InvalidTimeRangeError("release quantity must be positive")
        if quantity > self.booked_count:
            raise InvalidTimeRangeError(
                f"release quantity {quantity} exceeds booked_count {self.booked_count}"
            )
        self.booked_count -= quantity


@dataclass
class SubBooking:
    slot_id: str
    start_time: datetime
    end_time: datetime
    quantity: int

    def __post_init__(self) -> None:
        if self.start_time >= self.end_time:
            raise InvalidTimeRangeError(
                f"SubBooking start_time must be before end_time: {self.start_time} >= {self.end_time}"
            )
        if self.quantity <= 0:
            raise InvalidTimeRangeError(
                f"SubBooking quantity must be positive: {self.quantity}"
            )


@dataclass
class Booking:
    id: str
    user_id: str
    start_time: datetime
    end_time: datetime
    sub_bookings: List[SubBooking] = field(default_factory=list)
    status: BookingStatus = BookingStatus.CONFIRMED
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def create(
        cls,
        user_id: str,
        start_time: datetime,
        end_time: datetime,
        sub_bookings: Optional[List[SubBooking]] = None,
    ) -> "Booking":
        if start_time >= end_time:
            raise InvalidTimeRangeError(
                f"Booking start_time must be before end_time: {start_time} >= {end_time}"
            )
        return cls(
            id=str(uuid.uuid4()),
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            sub_bookings=sub_bookings or [],
            status=BookingStatus.CONFIRMED,
            created_at=datetime.now(),
        )

    def total_quantity(self) -> int:
        return sum(sb.quantity for sb in self.sub_bookings)

    def is_cancelled(self) -> bool:
        return self.status == BookingStatus.CANCELLED
