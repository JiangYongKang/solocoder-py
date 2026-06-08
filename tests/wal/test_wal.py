from __future__ import annotations

from time import sleep

import pytest

from solocoder_py.wal import (
    EmptyWalError,
    InvalidTruncateLsnError,
    LogEntry,
    LsnGapError,
    LsnNotFoundError,
    TruncatedLsnError,
    WalError,
    WriteAheadLog,
)


class TestLogEntryModel:
    def test_log_entry_creation(self):
        from datetime import datetime

        now = datetime.now()
        entry = LogEntry(lsn=0, data={"key": "value"}, created_at=now)
        assert entry.lsn == 0
        assert entry.data == {"key": "value"}
        assert entry.created_at == now

    def test_log_entry_default_created_at(self):
        before = __import__("datetime").datetime.now()
        sleep(0.001)
        entry = LogEntry(lsn=1, data="test")
        sleep(0.001)
        after = __import__("datetime").datetime.now()
        assert before < entry.created_at < after

    def test_negative_lsn_rejected(self):
        with pytest.raises(ValueError, match="LSN must be non-negative"):
            LogEntry(lsn=-1, data="test")


class TestExceptionsHierarchy:
    def test_all_exceptions_inherit_from_base(self):
        assert issubclass(EmptyWalError, WalError)
        assert issubclass(InvalidTruncateLsnError, WalError)
        assert issubclass(LsnGapError, WalError)
        assert issubclass(LsnNotFoundError, WalError)
        assert issubclass(TruncatedLsnError, WalError)


class TestInitialState:
    def test_new_wal_is_empty(self, wal: WriteAheadLog):
        assert wal.is_empty is True

    def test_new_wal_min_readable_lsn(self, wal: WriteAheadLog):
        assert wal.min_readable_lsn == 0

    def test_new_wal_max_lsn(self, wal: WriteAheadLog):
        assert wal.max_lsn == -1


class TestAppendAndRead:
    def test_append_first_entry(self, wal: WriteAheadLog):
        lsn = wal.append({"op": "insert", "id": 1})
        assert lsn == 0
        assert wal.is_empty is False
        assert wal.max_lsn == 0
        assert wal.min_readable_lsn == 0

    def test_append_multiple_entries(self, wal: WriteAheadLog):
        lsn1 = wal.append("entry-0")
        lsn2 = wal.append("entry-1")
        lsn3 = wal.append("entry-2")
        assert lsn1 == 0
        assert lsn2 == 1
        assert lsn3 == 2
        assert wal.max_lsn == 2

    def test_append_returns_monotonically_increasing_lsns(self, wal: WriteAheadLog):
        lsns = [wal.append(f"entry-{i}") for i in range(10)]
        assert lsns == list(range(10))

    def test_read_single_entry(self, wal: WriteAheadLog):
        wal.append({"op": "create"})
        entry = wal.read(0)
        assert entry.lsn == 0
        assert entry.data == {"op": "create"}

    def test_read_range(self, wal: WriteAheadLog):
        for i in range(5):
            wal.append(f"data-{i}")

        entries = wal.read_range(1, 3)
        assert len(entries) == 3
        assert [e.lsn for e in entries] == [1, 2, 3]
        assert [e.data for e in entries] == ["data-1", "data-2", "data-3"]

    def test_read_range_no_end_lsn(self, wal: WriteAheadLog):
        for i in range(4):
            wal.append(f"v{i}")

        entries = wal.read_range(2)
        assert [e.lsn for e in entries] == [2, 3]

    def test_read_range_start_equals_end(self, wal: WriteAheadLog):
        for i in range(3):
            wal.append(i)

        entries = wal.read_range(1, 1)
        assert len(entries) == 1
        assert entries[0].lsn == 1
        assert entries[0].data == 1

    def test_read_range_start_greater_than_end_returns_empty(self, wal: WriteAheadLog):
        for i in range(3):
            wal.append(i)

        entries = wal.read_range(2, 1)
        assert entries == []

    def test_entries_persist_immediately_after_append(self, wal: WriteAheadLog):
        for i in range(5):
            lsn = wal.append(f"val-{i}")
            entry = wal.read(lsn)
            assert entry.data == f"val-{i}"


class TestTruncation:
    def test_truncate_single_entry(self, wal: WriteAheadLog):
        for i in range(5):
            wal.append(f"entry-{i}")

        wal.truncate(2)
        assert wal.min_readable_lsn == 3
        assert wal.max_lsn == 4

        entry = wal.read(3)
        assert entry.data == "entry-3"

    def test_truncate_all_entries(self, wal: WriteAheadLog):
        for i in range(3):
            wal.append(f"e{i}")

        wal.truncate(2)
        assert wal.min_readable_lsn == 3
        assert wal.is_empty is True

    def test_truncate_min_readable_point(self, wal: WriteAheadLog):
        for i in range(5):
            wal.append(f"e{i}")

        wal.truncate(0)
        assert wal.min_readable_lsn == 1
        entry = wal.read(1)
        assert entry.data == "e1"

    def test_truncate_max_lsn(self, wal: WriteAheadLog):
        for i in range(4):
            wal.append(f"e{i}")

        wal.truncate(3)
        assert wal.min_readable_lsn == 4
        assert wal.is_empty is True

    def test_multiple_truncations(self, wal: WriteAheadLog):
        for i in range(10):
            wal.append(f"e{i}")

        wal.truncate(2)
        assert wal.min_readable_lsn == 3

        wal.truncate(5)
        assert wal.min_readable_lsn == 6

        entry = wal.read(6)
        assert entry.data == "e6"

    def test_truncated_entries_cannot_be_read(self, wal: WriteAheadLog):
        for i in range(5):
            wal.append(f"e{i}")

        wal.truncate(2)

        with pytest.raises(TruncatedLsnError) as exc:
            wal.read(0)
        assert exc.value.lsn == 0
        assert exc.value.min_readable_lsn == 3

        with pytest.raises(TruncatedLsnError):
            wal.read(2)

    def test_read_range_with_truncated_start(self, wal: WriteAheadLog):
        for i in range(6):
            wal.append(f"e{i}")

        wal.truncate(2)

        with pytest.raises(TruncatedLsnError):
            wal.read_range(0, 3)


class TestReplay:
    def test_replay_all_entries(self, wal: WriteAheadLog):
        for i in range(5):
            wal.append(f"entry-{i}")

        replayed = list(wal.replay())
        assert [e.lsn for e in replayed] == list(range(5))
        assert [e.data for e in replayed] == [f"entry-{i}" for i in range(5)]

    def test_replay_from_middle(self, wal: WriteAheadLog):
        for i in range(6):
            wal.append(f"v{i}")

        replayed = list(wal.replay(from_lsn=3))
        assert [e.lsn for e in replayed] == [3, 4, 5]
        assert [e.data for e in replayed] == ["v3", "v4", "v5"]

    def test_replay_from_min_readable_lsn(self, wal: WriteAheadLog):
        for i in range(5):
            wal.append(f"e{i}")

        wal.truncate(1)

        replayed = list(wal.replay())
        assert [e.lsn for e in replayed] == [2, 3, 4]

    def test_replay_from_truncated_lsn_raises(self, wal: WriteAheadLog):
        for i in range(5):
            wal.append(f"e{i}")

        wal.truncate(2)

        with pytest.raises(TruncatedLsnError):
            list(wal.replay(from_lsn=0))

    def test_replay_empty_wal_returns_empty(self, wal: WriteAheadLog):
        replayed = list(wal.replay())
        assert replayed == []

    def test_replay_from_lsn_beyond_max_returns_empty(self, wal: WriteAheadLog):
        for i in range(3):
            wal.append(f"e{i}")

        replayed = list(wal.replay(from_lsn=10))
        assert replayed == []

    def test_replay_preserves_append_order(self, wal: WriteAheadLog):
        data_list = ["first", "second", "third", "fourth", "fifth"]
        for d in data_list:
            wal.append(d)

        replayed = list(wal.replay())
        assert [e.data for e in replayed] == data_list

    def test_replay_after_truncate_from_explicit_lsn(self, wal: WriteAheadLog):
        for i in range(8):
            wal.append(f"e{i}")

        wal.truncate(3)

        replayed = list(wal.replay(from_lsn=5))
        assert [e.lsn for e in replayed] == [5, 6, 7]

    def test_replay_is_lazy_generator(self, wal: WriteAheadLog):
        for i in range(5):
            wal.append(f"entry-{i}")

        it = wal.replay()
        import types

        assert isinstance(it, types.GeneratorType)

        first = next(it)
        assert first.lsn == 0
        assert first.data == "entry-0"

        second = next(it)
        assert second.lsn == 1
        assert second.data == "entry-1"

        rest = list(it)
        assert [e.lsn for e in rest] == [2, 3, 4]

    def test_replay_does_not_materialize_all_entries_upfront(self, wal: WriteAheadLog):
        for i in range(3):
            wal.append(f"e{i}")

        it = wal.replay()

        first = next(it)
        assert first.lsn == 0

        wal._entries[999] = LogEntry(lsn=999, data="injected")
        del wal._entries[1]

        with pytest.raises(LsnGapError) as exc:
            next(it)
        assert exc.value.expected_lsn == 1

    def test_replay_lsn_gap_raises(self, wal: WriteAheadLog):
        for i in range(5):
            wal.append(f"e{i}")

        del wal._entries[2]

        it = wal.replay()
        assert next(it).lsn == 0
        assert next(it).lsn == 1

        with pytest.raises(LsnGapError) as exc:
            next(it)
        assert exc.value.expected_lsn == 2
        assert exc.value.min_readable_lsn == 0
        assert exc.value.max_lsn == 4

    def test_replay_concurrent_truncate_during_iteration_raises(self, wal: WriteAheadLog):
        for i in range(5):
            wal.append(f"e{i}")

        it = wal.replay()
        assert next(it).lsn == 0
        assert next(it).lsn == 1

        wal.truncate(2)

        with pytest.raises(TruncatedLsnError) as exc:
            next(it)
        assert exc.value.lsn == 2
        assert exc.value.min_readable_lsn == 3


class TestEdgeCases:
    def test_read_from_empty_wal(self, wal: WriteAheadLog):
        with pytest.raises(EmptyWalError):
            wal.read(0)

    def test_read_range_empty_wal_returns_empty(self, wal: WriteAheadLog):
        assert wal.read_range(0, 10) == []

    def test_truncate_empty_wal_raises(self, wal: WriteAheadLog):
        with pytest.raises(EmptyWalError):
            wal.truncate(0)

    def test_read_lsn_beyond_max(self, wal: WriteAheadLog):
        wal.append("only")

        with pytest.raises(LsnNotFoundError) as exc:
            wal.read(5)
        assert exc.value.lsn == 5
        assert exc.value.min_readable_lsn == 0
        assert exc.value.max_lsn == 0

    def test_read_range_end_beyond_max_raises(self, wal: WriteAheadLog):
        for i in range(3):
            wal.append(i)

        with pytest.raises(LsnNotFoundError):
            wal.read_range(0, 10)


class TestInvalidTruncation:
    def test_truncate_below_min_readable_lsn(self, wal: WriteAheadLog):
        for i in range(5):
            wal.append(f"e{i}")

        wal.truncate(2)

        with pytest.raises(InvalidTruncateLsnError) as exc:
            wal.truncate(0)
        assert exc.value.lsn == 0
        assert exc.value.min_readable_lsn == 3
        assert exc.value.max_lsn == 4

    def test_truncate_above_max_lsn(self, wal: WriteAheadLog):
        for i in range(3):
            wal.append(f"e{i}")

        with pytest.raises(InvalidTruncateLsnError) as exc:
            wal.truncate(10)
        assert exc.value.lsn == 10
        assert exc.value.max_lsn == 2

    def test_truncate_same_range_already_truncated(self, wal: WriteAheadLog):
        for i in range(6):
            wal.append(f"e{i}")

        wal.truncate(3)

        with pytest.raises(InvalidTruncateLsnError):
            wal.truncate(1)


class TestCrashRecoverySimulation:
    def test_all_entries_survive_until_truncated(self, wal: WriteAheadLog):
        for i in range(20):
            wal.append(f"transaction-{i}")

        for lsn in range(20):
            entry = wal.read(lsn)
            assert entry.data == f"transaction-{lsn}"

    def test_replay_recovers_all_entries_after_crash(self, wal: WriteAheadLog):
        for i in range(10):
            wal.append({"tx": i, "status": "committed"})

        replayed = list(wal.replay())
        assert len(replayed) == 10
        for lsn, entry in enumerate(replayed):
            assert entry.lsn == lsn
            assert entry.data == {"tx": lsn, "status": "committed"}

    def test_partial_truncate_then_continue_appending(self, wal: WriteAheadLog):
        for i in range(5):
            wal.append(f"phase1-{i}")

        wal.truncate(2)

        for i in range(5, 10):
            lsn = wal.append(f"phase2-{i}")
            assert lsn == i

        replayed = list(wal.replay())
        assert [e.lsn for e in replayed] == [3, 4, 5, 6, 7, 8, 9]
        assert replayed[0].data == "phase1-3"
        assert replayed[2].data == "phase2-5"
        assert replayed[-1].data == "phase2-9"

    def test_min_readable_and_max_lsn_consistency(self, wal: WriteAheadLog):
        assert wal.min_readable_lsn == 0
        assert wal.max_lsn == -1

        wal.append("a")
        assert wal.min_readable_lsn == 0
        assert wal.max_lsn == 0

        wal.append("b")
        wal.append("c")
        wal.truncate(0)
        assert wal.min_readable_lsn == 1
        assert wal.max_lsn == 2

        wal.truncate(2)
        assert wal.min_readable_lsn == 3
        assert wal.is_empty is True


class TestClearOperation:
    def test_clear_resets_everything(self, wal: WriteAheadLog):
        for i in range(5):
            wal.append(i)

        wal.truncate(1)
        wal.clear()

        assert wal.is_empty is True
        assert wal.min_readable_lsn == 0
        assert wal.max_lsn == -1

        lsn = wal.append("new")
        assert lsn == 0
