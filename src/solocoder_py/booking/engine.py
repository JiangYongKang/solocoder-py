from __future__ import annotations

import threading
import uuid
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

from .models import (
    Booking,
    BookingError,
    BookingNotFoundError,
    BookingStatus,
    InsufficientCapacityError,
    InvalidTimeRangeError,
    SubBooking,
    TimeSlot,
    TimeSlotConflictError,
    TimeSlotNotFoundError,
)


class BookingEngine:
    def __init__(self) -> None:
        self._slots: Dict[str, TimeSlot] = {}
        self._bookings: Dict[str, Booking] = {}
        self._holidays: Set[date] = set()
        self._lock = threading.RLock()

    def add_holiday(self, holiday_date: date) -> None:
        with self._lock:
            self._holidays.add(holiday_date)

    def remove_holiday(self, holiday_date: date) -> None:
        with self._lock:
            self._holidays.discard(holiday_date)

    def list_holidays(self) -> List[date]:
        return sorted(self._holidays)

    def is_holiday(self, check_date: date) -> bool:
        return check_date in self._holidays

    def _slot_is_on_holiday(self, slot: TimeSlot) -> bool:
        start_date = slot.start_time.date()
        end_date = slot.end_time.date()
        current = start_date
        while current <= end_date:
            if current in self._holidays:
                return True
            current = current + timedelta(days=1)
        return False

    def create_time_slot(
        self,
        start_time: datetime,
        end_time: datetime,
        capacity: int,
    ) -> TimeSlot:
        if start_time >= end_time:
            raise InvalidTimeRangeError(
                f"start_time must be before end_time: {start_time} >= {end_time}"
            )
        if capacity <= 0:
            raise InvalidTimeRangeError(f"capacity must be positive: {capacity}")

        with self._lock:
            slot_id = str(uuid.uuid4())
            slot = TimeSlot(
                id=slot_id,
                start_time=start_time,
                end_time=end_time,
                capacity=capacity,
                booked_count=0,
            )
            self._slots[slot_id] = slot
            return slot

    def get_time_slot(self, slot_id: str) -> TimeSlot:
        slot = self._slots.get(slot_id)
        if slot is None:
            raise TimeSlotNotFoundError(f"TimeSlot not found: {slot_id}")
        return slot

    def list_time_slots(self) -> List[TimeSlot]:
        return list(self._slots.values())

    def get_available_slots(
        self, start_time: datetime, end_time: datetime
    ) -> List[TimeSlot]:
        if start_time >= end_time:
            raise InvalidTimeRangeError(
                f"start_time must be before end_time: {start_time} >= {end_time}"
            )
        with self._lock:
            return [
                slot
                for slot in self._slots.values()
                if slot.overlaps(start_time, end_time)
                and slot.available_capacity > 0
                and not self._slot_is_on_holiday(slot)
            ]

    def _find_overlapping_slots(
        self, start_time: datetime, end_time: datetime
    ) -> List[TimeSlot]:
        slots = [
            slot
            for slot in self._slots.values()
            if slot.overlaps(start_time, end_time)
            and not self._slot_is_on_holiday(slot)
        ]
        slots.sort(key=lambda s: s.start_time)
        return slots

    def _validate_no_gaps(
        self,
        start_time: datetime,
        end_time: datetime,
        slots: List[TimeSlot],
    ) -> None:
        if not slots:
            raise TimeSlotConflictError(
                f"No time slots cover the requested range: {start_time} to {end_time}"
            )

        current = start_time
        for slot in slots:
            if slot.start_time > current:
                raise TimeSlotConflictError(
                    f"Gap detected between {current} and {slot.start_time}"
                )
            current = max(current, slot.end_time)

        if current < end_time:
            raise TimeSlotConflictError(
                f"No time slot covers up to {end_time}, only up to {current}"
            )

    def _split_into_sub_bookings(
        self,
        start_time: datetime,
        end_time: datetime,
        quantity: int,
        slots: List[TimeSlot],
    ) -> List[SubBooking]:
        sub_bookings: List[SubBooking] = []
        current = start_time

        for slot in slots:
            if current >= end_time:
                break
            sb_start = max(current, slot.start_time)
            sb_end = min(end_time, slot.end_time)
            if sb_start < sb_end:
                sub_bookings.append(
                    SubBooking(
                        slot_id=slot.id,
                        start_time=sb_start,
                        end_time=sb_end,
                        quantity=quantity,
                    )
                )
            current = sb_end

        return sub_bookings

    def create_booking(
        self,
        user_id: str,
        start_time: datetime,
        end_time: datetime,
        quantity: int = 1,
    ) -> Booking:
        if not user_id:
            raise BookingError("user_id cannot be empty")
        if start_time >= end_time:
            raise InvalidTimeRangeError(
                f"start_time must be before end_time: {start_time} >= {end_time}"
            )
        if quantity <= 0:
            raise InvalidTimeRangeError(f"quantity must be positive: {quantity}")

        with self._lock:
            overlapping_slots = self._find_overlapping_slots(start_time, end_time)
            self._validate_no_gaps(start_time, end_time, overlapping_slots)

            sub_bookings = self._split_into_sub_bookings(
                start_time, end_time, quantity, overlapping_slots
            )

            applied: List[Tuple[str, int]] = []
            try:
                for sb in sub_bookings:
                    slot = self._slots[sb.slot_id]
                    slot.reserve(sb.quantity)
                    applied.append((sb.slot_id, sb.quantity))

                booking = Booking.create(
                    user_id=user_id,
                    start_time=start_time,
                    end_time=end_time,
                    sub_bookings=sub_bookings,
                )
                self._bookings[booking.id] = booking
                return booking
            except Exception:
                for slot_id, qty in reversed(applied):
                    slot = self._slots.get(slot_id)
                    if slot is not None:
                        slot.release(qty)
                raise

    def cancel_booking(self, booking_id: str) -> None:
        with self._lock:
            booking = self._bookings.get(booking_id)
            if booking is None:
                raise BookingNotFoundError(f"Booking not found: {booking_id}")
            if booking.is_cancelled():
                raise BookingError(
                    f"Booking {booking_id} is already cancelled"
                )

            for sb in booking.sub_bookings:
                slot = self._slots.get(sb.slot_id)
                if slot is not None:
                    slot.release(sb.quantity)

            booking.status = BookingStatus.CANCELLED

    def get_booking(self, booking_id: str) -> Optional[Booking]:
        return self._bookings.get(booking_id)

    def list_bookings(self) -> List[Booking]:
        return list(self._bookings.values())

    def list_bookings_for_user(self, user_id: str) -> List[Booking]:
        return [b for b in self._bookings.values() if b.user_id == user_id]
