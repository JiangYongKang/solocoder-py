import pytest

from solocoder_py.priority_threadpool import (
    InvalidConfigError,
    Priority,
    PriorityThreadPool,
    TaskNotFoundError,
    TaskStatus,
    ThreadPoolConfig,
    ThreadPoolShutdownError,
    ThreadPoolState,
)


class TestThreadPoolConfig:
    def test_valid_config(self):
        config = ThreadPoolConfig(max_concurrency=4)
        assert config.max_concurrency == 4
        assert config.aging_threshold == 10.0
        assert config.aging_check_interval == 1.0

    def test_zero_concurrency_raises_error(self):
        with pytest.raises(InvalidConfigError):
            ThreadPoolConfig(max_concurrency=0)

    def test_negative_concurrency_raises_error(self):
        with pytest.raises(InvalidConfigError):
            ThreadPoolConfig(max_concurrency=-1)

    def test_negative_aging_threshold_raises_error(self):
        with pytest.raises(InvalidConfigError):
            ThreadPoolConfig(max_concurrency=2, aging_threshold=-1)

    def test_zero_aging_check_interval_raises_error(self):
        with pytest.raises(InvalidConfigError):
            ThreadPoolConfig(max_concurrency=2, aging_check_interval=0)


class TestPriorityScheduling:
    def test_high_priority_executes_before_low(self, make_pool, manual_clock):
        pool = make_pool(max_concurrency=1)
        execution_order = []

        def make_task(name):
            def task():
                execution_order.append(name)
                return name
            return task

        low_id = pool.submit(make_task("low"), priority=Priority.LOW, task_id="low")
        high_id = pool.submit(make_task("high"), priority=Priority.HIGH, task_id="high")

        pool.run_until_complete()

        assert execution_order[0] == "high"
        assert execution_order[1] == "low"

        low_result = pool.get_task_result(low_id)
        high_result = pool.get_task_result(high_id)
        assert low_result.status == TaskStatus.SUCCESS
        assert high_result.status == TaskStatus.SUCCESS
        assert high_result.result == "high"
        assert low_result.result == "low"

    def test_medium_priority_between_high_and_low(self, make_pool, manual_clock):
        pool = make_pool(max_concurrency=1)
        execution_order = []

        def make_task(name):
            def task():
                execution_order.append(name)
            return task

        pool.submit(make_task("low"), priority=Priority.LOW, task_id="low")
        pool.submit(make_task("high"), priority=Priority.HIGH, task_id="high")
        pool.submit(make_task("medium"), priority=Priority.MEDIUM, task_id="medium")

        pool.run_until_complete()

        assert execution_order == ["high", "medium", "low"]

    def test_all_same_priority_fifo_order(self, make_pool, manual_clock):
        pool = make_pool(max_concurrency=1)
        execution_order = []

        def make_task(name):
            def task():
                execution_order.append(name)
            return task

        for i in range(5):
            pool.submit(make_task(f"task{i}"), priority=Priority.MEDIUM, task_id=f"task{i}")

        pool.run_until_complete()

        assert execution_order == ["task0", "task1", "task2", "task3", "task4"]

    def test_multiple_priorities_fifo_within_same_priority(self, make_pool, manual_clock):
        pool = make_pool(max_concurrency=1)
        execution_order = []

        def make_task(name):
            def task():
                execution_order.append(name)
            return task

        pool.submit(make_task("low1"), priority=Priority.LOW, task_id="low1")
        pool.submit(make_task("high1"), priority=Priority.HIGH, task_id="high1")
        pool.submit(make_task("high2"), priority=Priority.HIGH, task_id="high2")
        pool.submit(make_task("low2"), priority=Priority.LOW, task_id="low2")
        pool.submit(make_task("medium1"), priority=Priority.MEDIUM, task_id="medium1")

        pool.run_until_complete()

        assert execution_order == ["high1", "high2", "medium1", "low1", "low2"]


class TestConcurrencyControl:
    def test_max_concurrency_respected(self, make_pool, manual_clock):
        pool = make_pool(max_concurrency=2)
        max_seen = [0]
        current = [0]

        def task():
            current[0] += 1
            if current[0] > max_seen[0]:
                max_seen[0] = current[0]
            current[0] -= 1

        for i in range(10):
            pool.submit(task, task_id=f"task{i}")

        pool.run_until_complete()

        assert max_seen[0] <= 2
        stats = pool.get_stats()
        assert stats.total_completed == 10
        assert stats.total_submitted == 10

    def test_single_concurrency(self, make_pool, manual_clock):
        pool = make_pool(max_concurrency=1)
        max_seen = [0]
        current = [0]

        def task():
            current[0] += 1
            if current[0] > max_seen[0]:
                max_seen[0] = current[0]
            current[0] -= 1

        for i in range(5):
            pool.submit(task, task_id=f"task{i}")

        pool.run_until_complete()

        assert max_seen[0] == 1

    def test_queue_when_concurrency_full(self, make_pool, manual_clock):
        pool = make_pool(max_concurrency=2)

        def task():
            pass

        for i in range(10):
            pool.submit(task, task_id=f"task{i}", duration=10.0)

        pool.tick()
        stats = pool.get_stats()
        assert stats.current_concurrency == 2
        assert stats.high_queue_size + stats.medium_queue_size + stats.low_queue_size == 8


class TestAgingPromotion:
    def test_low_priority_promoted_to_medium(self, make_pool, manual_clock):
        pool = make_pool(max_concurrency=1, aging_threshold=5.0, aging_check_interval=1.0)

        def blocking_task():
            pass

        def waiting_task():
            pass

        blocker_id = pool.submit(blocking_task, priority=Priority.HIGH, task_id="blocker", duration=100.0)
        low_id = pool.submit(waiting_task, priority=Priority.LOW, task_id="low_task")

        manual_clock.advance(2.0)
        pool.tick()
        stats = pool.get_stats()
        assert stats.low_queue_size == 1

        manual_clock.advance(4.0)
        pool.tick()
        stats = pool.get_stats()
        assert stats.medium_queue_size == 1
        assert stats.low_queue_size == 0

        result = pool.get_task_result(low_id)
        assert result.original_priority == Priority.LOW
        assert result.priority == Priority.MEDIUM
        assert result.priority_boost_count == 1

    def test_medium_priority_promoted_to_high(self, make_pool, manual_clock):
        pool = make_pool(max_concurrency=1, aging_threshold=5.0, aging_check_interval=1.0)

        def blocking_task():
            pass

        def waiting_task():
            pass

        pool.submit(blocking_task, priority=Priority.HIGH, task_id="blocker", duration=100.0)
        med_id = pool.submit(waiting_task, priority=Priority.MEDIUM, task_id="med_task")

        manual_clock.advance(6.0)
        pool.tick()
        stats = pool.get_stats()
        assert stats.high_queue_size == 1
        assert stats.medium_queue_size == 0

        result = pool.get_task_result(med_id)
        assert result.original_priority == Priority.MEDIUM
        assert result.priority == Priority.HIGH
        assert result.priority_boost_count == 1

    def test_aging_boundary_exact_threshold(self, make_pool, manual_clock):
        pool = make_pool(max_concurrency=1, aging_threshold=5.0, aging_check_interval=0.1)

        def blocking_task():
            pass

        def waiting_task():
            pass

        pool.submit(blocking_task, priority=Priority.HIGH, task_id="blocker", duration=100.0)
        low_id = pool.submit(waiting_task, priority=Priority.LOW, task_id="low_task")

        manual_clock.advance(4.9)
        pool.tick()
        stats = pool.get_stats()
        assert stats.low_queue_size == 1
        assert stats.medium_queue_size == 0

        manual_clock.advance(0.2)
        pool.tick()
        stats = pool.get_stats()
        assert stats.low_queue_size == 0
        assert stats.medium_queue_size == 1

    def test_promoted_task_executes_before_new_high_priority(self, make_pool, manual_clock):
        pool = make_pool(max_concurrency=1, aging_threshold=5.0, aging_check_interval=1.0)
        execution_order = []

        def make_task(name):
            def task():
                execution_order.append(name)
            return task

        blocker_id = pool.submit(make_task("blocker"), priority=Priority.HIGH, task_id="blocker", duration=100.0)
        aged_low_id = pool.submit(make_task("aged_low"), priority=Priority.LOW, task_id="aged_low")

        manual_clock.advance(10.0)
        pool.tick()

        aged_result = pool.get_task_result(aged_low_id)
        assert aged_result.priority_boost_count >= 1
        assert aged_result.priority == Priority.HIGH or aged_result.priority == Priority.MEDIUM

        new_high_id = pool.submit(make_task("new_high"), priority=Priority.HIGH, task_id="new_high")

        manual_clock.advance(100.0)
        pool.tick()
        pool.run_until_complete()

        assert execution_order[0] == "blocker"
        assert execution_order[1] == "aged_low"
        assert execution_order[2] == "new_high"


class TestGracefulShutdown:
    def test_empty_pool_shutdown(self, make_pool):
        pool = make_pool(max_concurrency=2)
        assert pool.state == ThreadPoolState.RUNNING

        pool.shutdown(wait=True)

        assert pool.state == ThreadPoolState.TERMINATED

    def test_shutdown_completes_all_pending_tasks(self, make_pool, manual_clock):
        pool = make_pool(max_concurrency=2)
        completed = []

        def make_task(name):
            def task():
                completed.append(name)
                return name
            return task

        for i in range(5):
            pool.submit(make_task(f"task{i}"), priority=Priority.MEDIUM, task_id=f"task{i}", duration=1.0)

        assert pool.state == ThreadPoolState.RUNNING

        pool.shutdown(wait=True)

        assert pool.state == ThreadPoolState.TERMINATED
        assert len(completed) == 5
        for i in range(5):
            result = pool.get_task_result(f"task{i}")
            assert result.status == TaskStatus.SUCCESS
            assert result.result == f"task{i}"

    def test_shutdown_rejects_new_tasks(self, make_pool, manual_clock):
        pool = make_pool(max_concurrency=2)

        pool.shutdown(wait=False)
        assert pool.state == ThreadPoolState.SHUTTING_DOWN or pool.state == ThreadPoolState.TERMINATED

        def task():
            pass

        with pytest.raises(ThreadPoolShutdownError):
            pool.submit(task, priority=Priority.HIGH)

    def test_shutdown_state_transitions(self, make_pool, manual_clock):
        pool = make_pool(max_concurrency=1)

        def task():
            pass

        for i in range(3):
            pool.submit(task, task_id=f"task{i}", duration=5.0)

        assert pool.state == ThreadPoolState.RUNNING

        pool.shutdown(wait=False)
        assert pool.state == ThreadPoolState.SHUTTING_DOWN

        manual_clock.advance(10.0)
        pool.tick()
        pool.shutdown(wait=True)

        assert pool.state == ThreadPoolState.TERMINATED

    def test_double_shutdown_is_safe(self, make_pool, manual_clock):
        pool = make_pool(max_concurrency=2)

        def task():
            pass

        pool.submit(task, task_id="task1")
        pool.shutdown(wait=True)
        pool.shutdown(wait=True)

        assert pool.state == ThreadPoolState.TERMINATED


class TestTaskResultsAndErrors:
    def test_successful_task_result(self, make_pool):
        pool = make_pool(max_concurrency=2)

        def add(a, b):
            return a + b

        task_id = pool.submit(add, 2, 3, priority=Priority.HIGH)
        pool.run_until_complete()

        result = pool.get_task_result(task_id)
        assert result.status == TaskStatus.SUCCESS
        assert result.result == 5
        assert result.exception is None

    def test_failed_task_captures_exception(self, make_pool):
        pool = make_pool(max_concurrency=2)

        def raise_error():
            raise ValueError("something went wrong")

        task_id = pool.submit(raise_error, priority=Priority.HIGH)
        pool.run_until_complete()

        result = pool.get_task_result(task_id)
        assert result.status == TaskStatus.FAILED
        assert result.result is None
        assert isinstance(result.exception, ValueError)
        assert str(result.exception) == "something went wrong"

    def test_task_not_found_raises_error(self, make_pool):
        pool = make_pool(max_concurrency=2)

        with pytest.raises(TaskNotFoundError):
            pool.get_task_result("nonexistent_id")

    def test_submit_with_custom_task_id(self, make_pool):
        pool = make_pool(max_concurrency=2)

        def task():
            return 42

        custom_id = "my-custom-task-id"
        returned_id = pool.submit(task, task_id=custom_id)

        assert returned_id == custom_id
        pool.run_until_complete()

        result = pool.get_task_result(custom_id)
        assert result.status == TaskStatus.SUCCESS
        assert result.result == 42


class TestThreadPoolStats:
    def test_initial_stats(self, make_pool):
        pool = make_pool(max_concurrency=4)

        stats = pool.get_stats()
        assert stats.state == ThreadPoolState.RUNNING
        assert stats.max_concurrency == 4
        assert stats.current_concurrency == 0
        assert stats.high_queue_size == 0
        assert stats.medium_queue_size == 0
        assert stats.low_queue_size == 0
        assert stats.total_submitted == 0
        assert stats.total_completed == 0
        assert stats.total_failed == 0

    def test_stats_after_submission(self, make_pool, manual_clock):
        pool = make_pool(max_concurrency=1)

        def task():
            pass

        pool.submit(task, priority=Priority.HIGH, task_id="h1", duration=10.0)
        pool.submit(task, priority=Priority.MEDIUM, task_id="m1", duration=10.0)
        pool.submit(task, priority=Priority.LOW, task_id="l1", duration=10.0)

        pool.tick()
        stats = pool.get_stats()
        assert stats.total_submitted == 3
        assert stats.current_concurrency == 1
        assert stats.high_queue_size == 0
        assert stats.medium_queue_size == 1
        assert stats.low_queue_size == 1

    def test_stats_after_completion(self, make_pool):
        pool = make_pool(max_concurrency=2)

        def succeed():
            return "ok"

        def fail():
            raise RuntimeError("fail")

        pool.submit(succeed, task_id="s1")
        pool.submit(succeed, task_id="s2")
        pool.submit(fail, task_id="f1")

        pool.run_until_complete()

        stats = pool.get_stats()
        assert stats.total_submitted == 3
        assert stats.total_completed == 2
        assert stats.total_failed == 1
        assert stats.current_concurrency == 0


class TestCompletionOrder:
    def test_completion_order_tracking(self, make_pool, manual_clock):
        pool = make_pool(max_concurrency=1)

        def task():
            pass

        ids = []
        for i in range(5):
            tid = pool.submit(task, priority=Priority.MEDIUM, task_id=f"t{i}")
            ids.append(tid)

        pool.run_until_complete()

        assert pool.completion_order == ids


class TestExceptionsHierarchy:
    def test_invalid_config_is_threadpool_error(self):
        assert issubclass(InvalidConfigError, Exception)

    def test_shutdown_error_is_threadpool_error(self):
        err = ThreadPoolShutdownError()
        assert isinstance(err, Exception)

    def test_task_not_found_is_threadpool_error(self):
        err = TaskNotFoundError("abc")
        assert isinstance(err, Exception)
        assert err.task_id == "abc"


class TestSubmitMany:
    def test_submit_many_basic(self, make_pool, manual_clock):
        pool = make_pool(max_concurrency=2)
        results = []

        def make_task(name):
            def task():
                results.append(name)
                return name
            return task

        tasks = [
            (make_task("t1"), (), {}, Priority.HIGH),
            (make_task("t2"), (), {}, Priority.MEDIUM),
            (make_task("t3"), (), {}, Priority.LOW),
        ]

        ids = pool.submit_many(tasks)
        assert len(ids) == 3

        pool.run_until_complete()
        assert len(results) == 3

        for tid in ids:
            result = pool.get_task_result(tid)
            assert result.status == TaskStatus.SUCCESS

    def test_submit_many_with_duration(self, make_pool, manual_clock):
        pool = make_pool(max_concurrency=1)

        def task():
            return "done"

        tasks = [
            (task, (), {"duration": 10.0}, Priority.HIGH),
            (task, (), {"duration": 5.0}, Priority.HIGH),
        ]

        ids = pool.submit_many(tasks)

        pool.tick()
        stats = pool.get_stats()
        assert stats.current_concurrency == 1
        assert stats.high_queue_size == 1

        manual_clock.advance(10.0)
        pool.tick()
        stats = pool.get_stats()
        assert stats.current_concurrency == 1
        assert stats.total_completed == 1

        manual_clock.advance(5.0)
        pool.tick()
        stats = pool.get_stats()
        assert stats.current_concurrency == 0
        assert stats.total_completed == 2

    def test_submit_many_with_args_kwargs(self, make_pool):
        pool = make_pool(max_concurrency=2)

        def add(a, b, *, c=0):
            return a + b + c

        tasks = [
            (add, (1, 2), {"c": 3}, Priority.HIGH),
            (add, (10, 20), {}, Priority.MEDIUM),
        ]

        ids = pool.submit_many(tasks)
        pool.run_until_complete()

        r1 = pool.get_task_result(ids[0])
        r2 = pool.get_task_result(ids[1])
        assert r1.result == 6
        assert r2.result == 30


class TestTaskResultTimestamps:
    def test_pending_task_has_none_timestamps(self, make_pool, manual_clock):
        pool = make_pool(max_concurrency=1)

        def task():
            pass

        tid = pool.submit(task, priority=Priority.HIGH, task_id="pending", duration=10.0)

        result = pool.get_task_result(tid)
        assert result.status == TaskStatus.PENDING
        assert result.started_at is None
        assert result.completed_at is None
        assert isinstance(result.submitted_at, float)

    def test_running_task_has_started_at_but_no_completed_at(self, make_pool, manual_clock):
        pool = make_pool(max_concurrency=1)

        def task():
            pass

        tid = pool.submit(task, priority=Priority.HIGH, task_id="running", duration=10.0)
        pool.tick()

        result = pool.get_task_result(tid)
        assert result.status == TaskStatus.RUNNING
        assert result.started_at is not None
        assert isinstance(result.started_at, float)
        assert result.completed_at is None

    def test_completed_task_has_both_timestamps(self, make_pool, manual_clock):
        pool = make_pool(max_concurrency=1)

        def task():
            return 42

        tid = pool.submit(task, priority=Priority.HIGH, task_id="done", duration=5.0)
        pool.tick()
        manual_clock.advance(5.0)
        pool.tick()

        result = pool.get_task_result(tid)
        assert result.status == TaskStatus.SUCCESS
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.completed_at >= result.started_at


class TestSystemClockIntegration:
    def test_systemclock_run_until_complete(self):
        pool = PriorityThreadPool(ThreadPoolConfig(max_concurrency=2))
        completed = []

        def make_task(name, duration):
            def task():
                completed.append(name)
                return name
            return task

        for i in range(3):
            pool.submit(make_task(f"t{i}", 0.01), task_id=f"t{i}", duration=0.01)

        pool.run_until_complete()

        assert len(completed) == 3
        stats = pool.get_stats()
        assert stats.total_completed == 3
        assert stats.current_concurrency == 0

    def test_systemclock_shutdown_wait(self):
        pool = PriorityThreadPool(ThreadPoolConfig(max_concurrency=1))

        def task():
            return "done"

        pool.submit(task, task_id="t1", duration=0.02)
        pool.submit(task, task_id="t2", duration=0.02)

        pool.shutdown(wait=True)

        assert pool.state == ThreadPoolState.TERMINATED
        stats = pool.get_stats()
        assert stats.total_completed == 2

    def test_systemclock_short_duration_tasks(self):
        pool = PriorityThreadPool(ThreadPoolConfig(max_concurrency=3))
        results = []

        def task(n):
            results.append(n)
            return n * 2

        for i in range(5):
            pool.submit(task, i, task_id=f"t{i}", duration=0.005)

        pool.run_until_complete()

        assert len(results) == 5
        for i in range(5):
            r = pool.get_task_result(f"t{i}")
            assert r.status == TaskStatus.SUCCESS
            assert r.result == i * 2
