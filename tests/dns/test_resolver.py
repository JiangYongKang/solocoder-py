from __future__ import annotations

import time

import pytest

from solocoder_py.dns import (
    DNSCache,
    DNSCNAMELoopError,
    DNSCNAMEChainTooLongError,
    DNSRecord,
    DNSRecordType,
    DNSResolutionError,
    DNSResponse,
    DNSTimeoutError,
    StubResolver,
)
from .conftest import make_cache, make_mock_upstream, make_resolver, MockUpstreamResolver


class TestDNSRecordModel:
    def test_record_creation(self):
        record = DNSRecord(
            name="example.com",
            type=DNSRecordType.A,
            value="192.168.1.1",
            ttl=300,
        )
        assert record.name == "example.com"
        assert record.type == DNSRecordType.A
        assert record.value == "192.168.1.1"
        assert record.ttl == 300

    def test_record_name_trailing_dot_stripped(self):
        record = DNSRecord(
            name="example.com.",
            type=DNSRecordType.A,
            value="192.168.1.1",
            ttl=300,
        )
        assert record.name == "example.com"

    def test_record_name_lowercased(self):
        record = DNSRecord(
            name="Example.COM",
            type=DNSRecordType.A,
            value="192.168.1.1",
            ttl=300,
        )
        assert record.name == "example.com"

    def test_record_negative_ttl_rejected(self):
        with pytest.raises(ValueError, match="ttl must be non-negative"):
            DNSRecord(
                name="example.com",
                type=DNSRecordType.A,
                value="192.168.1.1",
                ttl=-1,
            )

    def test_record_empty_name_rejected(self):
        with pytest.raises(ValueError, match="name cannot be empty"):
            DNSRecord(
                name="",
                type=DNSRecordType.A,
                value="192.168.1.1",
                ttl=300,
            )

    def test_record_empty_value_rejected(self):
        with pytest.raises(ValueError, match="value cannot be empty"):
            DNSRecord(
                name="example.com",
                type=DNSRecordType.A,
                value="",
                ttl=300,
            )


class TestDNSResponseModel:
    def test_empty_response(self):
        resp = DNSResponse()
        assert resp.has_records() is False
        assert len(resp.records) == 0

    def test_response_with_records(self):
        records = [
            DNSRecord(name="example.com", type=DNSRecordType.A, value="1.1.1.1", ttl=300),
            DNSRecord(name="example.com", type=DNSRecordType.AAAA, value="::1", ttl=300),
        ]
        resp = DNSResponse(records=records)
        assert resp.has_records() is True
        assert len(resp.records) == 2

    def test_filter_by_type(self):
        records = [
            DNSRecord(name="example.com", type=DNSRecordType.A, value="1.1.1.1", ttl=300),
            DNSRecord(name="example.com", type=DNSRecordType.A, value="2.2.2.2", ttl=300),
            DNSRecord(name="example.com", type=DNSRecordType.AAAA, value="::1", ttl=300),
        ]
        resp = DNSResponse(records=records)
        a_records = resp.filter_by_type(DNSRecordType.A)
        assert len(a_records) == 2
        aaaa_records = resp.filter_by_type(DNSRecordType.AAAA)
        assert len(aaaa_records) == 1
        cname_records = resp.filter_by_type(DNSRecordType.CNAME)
        assert len(cname_records) == 0


class TestDNSCacheBasics:
    def test_put_and_get(self):
        cache = make_cache()
        record = DNSRecord(name="example.com", type=DNSRecordType.A, value="1.1.1.1", ttl=300)
        cache.put(record)

        result = cache.get("example.com", DNSRecordType.A)
        assert result is not None
        assert len(result) == 1
        assert result[0].value == "1.1.1.1"

    def test_get_miss_returns_none(self):
        cache = make_cache()
        result = cache.get("nonexistent.com", DNSRecordType.A)
        assert result is None

    def test_different_record_types_independent(self):
        cache = make_cache()
        a_record = DNSRecord(name="example.com", type=DNSRecordType.A, value="1.1.1.1", ttl=300)
        aaaa_record = DNSRecord(name="example.com", type=DNSRecordType.AAAA, value="::1", ttl=300)
        cache.put(a_record)
        cache.put(aaaa_record)

        a_result = cache.get("example.com", DNSRecordType.A)
        assert a_result is not None and len(a_result) == 1 and a_result[0].value == "1.1.1.1"

        aaaa_result = cache.get("example.com", DNSRecordType.AAAA)
        assert aaaa_result is not None and len(aaaa_result) == 1 and aaaa_result[0].value == "::1"

    def test_ttl_zero_not_cached(self):
        cache = make_cache()
        record = DNSRecord(name="example.com", type=DNSRecordType.A, value="1.1.1.1", ttl=0)
        cache.put(record)

        result = cache.get("example.com", DNSRecordType.A)
        assert result is None

    def test_invalidate_specific_type(self):
        cache = make_cache()
        a_record = DNSRecord(name="example.com", type=DNSRecordType.A, value="1.1.1.1", ttl=300)
        aaaa_record = DNSRecord(name="example.com", type=DNSRecordType.AAAA, value="::1", ttl=300)
        cache.put(a_record)
        cache.put(aaaa_record)

        cache.invalidate("example.com", DNSRecordType.A)

        assert cache.get("example.com", DNSRecordType.A) is None
        assert cache.get("example.com", DNSRecordType.AAAA) is not None

    def test_invalidate_all_types(self):
        cache = make_cache()
        a_record = DNSRecord(name="example.com", type=DNSRecordType.A, value="1.1.1.1", ttl=300)
        aaaa_record = DNSRecord(name="example.com", type=DNSRecordType.AAAA, value="::1", ttl=300)
        cache.put(a_record)
        cache.put(aaaa_record)

        cache.invalidate("example.com")

        assert cache.get("example.com", DNSRecordType.A) is None
        assert cache.get("example.com", DNSRecordType.AAAA) is None

    def test_clear(self):
        cache = make_cache()
        cache.put(DNSRecord(name="a.com", type=DNSRecordType.A, value="1.1.1.1", ttl=300))
        cache.put(DNSRecord(name="b.com", type=DNSRecordType.A, value="2.2.2.2", ttl=300))

        cache.clear()

        assert len(cache) == 0

    def test_put_all(self):
        cache = make_cache()
        records = [
            DNSRecord(name="example.com", type=DNSRecordType.A, value="1.1.1.1", ttl=300),
            DNSRecord(name="example.com", type=DNSRecordType.A, value="2.2.2.2", ttl=300),
        ]
        cache.put_all(records)

        result = cache.get("example.com", DNSRecordType.A)
        assert result is not None
        assert len(result) == 2

    def test_contains(self):
        cache = make_cache()
        cache.put(DNSRecord(name="example.com", type=DNSRecordType.A, value="1.1.1.1", ttl=300))

        assert ("example.com", DNSRecordType.A) in cache
        assert ("example.com", DNSRecordType.AAAA) not in cache
        assert ("other.com", DNSRecordType.A) not in cache


class TestDNSCacheTTL:
    def test_expired_record_not_returned(self):
        cache = make_cache()
        record = DNSRecord(name="example.com", type=DNSRecordType.A, value="1.1.1.1", ttl=1)
        cache.put(record)

        assert cache.get("example.com", DNSRecordType.A) is not None

        time.sleep(1.1)

        result = cache.get("example.com", DNSRecordType.A)
        assert result is None

    def test_ttl_boundary_exactly_expired(self):
        cache = make_cache()
        cache.put(DNSRecord(name="example.com", type=DNSRecordType.A, value="1.1.1.1", ttl=300))

        from solocoder_py.dns import CacheEntry as _CE
        from solocoder_py.dns.models import CacheEntry

        import time as _time
        key = ("example.com", DNSRecordType.A)
        with cache._lock:
            entries = cache._store.get(key)
            if entries:
                entries[0].expires_at = _time.monotonic()

        result = cache.get("example.com", DNSRecordType.A)
        assert result is None

    def test_ttl_not_yet_expired(self):
        cache = make_cache()
        cache.put(DNSRecord(name="example.com", type=DNSRecordType.A, value="1.1.1.1", ttl=300))

        import time as _time
        key = ("example.com", DNSRecordType.A)
        with cache._lock:
            entries = cache._store.get(key)
            if entries:
                entries[0].expires_at = _time.monotonic() + 10

        result = cache.get("example.com", DNSRecordType.A)
        assert result is not None

    def test_purge_expired(self):
        cache = make_cache()
        cache.put(DNSRecord(name="a.com", type=DNSRecordType.A, value="1.1.1.1", ttl=1))
        cache.put(DNSRecord(name="b.com", type=DNSRecordType.A, value="2.2.2.2", ttl=300))

        time.sleep(1.1)

        purged = cache.purge_expired()
        assert purged >= 1
        assert cache.get("a.com", DNSRecordType.A) is None
        assert cache.get("b.com", DNSRecordType.A) is not None


class TestStubResolverNormalFlow:
    def test_first_resolve_uses_upstream_and_caches(self):
        upstream = make_mock_upstream()
        upstream.add_records([
            DNSRecord(name="example.com", type=DNSRecordType.A, value="1.2.3.4", ttl=300),
        ])
        resolver = make_resolver(upstream=upstream)

        assert upstream.call_count == 0

        response = resolver.resolve("example.com", DNSRecordType.A)

        assert upstream.call_count == 1
        assert response.has_records()
        a_records = response.filter_by_type(DNSRecordType.A)
        assert len(a_records) == 1
        assert a_records[0].value == "1.2.3.4"

    def test_second_resolve_hits_cache_no_upstream_call(self):
        upstream = make_mock_upstream()
        upstream.add_records([
            DNSRecord(name="example.com", type=DNSRecordType.A, value="1.2.3.4", ttl=300),
        ])
        resolver = make_resolver(upstream=upstream)

        resolver.resolve("example.com", DNSRecordType.A)
        assert upstream.call_count == 1

        upstream.reset_call_count()

        response = resolver.resolve("example.com", DNSRecordType.A)

        assert upstream.call_count == 0
        assert response.has_records()
        assert response.filter_by_type(DNSRecordType.A)[0].value == "1.2.3.4"

    def test_cname_chain_followed(self):
        upstream = make_mock_upstream()
        upstream.add_records([
            DNSRecord(name="www.example.com", type=DNSRecordType.CNAME, value="example.com", ttl=300),
            DNSRecord(name="example.com", type=DNSRecordType.A, value="1.2.3.4", ttl=300),
        ])
        resolver = make_resolver(upstream=upstream)

        response = resolver.resolve("www.example.com", DNSRecordType.A)

        assert response.has_records()
        a_records = response.filter_by_type(DNSRecordType.A)
        assert len(a_records) == 1
        assert a_records[0].value == "1.2.3.4"
        cname_records = response.filter_by_type(DNSRecordType.CNAME)
        assert len(cname_records) == 1
        assert cname_records[0].value == "example.com"
        assert upstream.call_count == 2

    def test_multi_level_cname_calls_upstream_for_each_level(self):
        upstream = make_mock_upstream()
        upstream.add_records([
            DNSRecord(name="a.example.com", type=DNSRecordType.CNAME, value="b.example.com", ttl=300),
            DNSRecord(name="b.example.com", type=DNSRecordType.CNAME, value="c.example.com", ttl=300),
            DNSRecord(name="c.example.com", type=DNSRecordType.CNAME, value="final.example.com", ttl=300),
            DNSRecord(name="final.example.com", type=DNSRecordType.A, value="5.6.7.8", ttl=300),
        ])
        resolver = make_resolver(upstream=upstream)

        response = resolver.resolve("a.example.com", DNSRecordType.A)

        assert response.has_records()
        assert upstream.call_count == 4

        a_records = response.filter_by_type(DNSRecordType.A)
        assert len(a_records) == 1
        assert a_records[0].value == "5.6.7.8"
        cname_records = response.filter_by_type(DNSRecordType.CNAME)
        assert len(cname_records) == 3

        upstream.reset_call_count()

        response2 = resolver.resolve("a.example.com", DNSRecordType.A)
        assert upstream.call_count == 0
        assert response2.has_records()

    def test_intermediate_cname_expired_requires_re_resolve(self):
        upstream = make_mock_upstream()
        upstream.add_records([
            DNSRecord(name="a.example.com", type=DNSRecordType.CNAME, value="b.example.com", ttl=1),
            DNSRecord(name="b.example.com", type=DNSRecordType.CNAME, value="final.example.com", ttl=300),
            DNSRecord(name="final.example.com", type=DNSRecordType.A, value="5.6.7.8", ttl=300),
        ])
        resolver = make_resolver(upstream=upstream)

        response = resolver.resolve("a.example.com", DNSRecordType.A)
        assert response.has_records()
        assert upstream.call_count == 3

        time.sleep(1.1)

        upstream.reset_call_count()

        response2 = resolver.resolve("a.example.com", DNSRecordType.A)
        assert response2.has_records()
        assert upstream.call_count == 1

        a_records = response2.filter_by_type(DNSRecordType.A)
        assert len(a_records) == 1
        assert a_records[0].value == "5.6.7.8"

    def test_final_cname_target_expired_requires_re_resolve(self):
        upstream = make_mock_upstream()
        upstream.add_records([
            DNSRecord(name="www.example.com", type=DNSRecordType.CNAME, value="example.com", ttl=300),
            DNSRecord(name="example.com", type=DNSRecordType.A, value="1.2.3.4", ttl=1),
        ])
        resolver = make_resolver(upstream=upstream)

        response = resolver.resolve("www.example.com", DNSRecordType.A)
        assert response.has_records()
        assert upstream.call_count == 2

        time.sleep(1.1)

        upstream.reset_call_count()

        response2 = resolver.resolve("www.example.com", DNSRecordType.A)
        assert response2.has_records()
        assert upstream.call_count == 1

        a_records = response2.filter_by_type(DNSRecordType.A)
        assert len(a_records) == 1
        assert a_records[0].value == "1.2.3.4"

    def test_each_cname_level_cached_independently(self):
        upstream = make_mock_upstream()
        upstream.add_records([
            DNSRecord(name="x.example.com", type=DNSRecordType.CNAME, value="y.example.com", ttl=300),
            DNSRecord(name="y.example.com", type=DNSRecordType.CNAME, value="z.example.com", ttl=300),
            DNSRecord(name="z.example.com", type=DNSRecordType.A, value="9.9.9.9", ttl=300),
        ])
        resolver = make_resolver(upstream=upstream)

        resolver.resolve("x.example.com", DNSRecordType.A)
        assert upstream.call_count == 3

        upstream.reset_call_count()
        resolver.resolve("y.example.com", DNSRecordType.A)
        assert upstream.call_count == 0

        upstream.reset_call_count()
        resolver.resolve("z.example.com", DNSRecordType.A)
        assert upstream.call_count == 0

    def test_cache_expired_re_resolve(self):
        upstream = make_mock_upstream()
        upstream.add_records([
            DNSRecord(name="example.com", type=DNSRecordType.A, value="1.2.3.4", ttl=1),
        ])
        resolver = make_resolver(upstream=upstream)

        resolver.resolve("example.com", DNSRecordType.A)
        assert upstream.call_count == 1

        time.sleep(1.1)
        upstream.reset_call_count()

        response = resolver.resolve("example.com", DNSRecordType.A)

        assert upstream.call_count == 1
        assert response.has_records()


class TestStubResolverBoundaryConditions:
    def test_ttl_boundary_hit(self):
        upstream = make_mock_upstream()
        upstream.add_records([
            DNSRecord(name="example.com", type=DNSRecordType.A, value="1.2.3.4", ttl=300),
        ])
        resolver = make_resolver(upstream=upstream)

        resolver.resolve("example.com", DNSRecordType.A)
        assert upstream.call_count == 1

        import time as _time
        key = ("example.com", DNSRecordType.A)
        with resolver.cache._lock:
            entries = resolver.cache._store.get(key)
            if entries:
                entries[0].expires_at = _time.monotonic() + 0.01

        time.sleep(0.02)
        upstream.reset_call_count()

        resolver.resolve("example.com", DNSRecordType.A)
        assert upstream.call_count == 1

    def test_empty_cache_upstream_returns_empty(self):
        upstream = make_mock_upstream()
        resolver = make_resolver(upstream=upstream)

        response = resolver.resolve("nonexistent.com", DNSRecordType.A)

        assert upstream.call_count == 1
        assert not response.has_records()
        assert len(response.records) == 0

    def test_multi_level_cname_chain(self):
        upstream = make_mock_upstream()
        upstream.add_records([
            DNSRecord(name="a.example.com", type=DNSRecordType.CNAME, value="b.example.com", ttl=300),
            DNSRecord(name="b.example.com", type=DNSRecordType.CNAME, value="c.example.com", ttl=300),
            DNSRecord(name="c.example.com", type=DNSRecordType.CNAME, value="final.example.com", ttl=300),
            DNSRecord(name="final.example.com", type=DNSRecordType.A, value="5.6.7.8", ttl=300),
        ])
        resolver = make_resolver(upstream=upstream)

        response = resolver.resolve("a.example.com", DNSRecordType.A)

        assert response.has_records()
        a_records = response.filter_by_type(DNSRecordType.A)
        assert len(a_records) == 1
        assert a_records[0].value == "5.6.7.8"
        cname_records = response.filter_by_type(DNSRecordType.CNAME)
        assert len(cname_records) == 3

    def test_resolve_a_and_aaaa_helpers(self):
        upstream = make_mock_upstream()
        upstream.add_records([
            DNSRecord(name="example.com", type=DNSRecordType.A, value="1.2.3.4", ttl=300),
            DNSRecord(name="example.com", type=DNSRecordType.AAAA, value="::1", ttl=300),
        ])
        resolver = make_resolver(upstream=upstream)

        a_resp = resolver.resolve_a("example.com")
        assert a_resp.filter_by_type(DNSRecordType.A)[0].value == "1.2.3.4"

        aaaa_resp = resolver.resolve_aaaa("example.com")
        assert aaaa_resp.filter_by_type(DNSRecordType.AAAA)[0].value == "::1"


class TestStubResolverExceptionCases:
    def test_cname_loop_detected(self):
        upstream = make_mock_upstream()
        upstream.add_records([
            DNSRecord(name="a.example.com", type=DNSRecordType.CNAME, value="b.example.com", ttl=300),
            DNSRecord(name="b.example.com", type=DNSRecordType.CNAME, value="a.example.com", ttl=300),
        ])
        resolver = make_resolver(upstream=upstream)

        with pytest.raises(DNSCNAMELoopError) as exc_info:
            resolver.resolve("a.example.com", DNSRecordType.A)

        assert "CNAME loop detected" in str(exc_info.value)
        assert len(exc_info.value.chain) >= 2

    def test_cname_chain_exceeds_max_depth(self):
        upstream = make_mock_upstream()
        resolver = make_resolver(upstream=upstream, max_cname_chain_depth=3)

        for i in range(10):
            upstream.add_records([
                DNSRecord(
                    name=f"level{i}.example.com",
                    type=DNSRecordType.CNAME,
                    value=f"level{i + 1}.example.com",
                    ttl=300,
                ),
            ])
        upstream.add_records([
            DNSRecord(name="level10.example.com", type=DNSRecordType.A, value="9.9.9.9", ttl=300),
        ])

        with pytest.raises(DNSCNAMEChainTooLongError) as exc_info:
            resolver.resolve("level0.example.com", DNSRecordType.A)

        assert "exceeded maximum depth" in str(exc_info.value)
        assert exc_info.value.max_depth == 3
        assert len(exc_info.value.chain) == 3

    def test_loop_and_chain_too_long_are_different_exceptions(self):
        assert issubclass(DNSCNAMELoopError, DNSResolutionError)
        assert issubclass(DNSCNAMEChainTooLongError, DNSResolutionError)
        assert DNSCNAMELoopError is not DNSCNAMEChainTooLongError

    def test_upstream_timeout(self):
        upstream = make_mock_upstream()
        upstream.set_should_timeout(True)
        resolver = make_resolver(upstream=upstream)

        with pytest.raises(DNSTimeoutError):
            resolver.resolve("example.com", DNSRecordType.A)

    def test_upstream_error(self):
        upstream = make_mock_upstream()
        upstream.set_should_error(True, "Custom upstream error")
        resolver = make_resolver(upstream=upstream)

        with pytest.raises(DNSResolutionError, match="Custom upstream error"):
            resolver.resolve("example.com", DNSRecordType.A)

    def test_upstream_generic_exception_wrapped(self):
        class BadUpstream:
            def resolve(self, name, record_type):
                raise RuntimeError("Something went very wrong")

        resolver = StubResolver(upstream=BadUpstream())

        with pytest.raises(DNSResolutionError, match="Upstream resolver failed"):
            resolver.resolve("example.com", DNSRecordType.A)

    def test_different_record_types_same_name_no_interference(self):
        upstream = make_mock_upstream()
        upstream.add_records([
            DNSRecord(name="example.com", type=DNSRecordType.A, value="1.2.3.4", ttl=300),
            DNSRecord(name="example.com", type=DNSRecordType.AAAA, value="::1", ttl=300),
        ])
        resolver = make_resolver(upstream=upstream)

        a_resp = resolver.resolve_a("example.com")
        assert len(a_resp.filter_by_type(DNSRecordType.A)) == 1
        assert len(a_resp.filter_by_type(DNSRecordType.AAAA)) == 0
        assert upstream.call_count == 1

        upstream.reset_call_count()

        aaaa_resp = resolver.resolve_aaaa("example.com")
        assert upstream.call_count == 1
        assert len(aaaa_resp.filter_by_type(DNSRecordType.AAAA)) == 1
        assert len(aaaa_resp.filter_by_type(DNSRecordType.A)) == 0

        upstream.reset_call_count()
        resolver.resolve_a("example.com")
        assert upstream.call_count == 0

        upstream.reset_call_count()
        resolver.resolve_aaaa("example.com")
        assert upstream.call_count == 0

    def test_ttl_zero_records_not_cached(self):
        upstream = make_mock_upstream()
        upstream.add_records([
            DNSRecord(name="example.com", type=DNSRecordType.A, value="1.2.3.4", ttl=0),
        ])
        resolver = make_resolver(upstream=upstream)

        resolver.resolve("example.com", DNSRecordType.A)
        assert upstream.call_count == 1

        upstream.reset_call_count()

        resolver.resolve("example.com", DNSRecordType.A)
        assert upstream.call_count == 1

    def test_resolver_requires_upstream(self):
        with pytest.raises(ValueError, match="upstream resolver cannot be None"):
            StubResolver(upstream=None)

    def test_resolver_requires_positive_max_depth(self):
        upstream = make_mock_upstream()
        with pytest.raises(ValueError, match="max_cname_chain_depth must be positive"):
            StubResolver(upstream=upstream, max_cname_chain_depth=0)
        with pytest.raises(ValueError, match="max_cname_chain_depth must be positive"):
            StubResolver(upstream=upstream, max_cname_chain_depth=-1)

    def test_clear_cache(self):
        upstream = make_mock_upstream()
        upstream.add_records([
            DNSRecord(name="example.com", type=DNSRecordType.A, value="1.2.3.4", ttl=300),
        ])
        resolver = make_resolver(upstream=upstream)

        resolver.resolve("example.com", DNSRecordType.A)
        assert len(resolver.cache) > 0

        resolver.clear_cache()
        assert len(resolver.cache) == 0

        upstream.reset_call_count()
        resolver.resolve("example.com", DNSRecordType.A)
        assert upstream.call_count == 1

    def test_self_referential_cname(self):
        upstream = make_mock_upstream()
        upstream.add_records([
            DNSRecord(name="loop.example.com", type=DNSRecordType.CNAME, value="loop.example.com", ttl=300),
        ])
        resolver = make_resolver(upstream=upstream)

        with pytest.raises(DNSCNAMELoopError) as exc_info:
            resolver.resolve("loop.example.com", DNSRecordType.A)

        assert "CNAME loop detected" in str(exc_info.value)


class TestCacheEntryModel:
    def test_cache_entry_not_expired(self):
        from solocoder_py.dns import CacheEntry
        record = DNSRecord(name="example.com", type=DNSRecordType.A, value="1.1.1.1", ttl=300)
        entry = CacheEntry(record=record, expires_at=time.monotonic() + 100)
        assert entry.is_expired is False
        assert entry.remaining_ttl > 0

    def test_cache_entry_expired(self):
        from solocoder_py.dns import CacheEntry
        record = DNSRecord(name="example.com", type=DNSRecordType.A, value="1.1.1.1", ttl=300)
        entry = CacheEntry(record=record, expires_at=time.monotonic() - 100)
        assert entry.is_expired is True
        assert entry.remaining_ttl == 0

    def test_cache_entry_remaining_ttl_non_negative(self):
        from solocoder_py.dns import CacheEntry
        record = DNSRecord(name="example.com", type=DNSRecordType.A, value="1.1.1.1", ttl=300)
        entry = CacheEntry(record=record, expires_at=time.monotonic() - 999)
        assert entry.remaining_ttl >= 0
