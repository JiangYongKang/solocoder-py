from __future__ import annotations

import gc

import pytest

from solocoder_py.eventbus import EventBus


class TestNoSubscriberPublish:
    def test_publish_to_nonexistent_event_type_no_error(self, bus: EventBus):
        bus.publish("nonexistent_event", "data")

    def test_publish_after_all_unsubscribed_no_error(self, bus: EventBus):
        received = []

        def cb(data):
            received.append(data)

        bus.subscribe("evt", cb)
        bus.unsubscribe("evt", cb)
        bus.publish("evt", "data")

        assert received == []

    def test_publish_to_empty_channel_no_error(self, bus: EventBus):
        bus.publish("empty_channel", None)


class TestDuplicateSubscription:
    def test_same_callback_registered_multiple_times_called_multiple_times(
        self, bus: EventBus
    ):
        count = 0

        def handler(_):
            nonlocal count
            count += 1

        bus.subscribe("evt", handler)
        bus.subscribe("evt", handler)
        bus.subscribe("evt", handler)

        bus.publish("evt", "data")

        assert count == 3

    def test_duplicate_subscription_counted_in_subscriber_count(
        self, bus: EventBus
    ):
        def handler(_): pass

        bus.subscribe("evt", handler)
        assert bus.subscriber_count("evt") == 1

        bus.subscribe("evt", handler)
        assert bus.subscriber_count("evt") == 2

    def test_unsubscribe_removes_all_matching_subscriptions(self, bus: EventBus):
        count = 0

        def handler(_):
            nonlocal count
            count += 1

        bus.subscribe("evt", handler)
        bus.subscribe("evt", handler)
        bus.subscribe("evt", handler)
        assert bus.subscriber_count("evt") == 3

        bus.unsubscribe("evt", handler)
        assert bus.subscriber_count("evt") == 0

        bus.publish("evt", "data")
        assert count == 0


class TestSubscribeImmediatelyUnsubscribe:
    def test_subscribe_then_immediately_unsubscribe_no_trigger(
        self, bus: EventBus
    ):
        received = []

        def handler(data):
            received.append(data)

        bus.subscribe("evt", handler)
        bus.unsubscribe("evt", handler)
        bus.publish("evt", "should-not-receive")

        assert received == []

    def test_subscribe_unsubscribe_subscribe_again_works(self, bus: EventBus):
        received = []

        def handler(data):
            received.append(data)

        bus.subscribe("evt", handler)
        bus.unsubscribe("evt", handler)
        bus.publish("evt", "first")
        assert received == []

        bus.subscribe("evt", handler)
        bus.publish("evt", "second")
        assert received == ["second"]


class TestEventDataNone:
    def test_none_data_passed_correctly(self, bus: EventBus):
        received = "not_none"

        def handler(data):
            nonlocal received
            received = data

        bus.subscribe("evt", handler)
        bus.publish("evt", None)

        assert received is None

    def test_default_data_is_none(self, bus: EventBus):
        received = "not_none"

        def handler(data):
            nonlocal received
            received = data

        bus.subscribe("evt", handler)
        bus.publish("evt")

        assert received is None

    def test_none_data_multiple_subscribers(self, bus: EventBus):
        r1 = "not_none"
        r2 = "not_none"

        def h1(d):
            nonlocal r1
            r1 = d

        def h2(d):
            nonlocal r2
            r2 = d

        bus.subscribe("evt", h1)
        bus.subscribe("evt", h2)
        bus.publish("evt", None)

        assert r1 is None
        assert r2 is None


class TestWeakReferenceWithMethods:
    def test_method_callback_uses_weak_reference(self, bus: EventBus):
        class Receiver:
            def __init__(self):
                self.events = []

            def on_event(self, data):
                self.events.append(data)

        receiver = Receiver()
        bus.subscribe("evt", receiver.on_event)

        bus.publish("evt", "first")
        assert receiver.events == ["first"]

        del receiver
        gc.collect()

        bus.publish("evt", "second")
        assert bus.subscriber_count("evt") == 0

    def test_object_garbage_collected_does_not_leak(self, bus: EventBus):
        class Handler:
            instances = 0

            def __init__(self):
                Handler.instances += 1

            def __del__(self):
                Handler.instances -= 1

            def handle(self, _):
                pass

        Handler.instances = 0

        h = Handler()
        assert Handler.instances == 1

        bus.subscribe("evt", h.handle)
        assert bus.subscriber_count("evt") == 1

        del h
        gc.collect()

        assert Handler.instances == 0
        bus.publish("evt", "data")
        assert bus.subscriber_count("evt") == 0

    def test_weakref_method_still_works_while_object_alive(
        self, bus: EventBus
    ):
        class Counter:
            def __init__(self):
                self.count = 0

            def inc(self, _):
                self.count += 1

        c = Counter()
        bus.subscribe("tick", c.inc)

        for i in range(5):
            bus.publish("tick", i)

        assert c.count == 5


class TestOnceEdgeCases:
    def test_once_unsubscribe_before_trigger(self, bus: EventBus):
        count = 0

        def on_once(_):
            nonlocal count
            count += 1

        bus.once("evt", on_once)
        bus.unsubscribe("evt", on_once)
        bus.publish("evt", "data")

        assert count == 0

    def test_once_with_method_callback(self, bus: EventBus):
        class Receiver:
            def __init__(self):
                self.count = 0

            def handle(self, _):
                self.count += 1

        r = Receiver()
        bus.once("evt", r.handle)

        bus.publish("evt", "first")
        assert r.count == 1

        bus.publish("evt", "second")
        assert r.count == 1

    def test_once_object_gced_before_trigger(self, bus: EventBus):
        class Receiver:
            def __init__(self):
                self.called = False

            def handle(self, _):
                self.called = True

        r = Receiver()
        bus.once("evt", r.handle)
        assert bus.subscriber_count("evt") == 1

        del r
        gc.collect()

        bus.publish("evt", "data")
        assert bus.subscriber_count("evt") == 0


class TestClear:
    def test_clear_removes_all_subscriptions(self, bus: EventBus):
        count_a = 0
        count_b = 0

        def cb_a(_):
            nonlocal count_a
            count_a += 1

        def cb_b(_):
            nonlocal count_b
            count_b += 1

        bus.subscribe("a", cb_a)
        bus.subscribe("b", cb_b)
        bus.once("a", cb_a)

        assert bus.subscriber_count("a") == 2
        assert bus.subscriber_count("b") == 1

        bus.clear()

        assert bus.subscriber_count("a") == 0
        assert bus.subscriber_count("b") == 0
        assert bus.event_types() == []

        bus.publish("a", "data")
        bus.publish("b", "data")
        assert count_a == 0
        assert count_b == 0
