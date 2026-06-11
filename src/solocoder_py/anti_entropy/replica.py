from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional

from .exceptions import VersionError
from .models import VersionedEntry


@dataclass
class Replica:
    replica_id: str
    _data: Dict[str, VersionedEntry] = field(default_factory=dict)
    _lock: threading.RLock = field(default_factory=threading.RLock)

    def __post_init__(self) -> None:
        if self.replica_id is None:
            raise ValueError("replica_id cannot be None")
        if not isinstance(self.replica_id, str):
            raise TypeError("replica_id must be a string")

    def get(self, key: str) -> Optional[VersionedEntry]:
        with self._lock:
            if key not in self._data:
                return None
            entry = self._data[key]
            return VersionedEntry(
                key=entry.key,
                value=entry.value,
                version=entry.version,
            )

    def put(self, key: str, value: Any, version: Optional[int] = None) -> VersionedEntry:
        with self._lock:
            if version is None:
                if key in self._data:
                    version = self._data[key].version + 1
                else:
                    version = 1
            if version < 0:
                raise VersionError("version must be non-negative")
            if key in self._data:
                current = self._data[key]
                if version < current.version:
                    raise VersionError(
                        f"Cannot downgrade version: current={current.version}, new={version}"
                    )
            entry = VersionedEntry(key=key, value=value, version=version)
            self._data[key] = entry
            return VersionedEntry(
                key=entry.key,
                value=entry.value,
                version=entry.version,
            )

    def delete(self, key: str) -> bool:
        with self._lock:
            if key not in self._data:
                return False
            del self._data[key]
            return True

    def has_key(self, key: str) -> bool:
        with self._lock:
            return key in self._data

    def get_version(self, key: str) -> Optional[int]:
        with self._lock:
            if key not in self._data:
                return None
            return self._data[key].version

    def keys(self) -> List[str]:
        with self._lock:
            return list(self._data.keys())

    def entries(self) -> List[VersionedEntry]:
        with self._lock:
            return [
                VersionedEntry(key=e.key, value=e.value, version=e.version)
                for e in self._data.values()
            ]

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)

    def __contains__(self, key: str) -> bool:
        return self.has_key(key)

    def __iter__(self) -> Iterator[str]:
        return iter(self.keys())

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def merge_entry(self, entry: VersionedEntry) -> bool:
        with self._lock:
            if entry.key in self._data:
                current = self._data[entry.key]
                if entry.version < current.version:
                    return False
                if entry.version == current.version:
                    if entry.value == current.value:
                        return False
            self._data[entry.key] = VersionedEntry(
                key=entry.key,
                value=entry.value,
                version=entry.version,
            )
            return True

    def to_dict(self) -> Dict[str, VersionedEntry]:
        with self._lock:
            return {
                k: VersionedEntry(key=v.key, value=v.value, version=v.version)
                for k, v in self._data.items()
            }
