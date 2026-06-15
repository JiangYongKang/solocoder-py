from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone

import pytest

from solocoder_py.event_counter import (
    EventCounter,
    Event,
    Granularity,
    InvalidTimeRangeError,
    WindowExpiredError,
)
from solocoder_py.event_counter.models import (
    CountResult,
    GranularityConfig,
    TimeWindow,
)


class TestGranularity:
    def test_granularity_durations(self):
        assert Granularity.MINUTE.duration == timedelta(minutes=1)
        assert Granularity.HOUR.duration == timedelta(hours=1)
        assert Granularity.DAY.duration == timedelta(days=1)

    def test_granularity_order(self):
        assert Granularity.MINUTE.order < Granularity.HOUR.order
        assert Granularity.HOUR.order < Granularity.DAY.order

    def test_is_finer_than(self):
        assert Granularity.MINUTE.is_finer_than(Granularity.HOUR)
        assert Granularity.MINUTE.is_finer_than(Granularity.DAY)
        assert Granularity.HOUR.is_finer_than(Granularity.DAY)
        assert not Granularity.HOUR.is_finer_than(Granularity.MINUTE)
        assert not Granularity.DAY.is_finer_than(Granularity.HOUR)

    def test_is_coarser_than(self):
        assert Granularity.HOUR.is_coarser_than(Granularity.MINUTE)
        assert Granularity.DAY.is_coarser_than(Granularity.MINUTE)
        assert Granularity.DAY.is_coarser_than(Granularity.HOUR)
        assert not Granularity.MINUTE.is_coarser_than(Granularity.HOUR)
        assert not Granularity.HOUR.is_coarser_than(Granularity.DAY)

    def test_from_order(self):
        assert Granularity.from_order(0) == Granularity.MINUTE
        assert Granularity.from_order(1) == Granularity.HOUR
        assert Granularity.from_order(2) == Granularity.DAY


class TestTimeWindow:
    def test_window_from_timestamp_minute(self, base_time):
        ts = datetime(2024, 1, 15, 12, 30, 45, tzinfo=timezone.utc)
        window = TimeWindow.from_timestamp(ts, Granularity.MINUTE)
        assert window.granularity == Granularity.MINUTE
        assert window.start == datetime(2024, 1, 15, 12, 30, 0, tzinfo=timezone.utc)
        assert window.end == datetime(2024, 1, 15, 12, 31, 0, tzinfo=timezone.utc)

    def test_window_from_timestamp_hour(self):
        ts = datetime(2024, 1, 15, 12, 30, 45, tzinfo=timezone.utc)
        window = TimeWindow.from_timestamp(ts, Granularity.HOUR)
        assert window.granularity == Granularity.HOUR
        assert window.start == datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        assert window.end == datetime(2024, 1, 15, 13, 0, 0, tzinfo=timezone.utc)

    def test_window_from_timestamp_day(self):
        ts = datetime(2024, 1, 15, 12, 30, 45, tzinfo=timezone.utc)
        window = TimeWindow.from_timestamp(ts, Granularity.DAY)
        assert window.granularity == Granularity.DAY
        assert window.start == datetime(2024, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        assert window.end == datetime(2024, 1, 16, 0, 0, 0, tzinfo=timezone.utc)

    def test_window_contains(self):
        ts = datetime(2024, 1, 15, 12, 30, 45, tzinfo=timezone.utc)
        window = TimeWindow.from_timestamp(ts, Granularity.HOUR)
        assert window.contains(datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc))
        assert window.contains(datetime(2024, 1, 15, 12, 30, 0, tzinfo=timezone.utc))
        assert window.contains(datetime(2024, 1, 15, 12, 59, 59, tzinfo=timezone.utc))
        assert not window.contains(datetime(2024, 1, 15, 13, 0, 0, tzinfo=timezone.utc))
        assert not window.contains(datetime(2024, 1, 15, 11, 59, 59, tzinfo=timezone.utc))

    def test_next_previous_window(self):
        ts = datetime(2024, 1, 15, 12, 30, 0, tzinfo=timezone.utc)
        window = TimeWindow.from_timestamp(ts, Granularity.HOUR)
        next_w = window.next_window()
        assert next_w.start == datetime(2024, 1, 15, 13, 0, 0, tzinfo=timezone.utc)
        prev_w = window.previous_window()
        assert prev_w.start == datetime(2024, 1, 15, 11, 0, 0, tzinfo=timezone.utc)

    def test_to_coarser(self):
        ts = datetime(2024, 1, 15, 12, 30, 0, tzinfo=timezone.utc)
        minute_window = TimeWindow.from_timestamp(ts, Granularity.MINUTE)
        hour_window = minute_window.to_coarser(Granularity.HOUR)
        assert hour_window.granularity == Granularity.HOUR
        assert hour_window.start == datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        day_window = minute_window.to_coarser(Granularity.DAY)
        assert day_window.granularity == Granularity.DAY
        assert day_window.start == datetime(2024, 1, 15, 0, 0, 0, tzinfo=timezone.utc)


class TestEvent:
    def test_event_creation(self):
        ts = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        event = Event(timestamp=ts)
        assert event.timestamp == ts
        assert event.count == 1

    def test_event_with_count(self):
        ts = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        event = Event(timestamp=ts, count=5)
        assert event.count == 5

    def test_event_naive_timezone(self):
        ts = datetime(2024, 1, 15, 12, 0, 0)
        event = Event(timestamp=ts)
        assert event.timestamp.tzinfo is not None

    def test_event_invalid_count(self):
        ts = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        with pytest.raises(ValueError, match="count must be positive"):
            Event(timestamp=ts, count=0)
        with pytest.raises(ValueError, match="count must be positive"):
            Event(timestamp=ts, count=-1)


class TestNormalFlows:
    def test_record_single_event(self, counter, base_time):
        event = Event(timestamp=base_time)
        counter.record(event)

        assert counter.get_count(base_time, Granularity.MINUTE) == 1
        assert counter.get_count(base_time, Granularity.HOUR) == 1
        assert counter.get_count(base_time, Granularity.DAY) == 1

    def test_record_multiple_events_same_window(self, counter, base_time):
        for _ in range(5):
            counter.record(Event(timestamp=base_time))

        assert counter.get_count(base_time, Granularity.MINUTE) == 5
        assert counter.get_count(base_time, Granularity.HOUR) == 5
        assert counter.get_count(base_time, Granularity.DAY) == 5

    def test_record_event_with_count(self, counter, base_time):
        counter.record(Event(timestamp=base_time, count=10))

        assert counter.get_count(base_time, Granularity.MINUTE) == 10
        assert counter.get_count(base_time, Granularity.HOUR) == 10
        assert counter.get_count(base_time, Granularity.DAY) == 10

    def test_record_many_events(self, counter, base_time):
        events = [
            Event(timestamp=base_time + timedelta(minutes=i), count=i + 1)
            for i in range(5)
        ]
        counter.record_many(events)

        for i in range(5):
            ts = base_time + timedelta(minutes=i)
            assert counter.get_count(ts, Granularity.MINUTE) == i + 1

        assert counter.get_count(base_time, Granularity.HOUR) == 15
        assert counter.get_count(base_time, Granularity.DAY) == 15

    def test_query_range_multiple_windows(self, counter, base_time):
        for i in range(5):
            ts = base_time + timedelta(minutes=i)
            counter.record(Event(timestamp=ts, count=2))

        start = base_time
        end = base_time + timedelta(minutes=5)
        results = counter.query(start, end, Granularity.MINUTE)

        assert len(results) == 5
        for i, r in enumerate(results):
            assert r.count == 2
            assert r.is_estimated is False
            assert r.source_granularity == Granularity.MINUTE

    def test_query_hour_range_from_minutes(self, counter, base_time):
        hour_start = base_time.replace(minute=0, second=0, microsecond=0)
        for minute in range(3):
            ts = hour_start + timedelta(minutes=minute * 20)
            counter.record(Event(timestamp=ts, count=5))

        start = hour_start
        end = hour_start + timedelta(hours=1)
        results = counter.query(start, end, Granularity.HOUR)

        assert len(results) == 1
        assert results[0].count == 15

    def test_query_day_range_from_hours(self, counter, base_time):
        day_start = base_time.replace(hour=0, minute=0, second=0, microsecond=0)
        for hour in range(3):
            ts = day_start + timedelta(hours=hour, minutes=30)
            counter.record(Event(timestamp=ts, count=10))

        start = day_start
        end = day_start + timedelta(days=1)
        results = counter.query(start, end, Granularity.DAY)

        assert len(results) == 1
        assert results[0].count == 30


class TestMultiGranularityRollup:
    def test_single_event_rolls_up_all_levels(self, counter, base_time):
        counter.record(Event(timestamp=base_time, count=3))

        minute_window = TimeWindow.from_timestamp(base_time, Granularity.MINUTE)
        hour_window = TimeWindow.from_timestamp(base_time, Granularity.HOUR)
        day_window = TimeWindow.from_timestamp(base_time, Granularity.DAY)

        minute_count = counter.query_single(base_time, Granularity.MINUTE)
        hour_count = counter.query_single(base_time, Granularity.HOUR)
        day_count = counter.query_single(base_time, Granularity.DAY)

        assert minute_count.count == 3
        assert hour_count.count == 3
        assert day_count.count == 3

    def test_multiple_minutes_same_hour(self, counter, base_time):
        hour_start = base_time.replace(minute=0, second=0, microsecond=0)

        for minute in range(10):
            ts = hour_start + timedelta(minutes=minute)
            counter.record(Event(timestamp=ts, count=2))

        assert counter.get_count(hour_start, Granularity.HOUR) == 20

        for minute in range(10):
            ts = hour_start + timedelta(minutes=minute)
            assert counter.get_count(ts, Granularity.MINUTE) == 2

    def test_multiple_hours_same_day(self, counter, base_time):
        day_start = base_time.replace(hour=0, minute=0, second=0, microsecond=0)

        for hour in range(5):
            ts = base_time.replace(hour=hour, minute=0, second=0, microsecond=0)
            counter.record(Event(timestamp=ts, count=10))

        assert counter.get_count(day_start, Granularity.DAY) == 50

        for hour in range(5):
            ts = base_time.replace(hour=hour, minute=0, second=0, microsecond=0)
            assert counter.get_count(ts, Granularity.HOUR) == 10

    def test_mixed_granularity_aggregation(self, counter, base_time):
        hour_start = base_time.replace(minute=0, second=0, microsecond=0)
        day_start = base_time.replace(hour=0, minute=0, second=0, microsecond=0)

        for hour in range(3):
            current_hour = hour_start + timedelta(hours=hour)
            for minute in range(4):
                ts = current_hour + timedelta(minutes=minute)
                counter.record(Event(timestamp=ts, count=1))

        assert counter.get_count(day_start, Granularity.DAY) == 12

        for hour in range(3):
            ts = hour_start + timedelta(hours=hour)
            assert counter.get_count(ts, Granularity.HOUR) == 4

    def test_consistency_across_granularities(self, counter, base_time):
        for minute in range(120):
            ts = base_time + timedelta(minutes=minute)
            counter.record(Event(timestamp=ts, count=1))

        total_minutes = sum(
            r.count for r in counter.query(
                base_time, base_time + timedelta(hours=2), Granularity.MINUTE
            )
        )
        total_hours = sum(
            r.count for r in counter.query(
                base_time, base_time + timedelta(hours=2), Granularity.HOUR
            )
        )
        total_days = sum(
            r.count for r in counter.query(
                base_time, base_time + timedelta(days=1), Granularity.DAY
            )
        )

        assert total_minutes == 120
        assert total_hours == 120
        assert total_days == 120


class TestBoundaryConditions:
    def test_event_at_window_boundary_minute(self, counter, base_time):
        minute_start = base_time.replace(second=0, microsecond=0)
        next_minute = minute_start + timedelta(minutes=1)

        counter.record(Event(timestamp=minute_start, count=5))
        counter.record(Event(timestamp=next_minute - timedelta(microseconds=1), count=3))

        assert counter.get_count(minute_start, Granularity.MINUTE) == 8
        assert counter.get_count(next_minute, Granularity.MINUTE) == 0

    def test_event_at_window_boundary_hour(self, counter, base_time):
        hour_start = base_time.replace(minute=0, second=0, microsecond=0)
        next_hour = hour_start + timedelta(hours=1)

        counter.record(Event(timestamp=hour_start, count=10))
        counter.record(Event(timestamp=next_hour - timedelta(microseconds=1), count=7))

        assert counter.get_count(hour_start, Granularity.HOUR) == 17
        assert counter.get_count(next_hour, Granularity.HOUR) == 0

    def test_event_at_window_boundary_day(self, counter, base_time):
        day_start = base_time.replace(hour=0, minute=0, second=0, microsecond=0)
        next_day = day_start + timedelta(days=1)

        counter.record(Event(timestamp=day_start, count=25))
        counter.record(Event(timestamp=next_day - timedelta(microseconds=1), count=15))

        assert counter.get_count(day_start, Granularity.DAY) == 40
        assert counter.get_count(next_day, Granularity.DAY) == 0

    def test_events_across_day_boundary(self, counter, base_time):
        day1 = base_time.replace(hour=23, minute=59, second=0, microsecond=0)
        day2 = day1 + timedelta(minutes=2)

        counter.record(Event(timestamp=day1, count=3))
        counter.record(Event(timestamp=day2, count=7))

        assert counter.get_count(day1, Granularity.DAY) == 3
        assert counter.get_count(day2, Granularity.DAY) == 7

    def test_empty_window_query(self, counter, base_time):
        result = counter.query_single(base_time, Granularity.MINUTE)
        assert result.count == 0
        assert result.is_estimated is False
        assert result.source_granularity is None

        results = counter.query(
            base_time, base_time + timedelta(hours=1), Granularity.MINUTE
        )
        assert all(r.count == 0 for r in results)
        assert len(results) == 60

    def test_query_start_equals_end_raises(self, counter, base_time):
        with pytest.raises(InvalidTimeRangeError, match="start time must be before end time"):
            counter.query(base_time, base_time, Granularity.MINUTE)

    def test_query_start_after_end_raises(self, counter, base_time):
        with pytest.raises(InvalidTimeRangeError, match="start time must be before end time"):
            counter.query(
                base_time + timedelta(hours=1),
                base_time,
                Granularity.MINUTE,
            )

    def test_query_single_window_range(self, counter, base_time):
        counter.record(Event(timestamp=base_time, count=5))
        results = counter.query(
            base_time,
            base_time + timedelta(minutes=1),
            Granularity.MINUTE,
        )
        assert len(results) == 1
        assert results[0].count == 5

    def test_partial_range_covers_partial_windows(self, counter, base_time):
        for minute in range(10):
            ts = base_time + timedelta(minutes=minute)
            counter.record(Event(timestamp=ts, count=1))

        start = base_time + timedelta(seconds=30)
        end = base_time + timedelta(minutes=5, seconds=30)
        results = counter.query(start, end, Granularity.MINUTE)

        assert len(results) == 6
        assert sum(r.count for r in results) == 6


class TestWindowExpiration:
    def test_cleanup_expired_minute_windows(self, expiry_test_configs):
        base = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        clock_time = {"current": base}

        counter = EventCounter(
            granularity_configs=expiry_test_configs,
            clock=lambda: clock_time["current"],
        )

        old_ts = base - timedelta(minutes=15)
        counter.record(Event(timestamp=old_ts, count=10))
        assert counter.get_count(old_ts, Granularity.MINUTE) == 10

        clock_time["current"] = base + timedelta(minutes=20)
        removed = counter.cleanup()
        assert removed[Granularity.MINUTE] == 1

        result = counter.query_single(old_ts, Granularity.MINUTE)
        assert result.source_granularity is not None or result.count == 0

    def test_cleanup_expired_hour_windows(self, expiry_test_configs):
        base = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        clock_time = {"current": base}

        counter = EventCounter(
            granularity_configs=expiry_test_configs,
            clock=lambda: clock_time["current"],
        )

        old_ts = base - timedelta(hours=4)
        counter.record(Event(timestamp=old_ts, count=5))
        assert counter.get_count(old_ts, Granularity.HOUR) == 5

        clock_time["current"] = base + timedelta(hours=3)
        removed = counter.cleanup()
        assert removed[Granularity.HOUR] >= 1

    def test_cleanup_preserves_recent_windows(self, counter, base_time):
        recent_ts = base_time - timedelta(minutes=10)
        counter.record(Event(timestamp=recent_ts, count=7))

        counter.cleanup()
        assert counter.get_count(recent_ts, Granularity.MINUTE) == 7

    def test_cleanup_counts_removed_windows(self, counter, base_time):
        for i in range(100):
            ts = base_time - timedelta(days=100, minutes=i)
            counter.record(Event(timestamp=ts, count=1))

        removed = counter.cleanup()
        assert removed[Granularity.MINUTE] >= 0
        assert removed[Granularity.HOUR] >= 0

    def test_record_triggers_cleanup(self, expiry_test_configs):
        base = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        clock_time = {"current": base}

        counter = EventCounter(
            granularity_configs=expiry_test_configs,
            clock=lambda: clock_time["current"],
        )

        old_ts = base - timedelta(minutes=45)
        counter.record(Event(timestamp=old_ts, count=1))

        clock_time["current"] = base + timedelta(minutes=1)
        new_ts = clock_time["current"]
        counter.record(Event(timestamp=new_ts, count=1))


class TestReadTimeMerge:
    def test_resolve_from_finer_granularity_minute_to_hour(self, counter, base_time):
        hour_start = base_time.replace(minute=0, second=0, microsecond=0)

        for minute in range(5):
            ts = hour_start + timedelta(minutes=minute)
            counter.record(Event(timestamp=ts, count=2))

        counter.clear(Granularity.HOUR)

        result = counter.query_single(hour_start, Granularity.HOUR)
        assert result.count == 10
        assert result.is_estimated is False
        assert result.source_granularity == Granularity.MINUTE

    def test_resolve_from_finer_granularity_hour_to_day(self, counter, base_time):
        day_start = base_time.replace(hour=0, minute=0, second=0, microsecond=0)

        for hour in range(3):
            ts = day_start + timedelta(hours=hour)
            counter.record(Event(timestamp=ts, count=10))

        counter.clear(Granularity.DAY)

        result = counter.query_single(day_start, Granularity.DAY)
        assert result.count == 30
        assert result.is_estimated is False
        assert result.source_granularity == Granularity.HOUR

    def test_resolve_from_finer_partial_coverage(self, counter, base_time):
        hour_start = base_time.replace(minute=0, second=0, microsecond=0)

        for minute in [10, 20, 30]:
            ts = hour_start + timedelta(minutes=minute)
            counter.record(Event(timestamp=ts, count=5))

        counter.clear(Granularity.HOUR)

        result = counter.query_single(hour_start, Granularity.HOUR)
        assert result.count == 15
        assert result.source_granularity == Granularity.MINUTE

    def test_resolve_from_coarser_granularity_hour_to_minute(self, short_retention_configs):
        base = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        clock_time = {"current": base}
        counter = EventCounter(
            granularity_configs=short_retention_configs,
            clock=lambda: clock_time["current"],
        )

        counter.record(Event(timestamp=base, count=60))

        clock_time["current"] = base + timedelta(hours=1)
        counter.clear(Granularity.MINUTE)

        result = counter.query_single(base + timedelta(minutes=30), Granularity.MINUTE)
        assert result.is_estimated is True
        assert result.source_granularity == Granularity.HOUR
        assert result.count >= 0

    def test_resolve_from_coarser_granularity_day_to_hour(self, short_retention_configs):
        base = datetime(2024, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        clock_time = {"current": base + timedelta(hours=12)}

        counter = EventCounter(
            granularity_configs=short_retention_configs,
            clock=lambda: clock_time["current"],
        )

        counter.record(Event(timestamp=base + timedelta(hours=12), count=240))
        counter.clear(Granularity.HOUR)

        result = counter.query_single(base + timedelta(hours=6), Granularity.HOUR)
        assert result.is_estimated is True
        assert result.source_granularity == Granularity.DAY
        assert result.count >= 0

    def test_all_windows_expired_fallback_chain(self):
        base = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        clock_time = {"current": base + timedelta(days=100)}

        configs = {
            Granularity.MINUTE: GranularityConfig(retention=timedelta(minutes=1)),
            Granularity.HOUR: GranularityConfig(retention=timedelta(hours=1)),
            Granularity.DAY: GranularityConfig(retention=timedelta(days=1)),
        }
        counter = EventCounter(
            granularity_configs=configs,
            clock=lambda: clock_time["current"],
        )

        counter.record(Event(timestamp=base, count=100))

        result = counter.query_single(base, Granularity.MINUTE)
        assert result.count == 0


class TestConcurrency:
    def test_concurrent_records_same_window(self, thread_safe_counter, base_time):
        num_threads = 10
        records_per_thread = 100

        def worker():
            for _ in range(records_per_thread):
                thread_safe_counter.record(Event(timestamp=base_time, count=1))

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        expected = num_threads * records_per_thread
        assert thread_safe_counter.get_count(base_time, Granularity.MINUTE) == expected
        assert thread_safe_counter.get_count(base_time, Granularity.HOUR) == expected
        assert thread_safe_counter.get_count(base_time, Granularity.DAY) == expected

    def test_concurrent_records_different_windows(self, thread_safe_counter, base_time):
        num_threads = 10
        windows_per_thread = 10

        def worker(thread_idx):
            for i in range(windows_per_thread):
                offset = thread_idx * windows_per_thread + i
                ts = base_time + timedelta(minutes=offset)
                thread_safe_counter.record(Event(timestamp=ts, count=1))

        threads = [
            threading.Thread(target=worker, args=(i,)) for i in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        expected = num_threads * windows_per_thread
        total = 0
        for i in range(expected):
            ts = base_time + timedelta(minutes=i)
            total += thread_safe_counter.get_count(ts, Granularity.MINUTE)
        assert total == expected

    def test_concurrent_queries_and_records(self, thread_safe_counter, base_time):
        results_collected = []
        errors_collected = []

        def recorder():
            try:
                for i in range(50):
                    thread_safe_counter.record(
                        Event(timestamp=base_time + timedelta(minutes=i), count=1)
                    )
            except Exception as e:
                errors_collected.append(e)

        def querier():
            try:
                for _ in range(50):
                    result = thread_safe_counter.query_single(
                        base_time + timedelta(minutes=25),
                        Granularity.MINUTE,
                    )
                    results_collected.append(result.count)
            except Exception as e:
                errors_collected.append(e)

        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=recorder))
            threads.append(threading.Thread(target=querier))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors_collected) == 0

    def test_concurrent_cleanup_and_records(self, expiry_test_configs):
        base = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        clock_time = {"current": base}

        counter = EventCounter(
            granularity_configs=expiry_test_configs,
            clock=lambda: clock_time["current"],
        )

        errors_collected = []

        def recorder():
            try:
                for i in range(100):
                    ts = base - timedelta(minutes=i)
                    counter.record(Event(timestamp=ts, count=1))
            except Exception as e:
                errors_collected.append(e)

        def cleaner():
            try:
                for i in range(50):
                    clock_time["current"] = base + timedelta(minutes=i * 2)
                    counter.cleanup()
            except Exception as e:
                errors_collected.append(e)

        t1 = threading.Thread(target=recorder)
        t2 = threading.Thread(target=cleaner)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(errors_collected) == 0


class TestExceptionBranches:
    def test_write_timestamp_far_in_past(self, counter, base_time):
        ancient_ts = base_time - timedelta(days=365)
        counter.record(Event(timestamp=ancient_ts, count=5))

        result = counter.query_single(ancient_ts, Granularity.MINUTE)
        assert result.source_granularity is None or result.count >= 0

    def test_query_future_time_range(self, counter, base_time):
        future_start = base_time + timedelta(days=10)
        future_end = future_start + timedelta(hours=1)

        results = counter.query(future_start, future_end, Granularity.MINUTE)
        assert all(r.count == 0 for r in results)
        assert len(results) == 60

    def test_query_single_future_timestamp(self, counter, base_time):
        future_ts = base_time + timedelta(days=10)
        result = counter.query_single(future_ts, Granularity.HOUR)
        assert result.count == 0
        assert result.is_estimated is False
        assert result.source_granularity is None

    def test_naive_datetime_handling(self, counter, base_time):
        naive_ts = datetime(2024, 1, 15, 12, 0, 0)
        counter.record(Event(timestamp=naive_ts, count=5))

        result = counter.query_single(naive_ts, Granularity.MINUTE)
        assert result.count == 5

    def test_invalid_event_count_zero(self, base_time):
        with pytest.raises(ValueError, match="count must be positive"):
            Event(timestamp=base_time, count=0)

    def test_invalid_event_count_negative(self, base_time):
        with pytest.raises(ValueError, match="count must be positive"):
            Event(timestamp=base_time, count=-5)

    def test_clear_all_granularities(self, counter, base_time):
        counter.record(Event(timestamp=base_time, count=10))
        assert counter.count_windows(Granularity.MINUTE) > 0

        counter.clear()
        assert counter.count_windows(Granularity.MINUTE) == 0
        assert counter.count_windows(Granularity.HOUR) == 0
        assert counter.count_windows(Granularity.DAY) == 0

    def test_clear_specific_granularity(self, counter, base_time):
        counter.record(Event(timestamp=base_time, count=10))

        counter.clear(Granularity.MINUTE)
        assert counter.count_windows(Granularity.MINUTE) == 0
        assert counter.count_windows(Granularity.HOUR) > 0

    def test_empty_record_many(self, counter):
        counter.record_many([])
        assert counter.count_windows(Granularity.MINUTE) == 0

    def test_configs_property_returns_copy(self, counter):
        configs = counter.configs
        assert Granularity.MINUTE in configs
        configs[Granularity.MINUTE] = GranularityConfig(retention=timedelta(days=999))
        assert counter.configs[Granularity.MINUTE].retention != timedelta(days=999)
