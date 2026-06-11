from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .models import TargetConnection


class InMemoryDnsResolver:
    def __init__(self) -> None:
        self._records: Dict[str, str] = {}

    def add_record(self, domain: str, ip: str) -> None:
        self._records[domain] = ip

    def resolve(self, domain: str) -> Optional[str]:
        return self._records.get(domain)


class InMemoryNetwork:
    def __init__(self) -> None:
        self._targets: Dict[Tuple[str, int], TargetConnection] = {}

    def register_target(self, host: str, port: int) -> TargetConnection:
        key = (host, port)
        conn = TargetConnection(host=host, port=port)
        self._targets[key] = conn
        return conn

    def connect(self, host: str, port: int) -> Optional[TargetConnection]:
        return self._targets.get((host, port))

    def is_target_available(self, host: str, port: int) -> bool:
        return (host, port) in self._targets
