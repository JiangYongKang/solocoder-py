from __future__ import annotations

import pytest

from solocoder_py.stream_window import Event, MemoryEventSource


class TestMemoryEventSourceCreation:
    def test_empty_source(self):
        source = MemoryEventSource()
        assert source.total_events == 0
        assert source.remaining_events == 0
        assert source.has_next() is False

    def test_source_with_events(self):
        events = [Event(timestamp=1.0), Event(timestamp=2.0)]
        source = MemoryEventSource(events=events)
        assert source.total_events == 2
        assert source.remaining_events == 2
        assert source.has_next() is True

    def test_source_with_none_events(self):
        source = MemoryEventSource(events=None)
        assert source.total_events == 0
        assert source.remaining_events == 0


class TestMemoryEventSourceIteration:
    def test_next_event_returns_events_in_order(self):
        events = [
            Event(timestamp=1.0, value=10),
            Event(timestamp=2.0, value=20),
            Event(timestamp=3.0, value=30),
        ]
        source = MemoryEventSource(events=events)

        e1 = source.next_event()
        assert e1.timestamp == 1.0
        assert e1.value == 10
        assert source.remaining_events == 2

        e2 = source.next_event()
        assert e2.timestamp == 2.0
        assert source.remaining_events == 1

        e3 = source.next_event()
        assert e3.timestamp == 3.0
        assert source.remaining_events == 0

    def test_next_event_returns_none_when_empty(self):
        source = MemoryEventSource()
        assert source.next_event() is None

    def test_peek_does_not_advance(self):
        events = [Event(timestamp=1.0), Event(timestamp=2.0)]
        source = MemoryEventSource(events=events)

        peeked = source.peek()
        assert peeked is not None
        assert peeked.timestamp == 1.0
        assert source.remaining_events == 2

        peeked_again = source.peek()
        assert peeked_again.timestamp == 1.0
        assert source.remaining_events == 2

    def test_peek_returns_none_when_empty(self):
        source = MemoryEventSource()
        assert source.peek() is None

    def test_iterator_protocol(self):
        events = [
            Event(timestamp=1.0),
            Event(timestamp=2.0),
            Event(timestamp=3.0),
        ]
        source = MemoryEventSource(events=events)

        collected = []
        for event in source:
            collected.append(event)

        assert len(collected) == 3
        assert collected[0].timestamp == 1.0
        assert collected[1].timestamp == 2.0
        assert collected[2].timestamp == 3.0
        assert source.remaining_events == 0

    def test_iterator_stopiteration(self):
        source = MemoryEventSource()
        with pytest.raises(StopIteration):
            next(iter(source))

    def test_len_returns_remaining(self):
        events = [Event(timestamp=1.0), Event(timestamp=2.0), Event(timestamp=3.0)]
        source = MemoryEventSource(events=events)
        assert len(source) == 3
        source.next_event()
        assert len(source) == 2
        source.next_event()
        source.next_event()
        assert len(source) == 0


class TestMemoryEventSourceModification:
    def test_add_event(self):
        source = MemoryEventSource()
        assert source.total_events == 0

        source.add_event(Event(timestamp=1.0))
        assert source.total_events == 1
        assert source.remaining_events == 1

        source.add_event(Event(timestamp=2.0))
        assert source.total_events == 2
        assert source.remaining_events == 2

    def test_add_events(self):
        source = MemoryEventSource()
        events = [Event(timestamp=1.0), Event(timestamp=2.0)]
        source.add_events(events)
        assert source.total_events == 2
        assert source.remaining_events == 2

    def test_add_event_after_partial_consumption(self):
        events = [Event(timestamp=1.0), Event(timestamp=2.0)]
        source = MemoryEventSource(events=events)
        source.next_event()
        assert source.remaining_events == 1

        source.add_event(Event(timestamp=3.0))
        assert source.total_events == 3
        assert source.remaining_events == 2

    def test_reset(self):
        events = [Event(timestamp=1.0), Event(timestamp=2.0), Event(timestamp=3.0)]
        source = MemoryEventSource(events=events)

        source.next_event()
        source.next_event()
        assert source.remaining_events == 1

        source.reset()
        assert source.remaining_events == 3
        assert source.total_events == 3

        first = source.next_event()
        assert first.timestamp == 1.0

    def test_reset_empty_source(self):
        source = MemoryEventSource()
        source.reset()
        assert source.remaining_events == 0
        assert source.total_events == 0


class TestMemoryEventSourceEdgeCases:
    def test_single_event(self):
        source = MemoryEventSource(events=[Event(timestamp=42.0, value="test")])
        assert source.has_next() is True
        event = source.next_event()
        assert event.timestamp == 42.0
        assert event.value == "test"
        assert source.has_next() is False
        assert source.next_event() is None

    def test_many_events(self):
        events = [Event(timestamp=float(i)) for i in range(1000)]
        source = MemoryEventSource(events=events)
        assert source.total_events == 1000

        count = 0
        for event in source:
            count += 1
        assert count == 1000
        assert source.remaining_events == 0

    def test_out_of_order_events(self):
        events = [
            Event(timestamp=3.0),
            Event(timestamp=1.0),
            Event(timestamp=2.0),
        ]
        source = MemoryEventSource(events=events)
        assert source.next_event().timestamp == 3.0
        assert source.next_event().timestamp == 1.0
        assert source.next_event().timestamp == 2.0

    def test_zero_timestamp_event(self):
        source = MemoryEventSource(events=[Event(timestamp=0.0)])
        event = source.next_event()
        assert event.timestamp == 0.0
