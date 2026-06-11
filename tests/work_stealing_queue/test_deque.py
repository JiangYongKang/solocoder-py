import threading
import time

import pytest

from solocoder_py.work_stealing_queue import (
    QueueFullError,
    WorkStealingDeque,
)


class TestLIFOBottomOperations:
    def test_push_and_pop_lifo_order(self, deque: WorkStealingDeque[int]):
        deque.push_bottom(1)
        deque.push_bottom(2)
        deque.push_bottom(3)

        assert deque.pop_bottom() == 3
        assert deque.pop_bottom() == 2
        assert deque.pop_bottom() == 1

    def test_pop_empty_returns_none(self, deque: WorkStealingDeque[int]):
        assert deque.pop_bottom() is None

    def test_size_tracking(self, deque: WorkStealingDeque[int]):
        assert deque.size() == 0
        assert deque.is_empty()

        deque.push_bottom(1)
        assert deque.size() == 1
        assert not deque.is_empty()

        deque.push_bottom(2)
        assert deque.size() == 2

        deque.pop_bottom()
        assert deque.size() == 1

        deque.pop_bottom()
        assert deque.size() == 0
        assert deque.is_empty()

    def test_len_dunder(self, deque: WorkStealingDeque[int]):
        deque.push_bottom(1)
        deque.push_bottom(2)
        assert len(deque) == 2

    def test_max_capacity_property(self, deque: WorkStealingDeque[int]):
        assert deque.max_capacity == 100

    def test_invalid_capacity_raises(self):
        with pytest.raises(ValueError):
            WorkStealingDeque(max_capacity=0)
        with pytest.raises(ValueError):
            WorkStealingDeque(max_capacity=-1)


class TestFIFOStealOperations:
    def test_steal_fifo_order(self, deque: WorkStealingDeque[int]):
        deque.push_bottom(1)
        deque.push_bottom(2)
        deque.push_bottom(3)

        assert deque.steal() == 1
        assert deque.steal() == 2
        assert deque.steal() == 3

    def test_steal_empty_returns_none(self, deque: WorkStealingDeque[int]):
        assert deque.steal() is None

    def test_steal_single_element(self, deque: WorkStealingDeque[int]):
        deque.push_bottom(42)
        assert deque.steal() == 42
        assert deque.is_empty()


class TestDualEndOperations:
    def test_push_steal_pop_mixed(self, deque: WorkStealingDeque[int]):
        deque.push_bottom(1)
        deque.push_bottom(2)
        deque.push_bottom(3)

        assert deque.steal() == 1

        deque.push_bottom(4)

        assert deque.pop_bottom() == 4
        assert deque.pop_bottom() == 3
        assert deque.steal() == 2

        assert deque.is_empty()

    def test_local_lifo_after_steal(self, deque: WorkStealingDeque[int]):
        deque.push_bottom("a")
        deque.push_bottom("b")
        deque.push_bottom("c")

        deque.steal()

        assert deque.pop_bottom() == "c"
        assert deque.pop_bottom() == "b"
        assert deque.pop_bottom() is None

    def test_steal_after_local_pop(self, deque: WorkStealingDeque[int]):
        deque.push_bottom(10)
        deque.push_bottom(20)
        deque.push_bottom(30)

        deque.pop_bottom()

        assert deque.steal() == 10
        assert deque.steal() == 20
        assert deque.steal() is None

    def test_alternating_steal_and_pop(self, deque: WorkStealingDeque[int]):
        for i in range(1, 7):
            deque.push_bottom(i)

        assert deque.steal() == 1
        assert deque.pop_bottom() == 6
        assert deque.steal() == 2
        assert deque.pop_bottom() == 5
        assert deque.steal() == 3
        assert deque.pop_bottom() == 4
        assert deque.is_empty()


class TestFullQueue:
    def test_push_to_full_raises(self, small_deque: WorkStealingDeque[int]):
        small_deque.push_bottom(1)
        small_deque.push_bottom(2)
        small_deque.push_bottom(3)

        with pytest.raises(QueueFullError):
            small_deque.push_bottom(4)

    def test_full_queue_error_message(self, small_deque: WorkStealingDeque[int]):
        small_deque.push_bottom(1)
        small_deque.push_bottom(2)
        small_deque.push_bottom(3)

        with pytest.raises(QueueFullError, match="full capacity"):
            small_deque.push_bottom(4)

    def test_pop_then_push_to_full(self, small_deque: WorkStealingDeque[int]):
        small_deque.push_bottom(1)
        small_deque.push_bottom(2)
        small_deque.push_bottom(3)

        small_deque.pop_bottom()
        small_deque.push_bottom(4)

        assert small_deque.size() == 3

    def test_steal_then_push_to_full(self, small_deque: WorkStealingDeque[int]):
        small_deque.push_bottom(1)
        small_deque.push_bottom(2)
        small_deque.push_bottom(3)

        small_deque.steal()
        small_deque.push_bottom(4)

        assert small_deque.size() == 3

    def test_steal_from_full_queue(self):
        dq = WorkStealingDeque[int](max_capacity=3)
        dq.push_bottom(1)
        dq.push_bottom(2)
        dq.push_bottom(3)

        assert dq.steal() == 1
        assert dq.size() == 2
        dq.push_bottom(4)
        assert dq.size() == 3


class TestSingleElement:
    def test_single_element_either_end(self, deque: WorkStealingDeque[int]):
        deque.push_bottom(42)

        assert deque.size() == 1
        assert deque.pop_bottom() == 42
        assert deque.is_empty()

    def test_single_element_steal_then_pop(self, deque: WorkStealingDeque[int]):
        deque.push_bottom("only")

        stolen = deque.steal()
        assert stolen == "only"

        popped = deque.pop_bottom()
        assert popped is None

    def test_single_element_pop_then_steal(self, deque: WorkStealingDeque[int]):
        deque.push_bottom("only")

        popped = deque.pop_bottom()
        assert popped == "only"

        stolen = deque.steal()
        assert stolen is None

    def test_push_steal_push_pop(self, deque: WorkStealingDeque[int]):
        deque.push_bottom(1)
        assert deque.steal() == 1
        assert deque.is_empty()

        deque.push_bottom(2)
        assert deque.pop_bottom() == 2
        assert deque.is_empty()


class TestConcurrency:
    def test_concurrent_push_and_steal(self, deque: WorkStealingDeque[int]):
        num_items = 100
        push_results: list[int] = []
        steal_results: list[int] = []

        def pusher():
            for i in range(num_items):
                try:
                    deque.push_bottom(i)
                    push_results.append(i)
                except QueueFullError:
                    pass

        def thief():
            for _ in range(num_items * 2):
                item = deque.steal()
                if item is not None:
                    steal_results.append(item)
                else:
                    time.sleep(0.001)

        t1 = threading.Thread(target=pusher)
        t2 = threading.Thread(target=thief)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        remaining = deque.size()
        assert len(push_results) == num_items
        assert len(steal_results) + remaining == num_items
        assert len(set(steal_results)) == len(steal_results)

    def test_single_element_race_correctness(self):
        num_trials = 200
        errors = []

        for i in range(num_trials):
            dq: WorkStealingDeque[int] = WorkStealingDeque(max_capacity=10)
            dq.push_bottom(i)

            pop_result: int | None = None
            steal_result: int | None = None

            def popper():
                nonlocal pop_result
                pop_result = dq.pop_bottom()

            def thief():
                nonlocal steal_result
                steal_result = dq.steal()

            t1 = threading.Thread(target=popper)
            t2 = threading.Thread(target=thief)

            if i % 2 == 0:
                t1.start()
                t2.start()
            else:
                t2.start()
                t1.start()

            t1.join()
            t2.join()

            both_got = pop_result is not None and steal_result is not None
            none_got = pop_result is None and steal_result is None
            if both_got:
                errors.append(f"Trial {i}: both got the element")
            if none_got and dq.size() > 0:
                errors.append(f"Trial {i}: nobody got the element but queue not empty")
            if not none_got and dq.size() != 0:
                errors.append(f"Trial {i}: element taken but queue not empty (size={dq.size()})")

        assert len(errors) == 0, f"Race condition errors: {errors[:5]}"

    def test_thief_can_win_race(self):
        thief_wins = 0
        num_trials = 100

        for i in range(num_trials):
            dq: WorkStealingDeque[int] = WorkStealingDeque(max_capacity=10)
            dq.push_bottom(i)

            steal_result: int | None = None
            pop_result: int | None = None

            def thief():
                nonlocal steal_result
                steal_result = dq.steal()

            def popper():
                nonlocal pop_result
                time.sleep(0.0001)
                pop_result = dq.pop_bottom()

            t1 = threading.Thread(target=thief)
            t2 = threading.Thread(target=popper)

            t1.start()
            t2.start()
            t1.join()
            t2.join()

            if steal_result == i:
                thief_wins += 1

        assert thief_wins > 0, f"Thief never won in {num_trials} trials"

    def test_pop_can_win_race(self):
        pop_wins = 0
        num_trials = 100

        for i in range(num_trials):
            dq: WorkStealingDeque[int] = WorkStealingDeque(max_capacity=10)
            dq.push_bottom(i)

            pop_result: int | None = None
            steal_result: int | None = None

            def popper():
                nonlocal pop_result
                pop_result = dq.pop_bottom()

            def thief():
                nonlocal steal_result
                time.sleep(0.0001)
                steal_result = dq.steal()

            t1 = threading.Thread(target=popper)
            t2 = threading.Thread(target=thief)

            t1.start()
            t2.start()
            t1.join()
            t2.join()

            if pop_result == i:
                pop_wins += 1

        assert pop_wins > 0, f"Pop never won in {num_trials} trials"

    def test_multiple_thieves(self):
        dq: WorkStealingDeque[int] = WorkStealingDeque(max_capacity=500)
        num_items = 200
        for i in range(num_items):
            dq.push_bottom(i)

        stolen_per_thief: list[list[int]] = [[], [], []]

        def thief(thief_id: int):
            while True:
                item = dq.steal()
                if item is None:
                    break
                stolen_per_thief[thief_id].append(item)

        threads = [
            threading.Thread(target=thief, args=(i,))
            for i in range(3)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        total_stolen = sum(len(items) for items in stolen_per_thief)
        assert total_stolen == num_items
        assert dq.is_empty()

        all_stolen = []
        for items in stolen_per_thief:
            all_stolen.extend(items)
        assert len(set(all_stolen)) == num_items

    def test_concurrent_push_pop_steal(self, deque: WorkStealingDeque[int]):
        num_operations = 50
        errors = []

        def local_worker():
            try:
                for i in range(num_operations):
                    deque.push_bottom(i)
                    item = deque.pop_bottom()
                    if item is None:
                        deque.push_bottom(i)
            except Exception as e:
                errors.append(e)

        def thief():
            try:
                for _ in range(num_operations):
                    deque.steal()
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=local_worker)
        t2 = threading.Thread(target=thief)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(errors) == 0
        assert deque.size() >= 0

    def test_concurrent_mixed_operations(self):
        dq: WorkStealingDeque[int] = WorkStealingDeque(max_capacity=1000)
        num_tasks = 300
        results = {"popped": [], "stolen": []}
        lock = threading.Lock()

        def pusher():
            for i in range(num_tasks):
                try:
                    dq.push_bottom(i)
                except QueueFullError:
                    pass

        def popper():
            for _ in range(num_tasks // 2):
                item = dq.pop_bottom()
                if item is not None:
                    with lock:
                        results["popped"].append(item)

        def thief():
            for _ in range(num_tasks // 2):
                item = dq.steal()
                if item is not None:
                    with lock:
                        results["stolen"].append(item)

        threads = [
            threading.Thread(target=pusher),
            threading.Thread(target=popper),
            threading.Thread(target=thief),
            threading.Thread(target=thief),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        total_processed = len(results["popped"]) + len(results["stolen"]) + dq.size()
        assert total_processed == num_tasks

        all_items = results["popped"] + results["stolen"]
        assert len(set(all_items)) == len(all_items)
