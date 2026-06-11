import time
from unittest.mock import patch

import pytest

from solocoder_py.log_segment import (
    CompactionInProgressError,
    LogEntry,
    LogSegment,
    LogSegmentError,
    OffsetMapper,
    OffsetNotFoundError,
    SegmentAlreadyRecycledError,
    SegmentedLog,
    SegmentedLogConfig,
)
from solocoder_py.log_segment.compactor import LogCompactor
from solocoder_py.log_segment.exceptions import SegmentRecycledError


class TestLogEntry:
    def test_entry_creation(self):
        entry = LogEntry(key="k1", value="v1")
        assert entry.key == "k1"
        assert entry.value == "v1"
        assert entry.logical_offset == 0
        assert entry.physical_offset == 0
        assert entry.tombstone is False

    def test_entry_size(self):
        entry = LogEntry(key="k1", value="v1")
        s = entry.size()
        assert s > 0

    def test_tombstone_entry(self):
        entry = LogEntry(key="k1", value=None, tombstone=True)
        assert entry.tombstone is True


class TestOffsetMapper:
    def test_add_and_get_mapping(self, make_offset_mapper):
        mapper = make_offset_mapper()
        mapper.add_entry(0, 100, 0)
        assert mapper.get_physical(100, 0) == 0
        assert mapper.get_physical(100) == 0

    def test_resolve_logical(self, make_offset_mapper):
        mapper = make_offset_mapper()
        mapper.add_entry(1, 200, 32)
        seg_id, phys = mapper.resolve_logical(200)
        assert seg_id == 1
        assert phys == 32

    def test_offset_not_found_raises_error(self, make_offset_mapper):
        mapper = make_offset_mapper()
        with pytest.raises(OffsetNotFoundError):
            mapper.get_physical(999)

    def test_mark_deleted(self, make_offset_mapper):
        mapper = make_offset_mapper()
        mapper.add_entry(0, 50, 10)
        mapper.mark_deleted(0, 50)
        assert mapper.global_mapping.is_deleted(50)
        with pytest.raises(OffsetNotFoundError):
            mapper.get_physical(50)

    def test_register_and_remove_segment(self, make_offset_mapper):
        mapper = make_offset_mapper()
        mapper.register_segment(42)
        assert 42 in mapper.segment_mappings
        mapper.remove_segment(42)
        assert 42 not in mapper.segment_mappings

    def test_snapshot(self, make_offset_mapper):
        mapper = make_offset_mapper()
        mapper.add_entry(0, 1, 10)
        mapper.add_entry(0, 2, 20)
        mapper.save_compaction_snapshot()
        assert len(mapper.compaction_snapshots) == 1


class TestLogSegment:
    def test_append_and_read(self):
        seg = LogSegment(segment_id=0, base_logical_offset=0, next_logical_offset=0)
        entry = LogEntry(key="k1", value="v1")
        logical = seg.append(entry)
        assert logical == 0
        assert seg.count() == 1

        read_entry = seg.read_at(0)
        assert read_entry is not None
        assert read_entry.key == "k1"
        assert read_entry.value == "v1"

    def test_read_all(self):
        seg = LogSegment(segment_id=0, base_logical_offset=0, next_logical_offset=0)
        seg.append(LogEntry(key="k1", value="v1"))
        seg.append(LogEntry(key="k2", value="v2"))
        entries = seg.read_all()
        assert len(entries) == 2

    def test_segment_expiry_no_retention(self):
        seg = LogSegment(segment_id=0)
        assert seg.is_expired() is False

    def test_segment_expiry_with_retention(self):
        now = time.time()
        seg = LogSegment(segment_id=0, created_at=now - 1000, retention_period=100)
        assert seg.is_expired(now) is True

    def test_segment_not_expired_yet(self):
        now = time.time()
        seg = LogSegment(segment_id=0, created_at=now - 50, retention_period=100)
        assert seg.is_expired(now) is False

    def test_mark_and_recycle(self):
        seg = LogSegment(segment_id=0, base_logical_offset=0, next_logical_offset=0)
        seg.append(LogEntry(key="k1", value="v1"))
        assert seg.is_marked_for_recycling is False
        seg.mark_for_recycling()
        assert seg.is_marked_for_recycling is True
        seg.recycle()
        assert seg.is_recycled is True
        assert seg.count() == 0
        assert seg.physical_size == 0

    def test_append_to_recycled_raises(self):
        seg = LogSegment(segment_id=0)
        seg.mark_for_recycling()
        seg.recycle()
        with pytest.raises(SegmentRecycledError):
            seg.append(LogEntry(key="k", value="v"))

    def test_read_recycled_raises(self):
        seg = LogSegment(segment_id=0)
        seg.recycle()
        with pytest.raises(SegmentRecycledError):
            seg.read_all()

    def test_double_recycle_raises(self):
        seg = LogSegment(segment_id=0)
        seg.recycle()
        with pytest.raises(SegmentAlreadyRecycledError):
            seg.recycle()

    def test_age(self):
        past = time.time() - 100
        seg = LogSegment(segment_id=0, created_at=past)
        age = seg.age()
        assert age >= 99

    def test_logical_offset_range(self):
        seg = LogSegment(segment_id=0, base_logical_offset=10, next_logical_offset=10)
        assert seg.first_logical_offset() == 10
        assert seg.last_logical_offset() == 9
        seg.append(LogEntry(key="k1", value="v1"))
        assert seg.first_logical_offset() == 10
        assert seg.last_logical_offset() == 10
        seg.append(LogEntry(key="k2", value="v2"))
        assert seg.last_logical_offset() == 11

    def test_compacted_copy(self):
        seg = LogSegment(segment_id=0, base_logical_offset=0, next_logical_offset=0)
        e1 = LogEntry(key="k1", value="old")
        seg.append(e1)
        e2 = LogEntry(key="k1", value="new")
        seg.append(e2)
        retained = [e2]
        new_seg = seg.compacted_copy(retained)
        assert new_seg.count() == 1
        assert new_seg.entries[0].key == "k1"
        assert new_seg.entries[0].value == "new"
        assert new_seg.entries[0].physical_offset == 0
        assert new_seg.physical_size < seg.physical_size

    def test_replace_entries(self):
        seg = LogSegment(segment_id=0, base_logical_offset=0, next_logical_offset=0)
        seg.append(LogEntry(key="k1", value="v1"))
        seg.append(LogEntry(key="k2", value="v2"))
        new_entries = [LogEntry(key="k1", value="v1", logical_offset=0)]
        seg.replace_entries(new_entries)
        assert seg.count() == 1
        assert seg.entries[0].physical_offset == 0


class TestCompactor:
    def test_compact_removes_duplicate_keys(self, make_offset_mapper, make_compactor):
        mapper = make_offset_mapper()
        compactor = make_compactor()
        seg = LogSegment(segment_id=0, base_logical_offset=0, next_logical_offset=0)
        e1 = LogEntry(key="k1", value="v1_old")
        lo1 = seg.append(e1)
        mapper.add_entry(0, lo1, e1.physical_offset)
        e2 = LogEntry(key="k1", value="v1_new")
        lo2 = seg.append(e2)
        mapper.add_entry(0, lo2, e2.physical_offset)
        e3 = LogEntry(key="k2", value="v2")
        lo3 = seg.append(e3)
        mapper.add_entry(0, lo3, e3.physical_offset)

        new_segs, result = compactor.compact_segments([seg], mapper)
        assert result.entries_removed == 1
        assert result.entries_retained == 2
        new_seg = new_segs[0]
        assert new_seg.count() == 2
        keys = {e.key for e in new_seg.entries}
        assert "k1" in keys and "k2" in keys
        k1_entry = next(e for e in new_seg.entries if e.key == "k1")
        assert k1_entry.value == "v1_new"

    def test_compact_with_tombstone(self, make_offset_mapper, make_compactor):
        mapper = make_offset_mapper()
        compactor = make_compactor()
        seg = LogSegment(segment_id=0, base_logical_offset=0, next_logical_offset=0)
        e1 = LogEntry(key="k1", value="v1")
        lo1 = seg.append(e1)
        mapper.add_entry(0, lo1, e1.physical_offset)
        e2 = LogEntry(key="k1", value=None, tombstone=True)
        lo2 = seg.append(e2)
        mapper.add_entry(0, lo2, e2.physical_offset)

        new_segs, result = compactor.compact_segments([seg], mapper)
        assert result.entries_removed == 2
        assert result.entries_retained == 0
        assert new_segs[0].count() == 0

    def test_compaction_in_progress_raises(self, make_offset_mapper, make_compactor):
        compactor = make_compactor()
        compactor.is_compacting = True
        with pytest.raises(CompactionInProgressError):
            compactor.compact_segments([], make_offset_mapper())

    def test_pending_writes(self, make_compactor):
        compactor = make_compactor()
        entry = LogEntry(key="k1", value="v1")
        compactor.queue_write_during_compaction(0, entry)
        pending = compactor.flush_pending_writes()
        assert len(pending) == 1
        assert pending[0] == (0, entry)
        pending2 = compactor.flush_pending_writes()
        assert len(pending2) == 0

    def test_empty_segments_compact(self, make_offset_mapper, make_compactor):
        mapper = make_offset_mapper()
        compactor = make_compactor()
        new_segs, result = compactor.compact_segments([], mapper)
        assert len(new_segs) == 0
        assert result.entries_retained == 0
        assert result.entries_removed == 0

    def test_space_saved_bytes(self, make_offset_mapper, make_compactor):
        mapper = make_offset_mapper()
        compactor = make_compactor()
        seg = LogSegment(segment_id=0, base_logical_offset=0, next_logical_offset=0)
        for i in range(5):
            e = LogEntry(key="dup", value=f"v{i}" * 100)
            lo = seg.append(e)
            mapper.add_entry(0, lo, e.physical_offset)
        original_size = seg.physical_size
        new_segs, result = compactor.compact_segments([seg], mapper)
        assert result.space_saved_bytes > 0
        assert new_segs[0].physical_size < original_size


class TestSegmentedLogNormalFlow:
    def test_append_and_read(self, make_default_log):
        log = make_default_log()
        off1 = log.append("k1", "v1")
        off2 = log.append("k2", "v2")
        e1 = log.read(off1)
        e2 = log.read(off2)
        assert e1 is not None and e1.value == "v1"
        assert e2 is not None and e2.value == "v2"

    def test_compact_keeps_latest_per_key(self, make_default_log):
        log = make_default_log()
        offsets = []
        for i in range(5):
            off = log.append("user_1", f"profile_v{i}")
            offsets.append(off)
        log.append("user_2", "profile_2")

        result = log.compact()
        assert result.entries_removed == 4
        assert result.entries_retained == 2

        latest = offsets[-1]
        e = log.read(latest)
        assert e is not None
        assert e.value == "profile_v4"

        for old_off in offsets[:-1]:
            assert log.is_offset_readable(old_off) is False

    def test_compact_preserves_other_keys(self, make_default_log):
        log = make_default_log()
        log.append("a", "a1")
        b_off = log.append("b", "b1")
        log.append("a", "a2")
        result = log.compact()
        assert result.entries_retained == 2
        b_entry = log.read(b_off)
        assert b_entry is not None
        assert b_entry.value == "b1"

    def test_offset_mapping_after_compaction(self, make_default_log):
        log = make_default_log()
        log.append("k", "v0")
        log.append("k", "v1")
        latest = log.append("k", "v2")
        log.compact()
        entry = log.read(latest)
        assert entry is not None
        assert entry.physical_offset == 0
        assert entry.value == "v2"

    def test_segment_retention_expiry_and_recycle(self, make_default_log):
        log = make_default_log(retention_period=1.0)
        off1 = log.append("k1", "v1")
        assert log.is_offset_readable(off1) is True
        future = time.time() + 10
        expired, recycled = log.cleanup(future)
        assert len(expired) >= 1
        assert recycled >= 1
        assert log.is_offset_readable(off1) is False

    def test_expired_segment_not_accessible(self, make_default_log):
        log = make_default_log(retention_period=0.001)
        off = log.append("x", "y")
        time.sleep(0.01)
        log.cleanup()
        assert log.read(off) is None

    def test_offset_mapping_points_to_new_physical(self, make_default_log):
        log = make_default_log()
        off_old = []
        for i in range(3):
            off = log.append("shared", f"val_{i}")
            off_old.append(off)
        other_off = log.append("other", "val_x")
        result = log.compact()
        assert len(result.offset_mapping_changes) > 0
        latest = off_old[-1]
        entry = log.read(latest)
        assert entry is not None
        assert entry.physical_offset <= result.offset_mapping_changes.get(latest, 9999)
        other_entry = log.read(other_off)
        assert other_entry is not None


class TestSegmentedLogBoundary:
    def test_single_record_compaction(self, make_default_log):
        log = make_default_log()
        off = log.append("only", "value")
        result = log.compact()
        assert result.entries_removed == 0
        assert result.entries_retained == 1
        e = log.read(off)
        assert e is not None
        assert e.value == "value"

    def test_empty_log_compaction(self, make_default_log):
        log = make_default_log()
        result = log.compact()
        assert result.entries_retained == 0
        assert result.entries_removed == 0
        assert result.segments_compacted >= 0

    def test_all_segments_expired(self, make_default_log):
        log = make_default_log(retention_period=0.001)
        off1 = log.append("a", "1")
        off2 = log.append("b", "2")
        time.sleep(0.01)
        expired, recycled = log.cleanup()
        assert recycled >= 1
        assert log.read(off1) is None
        assert log.read(off2) is None
        assert log.total_entries() == 0

    def test_max_segment_entries_creates_new_segment(self, make_default_log):
        log = make_default_log(max_segment_entries=3)
        for i in range(7):
            log.append(f"k{i}", f"v{i}")
        assert log.total_segments() >= 3

    def test_append_after_all_recycled_creates_new(self, make_default_log):
        log = make_default_log(retention_period=0.001)
        log.append("old", "data")
        time.sleep(0.01)
        log.cleanup()
        new_off = log.append("new", "data")
        e = log.read(new_off)
        assert e is not None
        assert e.value == "data"

    def test_total_entries_and_size(self, make_default_log):
        log = make_default_log()
        log.append("a", "1")
        log.append("b", "22")
        assert log.total_entries() == 2
        assert log.total_size_bytes() > 0

    def test_scan_all(self, make_default_log):
        log = make_default_log()
        for i in range(5):
            log.append(f"k{i}", f"v{i}")
        entries = log.scan_all()
        assert len(entries) == 5

    def test_list_segment_ids(self, make_default_log):
        log = make_default_log()
        ids = log.list_segment_ids()
        assert len(ids) >= 1
        assert 0 in ids


class TestSegmentedLogExceptions:
    def test_read_nonexistent_offset(self, make_default_log):
        log = make_default_log()
        log.append("k", "v")
        result = log.read(999999)
        assert result is None

    def test_double_recycle_segment_raises(self, make_default_log):
        log = make_default_log()
        log.append("k", "v")
        seg_id = log.list_segment_ids()[0]
        log.force_recycle_segment(seg_id)
        with pytest.raises(SegmentAlreadyRecycledError):
            log.force_recycle_segment(seg_id)

    def test_write_during_compaction(self, make_default_log):
        log = make_default_log()
        log.append("k", "v1")
        compactor = log.compactor
        compactor.is_compacting = True
        try:
            pending_off = log.append("during", "compact")
            assert len(compactor.pending_writes) == 1
            compactor.is_compacting = False
            log.compact()
            e = log.read(pending_off)
            assert e is not None
            assert e.value == "compact"
        finally:
            compactor.is_compacting = False

    def test_compaction_in_progress_error_on_second_compact(self, make_default_log):
        log = make_default_log()
        log.append("k", "v")
        log.compactor.is_compacting = True
        try:
            with pytest.raises(CompactionInProgressError):
                log.compact()
        finally:
            log.compactor.is_compacting = False

    def test_mark_tombstone_removes_on_compact(self, make_default_log):
        log = make_default_log()
        off1 = log.append("key", "data")
        log.mark_tombstone("key")
        result = log.compact()
        assert result.entries_retained == 0
        assert log.read(off1) is None

    def test_force_recycle_segment_read_fails(self, make_default_log):
        log = make_default_log()
        off = log.append("gone", "data")
        seg_id = log.list_segment_ids()[0]
        log.force_recycle_segment(seg_id)
        assert log.read(off) is None


class TestSegmentedLogMultipleSegments:
    def test_compact_across_multiple_segments(self, make_log_with_old_segments):
        log = make_log_with_old_segments(num_old_segments=3, entries_per_segment=5)
        old_entries = log.total_entries()
        result = log.compact()
        assert result.segments_compacted >= 3
        assert result.entries_removed == old_entries - 5

    def test_recycle_specific_segment(self, make_log_with_old_segments):
        log = make_log_with_old_segments(num_old_segments=2, entries_per_segment=3)
        seg0_id = log.list_segment_ids()[0]
        before = log.total_entries()
        log.force_recycle_segment(seg0_id)
        after = log.total_entries()
        assert after < before
        assert seg0_id not in log.list_segment_ids()

    def test_cleanup_returns_expired_and_recycled(self, make_log_with_old_segments):
        log = make_log_with_old_segments(
            num_old_segments=2,
            entries_per_segment=2,
            old_timestamp=time.time() - 10000,
        )
        for seg in log.segments.values():
            seg.retention_period = 1.0
        expired, recycled = log.cleanup()
        assert len(expired) >= 2
        assert recycled >= 2


class TestExceptionHierarchy:
    def test_log_segment_error_base(self):
        assert issubclass(OffsetNotFoundError, LogSegmentError)
        assert issubclass(SegmentRecycledError, LogSegmentError)
        assert issubclass(CompactionInProgressError, LogSegmentError)
        assert issubclass(SegmentAlreadyRecycledError, LogSegmentError)


class TestSegmentedLogConfig:
    def test_default_config(self):
        config = SegmentedLogConfig()
        assert config.retention_period is None
        assert config.max_segment_entries == 1000
        assert config.max_segment_bytes == 1024 * 1024

    def test_custom_config(self):
        config = SegmentedLogConfig(
            retention_period=3600,
            max_segment_entries=100,
            max_segment_bytes=512,
        )
        assert config.retention_period == 3600
        assert config.max_segment_entries == 100
        assert config.max_segment_bytes == 512


class TestConcurrentWritesDuringCompaction:
    def test_pending_writes_flushed_after_compact(self, make_default_log):
        log = make_default_log()
        for i in range(3):
            log.append("shared", f"old_{i}")
        log.compactor.is_compacting = True
        pending_offsets = []
        try:
            for i in range(2):
                off = log.append(f"new_k{i}", f"new_v{i}")
                pending_offsets.append(off)
            assert len(log.compactor.pending_writes) == 2
        finally:
            log.compactor.is_compacting = False
        result = log.compact()
        assert len(log.compactor.pending_writes) == 0
        for off in pending_offsets:
            e = log.read(off)
            assert e is not None


class TestGetSegment:
    def test_get_existing_segment(self, make_default_log):
        log = make_default_log()
        log.append("k", "v")
        seg_id = log.list_segment_ids()[0]
        seg = log.get_segment(seg_id)
        assert seg is not None
        assert seg.segment_id == seg_id

    def test_get_nonexistent_segment(self, make_default_log):
        log = make_default_log()
        assert log.get_segment(9999) is None
