from __future__ import annotations

import threading
import time
from typing import Dict, List, Optional, Tuple

from .exceptions import DNSCacheError
from .models import CacheEntry, DNSRecord, DNSRecordType


_CacheKey = Tuple[str, DNSRecordType]


class DNSCache:
    def __init__(self) -> None:
        self._store: Dict[_CacheKey, List[CacheEntry]] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _make_key(name: str, record_type: DNSRecordType) -> _CacheKey:
        normalized_name = name.rstrip(".").lower()
        return (normalized_name, record_type)

    def get(
        self, name: str, record_type: DNSRecordType
    ) -> Optional[List[DNSRecord]]:
        key = self._make_key(name, record_type)
        with self._lock:
            entries = self._store.get(key)
            if entries is None:
                return None

            valid_entries: List[CacheEntry] = []
            for entry in entries:
                if not entry.is_expired:
                    valid_entries.append(entry)

            if not valid_entries:
                del self._store[key]
                return None

            if len(valid_entries) != len(entries):
                self._store[key] = valid_entries

            return [entry.record for entry in valid_entries]

    def put(self, record: DNSRecord) -> None:
        if record.ttl == 0:
            return

        key = self._make_key(record.name, record.type)
        expires_at = time.monotonic() + record.ttl
        new_entry = CacheEntry(record=record, expires_at=expires_at)

        with self._lock:
            entries = self._store.get(key, [])
            entries = [e for e in entries if not e.is_expired]
            entries.append(new_entry)
            self._store[key] = entries

    def put_all(self, records: List[DNSRecord]) -> None:
        for record in records:
            self.put(record)

    def invalidate(self, name: str, record_type: Optional[DNSRecordType] = None) -> None:
        normalized_name = name.rstrip(".").lower()
        with self._lock:
            if record_type is not None:
                key = self._make_key(normalized_name, record_type)
                self._store.pop(key, None)
            else:
                keys_to_remove = [
                    k for k in self._store if k[0] == normalized_name
                ]
                for k in keys_to_remove:
                    del self._store[k]

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def purge_expired(self) -> int:
        with self._lock:
            purged_count = 0
            keys_to_remove: List[_CacheKey] = []

            for key, entries in self._store.items():
                valid_entries = [e for e in entries if not e.is_expired]
                purged_count += len(entries) - len(valid_entries)
                if not valid_entries:
                    keys_to_remove.append(key)
                elif len(valid_entries) != len(entries):
                    self._store[key] = valid_entries

            for key in keys_to_remove:
                del self._store[key]

            return purged_count

    def __len__(self) -> int:
        with self._lock:
            self.purge_expired()
            return sum(len(entries) for entries in self._store.values())

    def __contains__(self, item: Tuple[str, DNSRecordType]) -> bool:
        if not isinstance(item, tuple) or len(item) != 2:
            raise DNSCacheError("Cache key must be a tuple of (name, record_type)")
        name, record_type = item
        return self.get(name, record_type) is not None
