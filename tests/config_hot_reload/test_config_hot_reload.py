from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import List

import pytest

from solocoder_py.config_hot_reload import (
    ChangeEvent,
    ChangeType,
    ConfigChange,
    ConfigHotReloadManager,
    ConfigVersion,
    ListenerError,
    NoActiveVersionError,
    VersionNotFoundError,
)
from .conftest import make_manager


class TestConfigVersionModel:
    def test_config_version_creation(self):
        now = datetime.now()
        data = {"key1": "value1", "key2": 42}
        cv = ConfigVersion(version="v1", timestamp=now, data=data)
        assert cv.version == "v1"
        assert cv.timestamp == now
        assert cv.data == data

    def test_config_version_empty_version_raises(self):
        with pytest.raises(ValueError, match="version cannot be empty"):
            ConfigVersion(version="", timestamp=datetime.now(), data={})

    def test_config_version_get(self):
        cv = ConfigVersion(
            version="v1",
            timestamp=datetime.now(),
            data={"a": 1, "b": 2},
        )
        assert cv.get("a") == 1
        assert cv.get("c") is None
        assert cv.get("c", "default") == "default"

    def test_config_version_has_key(self):
        cv = ConfigVersion(
            version="v1",
            timestamp=datetime.now(),
            data={"a": 1, "b": 2},
        )
        assert cv.has_key("a") is True
        assert cv.has_key("c") is False

    def test_config_version_keys(self):
        cv = ConfigVersion(
            version="v1",
            timestamp=datetime.now(),
            data={"b": 2, "a": 1, "c": 3},
        )
        assert cv.keys() == ("a", "b", "c")


class TestConfigChangeModel:
    def test_config_change_added(self):
        change = ConfigChange(
            key="test",
            change_type=ChangeType.ADDED,
            old_value=None,
            new_value="value",
        )
        assert change.key == "test"
        assert change.change_type == ChangeType.ADDED
        assert change.old_value is None
        assert change.new_value == "value"

    def test_config_change_modified(self):
        change = ConfigChange(
            key="test",
            change_type=ChangeType.MODIFIED,
            old_value="old",
            new_value="new",
        )
        assert change.change_type == ChangeType.MODIFIED

    def test_config_change_removed(self):
        change = ConfigChange(
            key="test",
            change_type=ChangeType.REMOVED,
            old_value="value",
            new_value=None,
        )
        assert change.change_type == ChangeType.REMOVED


class TestChangeTypeEnum:
    def test_change_type_values(self):
        assert ChangeType.ADDED == "added"
        assert ChangeType.MODIFIED == "modified"
        assert ChangeType.REMOVED == "removed"


class TestPublishVersion:
    def test_first_publish(self):
        manager = make_manager()
        config = {"app.name": "test-app", "app.port": 8080}
        cv = manager.publish(config)

        assert cv.version == "v1"
        assert cv.data == config
        assert manager.version_count() == 1

        current = manager.get_current_version()
        assert current is not None
        assert current.version == "v1"

    def test_publish_multiple_versions(self):
        manager = make_manager()
        v1 = manager.publish({"a": 1})
        v2 = manager.publish({"a": 2})
        v3 = manager.publish({"a": 3})

        assert v1.version == "v1"
        assert v2.version == "v2"
        assert v3.version == "v3"
        assert manager.version_count() == 3

        current = manager.get_current_version()
        assert current is not None
        assert current.version == "v3"
        assert current.data == {"a": 3}

    def test_publish_increments_version_counter(self):
        manager = make_manager()
        for i in range(5):
            cv = manager.publish({"key": i})
            assert cv.version == f"v{i + 1}"

    def test_publish_snapshot_deep_copy(self):
        manager = make_manager()
        original = {"nested": {"inner": 1}}
        manager.publish(original)
        original["nested"]["inner"] = 999

        current_data = manager.get_all()
        assert current_data["nested"]["inner"] == 1

    def test_publish_invalid_type_raises(self):
        manager = make_manager()
        with pytest.raises(TypeError, match="config_data must be a dict"):
            manager.publish("not a dict")  # type: ignore


class TestReadCurrentConfig:
    def test_get_key(self):
        manager = make_manager()
        manager.publish({"a": 1, "b": 2})
        assert manager.get("a") == 1
        assert manager.get("b") == 2
        assert manager.get("c") is None
        assert manager.get("c", "default") == "default"

    def test_get_returns_default_identity_not_deepcopy(self):
        manager = make_manager()
        manager.publish({"a": 1})

        sentinel = object()
        result = manager.get("nonexistent", sentinel)
        assert result is sentinel

    def test_get_default_mutable_not_deepcopied(self):
        manager = make_manager()
        manager.publish({"a": 1})

        default_list = [1, 2, 3]
        result = manager.get("nonexistent", default_list)
        result.append(999)
        assert default_list == [1, 2, 3, 999]
        assert result is default_list

    def test_get_existing_key_returns_deepcopy(self):
        manager = make_manager()
        manager.publish({"nested": {"inner": [1, 2]}})

        value = manager.get("nested")
        value["inner"].append(999)
        value["extra"] = "injected"

        stored = manager.get("nested")
        assert stored == {"inner": [1, 2]}
        assert "extra" not in stored

    def test_get_no_active_version_raises(self):
        manager = make_manager()
        with pytest.raises(NoActiveVersionError):
            manager.get("any_key")

    def test_get_all(self):
        manager = make_manager()
        config = {"a": 1, "b": {"c": 2}}
        manager.publish(config)
        result = manager.get_all()
        assert result == config

        result["b"]["c"] = 999
        assert manager.get("b") == {"c": 2}

    def test_get_all_no_active_version_raises(self):
        manager = make_manager()
        with pytest.raises(NoActiveVersionError):
            manager.get_all()

    def test_get_current_version_returns_none_when_empty(self):
        manager = make_manager()
        assert manager.get_current_version() is None

    def test_hot_update_reads_latest(self):
        manager = make_manager()
        manager.publish({"feature_x": "off"})
        assert manager.get("feature_x") == "off"

        manager.publish({"feature_x": "on"})
        assert manager.get("feature_x") == "on"


class TestVersionHistory:
    def test_get_version(self):
        manager = make_manager()
        manager.publish({"a": 1})
        manager.publish({"a": 2})

        v1 = manager.get_version("v1")
        assert v1.version == "v1"
        assert v1.data == {"a": 1}

        v2 = manager.get_version("v2")
        assert v2.version == "v2"
        assert v2.data == {"a": 2}

    def test_get_version_not_found_raises(self):
        manager = make_manager()
        manager.publish({"a": 1})
        with pytest.raises(VersionNotFoundError):
            manager.get_version("v999")

    def test_get_history(self):
        manager = make_manager()
        manager.publish({"a": 1})
        manager.publish({"a": 2})
        manager.publish({"a": 3})

        history = manager.get_history()
        assert len(history) == 3
        assert history[0].version == "v1"
        assert history[1].version == "v2"
        assert history[2].version == "v3"
        assert [v.data["a"] for v in history] == [1, 2, 3]

    def test_get_history_empty(self):
        manager = make_manager()
        history = manager.get_history()
        assert history == ()

    def test_has_version(self):
        manager = make_manager()
        manager.publish({"a": 1})
        assert manager.has_version("v1") is True
        assert manager.has_version("v2") is False

    def test_version_count(self):
        manager = make_manager()
        assert manager.version_count() == 0
        manager.publish({"a": 1})
        assert manager.version_count() == 1
        manager.publish({"a": 2})
        assert manager.version_count() == 2


class TestChangeListener:
    def test_subscribe_listener(self):
        manager = make_manager()
        events: List[ChangeEvent] = []

        def on_change(event: ChangeEvent):
            events.append(event)

        listener_id = manager.subscribe(on_change)
        assert listener_id is not None
        assert manager.listener_count() == 1

    def test_subscribe_non_callable_raises(self):
        manager = make_manager()
        with pytest.raises(TypeError, match="listener must be callable"):
            manager.subscribe("not callable")  # type: ignore

    def test_unsubscribe_listener(self):
        manager = make_manager()
        listener_id = manager.subscribe(lambda e: None)
        assert manager.listener_count() == 1

        result = manager.unsubscribe(listener_id)
        assert result is True
        assert manager.listener_count() == 0

    def test_unsubscribe_invalid_id(self):
        manager = make_manager()
        result = manager.unsubscribe("invalid-id")
        assert result is False

    def test_listener_receives_change_event(self):
        manager = make_manager()
        events: List[ChangeEvent] = []
        manager.subscribe(lambda e: events.append(e))

        manager.publish({"a": 1})

        assert len(events) == 1
        event = events[0]
        assert event.version == "v1"
        assert event.is_rollback is False
        assert len(event.changes) == 1
        assert event.changes[0].key == "a"
        assert event.changes[0].change_type == ChangeType.ADDED
        assert event.changes[0].new_value == 1

    def test_listener_modified_change(self):
        manager = make_manager()
        events: List[ChangeEvent] = []
        manager.subscribe(lambda e: events.append(e))

        manager.publish({"a": 1})
        manager.publish({"a": 2})

        assert len(events) == 2
        modify_event = events[1]
        assert len(modify_event.changes) == 1
        assert modify_event.changes[0].change_type == ChangeType.MODIFIED
        assert modify_event.changes[0].old_value == 1
        assert modify_event.changes[0].new_value == 2

    def test_listener_removed_change(self):
        manager = make_manager()
        events: List[ChangeEvent] = []
        manager.subscribe(lambda e: events.append(e))

        manager.publish({"a": 1, "b": 2})
        manager.publish({"a": 1})

        remove_event = events[1]
        assert len(remove_event.changes) == 1
        assert remove_event.changes[0].key == "b"
        assert remove_event.changes[0].change_type == ChangeType.REMOVED
        assert remove_event.changes[0].old_value == 2

    def test_listener_multiple_changes(self):
        manager = make_manager()
        events: List[ChangeEvent] = []
        manager.subscribe(lambda e: events.append(e))

        manager.publish({"a": 1, "b": 2})
        manager.publish({"a": 10, "c": 3})

        event = events[1]
        change_keys = {c.key for c in event.changes}
        change_types = {c.key: c.change_type for c in event.changes}

        assert change_keys == {"a", "b", "c"}
        assert change_types["a"] == ChangeType.MODIFIED
        assert change_types["b"] == ChangeType.REMOVED
        assert change_types["c"] == ChangeType.ADDED

    def test_event_fired_even_when_no_changes(self):
        manager = make_manager()
        events: List[ChangeEvent] = []
        manager.subscribe(lambda e: events.append(e))

        manager.publish({"a": 1})
        manager.publish({"a": 1})

        assert len(events) == 2
        assert events[0].version == "v1"
        assert events[1].version == "v2"
        assert len(events[1].changes) == 0

    def test_multiple_listeners(self):
        manager = make_manager()
        events1: List[ChangeEvent] = []
        events2: List[ChangeEvent] = []

        manager.subscribe(lambda e: events1.append(e))
        manager.subscribe(lambda e: events2.append(e))

        manager.publish({"a": 1})

        assert len(events1) == 1
        assert len(events2) == 1
        assert events1[0].version == events2[0].version

    def test_listener_exception_raises_listener_error(self):
        manager = make_manager()

        def bad_listener(event: ChangeEvent):
            raise RuntimeError("listener failed")

        manager.subscribe(bad_listener)

        with pytest.raises(ListenerError, match="One or more listeners failed"):
            manager.publish({"a": 1})

    def test_multiple_listeners_some_fail(self):
        manager = make_manager()
        events: List[ChangeEvent] = []

        def good_listener(event: ChangeEvent):
            events.append(event)

        def bad_listener(event: ChangeEvent):
            raise RuntimeError("oops")

        manager.subscribe(good_listener)
        manager.subscribe(bad_listener)

        with pytest.raises(ListenerError):
            manager.publish({"a": 1})

        assert len(events) == 1


class TestListenerEventSnapshotIsolation:
    def test_listener_modifying_new_value_does_not_pollute_internal(self):
        manager = make_manager()

        def mutate_listener(event: ChangeEvent):
            for change in event.changes:
                if change.new_value is not None and isinstance(change.new_value, dict):
                    change.new_value["injected"] = "evil"
                    if "inner" in change.new_value:
                        change.new_value["inner"].append(999)

        manager.subscribe(mutate_listener)
        manager.publish({"nested": {"inner": [1, 2]}})

        stored = manager.get("nested")
        assert stored == {"inner": [1, 2]}
        assert "injected" not in stored

    def test_listener_modifying_old_value_does_not_pollute_internal(self):
        manager = make_manager()
        manager.publish({"nested": {"inner": [1, 2]}})

        def mutate_listener(event: ChangeEvent):
            for change in event.changes:
                if change.old_value is not None and isinstance(change.old_value, dict):
                    change.old_value["injected"] = "evil"
                    if "inner" in change.old_value:
                        change.old_value["inner"].append(999)

        manager.subscribe(mutate_listener)
        manager.publish({"nested": {"inner": [3, 4]}})

        v1 = manager.get_version("v1")
        assert v1.data["nested"] == {"inner": [1, 2]}
        assert "injected" not in v1.data["nested"]

    def test_rollback_listener_modifying_values_does_not_pollute(self):
        manager = make_manager()
        manager.publish({"cfg": {"list": [1, 2]}})
        manager.publish({"cfg": {"list": [3, 4]}})

        def mutate_listener(event: ChangeEvent):
            for change in event.changes:
                if change.new_value is not None and isinstance(change.new_value, dict):
                    change.new_value["list"].append(999)
                if change.old_value is not None and isinstance(change.old_value, dict):
                    change.old_value["list"].append(888)

        manager.subscribe(mutate_listener)
        manager.rollback("v1")

        v1 = manager.get_version("v1")
        v2 = manager.get_version("v2")
        assert v1.data["cfg"] == {"list": [1, 2]}
        assert v2.data["cfg"] == {"list": [3, 4]}


class TestRollback:
    def test_rollback_to_previous_version(self):
        manager = make_manager()
        manager.publish({"a": 1})
        manager.publish({"a": 2})

        rolled = manager.rollback("v1")
        assert rolled.version == "v1"
        assert rolled.data == {"a": 1}

        current = manager.get_current_version()
        assert current is not None
        assert current.version == "v1"
        assert current.data == {"a": 1}
        assert manager.version_count() == 2

    def test_rollback_switches_current_version_not_creates_new(self):
        manager = make_manager()
        manager.publish({"a": 1})
        manager.publish({"a": 2})
        manager.publish({"a": 3})

        assert manager.version_count() == 3
        assert manager.get_current_version() is not None
        assert manager.get_current_version().version == "v3"

        rolled = manager.rollback("v1")
        assert rolled.version == "v1"
        assert rolled.data == {"a": 1}
        assert manager.version_count() == 3
        assert manager.get_current_version() is not None
        assert manager.get_current_version().version == "v1"

    def test_rollback_triggers_change_event(self):
        manager = make_manager()
        events: List[ChangeEvent] = []
        manager.subscribe(lambda e: events.append(e))

        manager.publish({"a": 1, "b": 2})
        manager.publish({"a": 10})

        events.clear()
        manager.rollback("v1")

        assert len(events) == 1
        event = events[0]
        assert event.version == "v1"
        assert event.is_rollback is True
        change_types = {c.key: c.change_type for c in event.changes}
        assert change_types["a"] == ChangeType.MODIFIED
        assert change_types["b"] == ChangeType.ADDED

    def test_rollback_to_current_version_fires_event(self):
        manager = make_manager()
        events: List[ChangeEvent] = []
        manager.subscribe(lambda e: events.append(e))

        manager.publish({"a": 1})
        assert len(events) == 1

        manager.rollback("v1")
        assert len(events) == 2
        event = events[1]
        assert event.version == "v1"
        assert event.is_rollback is True
        assert len(event.changes) == 0

        current = manager.get_current_version()
        assert current is not None
        assert current.version == "v1"

    def test_rollback_duplicate_content_fires_event(self):
        manager = make_manager()
        events: List[ChangeEvent] = []
        manager.subscribe(lambda e: events.append(e))

        manager.publish({"a": 1})
        manager.publish({"a": 1})
        assert len(events) == 2

        manager.rollback("v1")
        assert len(events) == 3
        event = events[2]
        assert event.version == "v1"
        assert event.is_rollback is True
        assert len(event.changes) == 0

    def test_rollback_nonexistent_version_raises(self):
        manager = make_manager()
        manager.publish({"a": 1})
        with pytest.raises(VersionNotFoundError):
            manager.rollback("v999")

    def test_rollback_chain(self):
        manager = make_manager()
        manager.publish({"a": 1})
        manager.publish({"a": 2})
        manager.publish({"a": 3})

        manager.rollback("v1")
        assert manager.get("a") == 1
        assert manager.get_current_version() is not None
        assert manager.get_current_version().version == "v1"

        manager.rollback("v2")
        assert manager.get("a") == 2
        assert manager.get_current_version() is not None
        assert manager.get_current_version().version == "v2"

        assert manager.version_count() == 3
        history = manager.get_history()
        versions = [v.version for v in history]
        assert versions == ["v1", "v2", "v3"]


class TestBoundaryConditions:
    def test_publish_empty_config(self):
        manager = make_manager()
        cv = manager.publish({})
        assert cv.version == "v1"
        assert cv.data == {}

    def test_publish_empty_config_fires_event(self):
        manager = make_manager()
        events: List[ChangeEvent] = []
        manager.subscribe(lambda e: events.append(e))

        manager.publish({})
        assert len(events) == 1
        assert events[0].version == "v1"
        assert events[0].is_rollback is False
        assert len(events[0].changes) == 0

    def test_publish_duplicate_config_fires_event(self):
        manager = make_manager()
        events: List[ChangeEvent] = []
        manager.subscribe(lambda e: events.append(e))

        manager.publish({"a": 1, "b": 2})
        manager.publish({"a": 1, "b": 2})

        assert len(events) == 2
        assert events[0].version == "v1"
        assert events[1].version == "v2"
        assert len(events[0].changes) == 2
        assert len(events[1].changes) == 0

    def test_get_returns_deep_copy_isolates_nested_config(self):
        manager = make_manager()
        manager.publish({"nested": {"inner": [1, 2, 3]}})

        value = manager.get("nested")
        assert value == {"inner": [1, 2, 3]}

        value["inner"].append(999)
        value["new_key"] = "injected"

        stored = manager.get("nested")
        assert stored == {"inner": [1, 2, 3]}
        assert "new_key" not in stored

    def test_config_with_nested_structures(self):
        manager = make_manager()
        config = {
            "db": {
                "host": "localhost",
                "port": 5432,
                "credentials": {"user": "admin", "pass": "secret"},
            },
            "features": ["auth", "logging"],
        }
        manager.publish(config)
        assert manager.get("db") == config["db"]
        assert manager.get("features") == ["auth", "logging"]

    def test_many_versions(self):
        manager = make_manager()
        num_versions = 100
        for i in range(num_versions):
            manager.publish({"counter": i})

        assert manager.version_count() == num_versions
        assert manager.get("counter") == num_versions - 1

        for i in range(num_versions):
            cv = manager.get_version(f"v{i + 1}")
            assert cv.data["counter"] == i

    def test_subscribe_after_publish(self):
        manager = make_manager()
        events: List[ChangeEvent] = []

        manager.publish({"a": 1})
        manager.subscribe(lambda e: events.append(e))
        manager.publish({"a": 2})

        assert len(events) == 1
        assert events[0].version == "v2"

    def test_clear_manager(self):
        manager = make_manager()
        manager.subscribe(lambda e: None)
        manager.publish({"a": 1})
        manager.publish({"a": 2})

        manager.clear()

        assert manager.version_count() == 0
        assert manager.listener_count() == 0
        assert manager.get_current_version() is None

        cv = manager.publish({"b": 3})
        assert cv.version == "v1"


class TestConcurrency:
    def test_concurrent_publishes(self):
        manager = make_manager()
        results = []
        lock = threading.Lock()

        def publisher(start, count):
            for i in range(count):
                cv = manager.publish({f"key_{start}_{i}": i})
                with lock:
                    results.append(cv.version)

        threads = [threading.Thread(target=publisher, args=(i, 10)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
            assert t.is_alive() is False

        assert len(results) == 50
        assert manager.version_count() == 50

    def test_concurrent_reads_and_publishes(self):
        manager = make_manager()
        manager.publish({"counter": 0})
        errors = []
        read_values = []

        def reader():
            try:
                for _ in range(50):
                    val = manager.get("counter")
                    read_values.append(val)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        def writer():
            for i in range(20):
                manager.publish({"counter": i + 1})

        reader_thread = threading.Thread(target=reader)
        writer_thread = threading.Thread(target=writer)

        reader_thread.start()
        writer_thread.start()
        reader_thread.join(timeout=10)
        writer_thread.join(timeout=10)

        assert len(errors) == 0
        assert manager.get("counter") == 20

    def test_concurrent_subscribe_and_publish(self):
        manager = make_manager()
        event_count = {"count": 0}
        event_lock = threading.Lock()

        def counting_listener(event):
            with event_lock:
                event_count["count"] += 1

        errors = []

        def subscriber():
            try:
                for _ in range(20):
                    lid = manager.subscribe(counting_listener)
                    time.sleep(0.001)
                    manager.unsubscribe(lid)
            except Exception as e:
                errors.append(e)

        def publisher():
            for i in range(20):
                manager.publish({"key": i})

        sub_thread = threading.Thread(target=subscriber)
        pub_thread = threading.Thread(target=publisher)

        sub_thread.start()
        pub_thread.start()
        sub_thread.join(timeout=10)
        pub_thread.join(timeout=10)

        assert len(errors) == 0


class TestComputeChanges:
    def test_changes_added_keys(self):
        manager = make_manager()
        events: List[ChangeEvent] = []
        manager.subscribe(lambda e: events.append(e))

        manager.publish({})
        events.clear()
        manager.publish({"a": 1, "b": 2})

        event = events[0]
        assert len(event.changes) == 2
        assert all(c.change_type == ChangeType.ADDED for c in event.changes)

    def test_changes_modified_keys(self):
        manager = make_manager()
        events: List[ChangeEvent] = []
        manager.subscribe(lambda e: events.append(e))

        manager.publish({"a": 1, "b": 2})
        events.clear()
        manager.publish({"a": 10, "b": 2})

        event = events[0]
        assert len(event.changes) == 1
        assert event.changes[0].key == "a"
        assert event.changes[0].change_type == ChangeType.MODIFIED
        assert event.changes[0].old_value == 1
        assert event.changes[0].new_value == 10

    def test_changes_removed_keys(self):
        manager = make_manager()
        events: List[ChangeEvent] = []
        manager.subscribe(lambda e: events.append(e))

        manager.publish({"a": 1, "b": 2, "c": 3})
        events.clear()
        manager.publish({"a": 1})

        event = events[0]
        removed = {c.key for c in event.changes if c.change_type == ChangeType.REMOVED}
        assert removed == {"b", "c"}

    def test_changes_sorted_by_key(self):
        manager = make_manager()
        events: List[ChangeEvent] = []
        manager.subscribe(lambda e: events.append(e))

        manager.publish({})
        events.clear()
        manager.publish({"c": 3, "a": 1, "b": 2})

        event = events[0]
        keys = [c.key for c in event.changes]
        assert keys == ["a", "b", "c"]
