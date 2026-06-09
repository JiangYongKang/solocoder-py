from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .clock import Clock, SystemClock
from .exceptions import (
    ConsecutiveSeatsNotFoundError,
    InvalidSeatCountError,
    SeatAlreadyOccupiedError,
    SeatAlreadyReservedError,
    SeatNotFoundError,
    SeatNotReservedError,
    SeatReservationError,
    SeatReservationExpiredError,
    SeatReservationMismatchError,
)
from .models import Seat, SeatId, SeatState


@dataclass
class SeatReservationManager:
    rows: int
    columns: int
    default_reservation_timeout: float = 300.0
    cleanup_interval: float = 1.0
    clock: Clock = field(default_factory=SystemClock)
    _seats: Dict[SeatId, Seat] = field(default_factory=dict, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    _stop_cleanup: threading.Event = field(default_factory=threading.Event, init=False)
    _cleanup_thread: Optional[threading.Thread] = field(default=None, init=False)

    def __post_init__(self) -> None:
        if self.rows <= 0:
            raise ValueError("rows must be positive")
        if self.columns <= 0:
            raise ValueError("columns must be positive")
        if self.default_reservation_timeout <= 0:
            raise ValueError("default_reservation_timeout must be positive")
        if self.cleanup_interval <= 0:
            raise ValueError("cleanup_interval must be positive")
        self._seats = {}
        for row in range(self.rows):
            for col in range(self.columns):
                seat_id = SeatId(row=row, column=col)
                self._seats[seat_id] = Seat(seat_id=seat_id)
        self._start_cleanup_thread()

    def _start_cleanup_thread(self) -> None:
        self._stop_cleanup.clear()
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            name="SeatReservationManager-Cleanup",
            daemon=True,
        )
        self._cleanup_thread.start()

    def _cleanup_loop(self) -> None:
        while not self._stop_cleanup.is_set():
            try:
                self._cleanup_expired_reservations()
            except Exception:
                pass
            self._stop_cleanup.wait(self.cleanup_interval)

    def _cleanup_expired_reservations(self) -> int:
        now = self.clock.now()
        released = 0
        with self._lock:
            for seat in self._seats.values():
                if (
                    seat.state == SeatState.RESERVED
                    and seat.is_reservation_expired(now, self.default_reservation_timeout)
                ):
                    seat.force_release()
                    released += 1
        return released

    def shutdown(self) -> None:
        self._stop_cleanup.set()
        if self._cleanup_thread is not None:
            self._cleanup_thread.join(timeout=5)
            self._cleanup_thread = None

    def _expire_reservation_if_needed(self, seat: Seat, now: float) -> None:
        if seat.state == SeatState.RESERVED and seat.is_reservation_expired(
            now, self.default_reservation_timeout
        ):
            seat.force_release()

    def _get_seat(self, seat_id: SeatId) -> Seat:
        seat = self._seats.get(seat_id)
        if seat is None:
            raise SeatNotFoundError(f"Seat {seat_id} not found")
        return seat

    def _get_seat_or_raise(self, row: int, column: int) -> Seat:
        seat_id = SeatId(row=row, column=column)
        return self._get_seat(seat_id)

    def list_available_seats(self) -> List[SeatId]:
        now = self.clock.now()
        with self._lock:
            result: List[SeatId] = []
            for seat in self._seats.values():
                self._expire_reservation_if_needed(seat, now)
                if seat.is_available:
                    result.append(seat.seat_id)
            return sorted(result, key=lambda s: (s.row, s.column))

    def list_all_seats(self) -> List[Seat]:
        now = self.clock.now()
        with self._lock:
            result: List[Seat] = []
            for seat in self._seats.values():
                self._expire_reservation_if_needed(seat, now)
                snapshot = Seat(
                    seat_id=seat.seat_id,
                    state=seat.state,
                    reserved_by=seat.reserved_by,
                    reserved_at=seat.reserved_at,
                    occupied_by=seat.occupied_by,
                )
                result.append(snapshot)
            return sorted(result, key=lambda s: (s.seat_id.row, s.seat_id.column))

    def get_seat(self, row: int, column: int) -> Optional[Seat]:
        with self._lock:
            try:
                seat = self._get_seat_or_raise(row, column)
            except SeatNotFoundError:
                return None
            now = self.clock.now()
            self._expire_reservation_if_needed(seat, now)
            return Seat(
                seat_id=seat.seat_id,
                state=seat.state,
                reserved_by=seat.reserved_by,
                reserved_at=seat.reserved_at,
                occupied_by=seat.occupied_by,
            )

    def reserve_seat(self, row: int, column: int, user_id: str) -> bool:
        if not user_id:
            raise ValueError("user_id cannot be empty")
        now = self.clock.now()
        with self._lock:
            seat = self._get_seat_or_raise(row, column)
            self._expire_reservation_if_needed(seat, now)

            if seat.state == SeatState.OCCUPIED:
                raise SeatAlreadyOccupiedError(f"Seat {seat.seat_id} is already occupied")
            if seat.state == SeatState.RESERVED:
                raise SeatAlreadyReservedError(f"Seat {seat.seat_id} is already reserved")

            seat.reserve(user_id, now)
            return True

    def reserve_consecutive_seats(self, count: int, user_id: str) -> List[SeatId]:
        return self.reserve_consecutive_seats_in_row(count, user_id, row=None)

    def reserve_consecutive_seats_in_row(
        self, count: int, user_id: str, row: Optional[int] = None
    ) -> List[SeatId]:
        if not user_id:
            raise ValueError("user_id cannot be empty")
        if count <= 0:
            raise InvalidSeatCountError("count must be positive")
        if count > self.columns:
            raise ConsecutiveSeatsNotFoundError(
                f"Cannot reserve {count} consecutive seats: exceeds columns per row ({self.columns})"
            )
        if row is not None and (row < 0 or row >= self.rows):
            raise SeatNotFoundError(f"Row {row} does not exist")

        now = self.clock.now()
        with self._lock:
            rows_to_check: range = range(self.rows) if row is None else range(row, row + 1)

            for r in rows_to_check:
                consecutive_block = self._find_consecutive_available_block(r, count, now)
                if consecutive_block is not None:
                    seat_ids: List[SeatId] = []
                    for c in consecutive_block:
                        seat = self._seats[SeatId(row=r, column=c)]
                        if seat.state != SeatState.AVAILABLE:
                            for sid in seat_ids:
                                self._seats[sid].force_release()
                            break
                        seat.reserve(user_id, now)
                        seat_ids.append(seat.seat_id)
                    else:
                        return seat_ids

            if row is not None:
                raise ConsecutiveSeatsNotFoundError(
                    f"No {count} consecutive available seats found in row {row}"
                )
            raise ConsecutiveSeatsNotFoundError(
                f"No {count} consecutive available seats found"
            )

    def _find_consecutive_available_block(
        self, row: int, count: int, now: float
    ) -> Optional[range]:
        consecutive_count = 0
        start_col = 0
        for c in range(self.columns):
            seat = self._seats[SeatId(row=row, column=c)]
            self._expire_reservation_if_needed(seat, now)
            if seat.is_available:
                consecutive_count += 1
                if consecutive_count == count:
                    return range(start_col, start_col + count)
            else:
                consecutive_count = 0
                start_col = c + 1
        return None

    def cancel_reservation(self, row: int, column: int, user_id: str) -> bool:
        if not user_id:
            raise ValueError("user_id cannot be empty")
        now = self.clock.now()
        with self._lock:
            seat = self._get_seat_or_raise(row, column)

            if seat.state == SeatState.AVAILABLE:
                raise SeatNotReservedError(f"Seat {seat.seat_id} is not reserved")
            if seat.state == SeatState.OCCUPIED:
                raise SeatReservationError(f"Seat {seat.seat_id} is already occupied, cannot cancel reservation")

            if seat.is_reservation_expired(now, self.default_reservation_timeout):
                reserved_by = seat.reserved_by
                seat.force_release()
                if reserved_by == user_id:
                    raise SeatReservationExpiredError(
                        f"Reservation for seat {seat.seat_id} has expired"
                    )
                raise SeatReservationMismatchError(
                    f"Seat {seat.seat_id} is not reserved by user {user_id}"
                )

            if seat.reserved_by != user_id:
                raise SeatReservationMismatchError(
                    f"Seat {seat.seat_id} is not reserved by user {user_id}"
                )

            seat.cancel_reservation(user_id)
            return True

    def confirm_occupancy(self, row: int, column: int, user_id: str) -> bool:
        if not user_id:
            raise ValueError("user_id cannot be empty")
        now = self.clock.now()
        with self._lock:
            seat = self._get_seat_or_raise(row, column)

            if seat.state == SeatState.AVAILABLE:
                raise SeatNotReservedError(f"Seat {seat.seat_id} is not reserved")
            if seat.state == SeatState.OCCUPIED:
                raise SeatAlreadyOccupiedError(f"Seat {seat.seat_id} is already occupied")

            if seat.is_reservation_expired(now, self.default_reservation_timeout):
                reserved_by = seat.reserved_by
                seat.force_release()
                if reserved_by == user_id:
                    raise SeatReservationExpiredError(
                        f"Reservation for seat {seat.seat_id} has expired"
                    )
                raise SeatReservationMismatchError(
                    f"Seat {seat.seat_id} is not reserved by user {user_id}"
                )

            if seat.reserved_by != user_id:
                raise SeatReservationMismatchError(
                    f"Seat {seat.seat_id} is not reserved by user {user_id}"
                )

            seat.confirm_occupancy(user_id)
            return True

    def count_available(self) -> int:
        return len(self.list_available_seats())

    def count_available_in_row(self, row: int) -> int:
        if row < 0 or row >= self.rows:
            raise SeatNotFoundError(f"Row {row} does not exist")
        return sum(1 for s in self.list_available_seats() if s.row == row)

    def force_release_seat(self, row: int, column: int) -> bool:
        with self._lock:
            try:
                seat = self._get_seat_or_raise(row, column)
            except SeatNotFoundError:
                return False
            if seat.state == SeatState.AVAILABLE:
                return False
            seat.force_release()
            return True

    def clear(self) -> None:
        with self._lock:
            for seat in self._seats.values():
                seat.force_release()
