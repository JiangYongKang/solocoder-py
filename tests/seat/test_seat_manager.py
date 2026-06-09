from __future__ import annotations

import threading
import time

import pytest

from solocoder_py.seat import (
    ConsecutiveSeatsNotFoundError,
    InvalidSeatCountError,
    ManualClock,
    Seat,
    SeatAlreadyOccupiedError,
    SeatAlreadyReservedError,
    SeatId,
    SeatNotReservedError,
    SeatReservationError,
    SeatReservationExpiredError,
    SeatReservationManager,
    SeatReservationMismatchError,
    SeatState,
)
from solocoder_py.seat.exceptions import SeatNotFoundError
from .conftest import make_manager


class TestSeatIdModel:
    def test_seat_id_creation(self):
        sid = SeatId(row=0, column=0)
        assert sid.row == 0
        assert sid.column == 0

    def test_seat_id_str(self):
        sid = SeatId(row=2, column=5)
        assert str(sid) == "R2C5"

    def test_seat_id_negative_row_rejected(self):
        with pytest.raises(ValueError, match="row cannot be negative"):
            SeatId(row=-1, column=0)

    def test_seat_id_negative_column_rejected(self):
        with pytest.raises(ValueError, match="column cannot be negative"):
            SeatId(row=0, column=-1)

    def test_seat_id_equality(self):
        a = SeatId(row=1, column=2)
        b = SeatId(row=1, column=2)
        c = SeatId(row=1, column=3)
        assert a == b
        assert a != c


class TestSeatModel:
    def test_seat_creation_defaults(self):
        seat = Seat(seat_id=SeatId(row=0, column=0))
        assert seat.state == SeatState.AVAILABLE
        assert seat.reserved_by is None
        assert seat.reserved_at is None
        assert seat.occupied_by is None
        assert seat.is_available is True
        assert seat.is_reserved is False
        assert seat.is_occupied is False

    def test_seat_seat_id_none_rejected(self):
        with pytest.raises(ValueError, match="seat_id cannot be None"):
            Seat(seat_id=None)

    def test_seat_reserve(self):
        seat = Seat(seat_id=SeatId(row=0, column=0))
        seat.reserve("user-1", 100.0)
        assert seat.state == SeatState.RESERVED
        assert seat.reserved_by == "user-1"
        assert seat.reserved_at == 100.0
        assert seat.is_available is False
        assert seat.is_reserved is True
        assert seat.is_occupied is False
        assert seat.is_reserved_by("user-1") is True
        assert seat.is_reserved_by("user-2") is False

    def test_seat_reserve_not_available(self):
        seat = Seat(seat_id=SeatId(row=0, column=0))
        seat.reserve("user-1", 100.0)
        with pytest.raises(ValueError, match="Seat is not available"):
            seat.reserve("user-2", 200.0)

    def test_seat_reserve_empty_user(self):
        seat = Seat(seat_id=SeatId(row=0, column=0))
        with pytest.raises(ValueError, match="user_id cannot be empty"):
            seat.reserve("", 100.0)

    def test_seat_cancel_reservation(self):
        seat = Seat(seat_id=SeatId(row=0, column=0))
        seat.reserve("user-1", 100.0)
        seat.cancel_reservation("user-1")
        assert seat.state == SeatState.AVAILABLE
        assert seat.reserved_by is None
        assert seat.reserved_at is None

    def test_seat_cancel_reservation_wrong_user(self):
        seat = Seat(seat_id=SeatId(row=0, column=0))
        seat.reserve("user-1", 100.0)
        with pytest.raises(ValueError, match="Reservation does not belong to this user"):
            seat.cancel_reservation("user-2")

    def test_seat_cancel_reservation_not_reserved(self):
        seat = Seat(seat_id=SeatId(row=0, column=0))
        with pytest.raises(ValueError, match="Seat is not reserved"):
            seat.cancel_reservation("user-1")

    def test_seat_confirm_occupancy(self):
        seat = Seat(seat_id=SeatId(row=0, column=0))
        seat.reserve("user-1", 100.0)
        seat.confirm_occupancy("user-1")
        assert seat.state == SeatState.OCCUPIED
        assert seat.occupied_by == "user-1"
        assert seat.reserved_by is None
        assert seat.reserved_at is None
        assert seat.is_occupied is True
        assert seat.is_occupied_by("user-1") is True
        assert seat.is_occupied_by("user-2") is False

    def test_seat_confirm_occupancy_wrong_user(self):
        seat = Seat(seat_id=SeatId(row=0, column=0))
        seat.reserve("user-1", 100.0)
        with pytest.raises(ValueError, match="Reservation does not belong to this user"):
            seat.confirm_occupancy("user-2")

    def test_seat_confirm_occupancy_not_reserved(self):
        seat = Seat(seat_id=SeatId(row=0, column=0))
        with pytest.raises(ValueError, match="Seat is not reserved"):
            seat.confirm_occupancy("user-1")

    def test_seat_force_release(self):
        seat = Seat(seat_id=SeatId(row=0, column=0))
        seat.reserve("user-1", 100.0)
        seat.force_release()
        assert seat.state == SeatState.AVAILABLE
        assert seat.reserved_by is None
        assert seat.reserved_at is None

        seat.reserve("user-2", 200.0)
        seat.confirm_occupancy("user-2")
        seat.force_release()
        assert seat.state == SeatState.AVAILABLE
        assert seat.occupied_by is None

    def test_seat_is_reservation_expired(self):
        seat = Seat(seat_id=SeatId(row=0, column=0))
        seat.reserve("user-1", 100.0)
        assert seat.is_reservation_expired(150.0, 30.0) is True
        assert seat.is_reservation_expired(129.0, 30.0) is False
        assert seat.is_reservation_expired(130.0, 30.0) is True

    def test_seat_is_reservation_expired_not_reserved(self):
        seat = Seat(seat_id=SeatId(row=0, column=0))
        assert seat.is_reservation_expired(100.0, 30.0) is False


class TestManagerInitialization:
    def test_manager_creation(self):
        manager = make_manager(rows=3, columns=5)
        assert manager.rows == 3
        assert manager.columns == 5
        assert manager.count_available() == 15

    def test_manager_zero_rows_rejected(self):
        with pytest.raises(ValueError, match="rows must be positive"):
            SeatReservationManager(rows=0, columns=5)

    def test_manager_zero_columns_rejected(self):
        with pytest.raises(ValueError, match="columns must be positive"):
            SeatReservationManager(rows=5, columns=0)

    def test_manager_zero_timeout_rejected(self):
        with pytest.raises(ValueError, match="default_reservation_timeout must be positive"):
            SeatReservationManager(rows=5, columns=5, default_reservation_timeout=0)


class TestListAvailableSeats:
    def test_list_all_available_initially(self):
        manager = make_manager(rows=2, columns=3)
        seats = manager.list_available_seats()
        assert len(seats) == 6
        assert seats[0] == SeatId(row=0, column=0)
        assert seats[-1] == SeatId(row=1, column=2)

    def test_list_available_excludes_reserved(self):
        manager = make_manager(rows=2, columns=3)
        manager.reserve_seat(0, 0, "user-1")
        seats = manager.list_available_seats()
        assert len(seats) == 5
        assert SeatId(row=0, column=0) not in seats

    def test_list_available_excludes_occupied(self):
        manager = make_manager(rows=2, columns=3)
        manager.reserve_seat(0, 0, "user-1")
        manager.confirm_occupancy(0, 0, "user-1")
        seats = manager.list_available_seats()
        assert len(seats) == 5
        assert SeatId(row=0, column=0) not in seats

    def test_list_all_seats_returns_snapshots(self):
        manager = make_manager(rows=1, columns=2)
        manager.reserve_seat(0, 0, "user-1")
        all_seats = manager.list_all_seats()
        assert len(all_seats) == 2
        assert all_seats[0].state == SeatState.RESERVED
        assert all_seats[1].state == SeatState.AVAILABLE
        all_seats[0].state = SeatState.OCCUPIED
        assert manager.get_seat(0, 0).state == SeatState.RESERVED


class TestReserveSingleSeat:
    def test_reserve_free_seat(self):
        manager = make_manager()
        result = manager.reserve_seat(0, 0, "user-1")
        assert result is True
        seat = manager.get_seat(0, 0)
        assert seat is not None
        assert seat.state == SeatState.RESERVED
        assert seat.reserved_by == "user-1"

    def test_reserve_already_reserved_seat(self):
        manager = make_manager()
        manager.reserve_seat(0, 0, "user-1")
        with pytest.raises(SeatAlreadyReservedError):
            manager.reserve_seat(0, 0, "user-2")

    def test_reserve_already_occupied_seat(self):
        manager = make_manager()
        manager.reserve_seat(0, 0, "user-1")
        manager.confirm_occupancy(0, 0, "user-1")
        with pytest.raises(SeatAlreadyOccupiedError):
            manager.reserve_seat(0, 0, "user-2")

    def test_reserve_nonexistent_seat(self):
        manager = make_manager(rows=2, columns=3)
        with pytest.raises(SeatNotFoundError):
            manager.reserve_seat(5, 0, "user-1")

    def test_reserve_empty_user_id(self):
        manager = make_manager()
        with pytest.raises(ValueError, match="user_id cannot be empty"):
            manager.reserve_seat(0, 0, "")


class TestCancelReservation:
    def test_cancel_reservation_success(self):
        manager = make_manager()
        manager.reserve_seat(0, 0, "user-1")
        result = manager.cancel_reservation(0, 0, "user-1")
        assert result is True
        assert manager.get_seat(0, 0).state == SeatState.AVAILABLE

    def test_cancel_reservation_wrong_user(self):
        manager = make_manager()
        manager.reserve_seat(0, 0, "user-1")
        with pytest.raises(SeatReservationMismatchError):
            manager.cancel_reservation(0, 0, "user-2")
        assert manager.get_seat(0, 0).state == SeatState.RESERVED

    def test_cancel_reservation_not_reserved(self):
        manager = make_manager()
        with pytest.raises(SeatNotReservedError):
            manager.cancel_reservation(0, 0, "user-1")

    def test_cancel_reservation_already_occupied(self):
        manager = make_manager()
        manager.reserve_seat(0, 0, "user-1")
        manager.confirm_occupancy(0, 0, "user-1")
        with pytest.raises(SeatReservationError):
            manager.cancel_reservation(0, 0, "user-1")

    def test_cancel_reservation_expired(self):
        clock = ManualClock()
        manager = make_manager(default_reservation_timeout=60.0, clock=clock)
        manager.reserve_seat(0, 0, "user-1")
        clock.advance(61.0)
        with pytest.raises(SeatReservationExpiredError):
            manager.cancel_reservation(0, 0, "user-1")
        assert manager.get_seat(0, 0).state == SeatState.AVAILABLE


class TestConfirmOccupancy:
    def test_confirm_occupancy_success(self):
        manager = make_manager()
        manager.reserve_seat(0, 0, "user-1")
        result = manager.confirm_occupancy(0, 0, "user-1")
        assert result is True
        seat = manager.get_seat(0, 0)
        assert seat.state == SeatState.OCCUPIED
        assert seat.occupied_by == "user-1"

    def test_confirm_occupancy_wrong_user(self):
        manager = make_manager()
        manager.reserve_seat(0, 0, "user-1")
        with pytest.raises(SeatReservationMismatchError):
            manager.confirm_occupancy(0, 0, "user-2")

    def test_confirm_occupancy_not_reserved(self):
        manager = make_manager()
        with pytest.raises(SeatNotReservedError):
            manager.confirm_occupancy(0, 0, "user-1")

    def test_confirm_occupancy_already_occupied(self):
        manager = make_manager()
        manager.reserve_seat(0, 0, "user-1")
        manager.confirm_occupancy(0, 0, "user-1")
        with pytest.raises(SeatAlreadyOccupiedError):
            manager.confirm_occupancy(0, 0, "user-1")

    def test_confirm_occupancy_expired(self):
        clock = ManualClock()
        manager = make_manager(default_reservation_timeout=60.0, clock=clock)
        manager.reserve_seat(0, 0, "user-1")
        clock.advance(61.0)
        with pytest.raises(SeatReservationExpiredError):
            manager.confirm_occupancy(0, 0, "user-1")
        assert manager.get_seat(0, 0).state == SeatState.AVAILABLE


class TestConsecutiveSeats:
    def test_reserve_consecutive_seats_success(self):
        manager = make_manager(rows=2, columns=10)
        seats = manager.reserve_consecutive_seats(3, "user-1")
        assert len(seats) == 3
        assert seats[0] == SeatId(row=0, column=0)
        assert seats[1] == SeatId(row=0, column=1)
        assert seats[2] == SeatId(row=0, column=2)
        for s in seats:
            assert manager.get_seat(s.row, s.column).state == SeatState.RESERVED

    def test_reserve_consecutive_seats_in_specific_row(self):
        manager = make_manager(rows=3, columns=10)
        manager.reserve_seat(0, 0, "blocker")
        manager.reserve_seat(0, 1, "blocker")
        seats = manager.reserve_consecutive_seats_in_row(3, "user-1", row=1)
        assert len(seats) == 3
        assert all(s.row == 1 for s in seats)
        assert seats[0].column == 0
        assert seats[1].column == 1
        assert seats[2].column == 2

    def test_reserve_consecutive_seats_not_enough(self):
        manager = make_manager(rows=2, columns=5)
        manager.reserve_seat(0, 1, "blocker")
        manager.reserve_seat(0, 3, "blocker")
        manager.reserve_seat(1, 2, "blocker")
        with pytest.raises(ConsecutiveSeatsNotFoundError):
            manager.reserve_consecutive_seats(4, "user-1")

    def test_reserve_consecutive_seats_exceeds_columns(self):
        manager = make_manager(rows=3, columns=5)
        with pytest.raises(ConsecutiveSeatsNotFoundError):
            manager.reserve_consecutive_seats(6, "user-1")

    def test_reserve_consecutive_seats_invalid_count_zero(self):
        manager = make_manager()
        with pytest.raises(InvalidSeatCountError):
            manager.reserve_consecutive_seats(0, "user-1")

    def test_reserve_consecutive_seats_invalid_count_negative(self):
        manager = make_manager()
        with pytest.raises(InvalidSeatCountError):
            manager.reserve_consecutive_seats(-1, "user-1")

    def test_reserve_consecutive_seats_invalid_row(self):
        manager = make_manager(rows=2, columns=5)
        with pytest.raises(SeatNotFoundError):
            manager.reserve_consecutive_seats_in_row(2, "user-1", row=5)

    def test_reserve_consecutive_empty_user_id(self):
        manager = make_manager()
        with pytest.raises(ValueError, match="user_id cannot be empty"):
            manager.reserve_consecutive_seats(2, "")

    def test_reserve_consecutive_last_seats_exactly(self):
        manager = make_manager(rows=1, columns=5)
        manager.reserve_seat(0, 0, "blocker")
        seats = manager.reserve_consecutive_seats(4, "user-1")
        assert len(seats) == 4
        assert seats[0].column == 1
        assert seats[3].column == 4

    def test_reserve_consecutive_finds_first_available_block(self):
        manager = make_manager(rows=1, columns=10)
        manager.reserve_seat(0, 0, "blocker")
        manager.reserve_seat(0, 1, "blocker")
        manager.reserve_seat(0, 5, "blocker")
        seats = manager.reserve_consecutive_seats(3, "user-1")
        assert len(seats) == 3
        assert seats[0].column == 2
        assert seats[1].column == 3
        assert seats[2].column == 4

    def test_reserve_consecutive_searches_next_row(self):
        manager = make_manager(rows=3, columns=5)
        for c in range(5):
            manager.reserve_seat(0, c, f"blocker-{c}")
        seats = manager.reserve_consecutive_seats(3, "user-1")
        assert len(seats) == 3
        assert seats[0].row == 1
        assert seats[0].column == 0


class TestReservationTimeout:
    def test_expired_reservation_auto_released_on_list(self):
        clock = ManualClock()
        manager = make_manager(default_reservation_timeout=60.0, clock=clock)
        manager.reserve_seat(0, 0, "user-1")
        assert manager.count_available() == 49
        clock.advance(61.0)
        assert manager.count_available() == 50

    def test_expired_reservation_auto_released_on_get(self):
        clock = ManualClock()
        manager = make_manager(default_reservation_timeout=60.0, clock=clock)
        manager.reserve_seat(0, 0, "user-1")
        clock.advance(61.0)
        seat = manager.get_seat(0, 0)
        assert seat.state == SeatState.AVAILABLE

    def test_expired_reservation_can_be_reserved_by_other(self):
        clock = ManualClock()
        manager = make_manager(default_reservation_timeout=60.0, clock=clock)
        manager.reserve_seat(0, 0, "user-1")
        clock.advance(61.0)
        result = manager.reserve_seat(0, 0, "user-2")
        assert result is True
        assert manager.get_seat(0, 0).reserved_by == "user-2"

    def test_not_expired_reservation_cannot_be_reserved(self):
        clock = ManualClock()
        manager = make_manager(default_reservation_timeout=60.0, clock=clock)
        manager.reserve_seat(0, 0, "user-1")
        clock.advance(59.0)
        with pytest.raises(SeatAlreadyReservedError):
            manager.reserve_seat(0, 0, "user-2")

    def test_critical_point_exactly_at_timeout_considered_expired(self):
        clock = ManualClock()
        manager = make_manager(default_reservation_timeout=60.0, clock=clock)
        manager.reserve_seat(0, 0, "user-1")
        clock.advance(60.0)
        with pytest.raises(SeatReservationExpiredError):
            manager.confirm_occupancy(0, 0, "user-1")
        assert manager.get_seat(0, 0).state == SeatState.AVAILABLE

    def test_critical_point_just_before_timeout_not_expired(self):
        clock = ManualClock()
        manager = make_manager(default_reservation_timeout=60.0, clock=clock)
        manager.reserve_seat(0, 0, "user-1")
        clock.advance(59.999)
        result = manager.confirm_occupancy(0, 0, "user-1")
        assert result is True
        assert manager.get_seat(0, 0).state == SeatState.OCCUPIED


class TestConcurrentAccess:
    def test_concurrent_reserve_same_seat_only_one_succeeds(self):
        manager = make_manager(rows=10, columns=10, default_reservation_timeout=60.0)
        results: dict[str, bool] = {}
        errors: dict[str, str] = {}
        lock = threading.Lock()

        def try_reserve(user_id: str):
            try:
                result = manager.reserve_seat(0, 0, user_id)
                with lock:
                    results[user_id] = result
            except Exception as e:
                with lock:
                    errors[user_id] = type(e).__name__

        threads = [threading.Thread(target=try_reserve, args=(f"user-{i}",)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert len(results) == 1, f"Expected 1 success, got {len(results)}: {results}"
        success_user = list(results.keys())[0]
        seat = manager.get_seat(0, 0)
        assert seat.reserved_by == success_user
        assert len(errors) == 9
        for err_type in errors.values():
            assert err_type == "SeatAlreadyReservedError"

    def test_concurrent_reserve_consecutive_no_overlap(self):
        manager = make_manager(rows=2, columns=10, default_reservation_timeout=60.0)
        all_reserved_seats: list[list[SeatId]] = []
        lock = threading.Lock()

        def try_reserve_consecutive(user_id: str, count: int):
            try:
                seats = manager.reserve_consecutive_seats(count, user_id)
                with lock:
                    all_reserved_seats.append(seats)
            except Exception:
                pass

        threads = [
            threading.Thread(target=try_reserve_consecutive, args=(f"user-{i}", 4))
            for i in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        all_sids: set[SeatId] = set()
        for seat_list in all_reserved_seats:
            for sid in seat_list:
                assert sid not in all_sids, f"Seat {sid} was allocated twice"
                all_sids.add(sid)

    def test_concurrent_confirm_same_reservation(self):
        manager = make_manager(rows=5, columns=5, default_reservation_timeout=60.0)
        manager.reserve_seat(0, 0, "user-1")

        success_count = 0
        error_types: list[str] = []
        lock = threading.Lock()

        def try_confirm():
            nonlocal success_count
            try:
                result = manager.confirm_occupancy(0, 0, "user-1")
                if result:
                    with lock:
                        success_count += 1
            except Exception as e:
                with lock:
                    error_types.append(type(e).__name__)

        threads = [threading.Thread(target=try_confirm) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert success_count == 1
        assert manager.get_seat(0, 0).state == SeatState.OCCUPIED


class TestManagerUtilities:
    def test_count_available(self):
        manager = make_manager(rows=2, columns=5)
        assert manager.count_available() == 10
        manager.reserve_seat(0, 0, "user-1")
        assert manager.count_available() == 9

    def test_count_available_in_row(self):
        manager = make_manager(rows=3, columns=5)
        assert manager.count_available_in_row(0) == 5
        manager.reserve_seat(0, 0, "user-1")
        manager.reserve_seat(0, 1, "user-1")
        assert manager.count_available_in_row(0) == 3
        assert manager.count_available_in_row(1) == 5

    def test_count_available_in_row_invalid(self):
        manager = make_manager(rows=2, columns=5)
        with pytest.raises(SeatNotFoundError):
            manager.count_available_in_row(5)

    def test_get_seat_nonexistent_returns_none(self):
        manager = make_manager(rows=2, columns=5)
        assert manager.get_seat(10, 0) is None

    def test_get_seat_returns_snapshot(self):
        manager = make_manager()
        manager.reserve_seat(0, 0, "user-1")
        seat = manager.get_seat(0, 0)
        assert seat.state == SeatState.RESERVED
        seat.state = SeatState.OCCUPIED
        assert manager.get_seat(0, 0).state == SeatState.RESERVED

    def test_force_release_seat(self):
        manager = make_manager()
        manager.reserve_seat(0, 0, "user-1")
        assert manager.force_release_seat(0, 0) is True
        assert manager.get_seat(0, 0).state == SeatState.AVAILABLE

    def test_force_release_available_seat(self):
        manager = make_manager()
        assert manager.force_release_seat(0, 0) is False

    def test_force_release_nonexistent_seat(self):
        manager = make_manager(rows=2, columns=3)
        assert manager.force_release_seat(10, 0) is False

    def test_clear(self):
        manager = make_manager(rows=2, columns=3)
        manager.reserve_seat(0, 0, "user-1")
        manager.reserve_seat(0, 1, "user-2")
        manager.confirm_occupancy(0, 1, "user-2")
        assert manager.count_available() == 4
        manager.clear()
        assert manager.count_available() == 6


class TestSystemClock:
    def test_system_clock_monotonic(self):
        from solocoder_py.seat import SystemClock

        clock = SystemClock()
        t1 = clock.now()
        t2 = clock.now()
        assert t2 >= t1
        t3 = clock.now()
        assert t3 >= t2

    def test_system_clock_sleep_advances_time(self):
        from solocoder_py.seat import SystemClock

        clock = SystemClock()
        t1 = clock.now()
        clock.sleep(0.05)
        t2 = clock.now()
        elapsed = t2 - t1
        assert elapsed >= 0.04, f"Expected sleep to advance time by at least ~0.05s, got {elapsed}s"

    def test_system_clock_with_manager(self):
        from solocoder_py.seat import SystemClock

        manager = SeatReservationManager(
            rows=2, columns=3,
            default_reservation_timeout=0.05,
            cleanup_interval=0.02,
            clock=SystemClock(),
        )
        try:
            manager.reserve_seat(0, 0, "user-1")
            assert manager.count_available() == 5
            time.sleep(0.15)
            assert manager.count_available() == 6
        finally:
            manager.shutdown()


class TestManualClock:
    def test_sleep_records_history(self):
        clock = ManualClock()
        clock.sleep(10.0)
        clock.sleep(20.0)
        assert clock.sleep_history == [10.0, 20.0]

    def test_sleep_advances_time(self):
        clock = ManualClock()
        t1 = clock.now()
        clock.sleep(100.0)
        t2 = clock.now()
        assert t2 - t1 == 100.0

    def test_sleep_negative_rejected(self):
        clock = ManualClock()
        with pytest.raises(ValueError, match="Cannot sleep for negative seconds"):
            clock.sleep(-1.0)


class TestManagerConfiguration:
    def test_zero_cleanup_interval_rejected(self):
        with pytest.raises(ValueError, match="cleanup_interval must be positive"):
            SeatReservationManager(rows=5, columns=5, cleanup_interval=0)

    def test_negative_cleanup_interval_rejected(self):
        with pytest.raises(ValueError, match="cleanup_interval must be positive"):
            SeatReservationManager(rows=5, columns=5, cleanup_interval=-1)


class TestActiveAutoRelease:
    def test_cleanup_expired_reservations_direct(self):
        clock = ManualClock()
        manager = make_manager(
            rows=3, columns=5,
            default_reservation_timeout=60.0,
            clock=clock,
        )
        manager.reserve_seat(0, 0, "user-1")
        manager.reserve_seat(0, 1, "user-2")
        manager.reserve_seat(1, 0, "user-3")
        assert manager.cleanup_expired_reservations() == 0

        clock.advance(61.0)
        released = manager.cleanup_expired_reservations()
        assert released == 3
        assert manager.count_available() == 15

    def test_cleanup_expired_reservations_partial(self):
        clock = ManualClock()
        manager = make_manager(
            rows=3, columns=5,
            default_reservation_timeout=60.0,
            clock=clock,
        )
        manager.reserve_seat(0, 0, "user-1")
        clock.advance(30.0)
        manager.reserve_seat(0, 1, "user-2")
        clock.advance(31.0)
        released = manager.cleanup_expired_reservations()
        assert released == 1
        assert manager.get_seat(0, 0).state == SeatState.AVAILABLE
        assert manager.get_seat(0, 1).state == SeatState.RESERVED

    def test_cleanup_does_not_touch_occupied(self):
        clock = ManualClock()
        manager = make_manager(
            rows=2, columns=3,
            default_reservation_timeout=60.0,
            clock=clock,
        )
        manager.reserve_seat(0, 0, "user-1")
        manager.confirm_occupancy(0, 0, "user-1")
        manager.reserve_seat(0, 1, "user-2")
        clock.advance(100.0)
        released = manager.cleanup_expired_reservations()
        assert released == 1
        assert manager.get_seat(0, 0).state == SeatState.OCCUPIED
        assert manager.get_seat(0, 1).state == SeatState.AVAILABLE

    def test_active_auto_release_with_system_clock(self):
        from solocoder_py.seat import SystemClock

        manager = SeatReservationManager(
            rows=2, columns=3,
            default_reservation_timeout=0.05,
            cleanup_interval=0.02,
            clock=SystemClock(),
        )
        try:
            manager.reserve_seat(0, 0, "user-1")
            manager.reserve_seat(0, 1, "user-2")
            assert manager.count_reserved() == 2
            time.sleep(0.2)
            assert manager.count_reserved() == 0
        finally:
            manager.shutdown()

    def test_active_auto_release_without_external_calls(self):
        from solocoder_py.seat import SystemClock

        manager = SeatReservationManager(
            rows=1, columns=5,
            default_reservation_timeout=0.05,
            cleanup_interval=0.02,
            clock=SystemClock(),
        )
        try:
            manager.reserve_seat(0, 0, "user-1")
            time.sleep(0.2)
            seat = manager.get_seat(0, 0)
            assert seat is not None
            assert seat.state == SeatState.AVAILABLE
        finally:
            manager.shutdown()

    def test_shutdown_stops_cleanup_thread(self):
        from solocoder_py.seat import SystemClock

        manager = SeatReservationManager(
            rows=2, columns=3,
            cleanup_interval=0.01,
            clock=SystemClock(),
        )
        assert manager.is_cleanup_active is True
        manager.shutdown()
        assert manager.is_cleanup_active is False

    def test_shutdown_idempotent(self):
        from solocoder_py.seat import SystemClock

        manager = SeatReservationManager(
            rows=2, columns=3,
            cleanup_interval=0.01,
            clock=SystemClock(),
        )
        manager.shutdown()
        manager.shutdown()
        assert manager.is_cleanup_active is False

    def test_cleanup_errors_recorded(self):
        from solocoder_py.seat import SystemClock

        manager = SeatReservationManager(
            rows=2, columns=3,
            cleanup_interval=0.01,
            clock=SystemClock(),
        )
        try:
            assert len(manager.cleanup_errors) == 0
            original_cleanup = manager.cleanup_expired_reservations

            def broken_cleanup():
                raise RuntimeError("cleanup is broken")

            manager.cleanup_expired_reservations = broken_cleanup
            time.sleep(0.1)
            manager.cleanup_expired_reservations = original_cleanup
            assert len(manager.cleanup_errors) >= 1
            assert isinstance(manager.cleanup_errors[-1][1], RuntimeError)
            assert str(manager.cleanup_errors[-1][1]) == "cleanup is broken"
        finally:
            manager.shutdown()
