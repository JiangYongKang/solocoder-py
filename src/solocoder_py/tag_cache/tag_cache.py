from __future__ import annotations

import threading
import time
from typing import Any, Dict, Iterable, List, Optional, Set

from .exceptions import (
    AtomicOperationError,
    EntryNotFoundError,
    InvalidTagError,
    TagCacheError,
    TagNotFoundError,
)
from .models import CacheEntry, TagCacheStats


_MAX_PURGE_PER_CALL = 100


class TagCache:
    def __init__(
        self,
        default_ttl: Optional[float] = None,
        auto_cleanup_dangling: bool = True,
    ) -> None:
        if default_ttl is not None and default_ttl < 0:
            raise ValueError("default_ttl must be non-negative")

        self._default_ttl = default_ttl
        self._auto_cleanup_dangling = auto_cleanup_dangling
        self._store: Dict[Any, CacheEntry] = {}
        self._tag_index: Dict[Any, Set[Any]] = {}
        self._expirable_count: int = 0
        self._lock = threading.RLock()

    @property
    def default_ttl(self) -> Optional[float]:
        return self._default_ttl

    @property
    def size(self) -> int:
        with self._lock:
            self._purge_expired()
            return len(self._store)

    @property
    def tag_count(self) -> int:
        with self._lock:
            self._purge_expired()
            if self._auto_cleanup_dangling:
                self.cleanup_dangling_tags()
            return len(self._tag_index)

    def get_stats(self) -> TagCacheStats:
        with self._lock:
            self._purge_expired()
            dangling = self.find_dangling_tags()
            return TagCacheStats(
                entry_count=len(self._store),
                tag_count=len(self._tag_index),
                dangling_tag_count=len(dangling),
            )

    def set(
        self,
        key: Any,
        value: Any,
        tags: Optional[Iterable[Any]] = None,
        ttl: Optional[float] = None,
    ) -> None:
        if ttl is not None and ttl < 0:
            raise ValueError("ttl must be non-negative")

        effective_ttl = ttl if ttl is not None else self._default_ttl
        expire_at = time.monotonic() + effective_ttl if effective_ttl is not None else None
        tag_set: Set[Any] = set(tags) if tags else set()

        for tag in tag_set:
            if tag is None:
                raise InvalidTagError("Tag cannot be None")

        with self._lock:
            self._purge_expired()

            if key in self._store:
                old_entry = self._store[key]
                self._remove_entry_from_tag_index(key, old_entry.tags)
                if old_entry.expire_at is not None:
                    self._expirable_count -= 1

            new_entry = CacheEntry(
                key=key,
                value=value,
                tags=tag_set.copy(),
                expire_at=expire_at,
            )
            self._store[key] = new_entry
            self._add_entry_to_tag_index(key, tag_set)

            if expire_at is not None:
                self._expirable_count += 1

    def get(self, key: Any) -> Optional[Any]:
        with self._lock:
            self._purge_expired()
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.is_expired(time.monotonic()):
                self._delete_internal(key)
                return None
            return entry.value

    def get_entry(self, key: Any) -> Optional[CacheEntry]:
        with self._lock:
            self._purge_expired()
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.is_expired(time.monotonic()):
                self._delete_internal(key)
                return None
            return CacheEntry(
                key=entry.key,
                value=entry.value,
                tags=entry.tags.copy(),
                expire_at=entry.expire_at,
            )

    def has(self, key: Any) -> bool:
        with self._lock:
            self._purge_expired()
            entry = self._store.get(key)
            if entry is None:
                return False
            if entry.is_expired(time.monotonic()):
                self._delete_internal(key)
                return False
            return True

    def delete(self, key: Any) -> bool:
        with self._lock:
            self._purge_expired()
            if key not in self._store:
                return False
            self._delete_internal(key)
            if self._auto_cleanup_dangling:
                self.cleanup_dangling_tags()
            return True

    def add_tags(self, key: Any, tags: Iterable[Any]) -> int:
        tag_list = list(tags)
        for tag in tag_list:
            if tag is None:
                raise InvalidTagError("Tag cannot be None")

        with self._lock:
            self._purge_expired()
            entry = self._store.get(key)
            if entry is None:
                raise EntryNotFoundError(f"Entry with key {key!r} not found")
            if entry.is_expired(time.monotonic()):
                self._delete_internal(key)
                raise EntryNotFoundError(f"Entry with key {key!r} has expired")

            added = 0
            for tag in tag_list:
                if entry.add_tag(tag):
                    self._tag_index.setdefault(tag, set()).add(key)
                    added += 1

            return added

    def remove_tags(self, key: Any, tags: Iterable[Any]) -> int:
        tag_list = list(tags)
        with self._lock:
            self._purge_expired()
            entry = self._store.get(key)
            if entry is None:
                raise EntryNotFoundError(f"Entry with key {key!r} not found")
            if entry.is_expired(time.monotonic()):
                self._delete_internal(key)
                raise EntryNotFoundError(f"Entry with key {key!r} has expired")

            removed = 0
            for tag in tag_list:
                if entry.remove_tag(tag):
                    if tag in self._tag_index:
                        self._tag_index[tag].discard(key)
                    removed += 1

            if self._auto_cleanup_dangling:
                self.cleanup_dangling_tags()

            return removed

    def get_tags_for_entry(self, key: Any) -> Set[Any]:
        with self._lock:
            self._purge_expired()
            entry = self._store.get(key)
            if entry is None:
                raise EntryNotFoundError(f"Entry with key {key!r} not found")
            if entry.is_expired(time.monotonic()):
                self._delete_internal(key)
                raise EntryNotFoundError(f"Entry with key {key!r} has expired")
            return entry.tags.copy()

    def get_entries_by_tag(self, tag: Any) -> List[Any]:
        if tag is None:
            raise InvalidTagError("Tag cannot be None")

        with self._lock:
            self._purge_expired()
            if tag not in self._tag_index:
                return []

            keys = self._tag_index[tag].copy()
            valid_keys: List[Any] = []
            for key in keys:
                entry = self._store.get(key)
                if entry is not None and not entry.is_expired(time.monotonic()):
                    valid_keys.append(key)

            return valid_keys

    def has_tag(self, tag: Any) -> bool:
        if tag is None:
            raise InvalidTagError("Tag cannot be None")

        with self._lock:
            self._purge_expired()
            if tag not in self._tag_index:
                return False
            keys = self._tag_index[tag]
            for key in keys:
                entry = self._store.get(key)
                if entry is not None and not entry.is_expired(time.monotonic()):
                    return True
            return False

    def invalidate_tag(self, tag: Any) -> int:
        if tag is None:
            raise InvalidTagError("Tag cannot be None")

        with self._lock:
            self._purge_expired()

            if tag not in self._tag_index:
                return 0

            keys_to_delete = list(self._tag_index[tag])
            if not keys_to_delete:
                return 0

            deleted_count = 0
            try:
                snapshot = {}
                for key in keys_to_delete:
                    if key in self._store:
                        entry = self._store[key]
                        if not entry.is_expired(time.monotonic()):
                            snapshot[key] = CacheEntry(
                                key=entry.key,
                                value=entry.value,
                                tags=entry.tags.copy(),
                                expire_at=entry.expire_at,
                            )

                for key in snapshot:
                    self._delete_internal(key)
                    deleted_count += 1

            except Exception as e:
                for key, entry in snapshot.items():
                    if key not in self._store:
                        self._store[key] = entry
                        self._add_entry_to_tag_index(key, entry.tags)
                        if entry.expire_at is not None:
                            self._expirable_count += 1
                raise AtomicOperationError(
                    f"Atomic invalidate_tag failed for tag {tag!r}, changes rolled back"
                ) from e

            if self._auto_cleanup_dangling:
                self.cleanup_dangling_tags()

            return deleted_count

    def invalidate_tags(self, tags: Iterable[Any]) -> int:
        tag_list = list(tags)
        for tag in tag_list:
            if tag is None:
                raise InvalidTagError("Tag cannot be None")

        with self._lock:
            self._purge_expired()

            all_keys: Set[Any] = set()
            for tag in tag_list:
                if tag in self._tag_index:
                    all_keys.update(self._tag_index[tag])

            if not all_keys:
                return 0

            deleted_count = 0
            snapshot = {}
            try:
                for key in all_keys:
                    if key in self._store:
                        entry = self._store[key]
                        if not entry.is_expired(time.monotonic()):
                            snapshot[key] = CacheEntry(
                                key=entry.key,
                                value=entry.value,
                                tags=entry.tags.copy(),
                                expire_at=entry.expire_at,
                            )

                for key in snapshot:
                    self._delete_internal(key)
                    deleted_count += 1

            except Exception as e:
                for key, entry in snapshot.items():
                    if key not in self._store:
                        self._store[key] = entry
                        self._add_entry_to_tag_index(key, entry.tags)
                        if entry.expire_at is not None:
                            self._expirable_count += 1
                raise AtomicOperationError(
                    "Atomic invalidate_tags failed, changes rolled back"
                ) from e

            if self._auto_cleanup_dangling:
                self.cleanup_dangling_tags()

            return deleted_count

    def find_dangling_tags(self) -> Set[Any]:
        with self._lock:
            dangling: Set[Any] = set()
            for tag, keys in self._tag_index.items():
                valid_keys = [
                    k for k in keys
                    if k in self._store and not self._store[k].is_expired(time.monotonic())
                ]
                if not valid_keys:
                    dangling.add(tag)
            return dangling

    def cleanup_dangling_tags(self) -> int:
        with self._lock:
            dangling = self.find_dangling_tags()
            for tag in dangling:
                del self._tag_index[tag]
            return len(dangling)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._tag_index.clear()
            self._expirable_count = 0

    def _add_entry_to_tag_index(self, key: Any, tags: Set[Any]) -> None:
        for tag in tags:
            self._tag_index.setdefault(tag, set()).add(key)

    def _remove_entry_from_tag_index(self, key: Any, tags: Set[Any]) -> None:
        for tag in tags:
            if tag in self._tag_index:
                self._tag_index[tag].discard(key)

    def _delete_internal(self, key: Any) -> None:
        entry = self._store.pop(key, None)
        if entry is not None:
            self._remove_entry_from_tag_index(key, entry.tags)
            if entry.expire_at is not None:
                self._expirable_count -= 1

    def _purge_expired(self) -> None:
        if self._expirable_count == 0:
            return

        now = time.monotonic()
        expired_keys: List[Any] = []
        scanned = 0

        for key, entry in self._store.items():
            if scanned >= _MAX_PURGE_PER_CALL:
                break
            scanned += 1
            if entry.is_expired(now):
                expired_keys.append(key)

        for key in expired_keys:
            self._delete_internal(key)

        if self._auto_cleanup_dangling and expired_keys:
            self.cleanup_dangling_tags()
