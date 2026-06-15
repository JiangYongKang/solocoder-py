from __future__ import annotations

import pytest

from solocoder_py.batch_window.models import Event
from solocoder_py.batch_window.source import MemoryEventSource


class TestMemoryEventSourceCreation:
    def test_empty_source(self):
        source = MemoryEventSource()
        assert source.total_count() == 0
        assert source.remaining_count() == 0
        assert source.has_next() is False

    def test_source_with_initial_events(self):
        events = [Event(timestamp=1.0), Event(timestamp=2.0)]
        source = MemoryEventSource(_events=events)
        assert source.total_count() == 2
        assert source.remaining_count() == 2
        assert source.has_next() is True


class TestMemoryEventSourceAddEvents:
    def test_add_single_event(self):
        source = MemoryEventSource()
        source.add_event(Event(timestamp=1.0))
        assert source.total_count() == 1
        assert source.remaining_count() == 1
        assert source.has_next() is True

    def test_add_multiple_events(self):
        source = MemoryEventSource()
        source.add_events([Event(timestamp=1.0), Event(timestamp=2.0), Event(timestamp=3.0)])
        assert source.total_count() == 3
        assert source.remaining_count() == 3

    def test_add_after_partial_consumption(self):
        source = MemoryEventSource()
        source.add_event(Event(timestamp=1.0))
        source.next()
        source.add_event(Event(timestamp=2.0))
        assert source.total_count() == 2
        assert source.remaining_count() == 1


class TestMemoryEventSourceIteration:
    def test_next_event(self):
        source = MemoryEventSource()
        event = Event(timestamp=1.0, value=42)
        source.add_event(event)
        result = source.next()
        assert result == event
        assert source.remaining_count() == 0
        assert source.has_next() is False

    def test_next_empty_source_raises(self):
        source = MemoryEventSource()
        with pytest.raises(StopIteration, match="No more events available"):
            source.next()

    def test_peek_event(self):
        source = MemoryEventSource()
        event = Event(timestamp=1.0)
        source.add_event(event)
        peeked = source.peek()
        assert peeked == event
        assert source.remaining_count() == 1

    def test_peek_empty_source(self):
        source = MemoryEventSource()
        assert source.peek() is None

    def test_iterator_protocol(self):
        events = [Event(timestamp=1.0), Event(timestamp=2.0), Event(timestamp=3.0)]
        source = MemoryEventSource()
        source.add_events(events)
        collected = []
        for event in source:
            collected.append(event)
        assert len(collected) == 3
        assert collected == events

    def test_sequential_next_calls(self):
        events = [Event(timestamp=i) for i in range(5)]
        source = MemoryEventSource()
        source.add_events(events)
        for i in range(5):
            assert source.next().timestamp == float(i)
        assert source.has_next() is False


class TestMemoryEventSourceResetAndClear:
    def test_reset_position(self):
        events = [Event(timestamp=1.0), Event(timestamp=2.0)]
        source = MemoryEventSource()
        source.add_events(events)
        source.next()
        assert source.remaining_count() == 1
        source.reset()
        assert source.remaining_count() == 2
        assert source.next().timestamp == 1.0

    def test_clear_all(self):
        events = [Event(timestamp=1.0), Event(timestamp=2.0)]
        source = MemoryEventSource()
        source.add_events(events)
        source.next()
        source.clear()
        assert source.total_count() == 0
        assert source.remaining_count() == 0
        assert source.has_next() is False

    def test_get_all_events(self):
        events = [Event(timestamp=1.0), Event(timestamp=2.0)]
        source = MemoryEventSource()
        source.add_events(events)
        all_events = source.get_all_events()
        assert len(all_events) == 2
        assert all_events[0].timestamp == 1.0
        source.next()
        all_events_after = source.get_all_events()
        assert len(all_events_after) == 2
