from __future__ import annotations

import threading
import time

import pytest

from solocoder_py.rate_cap import (
    ManualClock,
    OperationRejectedError,
    RateCapConfig,
    RateCapManager,
    SubjectQuotas,
    SystemClock,
    WindowConfig,
)


class TestManagerConcurrency:
    def test_concurrent_check_no_overcount_global(self):
        config = RateCapConfig(
            windows=[WindowConfig("1min", 60, 1000)]
        )
        clock = ManualClock()
        manager = RateCapManager(config, clock=clock)
        successes = 0
        failures = 0
        lock = threading.Lock()

        def worker(n):
            nonlocal successes, failures
            for _ in range(n):
                try:
                    manager.check_operation("user")
                    with lock:
                        successes += 1
                except OperationRejectedError:
                    with lock:
                        failures += 1

        threads = [
            threading.Thread(target=worker, args=(200,)) for _ in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert successes == 1000
        assert failures == 1000
        assert manager.query_global_usage()["1min"].used == 1000

    def test_concurrent_subject_and_global_no_rollback_leak(self):
        config = RateCapConfig(
            windows=[WindowConfig("1min", 60, 500)],
            subject_quotas={
                "u1": SubjectQuotas(
                    subject_id="u1", per_window_quotas={"1min": 50}
                ),
                "u2": SubjectQuotas(
                    subject_id="u2", per_window_quotas={"1min": 50}
                ),
            },
        )
        clock = ManualClock()
        manager = RateCapManager(config, clock=clock)
        errors = []

        def worker_u1(n):
            for _ in range(n):
                try:
                    manager.check_operation("u1")
                except OperationRejectedError as e:
                    if e.dimension == "global":
                        errors.append(("u1", e.dimension, e.window_name))

        def worker_u2(n):
            for _ in range(n):
                try:
                    manager.check_operation("u2")
                except OperationRejectedError as e:
                    if e.dimension == "global":
                        errors.append(("u2", e.dimension, e.window_name))

        t1 = threading.Thread(target=worker_u1, args=(100,))
        t2 = threading.Thread(target=worker_u2, args=(100,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        g_used = manager.query_global_usage()["1min"].used
        s1_used = manager.query_subject_usage("u1")["1min"].used
        s2_used = manager.query_subject_usage("u2")["1min"].used

        assert s1_used == 50
        assert s2_used == 50
        assert g_used == s1_used + s2_used
        assert g_used <= 500

    def test_concurrent_subject_failure_rollback_global(self):
        config = RateCapConfig(
            windows=[
                WindowConfig("1min", 60, 10000),
                WindowConfig("1hour", 3600, 100000),
            ],
            subject_quotas={
                "victim": SubjectQuotas(
                    subject_id="victim",
                    per_window_quotas={"1min": 10, "1hour": 100000},
                )
            },
        )
        clock = ManualClock()
        manager = RateCapManager(config, clock=clock)

        for _ in range(10):
            manager.check_operation("victim")

        global_before_1min = manager.query_global_usage()["1min"].used
        global_before_1hour = manager.query_global_usage()["1hour"].used

        with pytest.raises(OperationRejectedError) as exc_info:
            manager.check_operation("victim")
        assert exc_info.value.dimension == "subject"

        global_after_1min = manager.query_global_usage()["1min"].used
        global_after_1hour = manager.query_global_usage()["1hour"].used

        assert global_before_1min == global_after_1min
        assert global_before_1hour == global_after_1hour

    def test_concurrent_query_and_check(self):
        config = RateCapConfig(
            windows=[
                WindowConfig("1min", 60, 500),
                WindowConfig("1hour", 3600, 5000),
            ],
        )
        clock = ManualClock()
        manager = RateCapManager(config, clock=clock)
        exceptions = []

        def check_worker(n):
            for i in range(n):
                try:
                    manager.check_operation(f"user-{i % 5}")
                except OperationRejectedError:
                    pass
                except Exception as e:
                    exceptions.append(("check", e))

        def query_worker(n):
            for i in range(n):
                try:
                    manager.query_subject_usage(f"user-{i % 5}")
                    manager.query_global_usage()
                    manager.query_usage(f"user-{i % 5}")
                except Exception as e:
                    exceptions.append(("query", e))

        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=check_worker, args=(150,)))
            threads.append(threading.Thread(target=query_worker, args=(100,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        for kind, exc in exceptions:
            assert False, f"{kind} worker raised: {exc!r}"

        g_used_1min = manager.query_global_usage()["1min"].used
        g_used_1hour = manager.query_global_usage()["1hour"].used
        assert g_used_1min <= 500
        assert g_used_1hour <= 5000
        assert g_used_1min == g_used_1hour

    def test_many_subjects_concurrent(self):
        num_subjects = 50
        per_subject_quota = 20
        global_quota = num_subjects * per_subject_quota

        config = RateCapConfig(
            windows=[WindowConfig("1min", 60, global_quota)],
            subject_quotas={
                f"user-{i}": SubjectQuotas(
                    subject_id=f"user-{i}",
                    per_window_quotas={"1min": per_subject_quota},
                )
                for i in range(num_subjects)
            },
        )
        clock = ManualClock()
        manager = RateCapManager(config, clock=clock)

        def worker(subject_id):
            for _ in range(per_subject_quota * 2):
                try:
                    manager.check_operation(subject_id)
                except OperationRejectedError:
                    pass

        threads = [
            threading.Thread(target=worker, args=(f"user-{i}",))
            for i in range(num_subjects)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        g_used = manager.query_global_usage()["1min"].used
        total_subject_used = sum(
            manager.query_subject_usage(f"user-{i}")["1min"].used
            for i in range(num_subjects)
        )
        assert g_used == total_subject_used
        assert g_used <= global_quota
        for i in range(num_subjects):
            s_used = manager.query_subject_usage(f"user-{i}")["1min"].used
            assert s_used == per_subject_quota


class TestSystemClockIntegration:
    def test_real_clock_basic_flow(self):
        config = RateCapConfig(
            windows=[WindowConfig("tiny", 0.1, 5)]
        )
        manager = RateCapManager(config)
        for _ in range(5):
            manager.check_operation("u1")
        with pytest.raises(OperationRejectedError):
            manager.check_operation("u1")

        time.sleep(0.15)
        manager.check_operation("u1")
