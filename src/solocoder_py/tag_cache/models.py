from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Set


@dataclass
class CacheEntry:
    key: Any
    value: Any
    tags: Set[Any] = field(default_factory=set)
    expire_at: Optional[float] = None

    def is_expired(self, now: float) -> bool:
        return self.expire_at is not None and self.expire_at <= now

    def has_tag(self, tag: Any) -> bool:
        return tag in self.tags

    def add_tag(self, tag: Any) -> bool:
        if tag in self.tags:
            return False
        self.tags.add(tag)
        return True

    def remove_tag(self, tag: Any) -> bool:
        if tag not in self.tags:
            return False
        self.tags.discard(tag)
        return True


@dataclass(frozen=True)
class TagCacheStats:
    entry_count: int = 0
    tag_count: int = 0
    dangling_tag_count: int = 0
