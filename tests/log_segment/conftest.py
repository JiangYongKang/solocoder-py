import time

import pytest

from solocoder_py.log_segment import (
    LogCompactor,
    LogEntry,
    LogSegment,
    OffsetMapper,
    SegmentedLog,
    SegmentedLogConfig,
)


@pytest.fixture
def make_default_log():
    def _make(retention_period: float | None = None,
              max_segment_entries: int = 1000,
              max_segment_bytes: int = 1024 * 1024) -> SegmentedLog:
        config = SegmentedLogConfig(
            retention_period=retention_period,
            max_segment_entries=max_segment_entries,
            max_segment_bytes=max_segment_bytes,
        )
        return SegmentedLog(config=config)
    return _make


@pytest.fixture
def make_log_with_old_segments():
    def _make(num_old_segments: int = 3,
              entries_per_segment: int = 5,
              old_timestamp: float | None = None) -> SegmentedLog:
        log = SegmentedLog()

        base_time = old_timestamp or (time.time() - 3600)
        current_offset = 0
        for i in range(num_old_segments):
            seg_id = i
            created_at = base_time + i * 60
            segment = LogSegment(
                segment_id=seg_id,
                created_at=created_at,
                retention_period=log.config.retention_period,
                base_logical_offset=current_offset,
                next_logical_offset=current_offset,
            )
            for j in range(entries_per_segment):
                entry = LogEntry(
                    key=f"key_{j}",
                    value=f"value_{i}_{j}",
                    timestamp=created_at,
                )
                segment.append(entry)
                log.offset_mapper.add_entry(seg_id, entry.logical_offset, entry.physical_offset)
                current_offset = entry.logical_offset + 1
            log.segments[seg_id] = segment
            log.segment_order.append(seg_id)
            log.offset_mapper.register_segment(seg_id)
        log.next_segment_id = num_old_segments
        log.next_logical_offset = current_offset
        return log
    return _make


@pytest.fixture
def make_offset_mapper():
    def _make() -> OffsetMapper:
        return OffsetMapper()
    return _make


@pytest.fixture
def make_compactor():
    def _make() -> LogCompactor:
        return LogCompactor()
    return _make
