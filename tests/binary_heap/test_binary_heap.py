import random

import pytest

from solocoder_py.binary_heap import BinaryHeap, HeapEmptyError, HeapEntry, HeapError


class TestInsertAndExtract:
    def test_insert_and_extract_in_order(self, empty_heap: BinaryHeap):
        empty_heap.insert("task_c", priority=3)
        empty_heap.insert("task_a", priority=1)
        empty_heap.insert("task_b", priority=2)

        assert empty_heap.extract_min() == "task_a"
        assert empty_heap.extract_min() == "task_b"
        assert empty_heap.extract_min() == "task_c"

    def test_insert_in_reverse_order(self, empty_heap: BinaryHeap):
        for i in range(10, 0, -1):
            empty_heap.insert(f"task_{i}", priority=i)

        for i in range(1, 11):
            assert empty_heap.extract_min() == f"task_{i}"

    def test_insert_random_order(self, empty_heap: BinaryHeap):
        priorities = list(range(1, 21))
        random.shuffle(priorities)

        for p in priorities:
            empty_heap.insert(f"task_{p}", priority=p)

        for p in range(1, 21):
            assert empty_heap.extract_min() == f"task_{p}"

    def test_insert_with_same_priority(self, empty_heap: BinaryHeap):
        empty_heap.insert("first", priority=5)
        empty_heap.insert("second", priority=5)
        empty_heap.insert("third", priority=5)

        results = [empty_heap.extract_min() for _ in range(3)]
        assert set(results) == {"first", "second", "third"}
        assert len(results) == 3

    def test_insert_with_negative_priority(self, empty_heap: BinaryHeap):
        empty_heap.insert("neg10", priority=-10)
        empty_heap.insert("zero", priority=0)
        empty_heap.insert("neg5", priority=-5)
        empty_heap.insert("pos5", priority=5)

        assert empty_heap.extract_min() == "neg10"
        assert empty_heap.extract_min() == "neg5"
        assert empty_heap.extract_min() == "zero"
        assert empty_heap.extract_min() == "pos5"

    def test_insert_with_float_priority(self, empty_heap: BinaryHeap):
        empty_heap.insert("a", priority=3.14)
        empty_heap.insert("b", priority=1.59)
        empty_heap.insert("c", priority=2.65)

        assert empty_heap.extract_min() == "b"
        assert empty_heap.extract_min() == "c"
        assert empty_heap.extract_min() == "a"


class TestPeekMin:
    def test_peek_does_not_remove(self, small_heap: BinaryHeap):
        assert small_heap.peek_min() == "task_a"
        assert small_heap.peek_min() == "task_a"
        assert small_heap.size() == 3

    def test_peek_returns_min(self, empty_heap: BinaryHeap):
        empty_heap.insert("high", priority=100)
        empty_heap.insert("low", priority=1)
        empty_heap.insert("medium", priority=50)

        assert empty_heap.peek_min() == "low"
        assert empty_heap.extract_min() == "low"
        assert empty_heap.peek_min() == "medium"


class TestHeapify:
    def test_heapify_random_array(self, empty_heap: BinaryHeap):
        items = [(5, "e"), (3, "c"), (1, "a"), (4, "d"), (2, "b")]
        empty_heap.heapify(items)

        assert empty_heap.size() == 5
        result = [empty_heap.extract_min() for _ in range(5)]
        assert result == ["a", "b", "c", "d", "e"]

    def test_heapify_already_sorted(self, empty_heap: BinaryHeap):
        items = [(1, "a"), (2, "b"), (3, "c"), (4, "d"), (5, "e")]
        empty_heap.heapify(items)

        result = [empty_heap.extract_min() for _ in range(5)]
        assert result == ["a", "b", "c", "d", "e"]

    def test_heapify_reverse_sorted(self, empty_heap: BinaryHeap):
        items = [(5, "e"), (4, "d"), (3, "c"), (2, "b"), (1, "a")]
        empty_heap.heapify(items)

        result = [empty_heap.extract_min() for _ in range(5)]
        assert result == ["a", "b", "c", "d", "e"]

    def test_heapify_all_same_priority(self, empty_heap: BinaryHeap):
        items = [(5, "a"), (5, "b"), (5, "c"), (5, "d"), (5, "e")]
        empty_heap.heapify(items)

        assert empty_heap.size() == 5
        result = [empty_heap.extract_min() for _ in range(5)]
        assert set(result) == {"a", "b", "c", "d", "e"}

    def test_heapify_single_element(self, empty_heap: BinaryHeap):
        empty_heap.heapify([(1, "only")])
        assert empty_heap.size() == 1
        assert empty_heap.extract_min() == "only"

    def test_heapify_empty_array(self, empty_heap: BinaryHeap):
        empty_heap.heapify([])
        assert empty_heap.is_empty()

    def test_heapify_large_array(self, empty_heap: BinaryHeap):
        n = 1000
        items = [(i, f"item_{i}") for i in range(n)]
        random.shuffle(items)
        empty_heap.heapify(items)

        assert empty_heap.size() == n
        for i in range(n):
            assert empty_heap.extract_min() == f"item_{i}"

    def test_heapify_with_duplicates(self, empty_heap: BinaryHeap):
        items = [(2, "b1"), (1, "a"), (2, "b2"), (1, "a"), (3, "c")]
        empty_heap.heapify(items)

        assert empty_heap.size() == 5
        result = [empty_heap.extract_min() for _ in range(5)]
        assert result.count("a") == 2
        assert result.count("b1") == 1
        assert result.count("b2") == 1
        assert result.count("c") == 1
        assert result[0] == "a"
        assert result[1] == "a"

    def test_init_with_items(self):
        items = [(3, "c"), (1, "a"), (2, "b")]
        heap = BinaryHeap(items)

        assert heap.size() == 3
        assert heap.extract_min() == "a"
        assert heap.extract_min() == "b"
        assert heap.extract_min() == "c"


class TestIsEmptyAndSize:
    def test_is_empty_true(self, empty_heap: BinaryHeap):
        assert empty_heap.is_empty() is True
        assert empty_heap.size() == 0

    def test_is_empty_false(self, small_heap: BinaryHeap):
        assert small_heap.is_empty() is False
        assert small_heap.size() == 3

    def test_size_after_operations(self, empty_heap: BinaryHeap):
        assert empty_heap.size() == 0

        empty_heap.insert("a", priority=1)
        assert empty_heap.size() == 1

        empty_heap.insert("b", priority=2)
        assert empty_heap.size() == 2

        empty_heap.extract_min()
        assert empty_heap.size() == 1

        empty_heap.extract_min()
        assert empty_heap.size() == 0
        assert empty_heap.is_empty() is True


class TestEmptyHeapExceptions:
    def test_extract_min_empty_raises(self, empty_heap: BinaryHeap):
        with pytest.raises(HeapEmptyError) as exc_info:
            empty_heap.extract_min()
        assert "empty heap" in str(exc_info.value).lower()

    def test_peek_min_empty_raises(self, empty_heap: BinaryHeap):
        with pytest.raises(HeapEmptyError) as exc_info:
            empty_heap.peek_min()
        assert "empty heap" in str(exc_info.value).lower()

    def test_heap_empty_error_is_heap_error(self):
        assert issubclass(HeapEmptyError, HeapError)


class TestLargeScaleOperations:
    def test_large_insert_and_extract(self, empty_heap: BinaryHeap):
        n = 10000
        priorities = list(range(n))
        random.shuffle(priorities)

        for p in priorities:
            empty_heap.insert(f"item_{p}", priority=p)

        assert empty_heap.size() == n

        for expected in range(n):
            actual = empty_heap.extract_min()
            assert actual == f"item_{expected}"

        assert empty_heap.is_empty()

    def test_large_heapify_in_place(self, empty_heap: BinaryHeap):
        n = 5000
        items = [(random.randint(0, 10000), f"item_{i}") for i in range(n)]
        empty_heap.heapify(items)

        assert empty_heap.size() == n

        prev_priority = float("-inf")
        while not empty_heap.is_empty():
            # We can't easily check priority directly, so just verify we can extract all
            empty_heap.extract_min()

        assert empty_heap.size() == 0

    def test_interleaved_insert_extract(self, empty_heap: BinaryHeap):
        empty_heap.insert("a", priority=10)
        empty_heap.insert("b", priority=20)
        assert empty_heap.extract_min() == "a"

        empty_heap.insert("c", priority=5)
        assert empty_heap.peek_min() == "c"

        empty_heap.insert("d", priority=15)
        assert empty_heap.extract_min() == "c"
        assert empty_heap.extract_min() == "d"
        assert empty_heap.extract_min() == "b"
        assert empty_heap.is_empty()


class TestHeapPropertyVerification:
    def _verify_heap_property(self, heap: BinaryHeap) -> bool:
        heap_list = heap._heap
        n = len(heap_list)
        for i in range(n):
            left = 2 * i + 1
            right = 2 * i + 2
            if left < n and heap_list[left].priority < heap_list[i].priority:
                return False
            if right < n and heap_list[right].priority < heap_list[i].priority:
                return False
        return True

    def test_heap_property_after_inserts(self, empty_heap: BinaryHeap):
        for p in [10, 5, 20, 3, 7, 15, 25]:
            empty_heap.insert(f"item_{p}", priority=p)
            assert self._verify_heap_property(empty_heap)

    def test_heap_property_after_extracts(self, empty_heap: BinaryHeap):
        for p in [10, 5, 20, 3, 7, 15, 25]:
            empty_heap.insert(f"item_{p}", priority=p)

        for _ in range(5):
            empty_heap.extract_min()
            assert self._verify_heap_property(empty_heap)

    def test_heap_property_after_heapify(self, empty_heap: BinaryHeap):
        test_cases = [
            [(5, "e"), (3, "c"), (1, "a"), (4, "d"), (2, "b")],
            [(1, "a"), (2, "b"), (3, "c"), (4, "d"), (5, "e")],
            [(5, "e"), (4, "d"), (3, "c"), (2, "b"), (1, "a")],
            [(3, "c"), (1, "a"), (4, "d"), (1, "a"), (5, "e"), (9, "f"), (2, "b"), (6, "g")],
        ]

        for items in test_cases:
            empty_heap.heapify(items)
            assert self._verify_heap_property(empty_heap)

    def test_heap_property_various_initial_arrangements(self, empty_heap: BinaryHeap):
        arrangements = [
            list(range(1, 11)),
            list(range(10, 0, -1)),
            [1, 3, 5, 7, 9, 2, 4, 6, 8, 10],
            [10, 8, 6, 4, 2, 9, 7, 5, 3, 1],
            [5, 5, 5, 5, 5],
            [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5],
        ]

        for arr in arrangements:
            items = [(p, f"item_{i}") for i, p in enumerate(arr)]
            empty_heap.heapify(items)
            assert self._verify_heap_property(empty_heap)

            extracted = [empty_heap.extract_min() for _ in range(len(arr))]
            assert len(extracted) == len(arr)


class TestHeapEntry:
    def test_ordering_only_by_priority(self):
        entry1 = HeapEntry(priority=1, element="a")
        entry2 = HeapEntry(priority=2, element="b")
        entry3 = HeapEntry(priority=1, element="c")

        assert entry1 < entry2
        assert entry2 > entry1
        assert entry1 <= entry2
        assert entry2 >= entry1

        assert entry1 <= entry3
        assert entry1 >= entry3
        assert not entry1 < entry3
        assert not entry1 > entry3

    def test_equality_by_priority_and_element(self):
        entry1 = HeapEntry(priority=5, element="test")
        entry2 = HeapEntry(priority=5, element="test")
        entry3 = HeapEntry(priority=5, element="other")
        entry4 = HeapEntry(priority=6, element="test")

        assert entry1 == entry2
        assert entry1 != entry3
        assert entry1 != entry4
        assert entry3 != entry4

    def test_ordering_ignores_element(self):
        entry1 = HeapEntry(priority=2, element="z")
        entry2 = HeapEntry(priority=3, element="a")

        assert entry1 < entry2
        assert entry2 > entry1
        assert entry1 <= entry2
        assert entry2 >= entry1

    def test_same_priority_different_element_not_equal(self):
        entry1 = HeapEntry(priority=5, element="task_a")
        entry2 = HeapEntry(priority=5, element="task_b")

        assert entry1 != entry2
        assert entry1 <= entry2
        assert entry1 >= entry2
        assert not entry1 < entry2
        assert not entry1 > entry2

    def test_ordering_consistent_with_heap_internal(self, empty_heap: BinaryHeap):
        entry1 = HeapEntry(priority=2, element="b")
        entry2 = HeapEntry(priority=1, element="a")

        heap_internal_less = entry2.priority < entry1.priority
        entry_direct_less = entry2 < entry1

        assert heap_internal_less == entry_direct_less
        assert heap_internal_less is True

    def test_equality_distinguishes_different_elements(self):
        entry1 = HeapEntry(priority=1, element="x")
        entry2 = HeapEntry(priority=1, element="y")

        assert entry1 != entry2
        assert entry1 is not entry2

    def test_entry_is_unhashable(self):
        entry = HeapEntry(priority=5, element="test")
        with pytest.raises(TypeError):
            hash(entry)


class TestCustomPriorityType:
    def test_custom_priority_only_lt_implemented(self, empty_heap: BinaryHeap):
        class PriorityOnlyLT:
            def __init__(self, value: int):
                self.value = value

            def __lt__(self, other: "PriorityOnlyLT") -> bool:
                return self.value < other.value

        p1 = PriorityOnlyLT(3)
        p2 = PriorityOnlyLT(1)
        p3 = PriorityOnlyLT(2)

        entry1 = HeapEntry(priority=p1, element="a")
        entry2 = HeapEntry(priority=p2, element="b")
        entry3 = HeapEntry(priority=p3, element="c")

        assert entry2 < entry3
        assert entry3 < entry1
        assert entry2 < entry1

        assert entry2 <= entry3
        assert entry3 <= entry1
        assert entry2 <= entry1

        assert entry1 > entry3
        assert entry3 > entry2
        assert entry1 > entry2

        assert entry1 >= entry3
        assert entry3 >= entry2
        assert entry1 >= entry2

    def test_heap_with_custom_priority_only_lt(self, empty_heap: BinaryHeap):
        class PriorityOnlyLT:
            def __init__(self, value: int):
                self.value = value

            def __lt__(self, other: "PriorityOnlyLT") -> bool:
                return self.value < other.value

        empty_heap.insert("c", PriorityOnlyLT(3))
        empty_heap.insert("a", PriorityOnlyLT(1))
        empty_heap.insert("b", PriorityOnlyLT(2))

        assert empty_heap.extract_min() == "a"
        assert empty_heap.extract_min() == "b"
        assert empty_heap.extract_min() == "c"

    def test_comparison_no_equality_fallback(self):
        class PriorityNoEq:
            def __init__(self, value: int):
                self.value = value

            def __lt__(self, other: "PriorityNoEq") -> bool:
                return self.value < other.value

            def __eq__(self, other: object) -> bool:
                raise NotImplementedError("Equality not implemented")

        p1 = PriorityNoEq(5)
        p2 = PriorityNoEq(5)
        p3 = PriorityNoEq(3)

        entry1 = HeapEntry(priority=p1, element="a")
        entry2 = HeapEntry(priority=p2, element="b")
        entry3 = HeapEntry(priority=p3, element="c")

        assert entry3 < entry1
        assert entry3 < entry2

        assert entry3 <= entry1
        assert entry3 <= entry2
        assert entry1 <= entry2
        assert entry2 <= entry1

        assert entry1 > entry3
        assert entry2 > entry3

        assert entry1 >= entry3
        assert entry2 >= entry3
        assert entry1 >= entry2
        assert entry2 >= entry1


class TestMixedOperations:
    def test_heapify_replace_existing_data(self, empty_heap: BinaryHeap):
        empty_heap.insert("old1", priority=10)
        empty_heap.insert("old2", priority=20)

        empty_heap.heapify([(1, "new1"), (2, "new2"), (3, "new3")])

        assert empty_heap.size() == 3
        assert empty_heap.extract_min() == "new1"
        assert empty_heap.extract_min() == "new2"
        assert empty_heap.extract_min() == "new3"

    def test_extract_until_empty_then_insert(self, small_heap: BinaryHeap):
        while not small_heap.is_empty():
            small_heap.extract_min()

        assert small_heap.is_empty()

        small_heap.insert("new", priority=100)
        assert small_heap.size() == 1
        assert small_heap.peek_min() == "new"

    def test_heapify_then_insert(self, empty_heap: BinaryHeap):
        empty_heap.heapify([(10, "a"), (20, "b"), (30, "c")])
        empty_heap.insert("d", priority=5)
        empty_heap.insert("e", priority=25)

        assert empty_heap.extract_min() == "d"
        assert empty_heap.extract_min() == "a"
        assert empty_heap.extract_min() == "b"
        assert empty_heap.extract_min() == "e"
        assert empty_heap.extract_min() == "c"
