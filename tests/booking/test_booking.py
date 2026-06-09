from datetime import datetime, timedelta
import threading
import time

import pytest

from solocoder_py.booking import (
    BookingEngine,
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

from .conftest import (
    build_engine_with_24h_slots,
    build_engine_with_continuous_slots,
    build_engine_with_daily_slots,
    make_datetime,
)


class TestTimeSlotModel:
    def test_timeslot_creation_success(self):
        start = make_datetime(2026, 6, 10, 9)
        end = start + timedelta(hours=1)
        slot = TimeSlot(id="s1", start_time=start, end_time=end, capacity=10)
        assert slot.id == "s1"
        assert slot.start_time == start
        assert slot.end_time == end
        assert slot.capacity == 10
        assert slot.booked_count == 0
        assert slot.available_capacity == 10

    def test_timeslot_start_after_end_raises(self):
        start = make_datetime(2026, 6, 10, 10)
        end = make_datetime(2026, 6, 10, 9)
        with pytest.raises(InvalidTimeRangeError):
            TimeSlot(id="s1", start_time=start, end_time=end, capacity=10)

    def test_timeslot_start_equals_end_raises(self):
        start = make_datetime(2026, 6, 10, 9)
        with pytest.raises(InvalidTimeRangeError):
            TimeSlot(id="s1", start_time=start, end_time=start, capacity=10)

    def test_timeslot_negative_capacity_raises(self):
        start = make_datetime(2026, 6, 10, 9)
        end = start + timedelta(hours=1)
        with pytest.raises(InvalidTimeRangeError):
            TimeSlot(id="s1", start_time=start, end_time=end, capacity=-1)

    def test_timeslot_zero_capacity_raises(self):
        start = make_datetime(2026, 6, 10, 9)
        end = start + timedelta(hours=1)
        with pytest.raises(InvalidTimeRangeError):
            TimeSlot(id="s1", start_time=start, end_time=end, capacity=0)

    def test_timeslot_booked_exceeds_capacity_raises(self):
        start = make_datetime(2026, 6, 10, 9)
        end = start + timedelta(hours=1)
        with pytest.raises(InsufficientCapacityError):
            TimeSlot(id="s1", start_time=start, end_time=end, capacity=5, booked_count=6)

    def test_timeslot_overlaps_detection(self):
        slot = TimeSlot(
            id="s1",
            start_time=make_datetime(2026, 6, 10, 9),
            end_time=make_datetime(2026, 6, 10, 12),
            capacity=10,
        )
        assert slot.overlaps(make_datetime(2026, 6, 10, 10), make_datetime(2026, 6, 10, 11))
        assert slot.overlaps(make_datetime(2026, 6, 10, 8), make_datetime(2026, 6, 10, 10))
        assert slot.overlaps(make_datetime(2026, 6, 10, 11), make_datetime(2026, 6, 10, 13))
        assert not slot.overlaps(make_datetime(2026, 6, 10, 12), make_datetime(2026, 6, 10, 13))
        assert not slot.overlaps(make_datetime(2026, 6, 10, 8), make_datetime(2026, 6, 10, 9))

    def test_timeslot_reserve_success(self):
        slot = TimeSlot(
            id="s1",
            start_time=make_datetime(2026, 6, 10, 9),
            end_time=make_datetime(2026, 6, 10, 10),
            capacity=10,
        )
        slot.reserve(3)
        assert slot.booked_count == 3
        assert slot.available_capacity == 7

    def test_timeslot_reserve_exceeds_capacity_raises(self):
        slot = TimeSlot(
            id="s1",
            start_time=make_datetime(2026, 6, 10, 9),
            end_time=make_datetime(2026, 6, 10, 10),
            capacity=5,
        )
        with pytest.raises(InsufficientCapacityError):
            slot.reserve(6)

    def test_timeslot_reserve_zero_raises(self):
        slot = TimeSlot(
            id="s1",
            start_time=make_datetime(2026, 6, 10, 9),
            end_time=make_datetime(2026, 6, 10, 10),
            capacity=10,
        )
        with pytest.raises(InvalidTimeRangeError):
            slot.reserve(0)

    def test_timeslot_release_success(self):
        slot = TimeSlot(
            id="s1",
            start_time=make_datetime(2026, 6, 10, 9),
            end_time=make_datetime(2026, 6, 10, 10),
            capacity=10,
            booked_count=5,
        )
        slot.release(3)
        assert slot.booked_count == 2
        assert slot.available_capacity == 8

    def test_timeslot_release_exceeds_booked_raises(self):
        slot = TimeSlot(
            id="s1",
            start_time=make_datetime(2026, 6, 10, 9),
            end_time=make_datetime(2026, 6, 10, 10),
            capacity=10,
            booked_count=3,
        )
        with pytest.raises(InvalidTimeRangeError):
            slot.release(5)


class TestSubBookingModel:
    def test_subbooking_creation_success(self):
        start = make_datetime(2026, 6, 10, 9)
        end = start + timedelta(hours=1)
        sb = SubBooking(slot_id="s1", start_time=start, end_time=end, quantity=2)
        assert sb.slot_id == "s1"
        assert sb.start_time == start
        assert sb.end_time == end
        assert sb.quantity == 2

    def test_subbooking_invalid_time_raises(self):
        with pytest.raises(InvalidTimeRangeError):
            SubBooking(
                slot_id="s1",
                start_time=make_datetime(2026, 6, 10, 10),
                end_time=make_datetime(2026, 6, 10, 9),
                quantity=1,
            )

    def test_subbooking_zero_quantity_raises(self):
        with pytest.raises(InvalidTimeRangeError):
            SubBooking(
                slot_id="s1",
                start_time=make_datetime(2026, 6, 10, 9),
                end_time=make_datetime(2026, 6, 10, 10),
                quantity=0,
            )


class TestTimeSlotManagement:
    def test_create_time_slot_success(self):
        engine = BookingEngine()
        start = make_datetime(2026, 6, 10, 9)
        end = start + timedelta(hours=1)
        slot = engine.create_time_slot(start, end, 10)
        assert slot.start_time == start
        assert slot.end_time == end
        assert slot.capacity == 10
        assert slot.booked_count == 0

    def test_create_time_slot_invalid_range_raises(self):
        engine = BookingEngine()
        with pytest.raises(InvalidTimeRangeError):
            engine.create_time_slot(
                make_datetime(2026, 6, 10, 10),
                make_datetime(2026, 6, 10, 9),
                10,
            )

    def test_create_time_slot_invalid_capacity_raises(self):
        engine = BookingEngine()
        with pytest.raises(InvalidTimeRangeError):
            engine.create_time_slot(
                make_datetime(2026, 6, 10, 9),
                make_datetime(2026, 6, 10, 10),
                0,
            )

    def test_get_time_slot_success(self):
        engine = BookingEngine()
        start = make_datetime(2026, 6, 10, 9)
        slot = engine.create_time_slot(start, start + timedelta(hours=1), 10)
        found = engine.get_time_slot(slot.id)
        assert found is slot

    def test_get_time_slot_not_found_raises(self):
        engine = BookingEngine()
        with pytest.raises(TimeSlotNotFoundError):
            engine.get_time_slot("nonexistent")

    def test_list_time_slots(self):
        engine, slots = build_engine_with_continuous_slots(
            make_datetime(2026, 6, 10, 9), 5
        )
        assert len(engine.list_time_slots()) == 5

    def test_get_available_slots_within_range(self):
        engine, slots = build_engine_with_daily_slots(
            make_datetime(2026, 6, 10), 1, capacity=10
        )
        available = engine.get_available_slots(
            make_datetime(2026, 6, 10, 9),
            make_datetime(2026, 6, 10, 12),
        )
        assert len(available) == 3

    def test_get_available_slots_invalid_range_raises(self):
        engine = BookingEngine()
        with pytest.raises(InvalidTimeRangeError):
            engine.get_available_slots(
                make_datetime(2026, 6, 10, 12),
                make_datetime(2026, 6, 10, 9),
            )


class TestSingleSlotBooking:
    def test_create_booking_single_slot_success(self):
        engine, slots = build_engine_with_continuous_slots(
            make_datetime(2026, 6, 10, 9), 1, capacity=5
        )
        booking = engine.create_booking(
            user_id="user-1",
            start_time=make_datetime(2026, 6, 10, 9),
            end_time=make_datetime(2026, 6, 10, 10),
            quantity=2,
        )
        assert booking.user_id == "user-1"
        assert booking.status == BookingStatus.CONFIRMED
        assert len(booking.sub_bookings) == 1
        assert booking.total_quantity() == 2
        assert slots[0].booked_count == 2

    def test_create_booking_invalid_user_raises(self):
        engine, _ = build_engine_with_continuous_slots(
            make_datetime(2026, 6, 10, 9), 1
        )
        with pytest.raises(BookingError):
            engine.create_booking(
                user_id="",
                start_time=make_datetime(2026, 6, 10, 9),
                end_time=make_datetime(2026, 6, 10, 10),
            )

    def test_create_booking_invalid_time_raises(self):
        engine, _ = build_engine_with_continuous_slots(
            make_datetime(2026, 6, 10, 9), 1
        )
        with pytest.raises(InvalidTimeRangeError):
            engine.create_booking(
                user_id="user-1",
                start_time=make_datetime(2026, 6, 10, 10),
                end_time=make_datetime(2026, 6, 10, 9),
            )

    def test_create_booking_no_slots_raises(self):
        engine = BookingEngine()
        with pytest.raises(TimeSlotConflictError):
            engine.create_booking(
                user_id="user-1",
                start_time=make_datetime(2026, 6, 10, 9),
                end_time=make_datetime(2026, 6, 10, 10),
            )

    def test_create_booking_gap_in_slots_raises(self):
        engine = BookingEngine()
        engine.create_time_slot(
            make_datetime(2026, 6, 10, 9),
            make_datetime(2026, 6, 10, 10),
            10,
        )
        engine.create_time_slot(
            make_datetime(2026, 6, 10, 11),
            make_datetime(2026, 6, 10, 12),
            10,
        )
        with pytest.raises(TimeSlotConflictError):
            engine.create_booking(
                user_id="user-1",
                start_time=make_datetime(2026, 6, 10, 9),
                end_time=make_datetime(2026, 6, 10, 12),
            )

    def test_create_booking_insufficient_capacity_raises(self):
        engine, _ = build_engine_with_continuous_slots(
            make_datetime(2026, 6, 10, 9), 1, capacity=3
        )
        with pytest.raises(InsufficientCapacityError):
            engine.create_booking(
                user_id="user-1",
                start_time=make_datetime(2026, 6, 10, 9),
                end_time=make_datetime(2026, 6, 10, 10),
                quantity=5,
            )

    def test_create_booking_uses_full_capacity(self):
        engine, slots = build_engine_with_continuous_slots(
            make_datetime(2026, 6, 10, 9), 1, capacity=3
        )
        booking = engine.create_booking(
            user_id="user-1",
            start_time=make_datetime(2026, 6, 10, 9),
            end_time=make_datetime(2026, 6, 10, 10),
            quantity=3,
        )
        assert slots[0].booked_count == 3
        assert slots[0].available_capacity == 0

        with pytest.raises(InsufficientCapacityError):
            engine.create_booking(
                user_id="user-2",
                start_time=make_datetime(2026, 6, 10, 9),
                end_time=make_datetime(2026, 6, 10, 10),
                quantity=1,
            )

    def test_cancel_booking_success(self):
        engine, slots = build_engine_with_continuous_slots(
            make_datetime(2026, 6, 10, 9), 1, capacity=10
        )
        booking = engine.create_booking(
            user_id="user-1",
            start_time=make_datetime(2026, 6, 10, 9),
            end_time=make_datetime(2026, 6, 10, 10),
            quantity=3,
        )
        assert slots[0].booked_count == 3

        engine.cancel_booking(booking.id)
        assert booking.is_cancelled()
        assert slots[0].booked_count == 0

    def test_cancel_booking_not_found_raises(self):
        engine = BookingEngine()
        with pytest.raises(BookingNotFoundError):
            engine.cancel_booking("nonexistent")

    def test_cancel_booking_already_cancelled_raises(self):
        engine, _ = build_engine_with_continuous_slots(
            make_datetime(2026, 6, 10, 9), 1, capacity=10
        )
        booking = engine.create_booking(
            user_id="user-1",
            start_time=make_datetime(2026, 6, 10, 9),
            end_time=make_datetime(2026, 6, 10, 10),
        )
        engine.cancel_booking(booking.id)
        with pytest.raises(BookingError):
            engine.cancel_booking(booking.id)

    def test_get_booking(self):
        engine, _ = build_engine_with_continuous_slots(
            make_datetime(2026, 6, 10, 9), 1, capacity=10
        )
        booking = engine.create_booking(
            user_id="user-1",
            start_time=make_datetime(2026, 6, 10, 9),
            end_time=make_datetime(2026, 6, 10, 10),
        )
        found = engine.get_booking(booking.id)
        assert found is booking
        assert engine.get_booking("nonexistent") is None

    def test_list_bookings_for_user(self):
        engine, slots = build_engine_with_continuous_slots(
            make_datetime(2026, 6, 10, 9), 5, capacity=10
        )
        engine.create_booking(
            user_id="user-1",
            start_time=slots[0].start_time,
            end_time=slots[0].end_time,
        )
        engine.create_booking(
            user_id="user-1",
            start_time=slots[1].start_time,
            end_time=slots[1].end_time,
        )
        engine.create_booking(
            user_id="user-2",
            start_time=slots[2].start_time,
            end_time=slots[2].end_time,
        )
        assert len(engine.list_bookings_for_user("user-1")) == 2
        assert len(engine.list_bookings_for_user("user-2")) == 1
        assert len(engine.list_bookings_for_user("user-3")) == 0


class TestMultiSlotCrossDayBooking:
    def test_booking_spans_multiple_slots_same_day(self):
        engine, slots = build_engine_with_continuous_slots(
            make_datetime(2026, 6, 10, 9), 4, slot_minutes=60, capacity=10
        )
        booking = engine.create_booking(
            user_id="user-1",
            start_time=make_datetime(2026, 6, 10, 9),
            end_time=make_datetime(2026, 6, 10, 12),
            quantity=2,
        )
        assert len(booking.sub_bookings) == 3
        assert booking.total_quantity() == 6
        for slot in slots[:3]:
            assert slot.booked_count == 2

    def test_booking_crosses_midnight(self):
        engine = BookingEngine()
        engine.create_time_slot(
            make_datetime(2026, 6, 10, 22),
            make_datetime(2026, 6, 11, 0),
            capacity=10,
        )
        engine.create_time_slot(
            make_datetime(2026, 6, 11, 0),
            make_datetime(2026, 6, 11, 2),
            capacity=10,
        )
        booking = engine.create_booking(
            user_id="user-1",
            start_time=make_datetime(2026, 6, 10, 23),
            end_time=make_datetime(2026, 6, 11, 1),
            quantity=3,
        )
        assert len(booking.sub_bookings) == 2
        assert booking.total_quantity() == 6

    def test_booking_crosses_multiple_days(self):
        engine, slots = build_engine_with_24h_slots(
            make_datetime(2026, 6, 10), 4, capacity=10
        )
        booking = engine.create_booking(
            user_id="user-1",
            start_time=make_datetime(2026, 6, 10, 10),
            end_time=make_datetime(2026, 6, 12, 15),
            quantity=2,
        )
        assert len(booking.sub_bookings) > 3

    def test_partial_slot_booking(self):
        engine, slots = build_engine_with_continuous_slots(
            make_datetime(2026, 6, 10, 9), 3, slot_minutes=60, capacity=10
        )
        booking = engine.create_booking(
            user_id="user-1",
            start_time=make_datetime(2026, 6, 10, 9, 30),
            end_time=make_datetime(2026, 6, 10, 11, 30),
            quantity=2,
        )
        assert len(booking.sub_bookings) == 3
        assert slots[0].booked_count == 2
        assert slots[1].booked_count == 2
        assert slots[2].booked_count == 2

    def test_cancel_cross_day_booking_restores_all_capacity(self):
        engine, slots = build_engine_with_continuous_slots(
            make_datetime(2026, 6, 10, 9), 4, slot_minutes=60, capacity=10
        )
        booking = engine.create_booking(
            user_id="user-1",
            start_time=make_datetime(2026, 6, 10, 9),
            end_time=make_datetime(2026, 6, 10, 13),
            quantity=3,
        )
        for slot in slots[:4]:
            assert slot.booked_count == 3

        engine.cancel_booking(booking.id)
        for slot in slots[:4]:
            assert slot.booked_count == 0


class TestConcurrentBooking:
    def test_concurrent_bookings_no_oversell(self):
        engine, slots = build_engine_with_continuous_slots(
            make_datetime(2026, 6, 10, 9), 1, capacity=10
        )
        slot = slots[0]

        errors: list[Exception] = []
        successes: list[int] = []

        def book(user_idx: int):
            try:
                engine.create_booking(
                    user_id=f"user-{user_idx}",
                    start_time=slot.start_time,
                    end_time=slot.end_time,
                    quantity=1,
                )
                successes.append(user_idx)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=book, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(successes) == 10
        assert len(errors) == 10
        assert all(isinstance(e, InsufficientCapacityError) for e in errors)
        assert slot.booked_count == 10
        assert slot.available_capacity == 0

    def test_concurrent_bookings_multiple_slots(self):
        engine, slots = build_engine_with_continuous_slots(
            make_datetime(2026, 6, 10, 9), 3, slot_minutes=60, capacity=5
        )

        errors: list[Exception] = []
        successes: list[int] = []

        def book(user_idx: int):
            try:
                engine.create_booking(
                    user_id=f"user-{user_idx}",
                    start_time=slots[0].start_time,
                    end_time=slots[2].end_time,
                    quantity=1,
                )
                successes.append(user_idx)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=book, args=(i,)) for i in range(15)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(successes) == 5
        for slot in slots:
            assert slot.booked_count == 5

    def test_concurrent_cancel_and_book(self):
        engine, slots = build_engine_with_continuous_slots(
            make_datetime(2026, 6, 10, 9), 1, capacity=3
        )
        slot = slots[0]

        booking1 = engine.create_booking(
            user_id="user-1",
            start_time=slot.start_time,
            end_time=slot.end_time,
            quantity=3,
        )
        assert slot.booked_count == 3

        results: dict[str, bool] = {"cancelled": False, "booked": False}

        def canceller():
            try:
                engine.cancel_booking(booking1.id)
                results["cancelled"] = True
            except Exception:
                pass

        def booker():
            try:
                engine.create_booking(
                    user_id="user-2",
                    start_time=slot.start_time,
                    end_time=slot.end_time,
                    quantity=3,
                )
                results["booked"] = True
            except Exception:
                pass

        t1 = threading.Thread(target=canceller)
        t2 = threading.Thread(target=booker)
        t1.start()
        time.sleep(0.01)
        t2.start()
        t1.join()
        t2.join()

        assert results["cancelled"]
        assert results["booked"]
        assert slot.booked_count == 3


class TestHolidayAndEdgeCases:
    def test_booking_exact_slot_boundaries(self):
        engine, slots = build_engine_with_continuous_slots(
            make_datetime(2026, 6, 10, 9), 2, slot_minutes=60, capacity=10
        )
        booking = engine.create_booking(
            user_id="user-1",
            start_time=slots[0].start_time,
            end_time=slots[1].end_time,
            quantity=1,
        )
        assert len(booking.sub_bookings) == 2

    def test_booking_on_holiday_still_works(self):
        engine = BookingEngine()
        christmas = make_datetime(2026, 12, 25, 10)
        slot = engine.create_time_slot(
            christmas,
            christmas + timedelta(hours=2),
            capacity=5,
        )
        booking = engine.create_booking(
            user_id="user-1",
            start_time=slot.start_time,
            end_time=slot.end_time,
            quantity=2,
        )
        assert booking is not None
        assert slot.booked_count == 2

    def test_booking_spanning_weekend(self):
        engine, _ = build_engine_with_24h_slots(
            make_datetime(2026, 6, 12), 4, capacity=10
        )
        booking = engine.create_booking(
            user_id="user-1",
            start_time=make_datetime(2026, 6, 12, 15),
            end_time=make_datetime(2026, 6, 15, 10),
            quantity=1,
        )
        assert len(booking.sub_bookings) > 1

    def test_quantity_one_default(self):
        engine, _ = build_engine_with_continuous_slots(
            make_datetime(2026, 6, 10, 9), 1, capacity=10
        )
        booking = engine.create_booking(
            user_id="user-1",
            start_time=make_datetime(2026, 6, 10, 9),
            end_time=make_datetime(2026, 6, 10, 10),
        )
        assert booking.total_quantity() == 1

    def test_booking_end_exactly_at_slot_end(self):
        engine, slots = build_engine_with_continuous_slots(
            make_datetime(2026, 6, 10, 9), 3, slot_minutes=60, capacity=10
        )
        booking = engine.create_booking(
            user_id="user-1",
            start_time=make_datetime(2026, 6, 10, 9),
            end_time=make_datetime(2026, 6, 10, 11),
            quantity=1,
        )
        assert len(booking.sub_bookings) == 2
        assert slots[0].booked_count == 1
        assert slots[1].booked_count == 1
        assert slots[2].booked_count == 0

    def test_rollback_on_partial_failure(self):
        engine = BookingEngine()
        slot1 = engine.create_time_slot(
            make_datetime(2026, 6, 10, 9),
            make_datetime(2026, 6, 10, 10),
            capacity=10,
        )
        slot2 = engine.create_time_slot(
            make_datetime(2026, 6, 10, 10),
            make_datetime(2026, 6, 10, 11),
            capacity=3,
        )

        with pytest.raises(InsufficientCapacityError):
            engine.create_booking(
                user_id="user-1",
                start_time=make_datetime(2026, 6, 10, 9),
                end_time=make_datetime(2026, 6, 10, 11),
                quantity=5,
            )

        assert slot1.booked_count == 0
        assert slot2.booked_count == 0

    def test_multiple_users_same_slot(self):
        engine, slots = build_engine_with_continuous_slots(
            make_datetime(2026, 6, 10, 9), 1, capacity=10
        )
        b1 = engine.create_booking(
            user_id="user-1",
            start_time=slots[0].start_time,
            end_time=slots[0].end_time,
            quantity=3,
        )
        b2 = engine.create_booking(
            user_id="user-2",
            start_time=slots[0].start_time,
            end_time=slots[0].end_time,
            quantity=4,
        )
        b3 = engine.create_booking(
            user_id="user-3",
            start_time=slots[0].start_time,
            end_time=slots[0].end_time,
            quantity=3,
        )
        assert slots[0].booked_count == 10
        assert slots[0].available_capacity == 0

        engine.cancel_booking(b2.id)
        assert slots[0].booked_count == 6
        assert slots[0].available_capacity == 4
