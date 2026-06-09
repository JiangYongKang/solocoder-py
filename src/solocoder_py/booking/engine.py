from __future__ import annotations

import threading
import uuid
from datetime import date, datetime, time, timedelta
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

    def _datetime_falls_on_holiday(self, dt: datetime) -> bool:
        return dt.date() in self._holidays

    def _split_non_holiday_ranges(
        self, start: datetime, end: datetime
    ) -> List[Tuple[datetime, datetime]]:
        if start >= end:
            return []

        result: List[Tuple[datetime, datetime]] = []
        segment_start = start
        current_date = start.date()
        end_date = end.date()

        while current_date <= end_date:
            day_start = datetime.combine(current_date, time.min)
            day_end = datetime.combine(current_date + timedelta(days=1), time.min)

            seg_end_in_day = min(end, day_end)

            if current_date in self._holidays:
                if result and result[-1][1] == segment_start:
                    pass
                segment_start = seg_end_in_day
            else:
                if segment_start < seg_end_in_day:
                    result.append((segment_start, seg_end_in_day))
                segment_start = seg_end_in_day

            current_date = current_date + timedelta(days=1)

        return result

    def _slot_has_available_non_holiday_overlap(
        self, slot: TimeSlot, query_start: datetime, query_end: datetime
    ) -> bool:
        if slot.available_capacity <= 0:
            return False
        overlap_start = max(slot.start_time, query_start)
        overlap_end = min(slot.end_time, query_end)
        if overlap_start >= overlap_end:
            return False
        non_holiday_segs = self._split_non_holiday_ranges(overlap_start, overlap_end)
        return len(non_holiday_segs) > 0

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
                and self._slot_has_available_non_holiday_overlap(
                    slot, start_time, end_time
                )
            ]

    def _find_overlapping_slots(
        self, start_time: datetime, end_time: datetime
    ) -> List[TimeSlot]:
        slots = [
            slot
            for slot in self._slots.values()
            if slot.overlaps(start_time, end_time)
        ]
        slots.sort(key=lambda s: s.start_time)
        return slots

    def _validate_no_gaps_for_range(
        self,
        seg_start: datetime,
        seg_end: datetime,
        slots: List[TimeSlot],
    ) -> None:
        current = seg_start
        for slot in slots:
            s_overlap = max(slot.start_time, seg_start)
            e_overlap = min(slot.end_time, seg_end)
            if s_overlap >= e_overlap:
                continue
            if s_overlap > current:
                raise TimeSlotConflictError(
                    f"Gap detected between {current} and {s_overlap}"
                )
            current = max(current, e_overlap)
            if current >= seg_end:
                break

        if current < seg_end:
            raise TimeSlotConflictError(
                f"No time slot covers up to {seg_end}, only up to {current}"
            )

    def _split_sub_bookings_for_range(
        self,
        seg_start: datetime,
        seg_end: datetime,
        quantity: int,
        slots: List[TimeSlot],
    ) -> List[SubBooking]:
        sub_bookings: List[SubBooking] = []
        for slot in slots:
            sb_start = max(slot.start_time, seg_start)
            sb_end = min(slot.end_time, seg_end)
            if sb_start < sb_end:
                sub_bookings.append(
                    SubBooking(
                        slot_id=slot.id,
                        start_time=sb_start,
                        end_time=sb_end,
                        quantity=quantity,
                    )
                )
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
            non_holiday_segs = self._split_non_holiday_ranges(start_time, end_time)
            if not non_holiday_segs:
                raise TimeSlotConflictError(
                    f"Booking range {start_time} to {end_time} falls entirely on holidays"
                )

            all_sub_bookings: List[SubBooking] = []
            for seg_start, seg_end in non_holiday_segs:
                overlapping_slots = self._find_overlapping_slots(seg_start, seg_end)
                if not overlapping_slots:
                    raise TimeSlotConflictError(
                        f"No time slots cover the requested range: {seg_start} to {seg_end}"
                    )
                self._validate_no_gaps_for_range(
                    seg_start, seg_end, overlapping_slots
                )
                seg_subs = self._split_sub_bookings_for_range(
                    seg_start, seg_end, quantity, overlapping_slots
                )
                all_sub_bookings.extend(seg_subs)

            if not all_sub_bookings:
                raise TimeSlotConflictError(
                    f"No valid sub-bookings could be created for range {start_time} to {end_time}"
                )

            applied: List[Tuple[str, int]] = []
            try:
                for sb in all_sub_bookings:
                    slot = self._slots[sb.slot_id]
                    slot.reserve(sb.quantity)
                    applied.append((sb.slot_id, sb.quantity))

                booking = Booking.create(
                    user_id=user_id,
                    start_time=start_time,
                    end_time=end_time,
                    sub_bookings=all_sub_bookings,
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
