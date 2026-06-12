from __future__ import annotations

import time
from dataclasses import replace

import pytest

from solocoder_py.auditlog import (
    AuditLogEntry,
    AuditLogStore,
    AuditLogValidator,
    ChainState,
    EmptyAuditLogError,
    InvalidIndexError,
    TimestampRegressionError,
    VerificationReport,
    compute_hash,
)
from solocoder_py.seat.clock import ManualClock


class TestHashChain:
    def test_genesis_entry_hash_contains_only_itself(self, store):
        entry = store.append(
            event_type="CREATE",
            subject="admin",
            target="user:alice",
            details={"role": "user"},
        )

        assert entry.index == 0
        assert entry.previous_hash == ""

        expected_content = AuditLogEntry(
            index=0,
            event_type="CREATE",
            subject="admin",
            target="user:alice",
            timestamp=entry.timestamp,
            details={"role": "user"},
            previous_hash="",
        )
        expected_hash = expected_content.compute_hash()
        assert entry.hash == expected_hash
        assert store.genesis_hash == expected_hash
        assert store.chain_tip_hash == expected_hash

    def test_subsequent_entry_links_to_previous_hash(self, store, manual_clock):
        entry1 = store.append(
            event_type="CREATE", subject="admin", target="user:alice"
        )
        manual_clock.advance(10)
        entry2 = store.append(
            event_type="UPDATE", subject="admin", target="user:alice"
        )

        assert entry2.previous_hash == entry1.hash
        assert entry2.hash != entry1.hash

        expected_content = AuditLogEntry(
            index=1,
            event_type="UPDATE",
            subject="admin",
            target="user:alice",
            timestamp=entry2.timestamp,
            details=None,
            previous_hash=entry1.hash,
        )
        expected_hash = expected_content.compute_hash()
        assert entry2.hash == expected_hash
        assert store.chain_tip_hash == expected_hash

    def test_chain_formation_multiple_entries(self, store, manual_clock):
        entries = []
        for i in range(5):
            manual_clock.advance(5)
            entry = store.append(
                event_type=f"EVENT_{i}",
                subject=f"user_{i}",
                target=f"resource_{i}",
            )
            entries.append(entry)

        for i in range(1, len(entries)):
            assert entries[i].previous_hash == entries[i - 1].hash
            assert entries[i].index == i

        for i, entry in enumerate(entries):
            prev_hash = entries[i - 1].hash if i > 0 else ""
            expected = AuditLogEntry(
                index=i,
                event_type=f"EVENT_{i}",
                subject=f"user_{i}",
                target=f"resource_{i}",
                timestamp=entry.timestamp,
                details=None,
                previous_hash=prev_hash,
            )
            assert entry.hash == expected.compute_hash()

        state = store.get_chain_state()
        assert state.length == 5
        assert state.genesis_hash == entries[0].hash
        assert state.chain_tip_hash == entries[-1].hash
        assert state.hashes == [e.hash for e in entries]

    def test_modifying_entry_breaks_chain(self, store, manual_clock):
        store.append(event_type="CREATE", subject="admin", target="user:alice")
        manual_clock.advance(10)
        store.append(event_type="UPDATE", subject="admin", target="user:alice")
        manual_clock.advance(10)
        store.append(event_type="DELETE", subject="admin", target="user:alice")

        entries = store.get_all_entries()
        original_computed_hash = entries[1].compute_hash()
        original_stored_hash = entries[1].hash
        assert original_computed_hash == original_stored_hash

        tampered = replace(entries[1], event_type="MODIFIED")
        tampered_computed_hash = tampered.compute_hash()
        store._unsafe_replace_entry(1, tampered)

        assert tampered_computed_hash != original_stored_hash
        assert tampered.hash == original_stored_hash

        assert store.verify() is False


class TestTimestampOrder:
    def test_timestamp_equals_previous_allowed(self, store, manual_clock):
        t = manual_clock.now()
        entry1 = store.append(
            event_type="EVENT1",
            subject="user",
            target="res",
            timestamp=t,
        )
        entry2 = store.append(
            event_type="EVENT2",
            subject="user",
            target="res",
            timestamp=t,
        )

        assert entry1.timestamp == entry2.timestamp
        assert entry2.index == 1

    def test_timestamp_earlier_than_previous_rejected(self, store, manual_clock):
        t1 = manual_clock.now()
        store.append(event_type="EVENT1", subject="user", target="res", timestamp=t1)

        t2 = t1 - 100
        with pytest.raises(TimestampRegressionError) as exc:
            store.append(
                event_type="EVENT2", subject="user", target="res", timestamp=t2
            )

        assert exc.value.new_timestamp == t2
        assert exc.value.last_timestamp == t1

    def test_timestamp_increasing_allowed(self, store, manual_clock):
        t = manual_clock.now()
        for i in range(10):
            entry = store.append(
                event_type=f"EVENT_{i}",
                subject="user",
                target="res",
                timestamp=t + i * 10,
            )
            assert entry.timestamp == t + i * 10
            assert entry.index == i

    def test_clock_based_timestamp_auto_increments(self, store, manual_clock):
        entry1 = store.append(event_type="EVENT1", subject="user", target="res")
        manual_clock.advance(60)
        entry2 = store.append(event_type="EVENT2", subject="user", target="res")

        assert entry2.timestamp > entry1.timestamp

    def test_explicit_timestamp_takes_precedence(self, store, manual_clock):
        t = 1_800_000_000.0
        entry = store.append(
            event_type="EVENT",
            subject="user",
            target="res",
            timestamp=t,
        )
        assert entry.timestamp == t


class TestIntegrityVerification:
    def test_empty_chain_verification(self, validator):
        report = validator.verify_chain([])
        assert report.is_valid is True
        assert report.total_entries == 0
        assert report.first_tampered_index is None
        assert "nothing to verify" in report.summary().lower()

    def test_single_entry_verification(self, store, validator):
        store.append(event_type="CREATE", subject="admin", target="user:alice")
        entries = store.get_all_entries()

        report = validator.verify_chain(entries)
        assert report.is_valid is True
        assert report.total_entries == 1
        assert report.tampered_indices == []
        assert report.passed_ranges == [(0, 0)]
        assert report.failed_ranges == []
        assert "1 entries verified" in report.summary()

    def test_full_chain_all_valid(self, store, validator, manual_clock):
        for i in range(5):
            manual_clock.advance(5)
            store.append(
                event_type=f"EVENT_{i}",
                subject=f"user_{i}",
                target=f"resource_{i}",
            )

        entries = store.get_all_entries()
        report = validator.verify_chain(entries)

        assert report.is_valid is True
        assert report.total_entries == 5
        assert report.tampered_indices == []
        assert report.passed_ranges == [(0, 4)]
        assert report.failed_ranges == []
        assert "5 entries verified successfully" in report.summary()

    def test_range_verification_middle(self, store, validator, manual_clock):
        for i in range(10):
            manual_clock.advance(5)
            store.append(
                event_type=f"EVENT_{i}",
                subject=f"user_{i}",
                target=f"resource_{i}",
            )

        entries = store.get_all_entries()
        report = validator.verify_chain(entries, start=3, end=7)

        assert report.is_valid is True
        assert report.total_entries == 4
        assert report.passed_ranges == [(3, 6)]

    def test_tamper_middle_entry_detected(self, store, validator, manual_clock):
        for i in range(5):
            manual_clock.advance(5)
            store.append(
                event_type=f"EVENT_{i}",
                subject=f"user_{i}",
                target=f"resource_{i}",
            )

        entries = store.get_all_entries()
        tampered = replace(entries[2], event_type="TAMPERED")
        store._unsafe_replace_entry(2, tampered)

        entries = store.get_all_entries()
        state = store.get_chain_state()
        report = validator.verify_chain(entries, anchor_hashes=state.hashes)

        assert report.is_valid is False
        assert report.first_tampered_index == 2
        assert 2 in report.tampered_indices
        assert 3 in report.tampered_indices
        assert 4 in report.tampered_indices
        assert report.passed_ranges == [(0, 1)]
        assert report.failed_ranges == [(2, 4)]
        assert "First tampered at index 2" in report.summary()
        assert store.verify() is False

    def test_tamper_genesis_entry_detected(self, store, validator, manual_clock):
        for i in range(3):
            manual_clock.advance(5)
            store.append(
                event_type=f"EVENT_{i}",
                subject=f"user_{i}",
                target=f"resource_{i}",
            )

        entries = store.get_all_entries()
        tampered = replace(entries[0], event_type="TAMPERED_GENESIS")
        store._unsafe_replace_entry(0, tampered)

        entries = store.get_all_entries()
        state = store.get_chain_state()
        report = validator.verify_chain(entries, anchor_hashes=state.hashes)

        assert report.is_valid is False
        assert report.first_tampered_index == 0
        assert report.tampered_indices == [0, 1, 2]
        assert report.passed_ranges == []
        assert report.failed_ranges == [(0, 2)]
        assert store.verify() is False

    def test_multiple_tampered_entries_detected(self, store, validator, manual_clock):
        for i in range(6):
            manual_clock.advance(5)
            store.append(
                event_type=f"EVENT_{i}",
                subject=f"user_{i}",
                target=f"resource_{i}",
            )

        entries = store.get_all_entries()

        tampered1 = replace(entries[1], event_type="TAMPERED_1")
        store._unsafe_replace_entry(1, tampered1)

        tampered4 = replace(entries[4], event_type="TAMPERED_4")
        store._unsafe_replace_entry(4, tampered4)

        entries = store.get_all_entries()
        state = store.get_chain_state()
        report = validator.verify_chain(entries, anchor_hashes=state.hashes)

        assert report.is_valid is False
        assert report.first_tampered_index == 1
        assert report.tampered_indices == [1, 2, 3, 4, 5]
        assert store.verify() is False

    def test_cover_up_tampering_by_recomputing_hashes_detected_with_anchor(
        self, store, validator, manual_clock
    ):
        for i in range(5):
            manual_clock.advance(5)
            store.append(
                event_type=f"EVENT_{i}",
                subject=f"user_{i}",
                target=f"resource_{i}",
            )

        entries = store.get_all_entries()
        tampered_index = 2
        tampered_content = replace(entries[tampered_index], event_type="COVER_UP")
        new_hash = tampered_content.compute_hash()
        tampered_entry = replace(tampered_content, hash=new_hash)
        store._unsafe_replace_entry(tampered_index, tampered_entry)

        for i in range(tampered_index + 1, len(entries)):
            prev_entry = store.get_entry(i - 1)
            modified = replace(entries[i], previous_hash=prev_entry.hash)
            new_hash = modified.compute_hash()
            store._unsafe_replace_entry(i, replace(modified, hash=new_hash))

        entries = store.get_all_entries()
        report_without_anchor = validator.verify_chain(entries, start=2, end=5)
        assert report_without_anchor.is_valid is True

        state = store.get_chain_state()
        report_with_anchor = validator.verify_chain(
            entries, anchor_hashes=state.hashes
        )
        assert report_with_anchor.is_valid is False
        assert report_with_anchor.first_tampered_index == 2

        assert store.verify() is False

    def test_store_verify_detects_systemic_overwrite(
        self, store, validator, manual_clock
    ):
        for i in range(5):
            manual_clock.advance(5)
            store.append(
                event_type=f"EVENT_{i}",
                subject=f"user_{i}",
                target=f"resource_{i}",
            )

        assert store.verify() is True

        entries = store.get_all_entries()
        tampered_index = 2
        tampered_content = replace(entries[tampered_index], event_type="COVER_UP")
        new_hash = tampered_content.compute_hash()
        tampered_entry = replace(tampered_content, hash=new_hash)
        store._unsafe_replace_entry(tampered_index, tampered_entry)

        for i in range(tampered_index + 1, len(entries)):
            prev_entry = store.get_entry(i - 1)
            modified = replace(entries[i], previous_hash=prev_entry.hash)
            new_hash = modified.compute_hash()
            store._unsafe_replace_entry(i, replace(modified, hash=new_hash))

        assert store.verify() is False

    def test_verify_single_entry(self, store, validator):
        entry = store.append(event_type="CREATE", subject="admin", target="user:alice")

        result = validator.verify_entry(entry, previous_hash="")
        assert result.valid is True

        result = validator.verify_entry(entry, previous_hash="wrong_hash")
        assert result.valid is False
        assert "Previous hash mismatch" in result.message

        tampered = replace(entry, event_type="MODIFIED")
        result = validator.verify_entry(tampered, previous_hash="")
        assert result.valid is False
        assert "Hash mismatch" in result.message

        state = store.get_chain_state()
        tampered_content = replace(entry, event_type="SYSTEMIC_TAMPER")
        rewritten_hash = tampered_content.compute_hash()
        tampered_rewrite = replace(tampered_content, hash=rewritten_hash)
        result = validator.verify_entry(
            tampered_rewrite, previous_hash="", anchor_hash=state.hashes[0]
        )
        assert result.valid is False
        assert "Systemic overwrite detected" in result.message


class TestInputConsistency:
    def test_entries_index_mismatch_with_start_raises(self, store, validator, manual_clock):
        for i in range(5):
            manual_clock.advance(5)
            store.append(
                event_type=f"EVENT_{i}",
                subject=f"user_{i}",
                target=f"resource_{i}",
            )

        all_entries = store.get_all_entries()
        sliced = all_entries[2:]

        with pytest.raises(InvalidIndexError):
            validator.verify_chain(sliced, start=0)

    def test_entries_index_correct_with_matching_start(self, store, validator, manual_clock):
        for i in range(5):
            manual_clock.advance(5)
            store.append(
                event_type=f"EVENT_{i}",
                subject=f"user_{i}",
                target=f"resource_{i}",
            )

        all_entries = store.get_all_entries()

        report = validator.verify_chain(all_entries, start=2, end=5)
        assert report.is_valid is True
        assert report.total_entries == 3

    def test_negative_start_raises(self, validator):
        entry = AuditLogEntry(
            index=0, event_type="E", subject="s", target="t", timestamp=1.0, hash="h"
        )
        with pytest.raises(InvalidIndexError):
            validator.verify_chain([entry], start=-1)

    def test_end_less_than_start_raises(self, validator):
        entry = AuditLogEntry(
            index=0, event_type="E", subject="s", target="t", timestamp=1.0, hash="h"
        )
        with pytest.raises(InvalidIndexError):
            validator.verify_chain([entry], start=3, end=1)

    def test_end_exceeds_entries_length_raises(self, validator):
        entries = [
            AuditLogEntry(
                index=i, event_type=f"E{i}", subject="s", target="t", timestamp=1.0, hash="h"
            )
            for i in range(3)
        ]
        with pytest.raises(InvalidIndexError):
            validator.verify_chain(entries, end=10)


class TestEdgeCases:
    def test_timestamp_equal_entries(self, store, manual_clock):
        t = manual_clock.now()
        for i in range(3):
            store.append(
                event_type=f"EVENT_{i}",
                subject="user",
                target="res",
                timestamp=t,
            )

        entries = store.get_all_entries()
        assert all(e.timestamp == t for e in entries)

        validator = AuditLogValidator()
        state = store.get_chain_state()
        report = validator.verify_chain(entries, anchor_hashes=state.hashes)
        assert report.is_valid is True
        assert store.verify() is True

    def test_large_chain_performance(self, store, validator, manual_clock):
        n = 2000
        start_time = time.time()

        for i in range(n):
            manual_clock.advance(1)
            store.append(
                event_type=f"EVENT_{i}",
                subject=f"user_{i % 10}",
                target=f"resource_{i % 100}",
                details={"seq": i},
            )

        append_time = time.time() - start_time

        entries = store.get_all_entries()
        assert len(entries) == n

        verify_start = time.time()
        state = store.get_chain_state()
        report = validator.verify_chain(entries, anchor_hashes=state.hashes)
        verify_time = time.time() - verify_start

        assert report.is_valid is True
        assert report.total_entries == n
        assert store.verify() is True

        assert append_time < 5.0
        assert verify_time < 2.0

    def test_verify_empty_range(self, store, validator, manual_clock):
        for i in range(5):
            manual_clock.advance(5)
            store.append(
                event_type=f"EVENT_{i}",
                subject=f"user_{i}",
                target=f"resource_{i}",
            )

        entries = store.get_all_entries()
        report = validator.verify_chain(entries, start=3, end=3)
        assert report.is_valid is True
        assert report.total_entries == 0

    def test_index_out_of_range(self, store):
        store.append(event_type="EVENT", subject="user", target="res")

        with pytest.raises(InvalidIndexError):
            store.get_entry(5)

        with pytest.raises(InvalidIndexError):
            store.get_entry(-1)

        with pytest.raises(InvalidIndexError):
            store.get_entries(start=10)

    def test_get_entries_range(self, store, manual_clock):
        for i in range(10):
            manual_clock.advance(1)
            store.append(
                event_type=f"EVENT_{i}",
                subject=f"user_{i}",
                target=f"resource_{i}",
            )

        entries = store.get_entries(start=2, end=5)
        assert len(entries) == 3
        assert entries[0].index == 2
        assert entries[2].index == 4

        all_entries = store.get_all_entries()
        assert len(all_entries) == 10

    def test_empty_store_get_entries_default(self, store):
        entries = store.get_entries()
        assert entries == []

    def test_empty_store_get_entries_nonzero_start_raises(self, store):
        with pytest.raises(EmptyAuditLogError):
            store.get_entries(start=1)


class TestEmptyAuditLogError:
    def test_last_entry_empty_raises(self, store):
        with pytest.raises(EmptyAuditLogError):
            _ = store.last_entry

    def test_genesis_hash_empty_raises(self, store):
        with pytest.raises(EmptyAuditLogError):
            _ = store.genesis_hash

    def test_chain_tip_hash_empty_raises(self, store):
        with pytest.raises(EmptyAuditLogError):
            _ = store.chain_tip_hash

    def test_get_entry_empty_raises(self, store):
        with pytest.raises(EmptyAuditLogError):
            store.get_entry(0)

    def test_verify_empty_returns_true(self, store):
        assert store.verify() is True

    def test_get_chain_state_empty(self, store):
        state = store.get_chain_state()
        assert isinstance(state, ChainState)
        assert state.length == 0
        assert state.genesis_hash == ""
        assert state.chain_tip_hash == ""
        assert state.hashes == []


class TestStoreProperties:
    def test_is_empty(self, store):
        assert store.is_empty is True
        assert store.length == 0

        store.append(event_type="EVENT", subject="user", target="res")
        assert store.is_empty is False
        assert store.length == 1
        assert store.last_entry is not None

    def test_last_entry(self, store, manual_clock):
        for i in range(3):
            manual_clock.advance(5)
            entry = store.append(
                event_type=f"EVENT_{i}",
                subject=f"user_{i}",
                target=f"resource_{i}",
            )
            assert store.last_entry.index == i
            assert store.last_entry.event_type == f"EVENT_{i}"

    def test_genesis_and_tip_hash(self, store, manual_clock):
        entry1 = store.append(event_type="EVENT_0", subject="u0", target="r0")
        manual_clock.advance(5)
        entry2 = store.append(event_type="EVENT_1", subject="u1", target="r1")
        manual_clock.advance(5)
        entry3 = store.append(event_type="EVENT_2", subject="u2", target="r2")

        assert store.genesis_hash == entry1.hash
        assert store.chain_tip_hash == entry3.hash
        assert store.genesis_hash != store.chain_tip_hash


class TestChainState:
    def test_chain_state_snapshot_independent(self, store, manual_clock):
        store.append(event_type="EVENT_0", subject="u0", target="r0")
        manual_clock.advance(5)
        store.append(event_type="EVENT_1", subject="u1", target="r1")

        state = store.get_chain_state()
        hashes_snapshot = state.hashes

        manual_clock.advance(5)
        store.append(event_type="EVENT_2", subject="u2", target="r2")

        assert len(hashes_snapshot) == 2
        assert len(store.get_chain_state().hashes) == 3


class TestModels:
    def test_compute_hash_deterministic(self):
        content1 = "test|content|123"
        content2 = "test|content|123"
        content3 = "test|content|456"

        assert compute_hash(content1) == compute_hash(content2)
        assert compute_hash(content1) != compute_hash(content3)

    def test_audit_log_entry_content_for_hash(self):
        entry = AuditLogEntry(
            index=0,
            event_type="CREATE",
            subject="admin",
            target="user:alice",
            timestamp=1.0,
            details={"role": "user"},
            previous_hash="",
        )
        content = entry.content_for_hash()
        assert "0" in content
        assert "CREATE" in content
        assert "admin" in content
        assert "user:alice" in content
        assert "1.0" in content

    def test_verification_report_summary(self):
        report = VerificationReport(
            is_valid=True,
            total_entries=10,
            passed_ranges=[(0, 9)],
            failed_ranges=[],
            tampered_indices=[],
            results=[],
            first_tampered_index=None,
        )
        assert "10 entries verified successfully" in report.summary()

        report = VerificationReport(
            is_valid=False,
            total_entries=10,
            passed_ranges=[(0, 2)],
            failed_ranges=[(3, 9)],
            tampered_indices=[3, 4, 5, 6, 7, 8, 9],
            results=[],
            first_tampered_index=3,
        )
        summary = report.summary()
        assert "FAILED" in summary
        assert "First tampered at index 3" in summary
