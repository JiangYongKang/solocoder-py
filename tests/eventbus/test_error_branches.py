from __future__ import annotations

import gc

import pytest

from solocoder_py.eventbus import EventBus


class TestCallbackExceptionIsolation:
    def test_exception_in_one_callback_does_not_affect_others(
        self, bus: EventBus
    ):
        results = []

        def bad_cb(_):
            raise RuntimeError("oops")

        def good_cb1(_):
            results.append("good1")

        def good_cb2(_):
            results.append("good2")

        bus.subscribe("evt", good_cb1)
        bus.subscribe("evt", bad_cb)
        bus.subscribe("evt", good_cb2)

        bus.publish("evt", "data")

        assert "good1" in results
        assert "good2" in results
        assert len(results) == 2

    def test_exception_in_callback_does_not_propagate(self, bus: EventBus):
        def bad_cb(_):
            raise ValueError("test error")

        bus.subscribe("evt", bad_cb)

        try:
            bus.publish("evt", "data")
        except Exception:
            pytest.fail("Exception should not propagate from callback")

    def test_multiple_failing_callbacks_all_others_still_run(
        self, bus: EventBus
    ):
        results = []

        def fail1(_):
            raise RuntimeError("fail1")

        def fail2(_):
            raise RuntimeError("fail2")

        def ok1(_):
            results.append("ok1")

        def ok2(_):
            results.append("ok2")

        bus.subscribe("evt", ok1)
        bus.subscribe("evt", fail1)
        bus.subscribe("evt", ok2)
        bus.subscribe("evt", fail2)

        bus.publish("evt", "data")

        assert results == ["ok1", "ok2"]


class TestWeakRefCleanupOnPublish:
    def test_dead_weakref_cleaned_up_during_publish(self, bus: EventBus):
        class Handler:
            def __init__(self):
                self.called = False

            def handle(self, _):
                self.called = True

        h = Handler()
        bus.subscribe("evt", h.handle)

        assert bus.subscriber_count("evt") == 1

        del h
        gc.collect()

        bus.publish("evt", "data")
        assert bus.subscriber_count("evt") == 0

    def test_mixed_alive_and_dead_subscribers(self, bus: EventBus):
        class Handler:
            def __init__(self, name):
                self.name = name
                self.called = False

            def handle(self, _):
                self.called = True

        h1 = Handler("h1")
        h2 = Handler("h2")
        h3 = Handler("h3")

        bus.subscribe("evt", h1.handle)
        bus.subscribe("evt", h2.handle)
        bus.subscribe("evt", h3.handle)

        assert bus.subscriber_count("evt") == 3

        del h2
        gc.collect()

        results = []

        def extra_cb(_):
            results.append("extra")

        bus.subscribe("evt", extra_cb)
        assert bus.subscriber_count("evt") == 3

        bus.publish("evt", "data")

        assert h1.called is True
        assert h3.called is True
        assert "extra" in results
        assert bus.subscriber_count("evt") == 3


class TestUnsubscribeNonexistent:
    def test_unsubscribe_nonexistent_callback_no_error(self, bus: EventBus):
        def some_cb(_): pass
        def other_cb(_): pass

        bus.subscribe("evt", some_cb)
        bus.unsubscribe("evt", other_cb)

        assert bus.subscriber_count("evt") == 1

    def test_unsubscribe_from_nonexistent_event_type_no_error(
        self, bus: EventBus
    ):
        def cb(_): pass

        bus.unsubscribe("nonexistent", cb)

    def test_unsubscribe_already_unsubscribed_no_error(self, bus: EventBus):
        def cb(_): pass

        bus.subscribe("evt", cb)
        bus.unsubscribe("evt", cb)
        bus.unsubscribe("evt", cb)

        assert bus.subscriber_count("evt") == 0


class TestOnceWeakRefCleanup:
    def test_once_callback_triggered_then_weakref_cleaned_up(
        self, bus: EventBus
    ):
        class Receiver:
            instances = 0

            def __init__(self):
                Receiver.instances += 1
                self.called = False

            def __del__(self):
                Receiver.instances -= 1

            def handle(self, _):
                self.called = True

        Receiver.instances = 0

        r = Receiver()
        assert Receiver.instances == 1

        bus.once("evt", r.handle)
        assert bus.subscriber_count("evt") == 1

        bus.publish("evt", "data")
        assert r.called is True
        assert bus.subscriber_count("evt") == 0

        del r
        gc.collect()
        assert Receiver.instances == 0

    def test_once_gced_then_publish_no_problem(self, bus: EventBus):
        class Receiver:
            def __init__(self):
                self.called = False

            def handle(self, _):
                self.called = True

        r = Receiver()
        bus.once("evt", r.handle)

        del r
        gc.collect()

        bus.publish("evt", "data")
        assert bus.subscriber_count("evt") == 0

    def test_once_after_trigger_object_can_be_garbage_collected(
        self, bus: EventBus
    ):
        class Receiver:
            instances = 0

            def __init__(self):
                Receiver.instances += 1

            def __del__(self):
                Receiver.instances -= 1

            def handle(self, _):
                pass

        Receiver.instances = 0

        r = Receiver()
        bus.once("evt", r.handle)
        assert Receiver.instances == 1

        bus.publish("evt", "first")
        assert bus.subscriber_count("evt") == 0

        del r
        gc.collect()
        assert Receiver.instances == 0


class TestInvalidInputs:
    def test_subscribe_empty_event_type_raises(self, bus: EventBus):
        def cb(_): pass

        with pytest.raises(ValueError, match="event_type cannot be empty"):
            bus.subscribe("", cb)

    def test_publish_empty_event_type_raises(self, bus: EventBus):
        with pytest.raises(ValueError, match="event_type cannot be empty"):
            bus.publish("", "data")

    def test_unsubscribe_empty_event_type_raises(self, bus: EventBus):
        def cb(_): pass

        with pytest.raises(ValueError, match="event_type cannot be empty"):
            bus.unsubscribe("", cb)

    def test_once_empty_event_type_raises(self, bus: EventBus):
        def cb(_): pass

        with pytest.raises(ValueError, match="event_type cannot be empty"):
            bus.once("", cb)

    def test_subscribe_none_callback_raises(self, bus: EventBus):
        with pytest.raises(ValueError, match="callback cannot be None"):
            bus.subscribe("evt", None)

    def test_once_none_callback_raises(self, bus: EventBus):
        with pytest.raises(ValueError, match="callback cannot be None"):
            bus.once("evt", None)

    def test_unsubscribe_none_callback_raises(self, bus: EventBus):
        with pytest.raises(ValueError, match="callback cannot be None"):
            bus.unsubscribe("evt", None)

    def test_subscribe_non_callable_raises(self, bus: EventBus):
        with pytest.raises(TypeError, match="callback must be callable"):
            bus.subscribe("evt", "not_callable")

    def test_once_non_callable_raises(self, bus: EventBus):
        with pytest.raises(TypeError, match="callback must be callable"):
            bus.once("evt", 42)


class TestExceptionOrderPreservation:
    def test_subscribers_after_exception_still_run_in_order(
        self, bus: EventBus
    ):
        order = []

        def first(_):
            order.append("first")

        def failing(_):
            order.append("failing")
            raise RuntimeError("boom")

        def second(_):
            order.append("second")

        def third(_):
            order.append("third")

        bus.subscribe("evt", first)
        bus.subscribe("evt", failing)
        bus.subscribe("evt", second)
        bus.subscribe("evt", third)

        bus.publish("evt", "data")

        assert order == ["first", "failing", "second", "third"]


class TestLambdasAndClosures:
    def test_lambda_callback_works(self, bus: EventBus):
        results = []

        bus.subscribe("evt", lambda d: results.append(d))
        bus.publish("evt", "lambda-data")

        assert results == ["lambda-data"]

    def test_closure_callback_works(self, bus: EventBus):
        results = []

        def make_handler(prefix):
            def handler(data):
                results.append(f"{prefix}:{data}")
            return handler

        bus.subscribe("evt", make_handler("a"))
        bus.subscribe("evt", make_handler("b"))

        bus.publish("evt", "x")

        assert "a:x" in results
        assert "b:x" in results


class TestOnceConcurrencySafety:
    def test_concurrent_publish_once_callback_fires_exactly_once(
        self, bus: EventBus
    ):
        import threading

        fire_count = 0
        lock = threading.Lock()

        def on_once(data):
            nonlocal fire_count
            with lock:
                fire_count += 1

        bus.once("evt", on_once)

        num_threads = 20
        barrier = threading.Barrier(num_threads)

        def publish_worker():
            barrier.wait()
            bus.publish("evt", "data")

        threads = [
            threading.Thread(target=publish_worker) for _ in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        assert fire_count == 1

    def test_concurrent_publish_once_subscription_removed(self, bus: EventBus):
        import threading

        bus.once("evt", lambda d: None)

        num_threads = 10
        barrier = threading.Barrier(num_threads)

        def publish_worker():
            barrier.wait()
            bus.publish("evt", "data")

        threads = [
            threading.Thread(target=publish_worker) for _ in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        assert bus.subscriber_count("evt") == 0

    def test_concurrent_publish_mixed_once_and_regular(
        self, bus: EventBus
    ):
        import threading

        once_count = 0
        regular_count = 0
        lock = threading.Lock()

        def on_once(data):
            nonlocal once_count
            with lock:
                once_count += 1

        def on_regular(data):
            nonlocal regular_count
            with lock:
                regular_count += 1

        bus.once("evt", on_once)
        bus.subscribe("evt", on_regular)

        num_threads = 20
        barrier = threading.Barrier(num_threads)

        def publish_worker():
            barrier.wait()
            bus.publish("evt", "data")

        threads = [
            threading.Thread(target=publish_worker) for _ in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        assert once_count == 1
        assert regular_count == num_threads

    def test_concurrent_publish_multiple_once_subscriptions(
        self, bus: EventBus
    ):
        import threading

        counts = {"a": 0, "b": 0, "c": 0}
        lock = threading.Lock()

        def make_handler(key):
            def handler(data):
                with lock:
                    counts[key] += 1
            return handler

        bus.once("evt", make_handler("a"))
        bus.once("evt", make_handler("b"))
        bus.once("evt", make_handler("c"))

        num_threads = 20
        barrier = threading.Barrier(num_threads)

        def publish_worker():
            barrier.wait()
            bus.publish("evt", "data")

        threads = [
            threading.Thread(target=publish_worker) for _ in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        assert counts["a"] == 1
        assert counts["b"] == 1
        assert counts["c"] == 1
