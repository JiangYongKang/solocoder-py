from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Set

from .cache import DNSCache
from .exceptions import (
    DNSCNAMELoopError,
    DNSResolutionError,
    DNSTimeoutError,
)
from .models import DNSRecord, DNSRecordType, DNSResponse


_MAX_CNAME_CHAIN_DEPTH = 16


class UpstreamResolver(ABC):
    @abstractmethod
    def resolve(self, name: str, record_type: DNSRecordType) -> DNSResponse:
        ...


class StubResolver:
    def __init__(
        self,
        upstream: UpstreamResolver,
        cache: Optional[DNSCache] = None,
        max_cname_chain_depth: int = _MAX_CNAME_CHAIN_DEPTH,
    ) -> None:
        if upstream is None:
            raise ValueError("upstream resolver cannot be None")
        if max_cname_chain_depth <= 0:
            raise ValueError("max_cname_chain_depth must be positive")

        self._upstream = upstream
        self._cache = cache if cache is not None else DNSCache()
        self._max_cname_chain_depth = max_cname_chain_depth

    @property
    def cache(self) -> DNSCache:
        return self._cache

    def resolve(
        self, name: str, record_type: DNSRecordType
    ) -> DNSResponse:
        normalized_name = name.rstrip(".").lower()
        visited: Set[str] = set()
        chain: List[str] = []
        all_records: List[DNSRecord] = []

        current_name = normalized_name

        for _ in range(self._max_cname_chain_depth):
            if current_name in visited:
                raise DNSCNAMELoopError(
                    f"CNAME loop detected: {' -> '.join(chain + [current_name])}",
                    chain=chain + [current_name],
                )
            visited.add(current_name)
            chain.append(current_name)

            final_records = self._cache.get(current_name, record_type)
            if final_records:
                all_records.extend(final_records)
                return DNSResponse(records=all_records)

            cname_records = self._cache.get(current_name, DNSRecordType.CNAME)
            if cname_records:
                all_records.extend(cname_records)
                current_name = cname_records[0].value.rstrip(".").lower()
                continue

            try:
                upstream_response = self._upstream.resolve(current_name, record_type)
            except DNSTimeoutError:
                raise
            except DNSResolutionError:
                raise
            except Exception as e:
                raise DNSResolutionError(f"Upstream resolver failed: {e}") from e

            upstream_records = upstream_response.records

            if not upstream_records:
                if len(chain) == 1:
                    return DNSResponse(records=[])
                break

            self._cache.put_all(upstream_records)
            all_records.extend(upstream_records)

            upstream_final = [r for r in upstream_records if r.type == record_type]
            if upstream_final:
                return DNSResponse(records=all_records)

            upstream_cname = [r for r in upstream_records if r.type == DNSRecordType.CNAME]
            if upstream_cname:
                current_name = upstream_cname[0].value.rstrip(".").lower()
                continue

            break
        else:
            raise DNSCNAMELoopError(
                f"CNAME chain exceeded maximum depth of {self._max_cname_chain_depth}",
                chain=chain,
            )

        return DNSResponse(records=all_records)

    def resolve_a(self, name: str) -> DNSResponse:
        return self.resolve(name, DNSRecordType.A)

    def resolve_aaaa(self, name: str) -> DNSResponse:
        return self.resolve(name, DNSRecordType.AAAA)

    def clear_cache(self) -> None:
        self._cache.clear()
