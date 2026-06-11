from typing import Dict, List, Tuple

from solocoder_py.dns import (
    DNSCache,
    DNSRecord,
    DNSRecordType,
    DNSResponse,
    StubResolver,
    UpstreamResolver,
)


class MockUpstreamResolver(UpstreamResolver):
    def __init__(self) -> None:
        self._records: Dict[Tuple[str, DNSRecordType], List[DNSRecord]] = {}
        self._call_count = 0
        self._should_timeout = False
        self._should_error = False
        self._error_message = "Upstream error"

    def add_records(self, records: List[DNSRecord]) -> None:
        for record in records:
            key = (record.name, record.type)
            if key not in self._records:
                self._records[key] = []
            self._records[key].append(record)

    def set_should_timeout(self, value: bool) -> None:
        self._should_timeout = value

    def set_should_error(self, value: bool, message: str = "Upstream error") -> None:
        self._should_error = value
        self._error_message = message

    @property
    def call_count(self) -> int:
        return self._call_count

    def reset_call_count(self) -> None:
        self._call_count = 0

    def resolve(self, name: str, record_type: DNSRecordType) -> DNSResponse:
        from solocoder_py.dns import DNSTimeoutError, DNSResolutionError

        self._call_count += 1

        if self._should_timeout:
            raise DNSTimeoutError("Upstream resolver timed out")

        if self._should_error:
            raise DNSResolutionError(self._error_message)

        normalized_name = name.rstrip(".").lower()
        key = (normalized_name, record_type)
        records = self._records.get(key, [])

        if not records and record_type in (DNSRecordType.A, DNSRecordType.AAAA):
            cname_key = (normalized_name, DNSRecordType.CNAME)
            cname_records = self._records.get(cname_key, [])
            if cname_records:
                all_records = list(cname_records)
                target_name = cname_records[0].value.rstrip(".").lower()
                target_key = (target_name, record_type)
                target_records = self._records.get(target_key, [])
                while target_records:
                    all_records.extend(target_records)
                    target_cname_key = (target_name, DNSRecordType.CNAME)
                    target_cname = self._records.get(target_cname_key, [])
                    if not target_cname:
                        break
                    all_records.extend(target_cname)
                    target_name = target_cname[0].value.rstrip(".").lower()
                    target_key = (target_name, record_type)
                    target_records = self._records.get(target_key, [])
                return DNSResponse(records=all_records)

        return DNSResponse(records=list(records))


def make_cache() -> DNSCache:
    return DNSCache()


def make_mock_upstream() -> MockUpstreamResolver:
    return MockUpstreamResolver()


def make_resolver(
    upstream: MockUpstreamResolver | None = None,
    cache: DNSCache | None = None,
    max_cname_chain_depth: int = 16,
) -> StubResolver:
    if upstream is None:
        upstream = make_mock_upstream()
    return StubResolver(
        upstream=upstream,
        cache=cache,
        max_cname_chain_depth=max_cname_chain_depth,
    )
