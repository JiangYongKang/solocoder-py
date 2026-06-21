import threading
import time
from typing import List, Set

import pytest

from solocoder_py.treiber_stack import TreiberStack


class TestNormalOperations:
    def test_push_and_pop_order(self, stack: TreiberStack[int]) -> None:
        stack.push(1)
        stack.push(2)
        stack.push(3)

        assert stack.pop() == 3
        assert stack.pop() == 2
        assert stack.pop() == 1

    def test_empty_pop_returns_none(self, stack: TreiberStack[int]) -> None:
        assert stack.pop() is None

    def test_peek_does_not_remove(self, stack: TreiberStack[int]) -> None:
        stack.push(42)
        stack.push(99)

        assert stack.peek() == 99
        assert stack.peek() == 99
        assert stack.pop() == 99
        assert stack.peek() == 42

    def test_is_empty(self, stack: TreiberStack[int]) -> None:
        assert stack.is_empty() is True
        stack.push(1)
        assert stack.is_empty() is False
        stack.pop()
        assert stack.is_empty() is True

    def test_all_pushed_elements_popped_no_duplicates(
        self, stack: TreiberStack[int]
    ) -> None:
        elements = list(range(100))
        for e in elements:
            stack.push(e)

        popped: List[int] = []
        while not stack.is_empty():
            val = stack.pop()
            assert val is not None
            popped.append(val)

        assert len(popped) == len(elements)
        assert len(set(popped)) == len(elements)
        assert set(popped) == set(elements)

    def test_size_tracking(self, stack: TreiberStack[int]) -> None:
        assert stack.size() == 0
        stack.push(1)
        assert stack.size() == 1
        stack.push(2)
        assert stack.size() == 2
        stack.pop()
        assert stack.size() == 1
        stack.pop()
        assert stack.size() == 0


class TestBoundaryConditions:
    def test_empty_peek_returns_none(self, stack: TreiberStack[int]) -> None:
        assert stack.peek() is None

    def test_empty_pop_does_not_change_state(
        self, stack: TreiberStack[int]
    ) -> None:
        assert stack.is_empty()
        assert stack.pop() is None
        assert stack.is_empty()
        assert stack.size() == 0

    def test_single_element_pop_state(self, stack: TreiberStack[int]) -> None:
        stack.push(100)
        assert stack.is_empty() is False
        assert stack.size() == 1

        val = stack.pop()
        assert val == 100
        assert stack.is_empty() is True
        assert stack.size() == 0
        assert stack.peek() is None

    def test_large_number_of_elements(self, stack: TreiberStack[int]) -> None:
        n = 1000
        for i in range(n):
            stack.push(i)

        assert stack.size() == n
        assert stack.peek() == n - 1

        for i in range(n - 1, -1, -1):
            assert stack.pop() == i

        assert stack.is_empty()
        assert stack.size() == 0

    def test_duplicate_values_stored_independently(
        self, stack: TreiberStack[int]
    ) -> None:
        stack.push(5)
        stack.push(5)
        stack.push(5)

        assert stack.size() == 3
        assert stack.pop() == 5
        assert stack.pop() == 5
        assert stack.pop() == 5
        assert stack.pop() is None
        assert stack.size() == 0

    def test_mixed_push_pop_sequence(self, stack: TreiberStack[int]) -> None:
        stack.push(1)
        stack.push(2)
        assert stack.pop() == 2
        stack.push(3)
        assert stack.pop() == 3
        assert stack.pop() == 1
        stack.push(4)
        assert stack.peek() == 4
        assert stack.pop() == 4
        assert stack.pop() is None


class TestConcurrentPush:
    def test_concurrent_push_no_loss(self, stack: TreiberStack[int]) -> None:
        num_threads = 10
        elements_per_thread = 100
        total_elements = num_threads * elements_per_thread

        def push_elements(thread_id: int) -> None:
            start = thread_id * elements_per_thread
            for i in range(start, start + elements_per_thread):
                stack.push(i)

        threads: List[threading.Thread] = []
        for i in range(num_threads):
            t = threading.Thread(target=push_elements, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert stack.size() == total_elements

        popped: Set[int] = set()
        while not stack.is_empty():
            val = stack.pop()
            assert val is not None
            assert val not in popped
            popped.add(val)

        assert len(popped) == total_elements
        assert popped == set(range(total_elements))

    def test_concurrent_pop_no_duplicates(self, stack: TreiberStack[int]) -> None:
        num_elements = 500
        for i in range(num_elements):
            stack.push(i)

        num_threads = 10
        popped_per_thread: List[List[int]] = [[] for _ in range(num_threads)]

        def pop_elements(thread_idx: int) -> None:
            while True:
                val = stack.pop()
                if val is None:
                    break
                popped_per_thread[thread_idx].append(val)

        threads: List[threading.Thread] = []
        for i in range(num_threads):
            t = threading.Thread(target=pop_elements, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        all_popped: List[int] = []
        for popped in popped_per_thread:
            all_popped.extend(popped)

        assert len(all_popped) == num_elements
        assert len(set(all_popped)) == num_elements
        assert set(all_popped) == set(range(num_elements))
        assert stack.is_empty()
        assert stack.size() == 0


class TestConcurrentPushPop:
    def test_concurrent_push_and_pop_interleaved(
        self, stack: TreiberStack[int]
    ) -> None:
        num_push_threads = 5
        num_pop_threads = 5
        elements_per_push_thread = 200
        total_elements = num_push_threads * elements_per_push_thread

        all_popped: List[int] = []
        popped_lock = threading.Lock()
        push_done = threading.Event()

        def push_elements(thread_id: int) -> None:
            start = thread_id * elements_per_push_thread
            for i in range(start, start + elements_per_push_thread):
                stack.push(i)
                time.sleep(0.0001)

        def pop_elements() -> None:
            while True:
                val = stack.pop()
                if val is not None:
                    with popped_lock:
                        all_popped.append(val)
                elif push_done.is_set() and stack.is_empty():
                    break
                else:
                    time.sleep(0.0001)

        push_threads: List[threading.Thread] = []
        for i in range(num_push_threads):
            t = threading.Thread(target=push_elements, args=(i,))
            push_threads.append(t)
            t.start()

        pop_threads: List[threading.Thread] = []
        for i in range(num_pop_threads):
            t = threading.Thread(target=pop_elements)
            pop_threads.append(t)
            t.start()

        for t in push_threads:
            t.join()

        push_done.set()

        for t in pop_threads:
            t.join()

        assert len(all_popped) == total_elements
        assert len(set(all_popped)) == total_elements
        assert set(all_popped) == set(range(total_elements))
        assert stack.is_empty()
        assert stack.size() == 0


class TestABAProtection:
    def test_aba_detection_with_version(self, stack: TreiberStack[int]) -> None:
        stack.push(1)
        stack.push(2)
        initial_version = stack._get_version()

        version_before_b = stack._get_version()

        val_b = stack.pop()
        assert val_b == 2
        version_after_pop = stack._get_version()
        assert version_after_pop > version_before_b

        stack.push(2)
        version_after_repush = stack._get_version()
        assert version_after_repush > version_after_pop

        assert stack._get_version() > initial_version

    def test_aba_scenario_detected(self, stack: TreiberStack[int]) -> None:
        stack.push("A")
        stack.push("B")

        version_before = stack._get_version()

        val1 = stack.pop()
        assert val1 == "B"
        version_after_pop = stack._get_version()
        assert version_after_pop > version_before

        stack.push("B")
        version_after_push = stack._get_version()
        assert version_after_push > version_after_pop

        assert stack.peek() == "B"
        assert stack._get_version() > version_before

        val2 = stack.pop()
        assert val2 == "B"
        val3 = stack.pop()
        assert val3 == "A"

    def test_concurrent_aba_scenario(self, stack: TreiberStack[int]) -> None:
        for i in range(3):
            stack.push(i)

        initial_version = stack._get_version()
        versions_seen: Set[int] = set()
        version_lock = threading.Lock()
        operations_count = 0
        count_lock = threading.Lock()

        def thread_a_operations() -> None:
            nonlocal operations_count
            for _ in range(100):
                val = stack.pop()
                if val is not None:
                    with version_lock:
                        versions_seen.add(stack._get_version())
                    stack.push(val)
                    with count_lock:
                        operations_count += 1

        def thread_b_operations() -> None:
            nonlocal operations_count
            for _ in range(100):
                val1 = stack.pop()
                val2 = stack.pop()
                if val1 is not None:
                    stack.push(val1)
                if val2 is not None:
                    stack.push(val2)
                with count_lock:
                    operations_count += 1

        t1 = threading.Thread(target=thread_a_operations)
        t2 = threading.Thread(target=thread_b_operations)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        final_version = stack._get_version()
        assert final_version >= initial_version
        assert len(versions_seen) > 0
        assert operations_count == 200

        remaining: List[int] = []
        while not stack.is_empty():
            val = stack.pop()
            assert val is not None
            remaining.append(val)

        assert len(remaining) == 3
        assert set(remaining) == {0, 1, 2}


class TestSizeApproximation:
    def test_size_is_approximate_in_concurrent_scenario(
        self, stack: TreiberStack[int]
    ) -> None:
        initial_size = stack.size()
        assert initial_size == 0

        num_threads = 5
        ops_per_thread = 50

        def mixed_operations() -> None:
            for i in range(ops_per_thread):
                stack.push(i)
                stack.size()
                stack.pop()
                stack.size()

        threads: List[threading.Thread] = []
        for _ in range(num_threads):
            t = threading.Thread(target=mixed_operations)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert stack.size() == 0
        assert stack.is_empty()
