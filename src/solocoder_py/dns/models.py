from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class DNSRecordType(str, Enum):
    A = "A"
    AAAA = "AAAA"
    CNAME = "CNAME"


@dataclass
class DNSRecord:
    name: str
    type: DNSRecordType
    value: str
    ttl: int

    def __post_init__(self) -> None:
        if self.ttl < 0:
            raise ValueError("ttl must be non-negative")
        if not self.name:
            raise ValueError("name cannot be empty")
        if not self.value:
            raise ValueError("value cannot be empty")
        self.name = self.name.rstrip(".").lower()


@dataclass
class DNSResponse:
    records: List[DNSRecord] = field(default_factory=list)

    def filter_by_type(self, record_type: DNSRecordType) -> List[DNSRecord]:
        return [r for r in self.records if r.type == record_type]

    def has_records(self) -> bool:
        return len(self.records) > 0


@dataclass
class CacheEntry:
    record: DNSRecord
    expires_at: float

    @property
    def is_expired(self) -> bool:
        import time

        return time.monotonic() >= self.expires_at

    @property
    def remaining_ttl(self) -> int:
        import time

        remaining = self.expires_at - time.monotonic()
        return max(0, int(remaining))
