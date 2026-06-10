from __future__ import annotations

import pytest

from solocoder_py.rate_cap import (
    InvalidWindowConfigError,
    ManualClock,
    OperationRejectedError,
    RateCapConfig,
    RateCapManager,
    SubjectNotFoundError,
    SubjectQuotas,
    WindowConfig,
)


class TestManagerBasicFlow:
    def test_check_passes_within_limit(self, single_window_config, simple_clock):
        manager = RateCapManager(single_window_config, clock=simple_clock)
        for _ in range(100):
            manager.check_operation("user-001")
        usage = manager.query_subject_usage("user-001")
        assert usage["1min"].used == 100
        assert usage["1min"].remaining == 0

    def test_check_rejects_over_limit(
        self, single_window_config, simple_clock
    ):
        manager = RateCapManager(single_window_config, clock=simple_clock)
        for _ in range(100):
            manager.check_operation("user-001")
        with pytest.raises(OperationRejectedError) as exc_info:
            manager.check_operation("user-001")
        assert exc_info.value.dimension == "global"
        assert exc_info.value.window_name == "1min"
        assert exc_info.value.used == 100
        assert exc_info.value.limit == 100
        assert exc_info.value.subject_id == "user-001"

    def test_is_allowed_non_consuming(
        self, single_window_config, simple_clock
    ):
        manager = RateCapManager(single_window_config, clock=simple_clock)
        for _ in range(100):
            assert manager.is_allowed("user-001") is True
        usage = manager.query_global_usage()
        assert usage["1min"].used == 0

        manager.check_operation("user-001")
        assert manager.query_global_usage()["1min"].used == 1

    def test_amount_parameter(self, single_window_config, simple_clock):
        manager = RateCapManager(single_window_config, clock=simple_clock)
        manager.check_operation("user-001", amount=40)
        manager.check_operation("user-001", amount=60)
        assert manager.query_global_usage()["1min"].used == 100
        with pytest.raises(OperationRejectedError):
            manager.check_operation("user-001", amount=1)

    def test_invalid_amount_raises(self, single_window_config, simple_clock):
        manager = RateCapManager(single_window_config, clock=simple_clock)
        with pytest.raises(ValueError, match="amount must be positive"):
            manager.check_operation("u1", 0)
        with pytest.raises(ValueError, match="amount must be positive"):
            manager.is_allowed("u1", -1)

    def test_subject_id_none_global_only(
        self, single_window_config, simple_clock
    ):
        manager = RateCapManager(single_window_config, clock=simple_clock)
        for _ in range(100):
            manager.check_operation(None)
        assert manager.query_global_usage()["1min"].used == 100
        with pytest.raises(OperationRejectedError) as exc_info:
            manager.check_operation(None)
        assert exc_info.value.subject_id is None
        assert exc_info.value.dimension == "global"


class TestManagerMultiWindow:
    def test_multi_window_both_limits(
        self, multi_window_config, simple_clock
    ):
        manager = RateCapManager(multi_window_config, clock=simple_clock)
        for _ in range(100):
            manager.check_operation("u1")
        usage = manager.query_subject_usage("u1")
        assert usage["1min"].used == 100
        assert usage["1min"].remaining == 0
        assert usage["1hour"].used == 100
        assert usage["1hour"].remaining == 900

        with pytest.raises(OperationRejectedError) as exc_info:
            manager.check_operation("u1")
        assert exc_info.value.dimension == "global"
        assert exc_info.value.window_name == "1min"

    def test_multi_window_expire_short_window(
        self, multi_window_config, simple_clock
    ):
        manager = RateCapManager(multi_window_config, clock=simple_clock)
        for _ in range(100):
            manager.check_operation("u1")

        simple_clock.advance(61)
        manager.check_operation("u1")
        usage = manager.query_global_usage()
        assert usage["1min"].used == 1
        assert usage["1hour"].used == 101


class TestManagerCrossDimension:
    def test_subject_limited_before_global(
        self, subject_quotas_config, simple_clock
    ):
        manager = RateCapManager(subject_quotas_config, clock=simple_clock)
        for _ in range(50):
            manager.check_operation("user-001")

        with pytest.raises(OperationRejectedError) as exc_info:
            manager.check_operation("user-001")
        assert exc_info.value.dimension == "subject"
        assert exc_info.value.window_name == "1min"
        assert exc_info.value.subject_id == "user-001"

        global_usage = manager.query_global_usage()["1min"]
        assert global_usage.used == 50
        assert global_usage.remaining == 950

    def test_global_limited_with_other_subjects(
        self, subject_quotas_config, simple_clock
    ):
        manager = RateCapManager(subject_quotas_config, clock=simple_clock)
        for i in range(50):
            manager.check_operation(f"user-new-{i:03d}", amount=20)

        with pytest.raises(OperationRejectedError) as exc_info:
            manager.check_operation("user-any")
        assert exc_info.value.dimension == "global"
        assert exc_info.value.window_name == "1min"

    def test_subject_quota_equals_global(
        self, simple_clock
    ):
        config = RateCapConfig(
            windows=[WindowConfig("1min", 60, 50)],
            subject_quotas={
                "only-user": SubjectQuotas(
                    subject_id="only-user",
                    per_window_quotas={"1min": 50},
                )
            },
        )
        manager = RateCapManager(config, clock=simple_clock)
        for _ in range(50):
            manager.check_operation("only-user")

        with pytest.raises(OperationRejectedError) as exc_info:
            manager.check_operation("only-user")
        assert exc_info.value.dimension == "global"
        assert exc_info.value.window_name == "1min"

    def test_rollback_when_subject_fails(
        self, subject_quotas_config, simple_clock
    ):
        manager = RateCapManager(subject_quotas_config, clock=simple_clock)
        for _ in range(50):
            manager.check_operation("user-001")

        global_before = manager.query_global_usage()["1min"].used
        with pytest.raises(OperationRejectedError) as exc_info:
            manager.check_operation("user-001")
        assert exc_info.value.dimension == "subject"
        global_after = manager.query_global_usage()["1min"].used
        assert global_before == global_after


class TestManagerWindowBoundary:
    def test_exact_boundary_allows(self, simple_clock):
        config = RateCapConfig(
            windows=[WindowConfig("w", 10.0, 1)]
        )
        manager = RateCapManager(config, clock=simple_clock)
        manager.check_operation("u1")
        simple_clock.advance(10.0)
        manager.check_operation("u1")

    def test_just_inside_boundary_rejects(self, simple_clock):
        config = RateCapConfig(
            windows=[WindowConfig("w", 10.0, 1)]
        )
        manager = RateCapManager(config, clock=simple_clock)
        manager.check_operation("u1")
        simple_clock.advance(9.999)
        with pytest.raises(OperationRejectedError):
            manager.check_operation("u1")

    def test_granular_boundary_behavior(self, simple_clock):
        config = RateCapConfig(
            windows=[
                WindowConfig(
                    "w", 60.0, 5, slide_granularity_seconds=10.0
                )
            ]
        )
        manager = RateCapManager(config, clock=simple_clock)
        manager.check_operation("u1")
        simple_clock.advance(5)
        manager.check_operation("u1")
        simple_clock.advance(10)
        manager.check_operation("u1")
        simple_clock.advance(60)
        manager.check_operation("u1")
        assert manager.query_global_usage()["w"].used == 1


class TestManagerUsageQuery:
    def test_query_unactivated_subject_returns_default(
        self, subject_quotas_config, simple_clock
    ):
        manager = RateCapManager(subject_quotas_config, clock=simple_clock)
        usage = manager.query_subject_usage("never-seen-user")
        assert usage["1min"].used == 0
        assert usage["1min"].remaining == 100
        assert usage["1min"].limit == 100
        assert usage["1hour"].used == 0
        assert usage["1hour"].remaining == 1000
        assert usage["1hour"].limit == 1000

    def test_query_empty_subject_raises(
        self, single_window_config, simple_clock
    ):
        manager = RateCapManager(single_window_config, clock=simple_clock)
        with pytest.raises(ValueError, match="subject_id cannot be empty"):
            manager.query_subject_usage("")

    def test_query_global_usage(
        self, multi_window_config, simple_clock
    ):
        manager = RateCapManager(multi_window_config, clock=simple_clock)
        manager.check_operation("u1", amount=5)
        manager.check_operation("u2", amount=3)
        global_usage = manager.query_global_usage()
        assert global_usage["1min"].used == 8
        assert global_usage["1min"].remaining == 92
        assert global_usage["1hour"].used == 8
        assert global_usage["1hour"].remaining == 992

    def test_query_usage_with_subject(
        self, subject_quotas_config, simple_clock
    ):
        manager = RateCapManager(subject_quotas_config, clock=simple_clock)
        manager.check_operation("user-001", amount=20)
        result = manager.query_usage("user-001")
        assert "global" in result
        assert "subject" in result
        assert result["global"]["1min"].used == 20
        assert result["subject"]["1min"].used == 20
        assert result["subject"]["1min"].limit == 50

    def test_query_usage_without_subject(
        self, single_window_config, simple_clock
    ):
        manager = RateCapManager(single_window_config, clock=simple_clock)
        manager.check_operation(None, amount=5)
        result = manager.query_usage()
        assert "global" in result
        assert "subject" not in result
        assert result["global"]["1min"].used == 5


class TestManagerReset:
    def test_reset_subject(self, subject_quotas_config, simple_clock):
        manager = RateCapManager(subject_quotas_config, clock=simple_clock)
        manager.check_operation("user-001", amount=30)
        manager.check_operation("user-002", amount=20)
        manager.reset_subject("user-001")
        assert manager.query_subject_usage("user-001")["1min"].used == 0
        assert manager.query_global_usage()["1min"].used == 20

    def test_reset_global(self, subject_quotas_config, simple_clock):
        manager = RateCapManager(subject_quotas_config, clock=simple_clock)
        manager.check_operation("user-001", amount=30)
        manager.check_operation("user-002", amount=20)
        manager.reset_global()
        assert manager.query_global_usage()["1min"].used == 0

    def test_reset_all(self, subject_quotas_config, simple_clock):
        manager = RateCapManager(subject_quotas_config, clock=simple_clock)
        manager.check_operation("user-001", amount=30)
        manager.check_operation("user-002", amount=20)
        manager.reset_all()
        assert manager.query_global_usage()["1min"].used == 0
        assert manager.query_subject_usage("user-001")["1min"].used == 0
        assert manager.query_subject_usage("user-002")["1min"].used == 0

    def test_reset_empty_subject_raises(
        self, single_window_config, simple_clock
    ):
        manager = RateCapManager(single_window_config, clock=simple_clock)
        with pytest.raises(ValueError, match="subject_id cannot be empty"):
            manager.reset_subject("")


class TestManagerAddSubject:
    def test_add_new_subject_quota(
        self, single_window_config, simple_clock
    ):
        manager = RateCapManager(single_window_config, clock=simple_clock)
        manager.add_subject_quota("new-user", {"1min": 10})
        usage = manager.query_subject_usage("new-user")
        assert usage["1min"].limit == 10

    def test_add_existing_subject_no_overwrite(
        self, subject_quotas_config, simple_clock
    ):
        manager = RateCapManager(subject_quotas_config, clock=simple_clock)
        manager.check_operation("user-001", amount=10)
        manager.add_subject_quota("user-001", {"1min": 999})
        usage = manager.query_subject_usage("user-001")
        assert usage["1min"].limit == 50

    def test_add_subject_invalid_window_raises(
        self, single_window_config, simple_clock
    ):
        manager = RateCapManager(single_window_config, clock=simple_clock)
        with pytest.raises(
            InvalidWindowConfigError, match="Unknown window"
        ):
            manager.add_subject_quota("u1", {"unknown": 10})

    def test_add_subject_invalid_limit_raises(
        self, single_window_config, simple_clock
    ):
        manager = RateCapManager(single_window_config, clock=simple_clock)
        with pytest.raises(
            InvalidWindowConfigError, match="quota must be positive"
        ):
            manager.add_subject_quota("u1", {"1min": -1})

    def test_add_empty_subject_raises(
        self, single_window_config, simple_clock
    ):
        manager = RateCapManager(single_window_config, clock=simple_clock)
        with pytest.raises(ValueError, match="subject_id cannot be empty"):
            manager.add_subject_quota("", {"1min": 10})


class TestManagerGranularSliding:
    def test_granular_counter_basic(
        self, granular_window_config, simple_clock
    ):
        manager = RateCapManager(granular_window_config, clock=simple_clock)
        for _ in range(100):
            manager.check_operation("u1")
        with pytest.raises(OperationRejectedError):
            manager.check_operation("u1")

    def test_granular_counter_sliding(
        self, granular_window_config, simple_clock
    ):
        manager = RateCapManager(granular_window_config, clock=simple_clock)
        manager.check_operation("u1", amount=50)
        simple_clock.advance(30)
        manager.check_operation("u1", amount=50)
        simple_clock.advance(31)
        manager.check_operation("u1", amount=50)


class TestManagerResetIsolation:
    def test_granular_reset_subject_a_does_not_affect_b(self, simple_clock):
        config = RateCapConfig(
            windows=[
                WindowConfig(
                    name="1min",
                    window_seconds=60,
                    max_operations=1000,
                    slide_granularity_seconds=1,
                )
            ],
            subject_quotas={
                "A": SubjectQuotas("A", {"1min": 500}),
                "B": SubjectQuotas("B", {"1min": 500}),
            },
        )
        manager = RateCapManager(config, clock=simple_clock)
        manager.check_operation("A", amount=30)
        manager.check_operation("B", amount=20)

        assert manager.query_subject_usage("A")["1min"].used == 30
        assert manager.query_subject_usage("B")["1min"].used == 20
        assert manager.query_global_usage()["1min"].used == 50

        manager.reset_subject("A")

        assert manager.query_subject_usage("A")["1min"].used == 0
        assert manager.query_subject_usage("B")["1min"].used == 20
        assert manager.query_global_usage()["1min"].used == 20

        manager.check_operation("B", amount=480)
        assert manager.query_subject_usage("B")["1min"].used == 500
        assert manager.query_global_usage()["1min"].used == 500

    def test_precise_reset_subject_a_does_not_affect_b(self, simple_clock):
        config = RateCapConfig(
            windows=[
                WindowConfig(name="1min", window_seconds=60, max_operations=1000),
            ],
            subject_quotas={
                "A": SubjectQuotas("A", {"1min": 500}),
                "B": SubjectQuotas("B", {"1min": 500}),
            },
        )
        manager = RateCapManager(config, clock=simple_clock)
        for _ in range(30):
            manager.check_operation("A")
        for _ in range(20):
            manager.check_operation("B")

        assert manager.query_subject_usage("A")["1min"].used == 30
        assert manager.query_subject_usage("B")["1min"].used == 20
        assert manager.query_global_usage()["1min"].used == 50

        manager.reset_subject("A")

        assert manager.query_subject_usage("A")["1min"].used == 0
        assert manager.query_subject_usage("B")["1min"].used == 20
        assert manager.query_global_usage()["1min"].used == 20

    def test_granular_multiple_buckets_reset_isolation(self, simple_clock):
        config = RateCapConfig(
            windows=[
                WindowConfig(
                    name="w",
                    window_seconds=60,
                    max_operations=1000,
                    slide_granularity_seconds=10,
                )
            ],
            subject_quotas={
                "A": SubjectQuotas("A", {"w": 500}),
                "B": SubjectQuotas("B", {"w": 500}),
            },
        )
        manager = RateCapManager(config, clock=simple_clock)
        manager.check_operation("A", amount=10)
        simple_clock.advance(12)
        manager.check_operation("A", amount=15)
        manager.check_operation("B", amount=5)
        simple_clock.advance(12)
        manager.check_operation("B", amount=25)
        manager.check_operation("A", amount=5)

        assert manager.query_subject_usage("A")["w"].used == 30
        assert manager.query_subject_usage("B")["w"].used == 30
        assert manager.query_global_usage()["w"].used == 60

        manager.reset_subject("A")

        assert manager.query_subject_usage("A")["w"].used == 0
        assert manager.query_subject_usage("B")["w"].used == 30
        assert manager.query_global_usage()["w"].used == 30

    def test_reset_subject_with_nonexistent_subject(self, simple_clock):
        config = RateCapConfig(
            windows=[WindowConfig("w", 60, 100)],
            subject_quotas={
                "A": SubjectQuotas("A", {"w": 50}),
                "B": SubjectQuotas("B", {"w": 50}),
            },
        )
        manager = RateCapManager(config, clock=simple_clock)
        manager.check_operation("A", amount=10)
        manager.reset_subject("NONEXISTENT")
        assert manager.query_subject_usage("A")["w"].used == 10
        assert manager.query_global_usage()["w"].used == 10


class TestManagerSubjectNotFound:
    def test_strict_query_unknown_subject_raises(self, simple_clock):
        config = RateCapConfig(
            windows=[WindowConfig("1min", 60, 1000)],
        )
        manager = RateCapManager(config, clock=simple_clock)
        with pytest.raises(SubjectNotFoundError, match="not found"):
            manager.query_subject_usage("ghost-user", strict=True)

    def test_strict_query_known_subject_ok(self, simple_clock):
        config = RateCapConfig(
            windows=[WindowConfig("1min", 60, 1000)],
            subject_quotas={
                "known-user": SubjectQuotas("known-user", {"1min": 50}),
            },
        )
        manager = RateCapManager(config, clock=simple_clock)
        usage = manager.query_subject_usage("known-user", strict=True)
        assert usage["1min"].limit == 50

    def test_strict_query_user_with_default_quota_ok(self, simple_clock):
        config = RateCapConfig(
            windows=[WindowConfig("1min", 60, 1000)],
            default_subject_quotas={"1min": 100},
        )
        manager = RateCapManager(config, clock=simple_clock)
        usage = manager.query_subject_usage("any-user", strict=True)
        assert usage["1min"].limit == 100

    def test_strict_query_user_with_history_ok(self, simple_clock):
        config = RateCapConfig(
            windows=[WindowConfig("1min", 60, 1000)],
        )
        manager = RateCapManager(config, clock=simple_clock)
        manager.check_operation("once-user", amount=1)
        usage = manager.query_subject_usage("once-user", strict=True)
        assert usage["1min"].used == 1

    def test_non_strict_query_unknown_subject_returns_default(
        self, single_window_config, simple_clock
    ):
        manager = RateCapManager(single_window_config, clock=simple_clock)
        usage = manager.query_subject_usage("ghost-user", strict=False)
        assert usage["1min"].used == 0
        assert usage["1min"].remaining == 100

    def test_query_usage_strict_propagates(self, simple_clock):
        config = RateCapConfig(
            windows=[WindowConfig("1min", 60, 1000)],
        )
        manager = RateCapManager(config, clock=simple_clock)
        with pytest.raises(SubjectNotFoundError, match="not found"):
            manager.query_usage("ghost-user", strict=True)


class TestManagerRollbackTagIsolation:
    def test_granular_rollback_global_tag_does_not_affect_other(self, simple_clock):
        config = RateCapConfig(
            windows=[
                WindowConfig(
                    name="1min",
                    window_seconds=60,
                    max_operations=1000,
                    slide_granularity_seconds=10,
                )
            ],
            subject_quotas={
                "A": SubjectQuotas("A", {"1min": 500}),
                "B": SubjectQuotas("B", {"1min": 500}),
                "X": SubjectQuotas("X", {"1min": 5}),
            },
        )
        manager = RateCapManager(config, clock=simple_clock)
        manager.check_operation("A", amount=30)
        manager.check_operation("B", amount=20)
        assert manager.query_global_usage()["1min"].used == 50
        with pytest.raises(OperationRejectedError) as excinfo:
            manager.check_operation("X", amount=10)
        assert excinfo.value.dimension == "subject"
        assert manager.query_subject_usage("A")["1min"].used == 30
        assert manager.query_subject_usage("B")["1min"].used == 20
        assert manager.query_global_usage()["1min"].used == 50

    def test_precise_rollback_global_tag_does_not_affect_other(self, simple_clock):
        config = RateCapConfig(
            windows=[WindowConfig(name="1min", window_seconds=60, max_operations=1000)],
            subject_quotas={
                "A": SubjectQuotas("A", {"1min": 500}),
                "B": SubjectQuotas("B", {"1min": 500}),
                "X": SubjectQuotas("X", {"1min": 5}),
            },
        )
        manager = RateCapManager(config, clock=simple_clock)
        for _ in range(30):
            manager.check_operation("A")
        for _ in range(20):
            manager.check_operation("B")
        with pytest.raises(OperationRejectedError) as excinfo:
            manager.check_operation("X", amount=10)
        assert excinfo.value.dimension == "subject"
        assert manager.query_subject_usage("A")["1min"].used == 30
        assert manager.query_subject_usage("B")["1min"].used == 20
        assert manager.query_global_usage()["1min"].used == 50

    def test_multi_window_rollback_tag_all_windows(self, simple_clock):
        config = RateCapConfig(
            windows=[
                WindowConfig(
                    name="1min",
                    window_seconds=60,
                    max_operations=1000,
                    slide_granularity_seconds=1,
                ),
                WindowConfig(
                    name="1hour",
                    window_seconds=3600,
                    max_operations=10000,
                    slide_granularity_seconds=10,
                ),
            ],
            subject_quotas={
                "A": SubjectQuotas("A", {"1min": 500, "1hour": 5000}),
                "B": SubjectQuotas("B", {"1min": 500, "1hour": 5000}),
                "X": SubjectQuotas("X", {"1min": 5, "1hour": 5}),
            },
        )
        manager = RateCapManager(config, clock=simple_clock)
        manager.check_operation("A", amount=10)
        manager.check_operation("B", amount=15)
        with pytest.raises(OperationRejectedError):
            manager.check_operation("X", amount=20)
        assert manager.query_subject_usage("A")["1min"].used == 10
        assert manager.query_subject_usage("A")["1hour"].used == 10
        assert manager.query_subject_usage("B")["1min"].used == 15
        assert manager.query_subject_usage("B")["1hour"].used == 15
        assert manager.query_global_usage()["1min"].used == 25
        assert manager.query_global_usage()["1hour"].used == 25

    def test_reset_then_continue_isolated_from_others(self, simple_clock):
        config = RateCapConfig(
            windows=[
                WindowConfig(
                    name="w",
                    window_seconds=60,
                    max_operations=1000,
                    slide_granularity_seconds=10,
                )
            ],
            subject_quotas={
                "A": SubjectQuotas("A", {"w": 500}),
                "B": SubjectQuotas("B", {"w": 500}),
            },
        )
        manager = RateCapManager(config, clock=simple_clock)
        manager.check_operation("A", amount=10)
        manager.check_operation("B", amount=20)
        manager.reset_subject("A")
        manager.check_operation("A", amount=15)
        assert manager.query_subject_usage("A")["w"].used == 15
        assert manager.query_subject_usage("B")["w"].used == 20
        assert manager.query_global_usage()["w"].used == 35
        manager.check_operation("B", amount=10)
        assert manager.query_subject_usage("A")["w"].used == 15
        assert manager.query_subject_usage("B")["w"].used == 30
        assert manager.query_global_usage()["w"].used == 45

    def test_global_rollback_when_global_fails(self, simple_clock):
        config = RateCapConfig(
            windows=[
                WindowConfig(
                    name="w",
                    window_seconds=60,
                    max_operations=30,
                    slide_granularity_seconds=1,
                )
            ],
            default_subject_quotas={"w": 100},
        )
        manager = RateCapManager(config, clock=simple_clock)
        manager.check_operation("A", amount=10)
        manager.check_operation("B", amount=10)
        with pytest.raises(OperationRejectedError) as excinfo:
            manager.check_operation("C", amount=15)
        assert excinfo.value.dimension == "global"
        assert manager.query_subject_usage("A")["w"].used == 10
        assert manager.query_subject_usage("B")["w"].used == 10
        assert manager.query_subject_usage("C")["w"].used == 0
        assert manager.query_global_usage()["w"].used == 20
