import threading
import time
from typing import Any

import pytest

from solocoder_py.tag_cache import (
    AtomicOperationError,
    CacheEntry,
    EntryNotFoundError,
    InvalidTagError,
    TagCache,
    TagCacheStats,
    TagNotFoundError,
)


class TestBasicOperations:
    def test_set_and_get_without_tags(self):
        cache = TagCache()
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        assert cache.size == 1

    def test_get_nonexistent_returns_none(self):
        cache = TagCache()
        assert cache.get("nonexistent") is None

    def test_overwrite_existing_key(self):
        cache = TagCache()
        cache.set("key", "old", tags=["tag1"])
        cache.set("key", "new", tags=["tag2"])
        assert cache.get("key") == "new"
        assert cache.get_tags_for_entry("key") == {"tag2"}
        with pytest.raises(TagNotFoundError):
            cache.get_entries_by_tag("tag1")
        assert cache.get_entries_by_tag("tag2") == ["key"]
        assert cache.size == 1

    def test_has(self):
        cache = TagCache()
        cache.set("a", 1, tags=["tag1"])
        assert cache.has("a") is True
        assert cache.has("b") is False

    def test_delete(self):
        cache = TagCache()
        cache.set("a", 1, tags=["tag1"])
        assert cache.delete("a") is True
        assert cache.get("a") is None
        assert cache.delete("a") is False

    def test_clear(self):
        cache = TagCache()
        cache.set("a", 1, tags=["tag1", "tag2"])
        cache.set("b", 2, tags=["tag1"])
        cache.clear()
        assert cache.size == 0
        assert cache.tag_count == 0
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_size(self):
        cache = TagCache()
        assert cache.size == 0
        cache.set("a", 1, tags=["tag1"])
        assert cache.size == 1
        cache.set("b", 2, tags=["tag1"])
        assert cache.size == 2


class TestSingleEntrySingleTag:
    def test_set_entry_with_single_tag(self):
        cache = TagCache()
        cache.set("user:1", {"name": "Alice"}, tags=["user"])
        assert cache.get("user:1") == {"name": "Alice"}
        assert cache.get_tags_for_entry("user:1") == {"user"}

    def test_query_entries_by_tag(self):
        cache = TagCache()
        cache.set("user:1", "Alice", tags=["user"])
        cache.set("user:2", "Bob", tags=["user"])
        cache.set("product:1", "Laptop", tags=["product"])

        user_entries = cache.get_entries_by_tag("user")
        assert sorted(user_entries) == ["user:1", "user:2"]
        product_entries = cache.get_entries_by_tag("product")
        assert product_entries == ["product:1"]

    def test_invalidate_single_tag(self):
        cache = TagCache()
        cache.set("user:1", "Alice", tags=["user"])
        cache.set("user:2", "Bob", tags=["user"])
        cache.set("product:1", "Laptop", tags=["product"])

        invalidated = cache.invalidate_tag("user")
        assert invalidated == 2
        assert cache.get("user:1") is None
        assert cache.get("user:2") is None
        assert cache.get("product:1") == "Laptop"

        with pytest.raises(TagNotFoundError):
            cache.get_entries_by_tag("user")
        product_entries = cache.get_entries_by_tag("product")
        assert product_entries == ["product:1"]

    def test_tag_association_is_many_to_many(self):
        cache = TagCache()
        cache.set("entry1", "value1", tags=["tag1", "tag2"])
        cache.set("entry2", "value2", tags=["tag1", "tag3"])

        tag1_entries = cache.get_entries_by_tag("tag1")
        assert sorted(tag1_entries) == ["entry1", "entry2"]
        tag2_entries = cache.get_entries_by_tag("tag2")
        assert tag2_entries == ["entry1"]
        tag3_entries = cache.get_entries_by_tag("tag3")
        assert tag3_entries == ["entry2"]

        assert cache.get_tags_for_entry("entry1") == {"tag1", "tag2"}
        assert cache.get_tags_for_entry("entry2") == {"tag1", "tag3"}


class TestSingleEntryMultipleTags:
    def test_entry_with_multiple_tags(self):
        cache = TagCache()
        cache.set("article:1", "Python Guide", tags=["tech", "python", "tutorial"])

        tags = cache.get_tags_for_entry("article:1")
        assert tags == {"tech", "python", "tutorial"}

    def test_cross_tag_query(self):
        cache = TagCache()
        cache.set("doc1", "Python API", tags=["tech", "python"])
        cache.set("doc2", "Java API", tags=["tech", "java"])
        cache.set("doc3", "Python Basics", tags=["python", "beginner"])

        tech_entries = cache.get_entries_by_tag("tech")
        assert sorted(tech_entries) == ["doc1", "doc2"]
        python_entries = cache.get_entries_by_tag("python")
        assert sorted(python_entries) == ["doc1", "doc3"]

    def test_invalidate_one_tag_preserves_other_tags(self):
        cache = TagCache()
        cache.set("doc1", "Python API", tags=["tech", "python"])
        cache.set("doc2", "Java API", tags=["tech", "java"])

        cache.invalidate_tag("python")
        assert cache.get("doc1") is None
        assert cache.get("doc2") == "Java API"

        tech_entries = cache.get_entries_by_tag("tech")
        assert tech_entries == ["doc2"]
        with pytest.raises(TagNotFoundError):
            cache.get_entries_by_tag("python")


class TestBatchInvalidationMultipleEntries:
    def test_invalidate_tag_with_many_entries(self):
        cache = TagCache()
        for i in range(100):
            cache.set(f"user:{i}", f"User {i}", tags=["user"])
        for i in range(50):
            cache.set(f"product:{i}", f"Product {i}", tags=["product"])

        assert cache.size == 150
        invalidated = cache.invalidate_tag("user")
        assert invalidated == 100
        assert cache.size == 50

        for i in range(100):
            assert cache.get(f"user:{i}") is None
        for i in range(50):
            assert cache.get(f"product:{i}") == f"Product {i}"

    def test_invalidate_tags_multiple_tags_at_once(self):
        cache = TagCache()
        cache.set("a", 1, tags=["tag1"])
        cache.set("b", 2, tags=["tag2"])
        cache.set("c", 3, tags=["tag1", "tag2"])
        cache.set("d", 4, tags=["tag3"])

        invalidated = cache.invalidate_tags(["tag1", "tag2"])
        assert invalidated == 3
        assert cache.get("a") is None
        assert cache.get("b") is None
        assert cache.get("c") is None
        assert cache.get("d") == 4

    def test_invalidate_tags_no_duplicate_deletes(self):
        cache = TagCache()
        cache.set("shared", "value", tags=["tag1", "tag2", "tag3"])

        invalidated = cache.invalidate_tags(["tag1", "tag2", "tag3"])
        assert invalidated == 1
        assert cache.get("shared") is None


class TestBoundaryConditions:
    def test_invalidate_tag_with_zero_entries(self):
        cache = TagCache()
        cache.set("a", 1, tags=["tag1"])
        cache.invalidate_tag("tag1")

        with pytest.raises(TagNotFoundError):
            cache.invalidate_tag("tag1")
        assert cache.size == 0

    def test_entry_without_tags(self):
        cache = TagCache()
        cache.set("no_tag", "value")
        assert cache.get("no_tag") == "value"
        assert cache.get_tags_for_entry("no_tag") == set()
        assert cache.size == 1
        assert cache.tag_count == 0

    def test_delete_entry_without_tags(self):
        cache = TagCache()
        cache.set("no_tag", "value")
        assert cache.delete("no_tag") is True
        assert cache.get("no_tag") is None
        assert cache.size == 0

    def test_all_entries_invalidated_tag_becomes_dangling(self):
        cache = TagCache(auto_cleanup_dangling=False)
        cache.set("a", 1, tags=["temp"])
        cache.set("b", 2, tags=["temp"])

        assert cache.tag_count == 1
        cache.invalidate_tag("temp")
        assert cache.size == 0

        dangling = cache.find_dangling_tags()
        assert dangling == {"temp"}
        cleaned = cache.cleanup_dangling_tags()
        assert cleaned == 1
        assert cache.tag_count == 0

    def test_expired_entry_causes_dangling_tag(self):
        cache = TagCache(auto_cleanup_dangling=False)
        cache.set("temp_key", "value", tags=["temp_tag"], ttl=0.01)
        assert cache.tag_count == 1

        time.sleep(0.05)
        _ = cache.get("temp_key")

        dangling = cache.find_dangling_tags()
        assert dangling == {"temp_tag"}

    def test_empty_tag_list_on_set(self):
        cache = TagCache()
        cache.set("key", "value", tags=[])
        assert cache.get("key") == "value"
        assert cache.get_tags_for_entry("key") == set()
        assert cache.tag_count == 0

    def test_none_tags_on_set(self):
        cache = TagCache()
        cache.set("key", "value", tags=None)
        assert cache.get("key") == "value"
        assert cache.get_tags_for_entry("key") == set()


class TestDanglingTagCleanup:
    def test_find_dangling_tags_after_delete(self):
        cache = TagCache(auto_cleanup_dangling=False)
        cache.set("a", 1, tags=["tag1", "tag2"])
        cache.set("b", 2, tags=["tag1"])

        cache.delete("a")
        cache.delete("b")

        dangling = cache.find_dangling_tags()
        assert dangling == {"tag1", "tag2"}

    def test_find_dangling_tags_after_invalidate(self):
        cache = TagCache(auto_cleanup_dangling=False)
        cache.set("a", 1, tags=["tag1"])
        cache.set("b", 2, tags=["tag1"])
        cache.set("c", 3, tags=["tag2"])

        cache.invalidate_tag("tag1")
        dangling = cache.find_dangling_tags()
        assert dangling == {"tag1"}
        assert "tag2" not in dangling

    def test_auto_cleanup_dangling_enabled(self):
        cache = TagCache(auto_cleanup_dangling=True)
        cache.set("a", 1, tags=["temp"])
        cache.delete("a")
        assert cache.tag_count == 0

    def test_auto_cleanup_dangling_disabled(self):
        cache = TagCache(auto_cleanup_dangling=False)
        cache.set("a", 1, tags=["temp"])
        cache.delete("a")
        assert cache.tag_count == 1
        cache.cleanup_dangling_tags()
        assert cache.tag_count == 0

    def test_cleanup_dangling_tags_returns_count(self):
        cache = TagCache(auto_cleanup_dangling=False)
        cache.set("a", 1, tags=["tag1", "tag2"])
        cache.delete("a")

        cleaned = cache.cleanup_dangling_tags()
        assert cleaned == 2

    def test_partial_tag_entries_not_dangling(self):
        cache = TagCache(auto_cleanup_dangling=False)
        cache.set("a", 1, tags=["tag1"])
        cache.set("b", 2, tags=["tag1"])
        cache.delete("a")

        dangling = cache.find_dangling_tags()
        assert dangling == set()
        assert cache.get_entries_by_tag("tag1") == ["b"]


class TestExceptionBranches:
    def test_invalidate_nonexistent_tag(self):
        cache = TagCache()
        with pytest.raises(TagNotFoundError):
            cache.invalidate_tag("nonexistent")

    def test_invalidate_already_invalidated_entries(self):
        cache = TagCache()
        cache.set("a", 1, tags=["tag1"])
        cache.invalidate_tag("tag1")

        with pytest.raises(TagNotFoundError):
            cache.invalidate_tag("tag1")
        assert cache.get("a") is None

    def test_duplicate_tag_association_is_idempotent(self):
        cache = TagCache()
        cache.set("a", 1, tags=["tag1", "tag1", "tag1"])
        assert cache.get_tags_for_entry("a") == {"tag1"}

        added = cache.add_tags("a", ["tag1", "tag1"])
        assert added == 0
        assert cache.get_tags_for_entry("a") == {"tag1"}

    def test_add_tags_to_nonexistent_entry(self):
        cache = TagCache()
        with pytest.raises(EntryNotFoundError, match="not found"):
            cache.add_tags("nonexistent", ["tag1"])

    def test_remove_tags_from_nonexistent_entry(self):
        cache = TagCache()
        with pytest.raises(EntryNotFoundError, match="not found"):
            cache.remove_tags("nonexistent", ["tag1"])

    def test_get_tags_for_nonexistent_entry(self):
        cache = TagCache()
        with pytest.raises(EntryNotFoundError, match="not found"):
            cache.get_tags_for_entry("nonexistent")

    def test_none_tag_raises_invalid_tag_error(self):
        cache = TagCache()
        with pytest.raises(InvalidTagError, match="Tag cannot be None"):
            cache.set("key", "value", tags=[None])

        with pytest.raises(InvalidTagError, match="Tag cannot be None"):
            cache.invalidate_tag(None)

        with pytest.raises(InvalidTagError, match="Tag cannot be None"):
            cache.get_entries_by_tag(None)

        with pytest.raises(InvalidTagError, match="Tag cannot be None"):
            cache.add_tags("key", [None])

        cache.set("key", "value", tags=["tag1"])
        with pytest.raises(InvalidTagError, match="Tag cannot be None"):
            cache.remove_tags("key", [None])

    def test_invalid_ttl_raises(self):
        cache = TagCache()
        with pytest.raises(ValueError, match="ttl must be non-negative"):
            cache.set("key", "value", ttl=-1)

    def test_invalid_default_ttl_raises(self):
        with pytest.raises(ValueError, match="default_ttl must be non-negative"):
            TagCache(default_ttl=-1)

    def test_invalidate_tags_with_none(self):
        cache = TagCache()
        with pytest.raises(InvalidTagError, match="Tag cannot be None"):
            cache.invalidate_tags(["tag1", None])


class TestAddRemoveTags:
    def test_add_tags_to_existing_entry(self):
        cache = TagCache()
        cache.set("a", 1, tags=["tag1"])
        added = cache.add_tags("a", ["tag2", "tag3"])
        assert added == 2
        assert cache.get_tags_for_entry("a") == {"tag1", "tag2", "tag3"}

    def test_remove_tags_from_entry(self):
        cache = TagCache()
        cache.set("a", 1, tags=["tag1", "tag2", "tag3"])
        removed = cache.remove_tags("a", ["tag1", "tag2"])
        assert removed == 2
        assert cache.get_tags_for_entry("a") == {"tag3"}

    def test_remove_nonexistent_tag_from_entry(self):
        cache = TagCache()
        cache.set("a", 1, tags=["tag1"])
        removed = cache.remove_tags("a", ["tag2", "tag3"])
        assert removed == 0
        assert cache.get_tags_for_entry("a") == {"tag1"}

    def test_remove_all_tags_creates_dangling(self):
        cache = TagCache(auto_cleanup_dangling=False)
        cache.set("a", 1, tags=["tag1", "tag2"])
        cache.remove_tags("a", ["tag1", "tag2"])

        dangling = cache.find_dangling_tags()
        assert dangling == {"tag1", "tag2"}


class TestTTLExpiration:
    def test_expired_entry_returns_none(self):
        cache = TagCache()
        cache.set("key", "value", ttl=0.01)
        time.sleep(0.05)
        assert cache.get("key") is None

    def test_expired_entry_removed_from_tag_index(self):
        cache = TagCache(auto_cleanup_dangling=False)
        cache.set("key", "value", tags=["tag1"], ttl=0.01)
        time.sleep(0.05)

        _ = cache.get("key")
        entries = cache.get_entries_by_tag("tag1")
        assert entries == []

    def test_default_ttl_applied(self):
        cache = TagCache(default_ttl=0.01)
        cache.set("key", "value")
        time.sleep(0.05)
        assert cache.get("key") is None

    def test_per_key_ttl_overrides_default(self):
        cache = TagCache(default_ttl=0.01)
        cache.set("a", 1, ttl=10)
        cache.set("b", 2)
        time.sleep(0.05)
        assert cache.get("a") == 1
        assert cache.get("b") is None

    def test_expired_entry_cleans_up_tags(self):
        cache = TagCache(auto_cleanup_dangling=True)
        cache.set("key", "value", tags=["temp"], ttl=0.01)
        time.sleep(0.05)
        _ = cache.get("key")
        assert cache.tag_count == 0


class TestHasTag:
    def test_has_tag_with_entries(self):
        cache = TagCache()
        cache.set("a", 1, tags=["tag1"])
        assert cache.has_tag("tag1") is True
        with pytest.raises(TagNotFoundError):
            cache.has_tag("nonexistent")

    def test_has_tag_with_expired_entries(self):
        cache = TagCache()
        cache.set("a", 1, tags=["tag1"], ttl=0.01)
        time.sleep(0.05)
        with pytest.raises(TagNotFoundError):
            cache.has_tag("tag1")

    def test_has_tag_with_dangling_tag(self):
        cache = TagCache(auto_cleanup_dangling=False)
        cache.set("a", 1, tags=["tag1"])
        cache.delete("a")
        assert cache.has_tag("tag1") is False


class TestAtomicity:
    def test_invalidate_tag_atomicity(self):
        cache = TagCache()
        for i in range(10):
            cache.set(f"key{i}", i, tags=["batch"])

        original_entries = [cache.get(f"key{i}") for i in range(10)]
        assert all(v is not None for v in original_entries)

        invalidated = cache.invalidate_tag("batch")
        assert invalidated == 10

        for i in range(10):
            assert cache.get(f"key{i}") is None

    def test_invalidate_tags_atomicity_across_tags(self):
        cache = TagCache()
        cache.set("a", 1, tags=["tag1"])
        cache.set("b", 2, tags=["tag2"])
        cache.set("c", 3, tags=["tag1", "tag2"])

        invalidated = cache.invalidate_tags(["tag1", "tag2"])
        assert invalidated == 3
        assert cache.get("a") is None
        assert cache.get("b") is None
        assert cache.get("c") is None


class TestStats:
    def test_get_stats(self):
        cache = TagCache(auto_cleanup_dangling=False)
        stats = cache.get_stats()
        assert isinstance(stats, TagCacheStats)
        assert stats.entry_count == 0
        assert stats.tag_count == 0
        assert stats.dangling_tag_count == 0

        cache.set("a", 1, tags=["tag1", "tag2"])
        cache.set("b", 2, tags=["tag1"])
        stats = cache.get_stats()
        assert stats.entry_count == 2
        assert stats.tag_count == 2
        assert stats.dangling_tag_count == 0

        cache.delete("a")
        cache.delete("b")
        stats = cache.get_stats()
        assert stats.entry_count == 0
        assert stats.tag_count == 2
        assert stats.dangling_tag_count == 2


class TestConcurrentAccess:
    def test_concurrent_writes_with_tags(self):
        cache = TagCache()
        errors = []
        num_threads = 10
        per_thread = 50

        def writer(start, count):
            try:
                for i in range(start, start + count):
                    cache.set(f"key{i}", f"value{i}", tags=[f"tag{i % 5}"])
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
        assert cache.size == num_threads * per_thread

    def test_concurrent_invalidate_tag(self):
        cache = TagCache()
        errors = []

        for i in range(100):
            cache.set(f"key{i}", i, tags=["shared"])

        def invalidator():
            try:
                cache.invalidate_tag("shared")
            except Exception as e:
                errors.append(e)

        def writer():
            try:
                for i in range(100, 200):
                    cache.set(f"key{i}", i, tags=["shared"])
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=invalidator),
            threading.Thread(target=writer),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_concurrent_reads_and_writes(self):
        cache = TagCache()
        errors = []
        mismatches = []

        for i in range(100):
            cache.set(f"key{i}", i, tags=[f"group{i % 10}"])

        def reader():
            try:
                for i in range(100):
                    val = cache.get(f"key{i}")
                    if val is not None and val != i:
                        mismatches.append((f"key{i}", val))
            except Exception as e:
                errors.append(e)

        def tag_invalidator():
            try:
                for i in range(10):
                    cache.invalidate_tag(f"group{i}")
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=reader),
            threading.Thread(target=tag_invalidator),
            threading.Thread(target=reader),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(mismatches) == 0


class TestCacheEntryModel:
    def test_cache_entry_creation(self):
        entry = CacheEntry(key="k", value="v", tags={"tag1"}, expire_at=None)
        assert entry.key == "k"
        assert entry.value == "v"
        assert entry.tags == {"tag1"}
        assert entry.expire_at is None

    def test_cache_entry_is_expired(self):
        entry = CacheEntry(key="k", value="v", expire_at=100.0)
        assert entry.is_expired(200.0) is True
        assert entry.is_expired(50.0) is False

    def test_cache_entry_has_tag(self):
        entry = CacheEntry(key="k", value="v", tags={"tag1", "tag2"})
        assert entry.has_tag("tag1") is True
        assert entry.has_tag("tag3") is False

    def test_cache_entry_add_tag(self):
        entry = CacheEntry(key="k", value="v", tags={"tag1"})
        assert entry.add_tag("tag2") is True
        assert entry.add_tag("tag1") is False
        assert entry.tags == {"tag1", "tag2"}

    def test_cache_entry_remove_tag(self):
        entry = CacheEntry(key="k", value="v", tags={"tag1", "tag2"})
        assert entry.remove_tag("tag1") is True
        assert entry.remove_tag("tag3") is False
        assert entry.tags == {"tag2"}


class TestEntryNotFoundAfterExpiry:
    def test_get_tags_for_expired_entry(self):
        cache = TagCache()
        cache.set("key", "value", tags=["tag1"], ttl=0.01)
        time.sleep(0.05)

        with pytest.raises(EntryNotFoundError):
            cache.get_tags_for_entry("key")

    def test_add_tags_to_expired_entry(self):
        cache = TagCache()
        cache.set("key", "value", tags=["tag1"], ttl=0.01)
        time.sleep(0.05)

        with pytest.raises(EntryNotFoundError):
            cache.add_tags("key", ["tag2"])

    def test_remove_tags_from_expired_entry(self):
        cache = TagCache()
        cache.set("key", "value", tags=["tag1", "tag2"], ttl=0.01)
        time.sleep(0.05)

        with pytest.raises(EntryNotFoundError):
            cache.remove_tags("key", ["tag1"])

    def test_get_entry_returns_copy(self):
        cache = TagCache()
        cache.set("key", "value", tags=["tag1"])

        entry = cache.get_entry("key")
        assert entry is not None
        entry.tags.add("tag2")

        actual_tags = cache.get_tags_for_entry("key")
        assert actual_tags == {"tag1"}


class TestEdgeCases:
    def test_set_same_key_updates_tags(self):
        cache = TagCache()
        cache.set("key", "value1", tags=["tag1", "tag2"])
        cache.set("key", "value2", tags=["tag2", "tag3"])

        assert cache.get("key") == "value2"
        assert cache.get_tags_for_entry("key") == {"tag2", "tag3"}
        with pytest.raises(TagNotFoundError):
            cache.get_entries_by_tag("tag1")
        assert cache.get_entries_by_tag("tag2") == ["key"]
        assert cache.get_entries_by_tag("tag3") == ["key"]

    def test_delete_then_reinsert_with_same_tags(self):
        cache = TagCache()
        cache.set("key", "value1", tags=["tag1"])
        cache.delete("key")
        cache.set("key", "value2", tags=["tag1"])

        assert cache.get("key") == "value2"
        assert cache.get_entries_by_tag("tag1") == ["key"]

    def test_invalidate_tag_then_reuse_tag(self):
        cache = TagCache()
        cache.set("key1", "value1", tags=["tag1"])
        cache.invalidate_tag("tag1")
        cache.set("key2", "value2", tags=["tag1"])

        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get_entries_by_tag("tag1") == ["key2"]

    def test_empty_cache_operations(self):
        cache = TagCache()
        assert cache.size == 0
        assert cache.tag_count == 0
        assert cache.get("anything") is None
        assert cache.has("anything") is False
        assert cache.delete("anything") is False
        with pytest.raises(TagNotFoundError):
            cache.invalidate_tag("anything")
        with pytest.raises(TagNotFoundError):
            cache.get_entries_by_tag("anything")
        with pytest.raises(TagNotFoundError):
            cache.has_tag("anything")
        assert cache.find_dangling_tags() == set()
        assert cache.cleanup_dangling_tags() == 0

    def test_various_hashable_tag_types(self):
        cache = TagCache()
        cache.set("key", "value", tags=[1, "string", (1, 2), frozenset([3, 4])])

        tags = cache.get_tags_for_entry("key")
        assert tags == {1, "string", (1, 2), frozenset([3, 4])}

        for tag in [1, "string", (1, 2), frozenset([3, 4])]:
            assert cache.get_entries_by_tag(tag) == ["key"]

    def test_many_tags_per_entry(self):
        cache = TagCache()
        tags = [f"tag{i}" for i in range(100)]
        cache.set("key", "value", tags=tags)

        entry_tags = cache.get_tags_for_entry("key")
        assert len(entry_tags) == 100

        for tag in tags:
            entries = cache.get_entries_by_tag(tag)
            assert entries == ["key"]

        invalidated = cache.invalidate_tag("tag50")
        assert invalidated == 1
        assert cache.get("key") is None


class TestPurgeExpiredFullScan:
    def test_purge_expired_cleans_all_entries_beyond_100(self):
        cache = TagCache(auto_cleanup_dangling=True)
        for i in range(200):
            cache.set(f"key{i}", f"value{i}", tags=[f"tag{i}"], ttl=0.5)

        assert cache.size == 200
        time.sleep(0.6)

        assert cache.size == 0

    def test_purge_expired_cleans_mixed_entries(self):
        cache = TagCache(auto_cleanup_dangling=True)
        for i in range(150):
            if i % 2 == 0:
                cache.set(f"key{i}", f"value{i}", tags=[f"tag{i}"], ttl=0.5)
            else:
                cache.set(f"key{i}", f"value{i}", tags=[f"tag{i}"])

        assert cache.size == 150
        time.sleep(0.6)

        assert cache.size == 75

        for i in range(150):
            if i % 2 == 0:
                assert cache.get(f"key{i}") is None
            else:
                assert cache.get(f"key{i}") == f"value{i}"

    def test_purge_expired_updates_tag_index(self):
        cache = TagCache(auto_cleanup_dangling=True)
        for i in range(200):
            cache.set(f"key{i}", f"value{i}", tags=["shared"], ttl=0.5)

        time.sleep(0.6)

        with pytest.raises(TagNotFoundError):
            cache.get_entries_by_tag("shared")


class TestTagNotFoundErrorConsistency:
    def test_get_entries_by_tag_raises_for_nonexistent(self):
        cache = TagCache()
        with pytest.raises(TagNotFoundError, match="not found"):
            cache.get_entries_by_tag("nonexistent")

    def test_has_tag_raises_for_nonexistent(self):
        cache = TagCache()
        with pytest.raises(TagNotFoundError, match="not found"):
            cache.has_tag("nonexistent")

    def test_invalidate_tag_raises_for_nonexistent(self):
        cache = TagCache()
        with pytest.raises(TagNotFoundError, match="not found"):
            cache.invalidate_tag("nonexistent")

    def test_invalidate_tags_raises_for_nonexistent(self):
        cache = TagCache()
        cache.set("a", 1, tags=["tag1"])
        with pytest.raises(TagNotFoundError, match="not found"):
            cache.invalidate_tags(["tag1", "nonexistent"])

    def test_tag_not_found_after_auto_cleanup(self):
        cache = TagCache(auto_cleanup_dangling=True)
        cache.set("a", 1, tags=["temp"])
        cache.delete("a")

        with pytest.raises(TagNotFoundError):
            cache.get_entries_by_tag("temp")

    def test_tag_still_queryable_with_manual_cleanup(self):
        cache = TagCache(auto_cleanup_dangling=False)
        cache.set("a", 1, tags=["temp"])
        cache.delete("a")

        entries = cache.get_entries_by_tag("temp")
        assert entries == []
        assert cache.has_tag("temp") is False
