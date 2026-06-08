from __future__ import annotations

import threading
import time

import pytest

from solocoder_py.bulkhead import (
    BulkheadExecutor,
    BulkheadFullError,
    BulkheadQueueTimeoutError,
    FullStrategy,
    GroupAlreadyExistsError,
    GroupConfig,
    GroupNotFoundError,
    GroupStats,
    InvalidConfigError,
    ManualClock,
    TaskResult,
    TaskStatus,
)


def _make_config(
    name: str = "test_group",
    max_concurrency: int = 2,
    full_strategy: FullStrategy = FullStrategy.QUEUE,
    queue_timeout: float = 1.0,
    max_queue_size: int = 0,
) -> GroupConfig:
    return GroupConfig(
        name=name,
        max_concurrency=max_concurrency,
        full_strategy=full_strategy,
        queue_timeout=queue_timeout,
        max_queue_size=max_queue_size,
    )


def _make_executor(clock: ManualClock | None = None) -> BulkheadExecutor:
    return BulkheadExecutor(clock=clock)


def _success_func(value: int = 42) -> int:
    return value


def _sleep_func(seconds: float, clock: ManualClock | None = None) -> str:
    if clock is not None:
        clock.advance(seconds)
    else:
        time.sleep(seconds)
    return "done"


def _failure_func() -> None:
    raise RuntimeError("boom")


class TestGroupConfigValidation:
    def test_empty_name_rejected(self):
        with pytest.raises(InvalidConfigError, match="group name must not be empty"):
            _make_config(name="")

    def test_zero_concurrency_rejected(self):
        with pytest.raises(InvalidConfigError, match="max_concurrency must be positive"):
            _make_config(max_concurrency=0)

    def test_negative_concurrency_rejected(self):
        with pytest.raises(InvalidConfigError, match="max_concurrency must be positive"):
            _make_config(max_concurrency=-1)

    def test_negative_queue_timeout_rejected(self):
        with pytest.raises(InvalidConfigError, match="queue_timeout must be non-negative"):
            _make_config(queue_timeout=-1.0, full_strategy=FullStrategy.QUEUE)

    def test_zero_queue_timeout_allowed(self):
        config = _make_config(queue_timeout=0.0, full_strategy=FullStrategy.QUEUE)
        assert config.queue_timeout == 0.0

    def test_negative_max_queue_size_rejected(self):
        with pytest.raises(InvalidConfigError, match="max_queue_size must be non-negative"):
            _make_config(max_queue_size=-1)


class TestGroupManagement:
    def test_create_group(self):
        executor = _make_executor()
        config = _make_config()
        executor.create_group(config)
        assert executor.has_group("test_group") is True

    def test_create_duplicate_group_raises(self):
        executor = _make_executor()
        config = _make_config()
        executor.create_group(config)
        with pytest.raises(GroupAlreadyExistsError, match="already exists"):
            executor.create_group(config)

    def test_remove_group(self):
        executor = _make_executor()
        config = _make_config()
        executor.create_group(config)
        executor.remove_group("test_group")
        assert executor.has_group("test_group") is False

    def test_remove_nonexistent_group_raises(self):
        executor = _make_executor()
        with pytest.raises(GroupNotFoundError, match="not found"):
            executor.remove_group("nonexistent")

    def test_submit_to_nonexistent_group_raises(self):
        executor = _make_executor()
        with pytest.raises(GroupNotFoundError, match="not found"):
            executor.submit("nonexistent", lambda: None)

    def test_get_stats_nonexistent_group_raises(self):
        executor = _make_executor()
        with pytest.raises(GroupNotFoundError, match="not found"):
            executor.get_group_stats("nonexistent")

    def test_update_group_config(self):
        executor = _make_executor()
        config = _make_config(max_concurrency=2)
        executor.create_group(config)
        new_config = _make_config(max_concurrency=5)
        executor.update_group_config(new_config)
        stats = executor.get_group_stats("test_group")
        assert stats.max_concurrency == 5

    def test_update_nonexistent_group_config_raises(self):
        executor = _make_executor()
        config = _make_config()
        with pytest.raises(GroupNotFoundError, match="not found"):
            executor.update_group_config(config)


class TestNormalFlow:
    def test_single_task_success(self):
        executor = _make_executor()
        executor.create_group(_make_config(max_concurrency=1))
        result = executor.submit("test_group", _success_func, 99)
        assert result.status == TaskStatus.SUCCESS
        assert result.result == 99
        assert isinstance(result, TaskResult)

    def test_task_with_kwargs(self):
        executor = _make_executor()
        executor.create_group(_make_config(max_concurrency=1))
        result = executor.submit("test_group", _success_func, value=123)
        assert result.status == TaskStatus.SUCCESS
        assert result.result == 123

    def test_multiple_groups_independent_concurrency(self):
        executor = _make_executor()
        executor.create_group(_make_config(name="group_a", max_concurrency=1))
        executor.create_group(_make_config(name="group_b", max_concurrency=1))

        barrier = threading.Barrier(2)

        def blocked_task() -> str:
            barrier.wait()
            return "ok"

        results: list[TaskResult] = []

        def run_task(group: str) -> None:
            results.append(executor.submit(group, blocked_task))

        t1 = threading.Thread(target=run_task, args=("group_a",))
        t2 = threading.Thread(target=run_task, args=("group_b",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(results) == 2
        for r in results:
            assert r.status == TaskStatus.SUCCESS
            assert r.result == "ok"

    def test_concurrency_slot_released_after_success(self):
        executor = _make_executor()
        executor.create_group(_make_config(max_concurrency=1))

        r1 = executor.submit("test_group", _success_func, 1)
        assert r1.status == TaskStatus.SUCCESS

        stats = executor.get_group_stats("test_group")
        assert stats.current_concurrency == 0
        assert stats.success_count == 1

        r2 = executor.submit("test_group", _success_func, 2)
        assert r2.status == TaskStatus.SUCCESS
        assert r2.result == 2

    def test_concurrency_slot_released_after_failure(self):
        executor = _make_executor()
        executor.create_group(_make_config(max_concurrency=1))

        r1 = executor.submit("test_group", _failure_func)
        assert r1.status == TaskStatus.FAILED
        assert isinstance(r1.exception, RuntimeError)

        stats = executor.get_group_stats("test_group")
        assert stats.current_concurrency == 0
        assert stats.failure_count == 1
        assert stats.success_count == 0

        r2 = executor.submit("test_group", _success_func, 42)
        assert r2.status == TaskStatus.SUCCESS

    def test_custom_task_id(self):
        executor = _make_executor()
        executor.create_group(_make_config())
        result = executor.submit("test_group", _success_func, task_id="custom-id-123")
        assert result.task_id == "custom-id-123"

    def test_auto_generated_task_id(self):
        executor = _make_executor()
        executor.create_group(_make_config())
        result = executor.submit("test_group", _success_func)
        assert result.task_id is not None
        assert len(result.task_id) > 0


class TestConcurrencyLimits:
    def test_max_concurrency_respected(self):
        executor = _make_executor()
        executor.create_group(_make_config(max_concurrency=2))
        start_events = [threading.Event() for _ in range(2)]
        continue_event = threading.Event()
        results: list[TaskResult] = []
        lock = threading.Lock()

        def make_task(idx: int):
            def _task() -> str:
                start_events[idx].set()
                continue_event.wait()
                return "done"
            return _task

        def run(idx: int) -> None:
            r = executor.submit("test_group", make_task(idx))
            with lock:
                results.append(r)

        threads = [threading.Thread(target=run, args=(i,)) for i in range(2)]
        for t in threads:
            t.start()
        for ev in start_events:
            ev.wait()

        stats = executor.get_group_stats("test_group")
        assert stats.current_concurrency == 2

        continue_event.set()
        for t in threads:
            t.join()

        assert len(results) == 2
        for r in results:
            assert r.status == TaskStatus.SUCCESS

        stats_after = executor.get_group_stats("test_group")
        assert stats_after.current_concurrency == 0
        assert stats_after.success_count == 2

    def test_exactly_at_concurrency_then_release(self):
        executor = _make_executor()
        executor.create_group(_make_config(max_concurrency=2, full_strategy=FullStrategy.QUEUE))
        start_events = [threading.Event() for _ in range(2)]
        continue_event = threading.Event()
        results: list[TaskResult] = []

        def make_first(idx: int):
            def _first_task() -> str:
                start_events[idx].set()
                continue_event.wait()
                return "first"
            return _first_task

        def second_task() -> str:
            return "second"

        t1 = threading.Thread(target=lambda: results.append(executor.submit("test_group", make_first(0))))
        t2 = threading.Thread(target=lambda: results.append(executor.submit("test_group", make_first(1))))
        t1.start()
        t2.start()
        for ev in start_events:
            ev.wait()

        stats = executor.get_group_stats("test_group")
        assert stats.current_concurrency == 2

        continue_event.set()
        t1.join()
        t2.join()

        stats_after = executor.get_group_stats("test_group")
        assert stats_after.current_concurrency == 0

        r3 = executor.submit("test_group", second_task)
        assert r3.status == TaskStatus.SUCCESS
        assert r3.result == "second"


class TestRejectStrategy:
    def test_reject_when_full(self):
        executor = _make_executor()
        executor.create_group(_make_config(max_concurrency=1, full_strategy=FullStrategy.REJECT))
        start_event = threading.Event()
        continue_event = threading.Event()
        result1_holder: list[TaskResult] = []

        def blocking_task() -> str:
            start_event.set()
            continue_event.wait()
            return "blocked"

        t = threading.Thread(target=lambda: result1_holder.append(executor.submit("test_group", blocking_task)))
        t.start()
        start_event.wait()

        stats = executor.get_group_stats("test_group")
        assert stats.current_concurrency == 1

        r2 = executor.submit("test_group", _success_func)
        assert r2.status == TaskStatus.REJECTED
        assert isinstance(r2.exception, BulkheadFullError)
        assert r2.exception.task_id == r2.task_id
        assert r2.exception.group_name == "test_group"

        continue_event.set()
        t.join()

        assert result1_holder[0].status == TaskStatus.SUCCESS

    def test_reject_with_max_queue_size(self):
        executor = _make_executor()
        executor.create_group(
            _make_config(
                max_concurrency=1,
                full_strategy=FullStrategy.QUEUE,
                max_queue_size=1,
            )
        )
        start_event = threading.Event()
        continue_event = threading.Event()
        result1_holder: list[TaskResult] = []

        def blocking_task() -> str:
            start_event.set()
            continue_event.wait()
            return "blocked"

        t = threading.Thread(target=lambda: result1_holder.append(executor.submit("test_group", blocking_task)))
        t.start()
        start_event.wait()

        queued_holder: list[TaskResult] = []

        def queued_task() -> str:
            return "queued"

        t_queued = threading.Thread(
            target=lambda: queued_holder.append(executor.submit("test_group", queued_task))
        )
        t_queued.start()
        time.sleep(0.05)

        stats = executor.get_group_stats("test_group")
        assert stats.current_concurrency == 1
        assert stats.queue_size == 1

        r3 = executor.submit("test_group", _success_func)
        assert r3.status == TaskStatus.REJECTED
        assert isinstance(r3.exception, BulkheadFullError)

        continue_event.set()
        t.join()
        t_queued.join()

        assert result1_holder[0].status == TaskStatus.SUCCESS
        assert queued_holder[0].status == TaskStatus.SUCCESS


class TestQueueAndTimeout:
    def test_queue_wait_then_execute(self):
        executor = _make_executor()
        executor.create_group(
            _make_config(
                max_concurrency=1,
                full_strategy=FullStrategy.QUEUE,
                queue_timeout=5.0,
            )
        )
        start_event = threading.Event()
        continue_event = threading.Event()
        result1_holder: list[TaskResult] = []

        def blocking_task() -> str:
            start_event.set()
            continue_event.wait()
            return "first"

        t1 = threading.Thread(target=lambda: result1_holder.append(executor.submit("test_group", blocking_task)))
        t1.start()
        start_event.wait()

        stats = executor.get_group_stats("test_group")
        assert stats.current_concurrency == 1

        result2_holder: list[TaskResult] = []

        def waiting_task() -> str:
            return "second"

        t2 = threading.Thread(target=lambda: result2_holder.append(executor.submit("test_group", waiting_task)))
        t2.start()
        time.sleep(0.05)

        stats_queued = executor.get_group_stats("test_group")
        assert stats_queued.queue_size == 1

        continue_event.set()
        t1.join()
        t2.join()

        assert result1_holder[0].status == TaskStatus.SUCCESS
        assert result2_holder[0].status == TaskStatus.SUCCESS
        assert result2_holder[0].result == "second"
        assert result2_holder[0].queue_wait_time >= 0

        stats_final = executor.get_group_stats("test_group")
        assert stats_final.queue_size == 0
        assert stats_final.current_concurrency == 0

    def test_queue_timeout(self):
        clock = ManualClock()
        executor = _make_executor(clock=clock)
        executor.create_group(
            _make_config(
                max_concurrency=1,
                full_strategy=FullStrategy.QUEUE,
                queue_timeout=1.0,
            )
        )
        result1_holder: list[TaskResult] = []
        start_event = threading.Event()
        continue_event = threading.Event()

        def blocking_task() -> str:
            start_event.set()
            continue_event.wait()
            return "blocked"

        t1 = threading.Thread(target=lambda: result1_holder.append(executor.submit("test_group", blocking_task)))
        t1.start()
        start_event.wait()

        result2_holder: list[TaskResult] = []

        def timed_out_task() -> str:
            return "timeout"

        def submit_timeout_task() -> None:
            result2_holder.append(executor.submit("test_group", timed_out_task))

        t2 = threading.Thread(target=submit_timeout_task)
        t2.start()
        time.sleep(0.05)

        stats = executor.get_group_stats("test_group")
        assert stats.queue_size == 1

        clock.advance(2.0)

        t2.join(timeout=5.0)
        assert not t2.is_alive()

        assert len(result2_holder) == 1
        r2 = result2_holder[0]
        assert r2.status == TaskStatus.QUEUE_TIMEOUT
        assert isinstance(r2.exception, BulkheadQueueTimeoutError)
        assert r2.exception.task_id == r2.task_id
        assert r2.exception.group_name == "test_group"

        continue_event.set()
        t1.join()

        assert result1_holder[0].status == TaskStatus.SUCCESS

    def test_fifo_queue_order(self):
        executor = _make_executor()
        executor.create_group(
            _make_config(
                max_concurrency=1,
                full_strategy=FullStrategy.QUEUE,
                queue_timeout=10.0,
            )
        )
        start_event = threading.Event()
        continue_event = threading.Event()
        result1_holder: list[TaskResult] = []
        execution_order: list[int] = []
        lock = threading.Lock()

        def first_task() -> str:
            start_event.set()
            continue_event.wait()
            with lock:
                execution_order.append(1)
            return "first"

        t1 = threading.Thread(target=lambda: result1_holder.append(executor.submit("test_group", first_task)))
        t1.start()
        start_event.wait()

        results: list[TaskResult] = []

        def make_task(n: int):
            def _task() -> int:
                with lock:
                    execution_order.append(n)
                return n
            return _task

        def submit_task(n: int) -> None:
            results.append(executor.submit("test_group", make_task(n)))

        threads = [threading.Thread(target=submit_task, args=(i,)) for i in range(2, 5)]
        for t in threads:
            t.start()
            time.sleep(0.02)

        time.sleep(0.05)
        continue_event.set()
        t1.join()
        for t in threads:
            t.join()

        assert execution_order == [1, 2, 3, 4]
        for r in results:
            assert r.status == TaskStatus.SUCCESS


class TestFaultIsolation:
    def test_one_group_failure_does_not_affect_other(self):
        executor = _make_executor()
        executor.create_group(_make_config(name="bad_group", max_concurrency=2))
        executor.create_group(_make_config(name="good_group", max_concurrency=2))

        for _ in range(5):
            executor.submit("bad_group", _failure_func)

        bad_stats = executor.get_group_stats("bad_group")
        assert bad_stats.failure_count == 5
        assert bad_stats.success_count == 0

        for i in range(3):
            result = executor.submit("good_group", _success_func, i)
            assert result.status == TaskStatus.SUCCESS
            assert result.result == i

        good_stats = executor.get_group_stats("good_group")
        assert good_stats.success_count == 3
        assert good_stats.failure_count == 0
        assert good_stats.current_concurrency == 0

    def test_failure_does_not_block_concurrency_slots(self):
        executor = _make_executor()
        executor.create_group(_make_config(max_concurrency=1))

        for i in range(5):
            if i % 2 == 0:
                result = executor.submit("test_group", _failure_func)
                assert result.status == TaskStatus.FAILED
            else:
                result = executor.submit("test_group", _success_func, i)
                assert result.status == TaskStatus.SUCCESS
                assert result.result == i

        stats = executor.get_group_stats("test_group")
        assert stats.current_concurrency == 0
        assert stats.success_count == 2
        assert stats.failure_count == 3

    def test_exception_propagation_via_result(self):
        executor = _make_executor()
        executor.create_group(_make_config(max_concurrency=1))

        def specific_error() -> None:
            raise ValueError("specific message")

        result = executor.submit("test_group", specific_error)
        assert result.status == TaskStatus.FAILED
        assert isinstance(result.exception, ValueError)
        assert str(result.exception) == "specific message"


class TestAcquireContextManager:
    def test_acquire_success(self):
        executor = _make_executor()
        executor.create_group(_make_config(max_concurrency=1))

        with executor.acquire("test_group"):
            stats = executor.get_group_stats("test_group")
            assert stats.current_concurrency == 1

        stats_after = executor.get_group_stats("test_group")
        assert stats_after.current_concurrency == 0

    def test_acquire_rejected(self):
        executor = _make_executor()
        executor.create_group(_make_config(max_concurrency=1, full_strategy=FullStrategy.REJECT))
        start_event = threading.Event()
        continue_event = threading.Event()

        def holder() -> None:
            with executor.acquire("test_group"):
                start_event.set()
                continue_event.wait()

        t = threading.Thread(target=holder)
        t.start()
        start_event.wait()

        with pytest.raises(BulkheadFullError):
            with executor.acquire("test_group"):
                pass

        continue_event.set()
        t.join()

    def test_acquire_releases_on_exception(self):
        executor = _make_executor()
        executor.create_group(_make_config(max_concurrency=1))

        with pytest.raises(RuntimeError):
            with executor.acquire("test_group"):
                stats = executor.get_group_stats("test_group")
                assert stats.current_concurrency == 1
                raise RuntimeError("test")

        stats_after = executor.get_group_stats("test_group")
        assert stats_after.current_concurrency == 0

    def test_acquire_custom_task_id(self):
        executor = _make_executor()
        executor.create_group(_make_config(max_concurrency=1, full_strategy=FullStrategy.REJECT))
        start_event = threading.Event()
        continue_event = threading.Event()

        def holder() -> None:
            with executor.acquire("test_group"):
                start_event.set()
                continue_event.wait()

        t = threading.Thread(target=holder)
        t.start()
        start_event.wait()

        try:
            with pytest.raises(BulkheadFullError) as exc_info:
                with executor.acquire("test_group", task_id="my-task"):
                    pass
        finally:
            continue_event.set()
            t.join()

        assert exc_info.value.task_id == "my-task"
        assert exc_info.value.group_name == "test_group"


class TestStatsAndStatus:
    def test_initial_stats(self):
        executor = _make_executor()
        executor.create_group(
            _make_config(
                name="stat_test",
                max_concurrency=3,
                full_strategy=FullStrategy.QUEUE,
                queue_timeout=5.0,
                max_queue_size=10,
            )
        )
        stats = executor.get_group_stats("stat_test")
        assert isinstance(stats, GroupStats)
        assert stats.name == "stat_test"
        assert stats.max_concurrency == 3
        assert stats.current_concurrency == 0
        assert stats.queue_size == 0
        assert stats.success_count == 0
        assert stats.failure_count == 0
        assert stats.full_strategy == FullStrategy.QUEUE
        assert stats.queue_timeout == 5.0
        assert stats.max_queue_size == 10

    def test_stats_updated_after_tasks(self):
        executor = _make_executor()
        executor.create_group(_make_config(max_concurrency=2))

        executor.submit("test_group", _success_func)
        executor.submit("test_group", _failure_func)
        executor.submit("test_group", _success_func)

        stats = executor.get_group_stats("test_group")
        assert stats.success_count == 2
        assert stats.failure_count == 1
        assert stats.current_concurrency == 0

    def test_get_all_group_stats(self):
        executor = _make_executor()
        executor.create_group(_make_config(name="g1", max_concurrency=1))
        executor.create_group(_make_config(name="g2", max_concurrency=2, full_strategy=FullStrategy.REJECT))

        executor.submit("g1", _success_func)
        executor.submit("g2", _failure_func)

        all_stats = executor.get_all_group_stats()
        assert "g1" in all_stats
        assert "g2" in all_stats
        assert all_stats["g1"].success_count == 1
        assert all_stats["g2"].failure_count == 1
        assert all_stats["g2"].full_strategy == FullStrategy.REJECT

    def test_strategy_switch_via_update_config(self):
        executor = _make_executor()
        executor.create_group(_make_config(max_concurrency=1, full_strategy=FullStrategy.QUEUE))

        stats_before = executor.get_group_stats("test_group")
        assert stats_before.full_strategy == FullStrategy.QUEUE

        new_config = _make_config(max_concurrency=1, full_strategy=FullStrategy.REJECT)
        executor.update_group_config(new_config)

        stats_after = executor.get_group_stats("test_group")
        assert stats_after.full_strategy == FullStrategy.REJECT


class TestThreadSafety:
    def test_concurrent_submissions_multiple_groups(self):
        executor = _make_executor()
        executor.create_group(_make_config(name="a", max_concurrency=5))
        executor.create_group(_make_config(name="b", max_concurrency=5))

        results: list[TaskResult] = []
        lock = threading.Lock()

        def do_work(group: str, n: int) -> None:
            r = executor.submit(group, _success_func, n)
            with lock:
                results.append(r)

        threads = []
        for i in range(20):
            group = "a" if i % 2 == 0 else "b"
            t = threading.Thread(target=do_work, args=(group, i))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 20
        for r in results:
            assert r.status == TaskStatus.SUCCESS

        stats_a = executor.get_group_stats("a")
        stats_b = executor.get_group_stats("b")
        assert stats_a.success_count + stats_b.success_count == 20
        assert stats_a.current_concurrency == 0
        assert stats_b.current_concurrency == 0


class TestClock:
    def test_system_clock_advances(self):
        from solocoder_py.bulkhead import SystemClock

        clock = SystemClock()
        t1 = clock.now()
        time.sleep(0.01)
        t2 = clock.now()
        assert t2 >= t1

    def test_manual_clock_advance(self):
        clock = ManualClock(start_time=10.0)
        assert clock.now() == 10.0
        clock.advance(5.0)
        assert clock.now() == 15.0

    def test_manual_clock_set(self):
        clock = ManualClock()
        clock.set(42.0)
        assert clock.now() == 42.0

    def test_manual_clock_negative_advance_rejected(self):
        clock = ManualClock()
        with pytest.raises(ValueError, match="Cannot advance by negative"):
            clock.advance(-1.0)


class TestTaskIdKwargsConflict:
    def test_submit_user_func_task_id_via_positional_arg(self):
        executor = _make_executor()
        executor.create_group(_make_config(max_concurrency=1))

        captured: dict = {}

        def func_with_task_id(task_id: str, value: int) -> tuple:
            captured["task_id"] = task_id
            captured["value"] = value
            return (task_id, value)

        result = executor.submit(
            "test_group",
            func_with_task_id,
            "user-expected-id",
            value=99,
        )

        assert result.status == TaskStatus.SUCCESS
        assert captured["task_id"] == "user-expected-id"
        assert captured["value"] == 99
        assert result.task_id != "user-expected-id"
        assert result.result == ("user-expected-id", 99)

    def test_submit_framework_task_id_is_keyword_only(self):
        executor = _make_executor()
        executor.create_group(_make_config(max_concurrency=1))

        captured: dict = {}

        def func_no_task_id(value: int) -> int:
            captured["value"] = value
            return value

        result = executor.submit(
            "test_group",
            func_no_task_id,
            99,
            task_id="my-framework-task-id",
        )

        assert result.status == TaskStatus.SUCCESS
        assert result.task_id == "my-framework-task-id"
        assert captured["value"] == 99
        assert result.result == 99

    def test_submit_auto_task_id_not_leaked_to_user_kwargs(self):
        executor = _make_executor()
        executor.create_group(_make_config(max_concurrency=1))

        captured_kwargs: dict = {}

        def func_capture_kwargs(**kwargs) -> dict:
            captured_kwargs.update(kwargs)
            return kwargs

        result = executor.submit("test_group", func_capture_kwargs, x=1, y=2)

        assert result.status == TaskStatus.SUCCESS
        assert "task_id" not in captured_kwargs
        assert captured_kwargs == {"x": 1, "y": 2}
        assert result.task_id is not None


class TestAcquireQueueStrategy:
    def test_acquire_queue_then_get_slot(self):
        executor = _make_executor()
        executor.create_group(
            _make_config(
                max_concurrency=1,
                full_strategy=FullStrategy.QUEUE,
                queue_timeout=5.0,
            )
        )
        start_event = threading.Event()
        continue_event = threading.Event()

        def holder() -> None:
            with executor.acquire("test_group"):
                start_event.set()
                continue_event.wait()

        t1 = threading.Thread(target=holder)
        t1.start()
        start_event.wait()

        stats = executor.get_group_stats("test_group")
        assert stats.current_concurrency == 1
        assert stats.queue_size == 0

        acquire_result_holder: list = []

        def waiting_acquirer() -> None:
            try:
                with executor.acquire("test_group"):
                    stats_inside = executor.get_group_stats("test_group")
                    acquire_result_holder.append(("ok", stats_inside.current_concurrency))
            except Exception as e:
                acquire_result_holder.append(("error", e))

        t2 = threading.Thread(target=waiting_acquirer)
        t2.start()
        time.sleep(0.05)

        stats_with_waiter = executor.get_group_stats("test_group")
        assert stats_with_waiter.queue_size == 1

        continue_event.set()
        t1.join()
        t2.join()

        assert len(acquire_result_holder) == 1
        assert acquire_result_holder[0][0] == "ok"
        assert acquire_result_holder[0][1] == 1

        stats_final = executor.get_group_stats("test_group")
        assert stats_final.current_concurrency == 0
        assert stats_final.queue_size == 0

    def test_acquire_queue_timeout(self):
        clock = ManualClock()
        executor = _make_executor(clock=clock)
        executor.create_group(
            _make_config(
                max_concurrency=1,
                full_strategy=FullStrategy.QUEUE,
                queue_timeout=1.0,
            )
        )
        start_event = threading.Event()
        continue_event = threading.Event()

        def holder() -> None:
            with executor.acquire("test_group"):
                start_event.set()
                continue_event.wait()

        t1 = threading.Thread(target=holder)
        t1.start()
        start_event.wait()

        error_holder: list = []

        def timed_out_acquirer() -> None:
            try:
                with executor.acquire("test_group"):
                    pass
            except Exception as e:
                error_holder.append(e)

        t2 = threading.Thread(target=timed_out_acquirer)
        t2.start()
        time.sleep(0.05)

        stats_with_waiter = executor.get_group_stats("test_group")
        assert stats_with_waiter.queue_size == 1

        clock.advance(2.0)
        t2.join(timeout=5.0)
        assert not t2.is_alive()

        assert len(error_holder) == 1
        assert isinstance(error_holder[0], BulkheadQueueTimeoutError)
        assert error_holder[0].group_name == "test_group"

        stats_final = executor.get_group_stats("test_group")
        assert stats_final.queue_size == 0

        continue_event.set()
        t1.join()

    def test_acquire_queue_respects_max_queue_size(self):
        executor = _make_executor()
        executor.create_group(
            _make_config(
                max_concurrency=1,
                full_strategy=FullStrategy.QUEUE,
                max_queue_size=1,
                queue_timeout=10.0,
            )
        )
        start_event = threading.Event()
        continue_event = threading.Event()

        def holder() -> None:
            with executor.acquire("test_group"):
                start_event.set()
                continue_event.wait()

        t1 = threading.Thread(target=holder)
        t1.start()
        start_event.wait()

        queued_result: list = []

        def queued_acquirer() -> None:
            try:
                with executor.acquire("test_group"):
                    queued_result.append("ok")
            except Exception as e:
                queued_result.append(("error", e))

        t2 = threading.Thread(target=queued_acquirer)
        t2.start()
        time.sleep(0.05)

        stats = executor.get_group_stats("test_group")
        assert stats.current_concurrency == 1
        assert stats.queue_size == 1

        rejected_error: list = []
        try:
            with executor.acquire("test_group"):
                pass
        except Exception as e:
            rejected_error.append(e)

        assert len(rejected_error) == 1
        assert isinstance(rejected_error[0], BulkheadFullError)
        assert "queue is full" in str(rejected_error[0])

        continue_event.set()
        t1.join()
        t2.join()

        assert queued_result[0] == "ok"
