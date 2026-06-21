from __future__ import annotations

from solocoder_py.eventbus import EventBus


class TestSubscribePublishByEventType:
    def test_publish_reaches_subscriber_of_same_type(self, bus: EventBus):
        received = []

        def on_user_created(data):
            received.append(data)

        bus.subscribe("user_created", on_user_created)
        bus.publish("user_created", {"id": 1, "name": "Alice"})

        assert len(received) == 1
        assert received[0] == {"id": 1, "name": "Alice"}

    def test_subscribe_isolated_by_event_type(self, bus: EventBus):
        created_received = []
        updated_received = []

        def on_created(data):
            created_received.append(data)

        def on_updated(data):
            updated_received.append(data)

        bus.subscribe("user_created", on_created)
        bus.subscribe("user_updated", on_updated)

        bus.publish("user_created", "create-data")
        bus.publish("user_updated", "update-data")

        assert created_received == ["create-data"]
        assert updated_received == ["update-data"]

    def test_publish_other_event_type_does_not_trigger(self, bus: EventBus):
        received = []

        def on_event(data):
            received.append(data)

        bus.subscribe("event_a", on_event)
        bus.publish("event_b", "data-b")

        assert received == []


class TestMultipleSubscribers:
    def test_multiple_subscribers_all_receive_event(self, bus: EventBus):
        results = []

        def subscriber1(data):
            results.append(("s1", data))

        def subscriber2(data):
            results.append(("s2", data))

        def subscriber3(data):
            results.append(("s3", data))

        bus.subscribe("test_event", subscriber1)
        bus.subscribe("test_event", subscriber2)
        bus.subscribe("test_event", subscriber3)

        bus.publish("test_event", "payload")

        assert len(results) == 3
        assert [r[0] for r in results] == ["s1", "s2", "s3"]
        assert all(r[1] == "payload" for r in results)

    def test_subscribers_called_in_registration_order(self, bus: EventBus):
        order = []

        def first(_):
            order.append("first")

        def second(_):
            order.append("second")

        def third(_):
            order.append("third")

        bus.subscribe("event", first)
        bus.subscribe("event", second)
        bus.subscribe("event", third)

        bus.publish("event", None)

        assert order == ["first", "second", "third"]

    def test_subscriber_count_reflects_multiple_subs(self, bus: EventBus):
        def cb1(_): pass
        def cb2(_): pass
        def cb3(_): pass

        assert bus.subscriber_count("test") == 0

        bus.subscribe("test", cb1)
        assert bus.subscriber_count("test") == 1

        bus.subscribe("test", cb2)
        assert bus.subscriber_count("test") == 2

        bus.subscribe("test", cb3)
        assert bus.subscriber_count("test") == 3


class TestUnsubscribe:
    def test_unsubscribe_stops_future_events(self, bus: EventBus):
        received = []

        def on_event(data):
            received.append(data)

        bus.subscribe("test", on_event)
        bus.publish("test", "first")
        assert len(received) == 1

        bus.unsubscribe("test", on_event)
        bus.publish("test", "second")
        assert len(received) == 1
        assert received == ["first"]

    def test_unsubscribe_one_does_not_affect_others(self, bus: EventBus):
        r1 = []
        r2 = []
        r3 = []

        def cb1(d): r1.append(d)
        def cb2(d): r2.append(d)
        def cb3(d): r3.append(d)

        bus.subscribe("evt", cb1)
        bus.subscribe("evt", cb2)
        bus.subscribe("evt", cb3)

        bus.unsubscribe("evt", cb2)
        bus.publish("evt", "data")

        assert r1 == ["data"]
        assert r2 == []
        assert r3 == ["data"]


class TestEventDataPassing:
    def test_event_data_dict_passed_correctly(self, bus: EventBus):
        received = None

        def handler(data):
            nonlocal received
            received = data

        bus.subscribe("event", handler)
        payload = {"key": "value", "num": 42, "nested": {"a": 1}}
        bus.publish("event", payload)

        assert received == payload
        assert received is payload

    def test_event_data_object_passed_correctly(self, bus: EventBus):
        class DataObj:
            def __init__(self, value):
                self.value = value

        received = None

        def handler(data):
            nonlocal received
            received = data

        obj = DataObj(99)
        bus.subscribe("event", handler)
        bus.publish("event", obj)

        assert received is obj
        assert received.value == 99

    def test_event_data_string_passed(self, bus: EventBus):
        received = []

        def handler(data):
            received.append(data)

        bus.subscribe("log", handler)
        bus.publish("log", "hello world")

        assert received == ["hello world"]

    def test_event_data_integer_passed(self, bus: EventBus):
        received = []

        def handler(data):
            received.append(data)

        bus.subscribe("count", handler)
        bus.publish("count", 42)

        assert received == [42]


class TestOnceSubscription:
    def test_once_callback_triggers_exactly_once(self, bus: EventBus):
        count = 0

        def on_once(data):
            nonlocal count
            count += 1

        bus.once("event", on_once)
        bus.publish("event", "first")
        bus.publish("event", "second")
        bus.publish("event", "third")

        assert count == 1

    def test_once_receives_correct_data(self, bus: EventBus):
        received = None

        def on_once(data):
            nonlocal received
            received = data

        bus.once("event", on_once)
        bus.publish("event", "once-data")

        assert received == "once-data"

    def test_once_removed_after_trigger(self, bus: EventBus):
        def on_once(_): pass

        bus.once("event", on_once)
        assert bus.subscriber_count("event") == 1

        bus.publish("event", "data")
        assert bus.subscriber_count("event") == 0

    def test_once_mixed_with_regular_subscribe(self, bus: EventBus):
        regular_count = 0
        once_count = 0

        def regular(_):
            nonlocal regular_count
            regular_count += 1

        def once_cb(_):
            nonlocal once_count
            once_count += 1

        bus.subscribe("evt", regular)
        bus.once("evt", once_cb)

        bus.publish("evt", "1")
        assert regular_count == 1
        assert once_count == 1

        bus.publish("evt", "2")
        assert regular_count == 2
        assert once_count == 1

    def test_multiple_once_subscriptions(self, bus: EventBus):
        counts = {"a": 0, "b": 0}

        def once_a(_):
            counts["a"] += 1

        def once_b(_):
            counts["b"] += 1

        bus.once("evt", once_a)
        bus.once("evt", once_b)

        bus.publish("evt", "data")

        assert counts["a"] == 1
        assert counts["b"] == 1
        assert bus.subscriber_count("evt") == 0


class TestEventTypesListing:
    def test_event_types_returns_registered_types(self, bus: EventBus):
        def cb(_): pass

        bus.subscribe("type_a", cb)
        bus.subscribe("type_b", cb)

        types = bus.event_types()
        assert "type_a" in types
        assert "type_b" in types
        assert len(types) == 2

    def test_event_types_empty_initially(self, bus: EventBus):
        assert bus.event_types() == []

    def test_event_types_updated_after_clear(self, bus: EventBus):
        def cb(_): pass

        bus.subscribe("a", cb)
        bus.subscribe("b", cb)
        assert len(bus.event_types()) == 2

        bus.clear()
        assert bus.event_types() == []


class TestIsSubscribed:
    def test_is_subscribed_true_for_active_sub(self, bus: EventBus):
        def handler(_): pass

        bus.subscribe("evt", handler)
        assert bus.is_subscribed("evt", handler) is True

    def test_is_subscribed_false_for_unknown(self, bus: EventBus):
        def handler(_): pass

        assert bus.is_subscribed("evt", handler) is False

    def test_is_subscribed_false_after_unsubscribe(self, bus: EventBus):
        def handler(_): pass

        bus.subscribe("evt", handler)
        bus.unsubscribe("evt", handler)
        assert bus.is_subscribed("evt", handler) is False
