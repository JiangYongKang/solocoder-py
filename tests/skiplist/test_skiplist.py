import threading
import time

import pytest

from solocoder_py.skiplist import (
    EmptySkipListError,
    InvalidRangeError,
    InvalidRankError,
    RangeQueryResult,
    SkipList,
)


class TestSkipListBasicOperations:
    def test_insert_and_size(self):
        sl = SkipList()
        assert sl.is_empty is True
        assert sl.size == 0

        sl.insert(1.0, "a")
        assert sl.size == 1
        assert sl.is_empty is False

        sl.insert(2.0, "b")
        assert sl.size == 2

    def test_insert_same_score_preserves_order(self):
        sl = SkipList()
        sl.insert(2.0, "first")
        sl.insert(2.0, "second")
        sl.insert(2.0, "third")

        results = sl.range_query(min_score=2.0, max_score=2.0)
        assert len(results) == 3
        assert results[0].value == "first"
        assert results[1].value == "second"
        assert results[2].value == "third"

    def test_insert_mixed_scores_sorted(self):
        sl = SkipList()
        sl.insert(5.0, "e")
        sl.insert(1.0, "a")
        sl.insert(3.0, "c")
        sl.insert(2.0, "b")
        sl.insert(4.0, "d")

        results = sl.range_query()
        assert [r.score for r in results] == [1.0, 2.0, 3.0, 4.0, 5.0]
        assert [r.value for r in results] == ["a", "b", "c", "d", "e"]

    def test_delete_existing_node(self):
        sl = SkipList()
        sl.insert(1.0, "a")
        sl.insert(2.0, "b")

        assert sl.delete(1.0) is True
        assert sl.size == 1
        results = sl.range_query()
        assert len(results) == 1
        assert results[0].score == 2.0

    def test_delete_nonexistent_returns_false(self):
        sl = SkipList()
        sl.insert(1.0, "a")
        assert sl.delete(999.0) is False
        assert sl.size == 1

    def test_delete_from_empty_returns_false(self):
        sl = SkipList()
        assert sl.delete(1.0) is False

    def test_delete_only_removes_one_same_score(self):
        sl = SkipList()
        sl.insert(2.0, "first")
        sl.insert(2.0, "second")
        sl.insert(2.0, "third")

        assert sl.delete(2.0) is True
        assert sl.size == 2

        results = sl.range_query()
        assert len(results) == 2
        assert results[0].value == "second"
        assert results[1].value == "third"

    def test_is_empty_property(self):
        sl = SkipList()
        assert sl.is_empty is True
        sl.insert(1.0, "a")
        assert sl.is_empty is False
        sl.delete(1.0)
        assert sl.is_empty is True


class TestSkipListRangeQuery:
    def test_range_query_full(self):
        sl = SkipList()
        for i in range(1, 6):
            sl.insert(float(i), f"v{i}")

        results = sl.range_query()
        assert len(results) == 5
        assert [r.score for r in results] == [1.0, 2.0, 3.0, 4.0, 5.0]

    def test_range_query_inclusive_both(self):
        sl = SkipList()
        for i in range(1, 11):
            sl.insert(float(i), f"v{i}")

        results = sl.range_query(
            min_score=3.0, max_score=7.0,
            min_inclusive=True, max_inclusive=True
        )
        assert [r.score for r in results] == [3.0, 4.0, 5.0, 6.0, 7.0]

    def test_range_query_exclusive_both(self):
        sl = SkipList()
        for i in range(1, 11):
            sl.insert(float(i), f"v{i}")

        results = sl.range_query(
            min_score=3.0, max_score=7.0,
            min_inclusive=False, max_inclusive=False
        )
        assert [r.score for r in results] == [4.0, 5.0, 6.0]

    def test_range_query_min_exclusive_max_inclusive(self):
        sl = SkipList()
        for i in range(1, 11):
            sl.insert(float(i), f"v{i}")

        results = sl.range_query(
            min_score=3.0, max_score=7.0,
            min_inclusive=False, max_inclusive=True
        )
        assert [r.score for r in results] == [4.0, 5.0, 6.0, 7.0]

    def test_range_query_min_inclusive_max_exclusive(self):
        sl = SkipList()
        for i in range(1, 11):
            sl.insert(float(i), f"v{i}")

        results = sl.range_query(
            min_score=3.0, max_score=7.0,
            min_inclusive=True, max_inclusive=False
        )
        assert [r.score for r in results] == [3.0, 4.0, 5.0, 6.0]

    def test_range_query_only_min(self):
        sl = SkipList()
        for i in range(1, 6):
            sl.insert(float(i), f"v{i}")

        results = sl.range_query(min_score=3.0)
        assert [r.score for r in results] == [3.0, 4.0, 5.0]

    def test_range_query_only_max(self):
        sl = SkipList()
        for i in range(1, 6):
            sl.insert(float(i), f"v{i}")

        results = sl.range_query(max_score=3.0)
        assert [r.score for r in results] == [1.0, 2.0, 3.0]

    def test_range_query_empty_result(self):
        sl = SkipList()
        for i in range(1, 6):
            sl.insert(float(i), f"v{i}")

        results = sl.range_query(min_score=10.0)
        assert results == []

    def test_range_query_empty_list(self):
        sl = SkipList()
        results = sl.range_query(min_score=1.0, max_score=10.0)
        assert results == []

    def test_range_query_invalid_range(self):
        sl = SkipList()
        sl.insert(1.0, "a")
        with pytest.raises(InvalidRangeError):
            sl.range_query(min_score=5.0, max_score=1.0)

    def test_range_query_with_same_scores(self):
        sl = SkipList()
        sl.insert(2.0, "a")
        sl.insert(2.0, "b")
        sl.insert(2.0, "c")
        sl.insert(5.0, "d")

        results = sl.range_query(min_score=2.0, max_score=2.0)
        assert len(results) == 3
        assert [r.value for r in results] == ["a", "b", "c"]


class TestSkipListRankQuery:
    def test_get_rank_basic(self):
        sl = SkipList()
        sl.insert(1.0, "a")
        sl.insert(3.0, "c")
        sl.insert(5.0, "e")

        assert sl.get_rank(1.0) == 0
        assert sl.get_rank(3.0) == 1
        assert sl.get_rank(5.0) == 2
        assert sl.get_rank(10.0) == 3

    def test_get_rank_with_nonexistent_score(self):
        sl = SkipList()
        sl.insert(2.0, "a")
        sl.insert(4.0, "b")

        assert sl.get_rank(3.0) == 1
        assert sl.get_rank(1.0) == 0
        assert sl.get_rank(10.0) == 2

    def test_get_rank_with_same_scores(self):
        sl = SkipList()
        sl.insert(2.0, "a")
        sl.insert(2.0, "b")
        sl.insert(5.0, "c")

        assert sl.get_rank(2.0) == 0
        assert sl.get_rank(5.0) == 2

    def test_get_rank_empty_list(self):
        sl = SkipList()
        with pytest.raises(EmptySkipListError):
            sl.get_rank(1.0)

    def test_get_by_rank_basic(self):
        sl = SkipList()
        sl.insert(1.0, "a")
        sl.insert(2.0, "b")
        sl.insert(3.0, "c")

        r1 = sl.get_by_rank(1)
        assert r1.score == 1.0 and r1.value == "a"

        r2 = sl.get_by_rank(2)
        assert r2.score == 2.0 and r2.value == "b"

        r3 = sl.get_by_rank(3)
        assert r3.score == 3.0 and r3.value == "c"

    def test_get_by_rank_with_same_scores(self):
        sl = SkipList()
        sl.insert(2.0, "first")
        sl.insert(2.0, "second")
        sl.insert(5.0, "third")

        assert sl.get_by_rank(1).value == "first"
        assert sl.get_by_rank(2).value == "second"
        assert sl.get_by_rank(3).value == "third"

    def test_get_by_rank_empty_list(self):
        sl = SkipList()
        with pytest.raises(EmptySkipListError):
            sl.get_by_rank(1)

    def test_get_by_rank_invalid_rank_zero(self):
        sl = SkipList()
        sl.insert(1.0, "a")
        with pytest.raises(InvalidRankError):
            sl.get_by_rank(0)

    def test_get_by_rank_invalid_rank_negative(self):
        sl = SkipList()
        sl.insert(1.0, "a")
        with pytest.raises(InvalidRankError):
            sl.get_by_rank(-1)

    def test_get_by_rank_invalid_rank_out_of_range(self):
        sl = SkipList()
        sl.insert(1.0, "a")
        sl.insert(2.0, "b")
        with pytest.raises(InvalidRankError):
            sl.get_by_rank(10)


class TestSkipListDeletionEffects:
    def test_range_query_reflects_deletion(self):
        sl = SkipList()
        for i in range(1, 6):
            sl.insert(float(i), f"v{i}")

        sl.delete(3.0)
        results = sl.range_query()
        assert [r.score for r in results] == [1.0, 2.0, 4.0, 5.0]

    def test_rank_query_reflects_deletion(self):
        sl = SkipList()
        sl.insert(1.0, "a")
        sl.insert(2.0, "b")
        sl.insert(3.0, "c")
        sl.insert(4.0, "d")

        sl.delete(2.0)
        assert sl.get_rank(3.0) == 1
        assert sl.get_rank(4.0) == 2

        assert sl.get_by_rank(2).score == 3.0
        assert sl.get_by_rank(3).score == 4.0

    def test_delete_all_nodes(self):
        sl = SkipList()
        sl.insert(1.0, "a")
        sl.insert(2.0, "b")

        sl.delete(1.0)
        sl.delete(2.0)

        assert sl.is_empty is True
        assert sl.size == 0
        assert sl.range_query() == []


class TestSkipListSingleNode:
    def test_insert_single_node(self):
        sl = SkipList()
        sl.insert(42.0, "answer")
        assert sl.size == 1

        results = sl.range_query()
        assert len(results) == 1
        assert results[0].score == 42.0
        assert results[0].value == "answer"

    def test_delete_single_node(self):
        sl = SkipList()
        sl.insert(1.0, "only")
        assert sl.delete(1.0) is True
        assert sl.is_empty is True

    def test_rank_single_node(self):
        sl = SkipList()
        sl.insert(5.0, "mid")
        assert sl.get_rank(5.0) == 0
        assert sl.get_rank(10.0) == 1
        assert sl.get_by_rank(1).value == "mid"

    def test_range_query_single_node(self):
        sl = SkipList()
        sl.insert(3.0, "single")

        r1 = sl.range_query(min_score=3.0, max_score=3.0)
        assert len(r1) == 1

        r2 = sl.range_query(min_score=3.0, max_score=3.0, min_inclusive=False)
        assert len(r2) == 0

        r3 = sl.range_query(min_score=3.0, max_score=3.0, max_inclusive=False)
        assert len(r3) == 0


class TestSkipListEmptyOperations:
    def test_empty_size(self):
        sl = SkipList()
        assert sl.size == 0

    def test_empty_is_empty(self):
        sl = SkipList()
        assert sl.is_empty is True

    def test_empty_range_query(self):
        sl = SkipList()
        assert sl.range_query() == []
        assert sl.range_query(min_score=-100.0, max_score=100.0) == []

    def test_empty_get_rank_raises(self):
        sl = SkipList()
        with pytest.raises(EmptySkipListError):
            sl.get_rank(1.0)

    def test_empty_get_by_rank_raises(self):
        sl = SkipList()
        with pytest.raises(EmptySkipListError):
            sl.get_by_rank(1)

    def test_empty_delete_returns_false(self):
        sl = SkipList()
        assert sl.delete(1.0) is False


class TestSkipListConcurrentAccess:
    def test_concurrent_inserts_data_integrity(self):
        sl = SkipList()
        errors = []
        num_threads = 10
        per_thread = 100

        def writer(start, count):
            try:
                for i in range(start, start + count):
                    sl.insert(float(i), f"value{i}")
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=writer, args=(i * per_thread, per_thread))
            for i in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert sl.size == num_threads * per_thread

        all_scores = sorted([r.score for r in sl.range_query()])
        expected = [float(i) for i in range(num_threads * per_thread)]
        assert all_scores == expected

    def test_concurrent_inserts_and_deletes(self):
        sl = SkipList()
        errors = []
        num_threads = 5
        per_thread = 50

        for i in range(num_threads * per_thread):
            sl.insert(float(i), f"value{i}")

        initial_size = sl.size

        def deleter(start, count):
            try:
                for i in range(start, start + count):
                    sl.delete(float(i))
            except Exception as e:
                errors.append(e)

        def inserter(start, count):
            try:
                for i in range(start, start + count):
                    sl.insert(float(i) + 10000, f"new_value{i}")
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(num_threads):
            threads.append(threading.Thread(target=deleter, args=(i * per_thread, per_thread)))
            threads.append(threading.Thread(target=inserter, args=(i * per_thread, per_thread)))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert sl.size > 0

        results = sl.range_query()
        scores = [r.score for r in results]
        assert scores == sorted(scores)

    def test_concurrent_reads_and_writes(self):
        sl = SkipList()
        errors = []

        def writer():
            for i in range(200):
                try:
                    sl.insert(float(i), f"value{i}")
                except Exception as e:
                    errors.append(e)

        def reader():
            for _ in range(200):
                try:
                    _ = sl.range_query(min_score=10.0, max_score=50.0)
                    if not sl.is_empty:
                        _ = sl.get_by_rank(1)
                except EmptySkipListError:
                    pass
                except InvalidRankError:
                    pass
                except Exception as e:
                    errors.append(e)

        threads = []
        for _ in range(4):
            threads.append(threading.Thread(target=writer))
            threads.append(threading.Thread(target=reader))
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_concurrent_rank_queries(self):
        sl = SkipList()
        errors = []

        for i in range(100):
            sl.insert(float(i), f"value{i}")

        def rank_reader():
            try:
                for i in range(50, 150):
                    _ = sl.get_rank(float(i))
            except Exception as e:
                errors.append(e)

        def rank_access():
            try:
                for i in range(1, 101):
                    r = sl.get_by_rank(i)
                    assert isinstance(r, RangeQueryResult)
            except Exception as e:
                errors.append(e)

        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=rank_reader))
            threads.append(threading.Thread(target=rank_access))
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_concurrent_deletes_maintain_order(self):
        sl = SkipList()
        errors = []

        for i in range(200):
            sl.insert(float(i), f"value{i}")

        def deleter(step, offset):
            try:
                for i in range(offset, 200, step):
                    sl.delete(float(i))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=deleter, args=(4, i)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

        results = sl.range_query()
        for i in range(len(results) - 1):
            assert results[i].score <= results[i + 1].score


class TestSkipListConstructorValidation:
    def test_negative_max_level_raises(self):
        with pytest.raises(ValueError):
            SkipList(max_level=0)

    def test_zero_p_raises(self):
        with pytest.raises(ValueError):
            SkipList(p=0)

    def test_p_equals_one_raises(self):
        with pytest.raises(ValueError):
            SkipList(p=1)

    def test_p_greater_than_one_raises(self):
        with pytest.raises(ValueError):
            SkipList(p=1.5)

    def test_negative_p_raises(self):
        with pytest.raises(ValueError):
            SkipList(p=-0.5)

    def test_valid_construction(self):
        sl = SkipList(max_level=16, p=0.25)
        assert sl.is_empty is True
        sl.insert(1.0, "a")
        assert sl.size == 1


class TestSkipListLargeScale:
    def test_large_insertion_and_query(self):
        sl = SkipList()
        n = 1000

        for i in range(n):
            sl.insert(float(i), f"value{i}")

        assert sl.size == n

        all_results = sl.range_query()
        assert len(all_results) == n
        assert all_results[0].score == 0.0
        assert all_results[-1].score == float(n - 1)

        mid_results = sl.range_query(min_score=100.0, max_score=200.0)
        assert len(mid_results) == 101
        assert mid_results[0].score == 100.0
        assert mid_results[-1].score == 200.0

        assert sl.get_rank(500.0) == 500
        assert sl.get_by_rank(501).score == 500.0

    def test_large_deletion(self):
        sl = SkipList()
        n = 500

        for i in range(n):
            sl.insert(float(i), f"value{i}")

        for i in range(0, n, 2):
            sl.delete(float(i))

        assert sl.size == n // 2

        results = sl.range_query()
        for r in results:
            assert int(r.score) % 2 == 1
