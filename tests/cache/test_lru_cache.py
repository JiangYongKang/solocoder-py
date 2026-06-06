import threading
import time

import pytest

from solocoder_py.cache import LRUCache


class TestLRUBasicOperations:
    def test_set_and_get(self):
        cache = LRUCache(capacity=10)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_nonexistent_returns_none(self):
        cache = LRUCache(capacity=10)
        assert cache.get("nonexistent") is None

    def test_overwrite_existing_key(self):
        cache = LRUCache(capacity=10)
        cache.set("key", "old")
        cache.set("key", "new")
        assert cache.get("key") == "new"
        assert cache.size == 1

    def test_delete(self):
        cache = LRUCache(capacity=10)
        cache.set("a", 1)
        assert cache.delete("a") is True
        assert cache.get("a") is None
        assert cache.delete("a") is False

    def test_delete_purges_expired(self):
        cache = LRUCache(capacity=10)
        cache.set("a", 1, ttl=0.01)
        cache.set("b", 2)
        time.sleep(0.05)
        cache.delete("nonexistent")
        assert cache.size == 1
        assert cache.has("a") is False

    def test_has(self):
        cache = LRUCache(capacity=10)
        cache.set("a", 1)
        assert cache.has("a") is True
        assert cache.has("b") is False

    def test_clear(self):
        cache = LRUCache(capacity=10)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.size == 0
        assert cache.get("a") is None
        assert cache.current_weight == 0

    def test_size(self):
        cache = LRUCache(capacity=10)
        assert cache.size == 0
        cache.set("a", 1)
        assert cache.size == 1
        cache.set("b", 2)
        assert cache.size == 2


class TestLRUEviction:
    def test_evicts_lru_when_capacity_exceeded(self):
        cache = LRUCache(capacity=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.set("d", 4)
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3
        assert cache.get("d") == 4

    def test_get_updates_lru_order(self):
        cache = LRUCache(capacity=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.get("a")
        cache.set("d", 4)
        assert cache.get("a") == 1
        assert cache.get("b") is None
        assert cache.get("c") == 3
        assert cache.get("d") == 4

    def test_set_existing_key_updates_lru_order(self):
        cache = LRUCache(capacity=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.set("a", 10)
        cache.set("d", 4)
        assert cache.get("a") == 10
        assert cache.get("b") is None
        assert cache.get("c") == 3
        assert cache.get("d") == 4


class TestTTLExpiration:
    def test_expired_entry_returns_none(self):
        cache = LRUCache(capacity=10)
        cache.set("key", "value", ttl=0.05)
        time.sleep(0.1)
        assert cache.get("key") is None

    def test_non_expired_entry_returns_value(self):
        cache = LRUCache(capacity=10)
        cache.set("key", "value", ttl=10)
        assert cache.get("key") == "value"

    def test_expired_entry_removed_on_access(self):
        cache = LRUCache(capacity=10)
        cache.set("a", 1, ttl=0.05)
        cache.set("b", 2)
        time.sleep(0.1)
        _ = cache.get("a")
        assert cache.size == 1
        assert cache.has("a") is False

    def test_has_checks_expiration(self):
        cache = LRUCache(capacity=10)
        cache.set("key", "value", ttl=0.05)
        assert cache.has("key") is True
        time.sleep(0.1)
        assert cache.has("key") is False

    def test_default_ttl_applied(self):
        cache = LRUCache(capacity=10, default_ttl=0.05)
        cache.set("key", "value")
        assert cache.get("key") == "value"
        time.sleep(0.1)
        assert cache.get("key") is None

    def test_per_key_ttl_overrides_default(self):
        cache = LRUCache(capacity=10, default_ttl=0.05)
        cache.set("a", 1, ttl=10)
        cache.set("b", 2)
        time.sleep(0.1)
        assert cache.get("a") == 1
        assert cache.get("b") is None

    def test_size_excludes_expired(self):
        cache = LRUCache(capacity=10)
        cache.set("a", 1, ttl=0.05)
        cache.set("b", 2)
        assert cache.size == 2
        time.sleep(0.1)
        assert cache.size == 1

    def test_no_ttl_never_expires(self):
        cache = LRUCache(capacity=10)
        cache.set("key", "value")
        time.sleep(0.05)
        assert cache.get("key") == "value"

    def test_expired_entry_at_tail_caught_by_get(self):
        cache = LRUCache(capacity=200)
        for i in range(150):
            cache.set(f"fresh{i}", i, ttl=100)
        cache.set("expired_soon", "gone", ttl=0.01)
        time.sleep(0.05)
        assert cache.get("expired_soon") is None

    def test_expired_entry_at_tail_caught_by_has(self):
        cache = LRUCache(capacity=200)
        for i in range(150):
            cache.set(f"fresh{i}", i, ttl=100)
        cache.set("expired_soon", "gone", ttl=0.01)
        time.sleep(0.05)
        assert cache.has("expired_soon") is False


class TestWeightControl:
    def test_current_weight_tracking(self):
        cache = LRUCache(max_weight=100)
        cache.set("a", 1, weight=3)
        cache.set("b", 2, weight=5)
        assert cache.current_weight == 8

    def test_eviction_by_weight(self):
        cache = LRUCache(capacity=100, max_weight=10)
        cache.set("a", 1, weight=6)
        cache.set("b", 2, weight=3)
        assert cache.current_weight == 9
        cache.set("c", 3, weight=2)
        assert cache.current_weight <= 10
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3

    def test_update_weight_when_overwriting(self):
        cache = LRUCache(max_weight=20)
        cache.set("a", 1, weight=5)
        assert cache.current_weight == 5
        cache.set("a", 2, weight=10)
        assert cache.current_weight == 10
        assert cache.size == 1

    def test_delete_reduces_weight(self):
        cache = LRUCache(max_weight=100)
        cache.set("a", 1, weight=7)
        cache.delete("a")
        assert cache.current_weight == 0

    def test_clear_resets_weight(self):
        cache = LRUCache(max_weight=100)
        cache.set("a", 1, weight=5)
        cache.set("b", 2, weight=3)
        cache.clear()
        assert cache.current_weight == 0

    def test_zero_weight_item(self):
        cache = LRUCache(max_weight=5)
        cache.set("a", 1, weight=0)
        cache.set("b", 2, weight=0)
        assert cache.current_weight == 0
        assert cache.size == 2

    def test_item_weight_exceeds_max_weight_rejected(self):
        cache = LRUCache(max_weight=5)
        cache.set("a", 1, weight=10)
        assert cache.get("a") is None
        assert cache.size == 0

    def test_lru_eviction_respects_weight_order(self):
        cache = LRUCache(capacity=100, max_weight=10)
        cache.set("a", 1, weight=4)
        cache.set("b", 2, weight=4)
        cache.get("a")
        cache.set("c", 3, weight=4)
        assert cache.get("a") == 1
        assert cache.get("b") is None
        assert cache.get("c") == 3

    def test_combined_capacity_and_weight(self):
        cache = LRUCache(capacity=3, max_weight=10)
        cache.set("a", 1, weight=2)
        cache.set("b", 2, weight=2)
        cache.set("c", 3, weight=2)
        cache.set("d", 4, weight=2)
        assert cache.get("a") is None
        assert cache.current_weight == 6


class TestZeroCapacityCache:
    def test_zero_capacity_means_unlimited(self):
        cache = LRUCache(capacity=0, max_weight=0)
        for i in range(1000):
            cache.set(f"key{i}", f"value{i}")
        assert cache.size == 1000
        assert cache.get("key0") == "value0"
        assert cache.get("key999") == "value999"

    def test_zero_capacity_never_evicts(self):
        cache = LRUCache(capacity=0)
        for i in range(100):
            cache.set(f"key{i}", i)
        for i in range(100):
            assert cache.get(f"key{i}") == i
        assert cache.size == 100


class TestZeroWeightLimit:
    def test_zero_weight_limit_allows_entries(self):
        cache = LRUCache(capacity=10, max_weight=0)
        cache.set("a", 1, weight=5)
        cache.set("b", 2, weight=10)
        assert cache.get("a") == 1
        assert cache.get("b") == 2

    def test_zero_weight_limit_does_not_evict(self):
        cache = LRUCache(capacity=100, max_weight=0)
        for i in range(50):
            cache.set(f"key{i}", i, weight=100)
        assert cache.size == 50


class TestTTLZeroImmediateExpiration:
    def test_ttl_zero_expires_immediately_on_get(self):
        cache = LRUCache(capacity=10)
        cache.set("key", "value", ttl=0)
        assert cache.get("key") is None

    def test_ttl_zero_expires_immediately_on_has(self):
        cache = LRUCache(capacity=10)
        cache.set("key", "value", ttl=0)
        assert cache.has("key") is False

    def test_default_ttl_zero(self):
        cache = LRUCache(capacity=10, default_ttl=0)
        cache.set("key", "value")
        assert cache.get("key") is None


class TestConcurrentAccess:
    def test_concurrent_writes_data_integrity(self):
        cache = LRUCache(capacity=1000, max_weight=10000)
        errors = []
        results = {}
        num_threads = 10
        per_thread = 100

        def writer(start, count):
            try:
                for i in range(start, start + count):
                    cache.set(f"key{i}", f"value{i}", weight=1)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=writer, args=(i * per_thread, per_thread))
            for i in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert cache.size <= 1000

        for i in range(num_threads * per_thread):
            val = cache.get(f"key{i}")
            if val is not None:
                assert val == f"value{i}", f"key{i} has corrupted value: {val}"
                results[f"key{i}"] = val

        assert len(results) == cache.size

    def test_concurrent_reads_and_writes(self):
        cache = LRUCache(capacity=1000, max_weight=10000)
        errors = []

        def writer():
            for i in range(200):
                cache.set(f"key{i}", f"value{i}")

        def reader():
            for i in range(200):
                try:
                    val = cache.get(f"key{i}")
                    if val is not None:
                        assert val == f"value{i}"
                except Exception as e:
                    errors.append(e)

        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=writer))
            threads.append(threading.Thread(target=reader))
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_concurrent_weight_consistency(self):
        cache = LRUCache(capacity=10000, max_weight=100000)

        def writer(start, count):
            for i in range(start, start + count):
                cache.set(f"key{i}", i, weight=2)

        threads = [threading.Thread(target=writer, args=(i * 50, 50)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        expected_weight = cache.size * 2
        assert cache.current_weight == expected_weight

    def test_concurrent_set_delete_clear(self):
        cache = LRUCache(capacity=100, max_weight=10000)
        errors = []

        def setter():
            for i in range(100):
                try:
                    cache.set(f"key{i}", i)
                except Exception as e:
                    errors.append(e)

        def deleter():
            for i in range(100):
                try:
                    cache.delete(f"key{i}")
                except Exception as e:
                    errors.append(e)

        def clearer():
            for _ in range(10):
                try:
                    cache.clear()
                except Exception as e:
                    errors.append(e)

        threads = [
            threading.Thread(target=setter),
            threading.Thread(target=deleter),
            threading.Thread(target=clearer),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_concurrent_writes_with_eviction(self):
        cache = LRUCache(capacity=50, max_weight=500)
        errors = []
        mismatches = []
        num_threads = 8
        per_thread = 100

        def writer(start, count):
            try:
                for i in range(start, start + count):
                    cache.set(f"key{i}", f"value{i}", weight=1)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=writer, args=(i * per_thread, per_thread))
            for i in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert cache.size <= 50
        assert cache.current_weight <= 500

        for i in range(num_threads * per_thread):
            val = cache.get(f"key{i}")
            if val is not None:
                if val != f"value{i}":
                    mismatches.append((f"key{i}", val))

        assert len(mismatches) == 0, f"Data mismatches found: {mismatches[:5]}"

    def test_concurrent_reads_writes_with_weight_eviction(self):
        cache = LRUCache(capacity=1000, max_weight=100)
        errors = []
        mismatches = []

        def writer():
            for i in range(200):
                try:
                    cache.set(f"key{i}", f"value{i}", weight=3)
                except Exception as e:
                    errors.append(e)

        def reader():
            for i in range(200):
                try:
                    val = cache.get(f"key{i}")
                    if val is not None and val != f"value{i}":
                        mismatches.append((f"key{i}", val))
                except Exception as e:
                    errors.append(e)

        threads = []
        for _ in range(4):
            threads.append(threading.Thread(target=writer))
            threads.append(threading.Thread(target=reader))
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(mismatches) == 0
        assert cache.current_weight <= 100


class TestWeightBoundary:
    def test_weight_exactly_at_limit(self):
        cache = LRUCache(max_weight=10)
        cache.set("a", 1, weight=5)
        cache.set("b", 2, weight=5)
        assert cache.current_weight == 10
        assert cache.size == 2
        assert cache.get("a") == 1
        assert cache.get("b") == 2

    def test_weight_one_over_triggers_eviction(self):
        cache = LRUCache(max_weight=10)
        cache.set("a", 1, weight=5)
        cache.set("b", 2, weight=5)
        cache.set("c", 3, weight=1)
        assert cache.current_weight <= 10
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3

    def test_weight_just_below_limit(self):
        cache = LRUCache(max_weight=10)
        cache.set("a", 1, weight=4)
        cache.set("b", 2, weight=5)
        assert cache.current_weight == 9
        assert cache.size == 2

    def test_weight_eviction_cascades(self):
        cache = LRUCache(max_weight=10)
        cache.set("a", 1, weight=3)
        cache.set("b", 2, weight=3)
        cache.set("c", 3, weight=3)
        cache.set("d", 4, weight=5)
        assert cache.current_weight <= 10
        assert cache.get("a") is None
        assert cache.get("d") == 4


class TestExpiredAccessReturnsNone:
    def test_access_after_ttl_returns_none(self):
        cache = LRUCache(capacity=10)
        cache.set("key", "value", ttl=0.01)
        time.sleep(0.05)
        assert cache.get("key") is None

    def test_multiple_accesses_after_expiry(self):
        cache = LRUCache(capacity=10)
        cache.set("key", "value", ttl=0.01)
        time.sleep(0.05)
        assert cache.get("key") is None
        assert cache.get("key") is None
        assert cache.has("key") is False

    def test_expired_then_reinserted(self):
        cache = LRUCache(capacity=10)
        cache.set("key", "old", ttl=0.01)
        time.sleep(0.05)
        cache.set("key", "new", ttl=10)
        assert cache.get("key") == "new"

    def test_expired_frees_capacity(self):
        cache = LRUCache(capacity=2)
        cache.set("a", 1, ttl=0.01)
        cache.set("b", 2)
        time.sleep(0.05)
        cache.set("c", 3)
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3

    def test_expired_frees_weight(self):
        cache = LRUCache(max_weight=10)
        cache.set("a", 1, ttl=0.01, weight=8)
        cache.set("b", 2, weight=2)
        time.sleep(0.05)
        cache.set("c", 3, weight=7)
        assert cache.current_weight <= 10
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3


class TestConstructorValidation:
    def test_negative_capacity_raises(self):
        with pytest.raises(ValueError, match="capacity must be non-negative"):
            LRUCache(capacity=-1)

    def test_negative_max_weight_raises(self):
        with pytest.raises(ValueError, match="max_weight must be non-negative"):
            LRUCache(max_weight=-1)

    def test_negative_default_ttl_raises(self):
        with pytest.raises(ValueError, match="default_ttl must be non-negative"):
            LRUCache(default_ttl=-1)

    def test_negative_weight_on_set_raises(self):
        cache = LRUCache()
        with pytest.raises(ValueError, match="weight must be non-negative"):
            cache.set("key", "value", weight=-1)

    def test_negative_ttl_on_set_raises(self):
        cache = LRUCache()
        with pytest.raises(ValueError, match="ttl must be non-negative"):
            cache.set("key", "value", ttl=-1)
