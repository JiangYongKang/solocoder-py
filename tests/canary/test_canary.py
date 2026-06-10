from __future__ import annotations

import pytest

from solocoder_py.canary import (
    CanaryController,
    CanaryPhase,
    CanaryReleaseConfig,
    InvalidMetricsThresholdError,
    InvalidReleasePhaseError,
    InvalidTrafficPercentageError,
    ReleaseAlreadyExistsError,
    ReleaseNotFoundError,
    RollbackNotAllowedError,
    RollbackReason,
    TrafficRouter,
    VersionNotFoundError,
    VersionType,
)
from solocoder_py.canary.router import StableHashBucketer


# ============================================================
# TrafficRouter Tests
# ============================================================


class TestStableHashBucketer:
    def test_hash_consistency(self):
        key = "user-12345"
        bucket1 = StableHashBucketer.get_bucket(key)
        bucket2 = StableHashBucketer.get_bucket(key)
        assert bucket1 == bucket2

    def test_hash_within_0_99(self):
        for i in range(1000):
            bucket = StableHashBucketer.get_bucket(f"user-{i}")
            assert 0 <= bucket <= 99

    def test_hash_distribution_approx_uniform(self):
        buckets = {}
        for i in range(10000):
            b = StableHashBucketer.get_bucket(f"user-{i}")
            buckets[b] = buckets.get(b, 0) + 1
        for count in buckets.values():
            assert 50 <= count <= 150


class TestTrafficRouterVersionManagement:
    def test_register_baseline_version(self):
        router = TrafficRouter()
        info = router.register_version("v1.0.0", VersionType.BASELINE, "stable version")
        assert info.version == "v1.0.0"
        assert info.version_type == VersionType.BASELINE
        assert info.description == "stable version"

    def test_register_candidate_version(self):
        router = TrafficRouter()
        info = router.register_version("v2.0.0", VersionType.CANDIDATE)
        assert info.version == "v2.0.0"
        assert info.version_type == VersionType.CANDIDATE

    def test_register_empty_version_raises(self):
        router = TrafficRouter()
        with pytest.raises(ValueError, match="version must not be empty"):
            router.register_version("", VersionType.BASELINE)

    def test_list_versions(self):
        router = TrafficRouter()
        router.register_version("v1", VersionType.BASELINE)
        router.register_version("v2", VersionType.CANDIDATE)
        versions = router.list_versions()
        assert len(versions) == 2

    def test_get_version(self):
        router = TrafficRouter()
        router.register_version("v1", VersionType.BASELINE)
        info = router.get_version("v1")
        assert info.version == "v1"

    def test_get_nonexistent_version_raises(self):
        router = TrafficRouter()
        with pytest.raises(VersionNotFoundError):
            router.get_version("nonexistent")

    def test_set_baseline_version(self):
        router = TrafficRouter()
        router.register_version("v1", VersionType.BASELINE)
        router.register_version("v1-old", VersionType.BASELINE)
        router.set_baseline_version("v1-old")
        assert router._baseline_version == "v1-old"

    def test_set_nonexistent_baseline_raises(self):
        router = TrafficRouter()
        with pytest.raises(VersionNotFoundError):
            router.set_baseline_version("nonexistent")


class TestTrafficRouterRouting:
    def setup_method(self):
        self.router = TrafficRouter()
        self.router.register_version("v1", VersionType.BASELINE)
        self.router.register_version("v2", VersionType.CANDIDATE)

    def test_route_empty_key_raises(self):
        with pytest.raises(ValueError, match="request_key must not be empty"):
            self.router.route("")

    def test_route_without_baseline_raises(self):
        router = TrafficRouter()
        router.register_version("v2", VersionType.CANDIDATE)
        with pytest.raises(VersionNotFoundError, match="no baseline version"):
            router.route("user-1")

    def test_route_without_candidate_raises(self):
        router = TrafficRouter()
        router.register_version("v1", VersionType.BASELINE)
        with pytest.raises(VersionNotFoundError, match="no candidate version"):
            router.route("user-1")

    def test_zero_percent_all_baseline(self):
        self.router.set_traffic_percentage(0)
        for i in range(1000):
            version, vtype = self.router.route(f"user-{i}")
            assert version == "v1"
            assert vtype == VersionType.BASELINE

    def test_hundred_percent_all_candidate(self):
        self.router.set_traffic_percentage(100)
        for i in range(1000):
            version, vtype = self.router.route(f"user-{i}")
            assert version == "v2"
            assert vtype == VersionType.CANDIDATE

    def test_fifty_percent_split(self):
        self.router.set_traffic_percentage(50)
        counts = {"v1": 0, "v2": 0}
        for i in range(10000):
            version, _ = self.router.route(f"user-{i}")
            counts[version] += 1
        assert 4000 <= counts["v1"] <= 6000
        assert 4000 <= counts["v2"] <= 6000

    def test_route_consistency_same_key(self):
        self.router.set_traffic_percentage(30)
        results = set()
        for _ in range(50):
            version, vtype = self.router.route("same-user")
            results.add((version, vtype))
        assert len(results) == 1

    def test_set_invalid_traffic_percentage_raises(self):
        with pytest.raises(InvalidTrafficPercentageError):
            self.router.set_traffic_percentage(-1)
        with pytest.raises(InvalidTrafficPercentageError):
            self.router.set_traffic_percentage(101)


class TestTrafficRouterStats:
    def setup_method(self):
        self.router = TrafficRouter()
        self.router.register_version("v1", VersionType.BASELINE)
        self.router.register_version("v2", VersionType.CANDIDATE)
        self.router.set_traffic_percentage(100)

    def test_record_candidate_metrics(self):
        for _ in range(10):
            self.router.route("user-x", "release-1")
            self.router.record_candidate_metrics("release-1", latency_ms=100.0, is_error=False)
        stats = self.router.get_stats("release-1")
        assert stats.candidate_requests == 10
        assert stats.candidate_errors == 0
        assert stats.candidate_avg_latency_ms == pytest.approx(100.0)

    def test_record_candidate_errors(self):
        for i in range(20):
            self.router.route(f"user-{i}", "release-1")
            is_error = i % 4 == 0
            self.router.record_candidate_metrics("release-1", latency_ms=50.0, is_error=is_error)
        stats = self.router.get_stats("release-1")
        assert stats.candidate_requests == 20
        assert stats.candidate_errors == 5
        assert stats.candidate_error_rate == pytest.approx(0.25)

    def test_candidate_p99_latency(self):
        for i in range(100):
            self.router.route(f"user-{i}", "release-1")
            latency = 10.0 if i < 99 else 1000.0
            self.router.record_candidate_metrics("release-1", latency_ms=latency, is_error=False)
        stats = self.router.get_stats("release-1")
        assert stats.candidate_p99_latency_ms >= 900.0

    def test_empty_stats(self):
        stats = self.router.get_stats("nonexistent-release")
        assert stats.total_requests == 0
        assert stats.candidate_error_rate == 0.0
        assert stats.candidate_avg_latency_ms == 0.0
        assert stats.candidate_p99_latency_ms == 0.0

    def test_reset_stats(self):
        for i in range(50):
            self.router.route(f"user-{i}", "release-1")
            self.router.record_candidate_metrics("release-1", latency_ms=30.0, is_error=False)
        self.router.reset_stats("release-1")
        stats = self.router.get_stats("release-1")
        assert stats.total_requests == 0


# ============================================================
# CanaryController Tests - Normal Flows
# ============================================================


class TestCanaryReleaseCreation:
    def test_create_release(self):
        controller = CanaryController()
        config = CanaryReleaseConfig(
            baseline_version="v1.0.0",
            candidate_version="v2.0.0",
        )
        release = controller.create_release("test-release", config)
        assert release.name == "test-release"
        assert release.config.baseline_version == "v1.0.0"
        assert release.config.candidate_version == "v2.0.0"
        assert release.phase == CanaryPhase.DRAFT
        assert release.current_traffic_percentage == 0
        assert release.current_step_index == -1

    def test_create_release_with_custom_steps(self):
        controller = CanaryController()
        config = CanaryReleaseConfig(
            baseline_version="v1",
            candidate_version="v2",
            traffic_steps=[10, 25, 50, 75, 100],
            max_error_rate=0.1,
            max_latency_p99_ms=1000.0,
            min_requests_for_evaluation=50,
        )
        release = controller.create_release("custom-release", config)
        assert release.config.traffic_steps == [10, 25, 50, 75, 100]
        assert release.config.max_error_rate == 0.1
        assert release.config.max_latency_p99_ms == 1000.0
        assert release.config.min_requests_for_evaluation == 50

    def test_create_duplicate_release_raises(self):
        controller = CanaryController()
        config = CanaryReleaseConfig(baseline_version="v1", candidate_version="v2")
        controller.create_release("dup", config)
        with pytest.raises(ReleaseAlreadyExistsError):
            controller.create_release("dup", config)

    def test_create_release_empty_name_raises(self):
        controller = CanaryController()
        config = CanaryReleaseConfig(baseline_version="v1", candidate_version="v2")
        with pytest.raises(ValueError, match="release name must not be empty"):
            controller.create_release("", config)


class TestCanaryReleaseConfigValidation:
    def test_same_baseline_and_candidate_raises(self):
        controller = CanaryController()
        config = CanaryReleaseConfig(baseline_version="v1", candidate_version="v1")
        with pytest.raises(ValueError, match="must be different"):
            controller.create_release("test", config)

    def test_empty_baseline_raises(self):
        with pytest.raises(ValueError, match="baseline_version must not be empty"):
            CanaryController().create_release(
                "test", CanaryReleaseConfig(baseline_version="", candidate_version="v2")
            )

    def test_empty_candidate_raises(self):
        with pytest.raises(ValueError, match="candidate_version must not be empty"):
            CanaryController().create_release(
                "test", CanaryReleaseConfig(baseline_version="v1", candidate_version="")
            )

    def test_empty_traffic_steps_raises(self):
        controller = CanaryController()
        config = CanaryReleaseConfig(
            baseline_version="v1", candidate_version="v2", traffic_steps=[]
        )
        with pytest.raises(InvalidTrafficPercentageError, match="must not be empty"):
            controller.create_release("test", config)

    def test_invalid_traffic_step_raises(self):
        controller = CanaryController()
        config = CanaryReleaseConfig(
            baseline_version="v1", candidate_version="v2", traffic_steps=[-1, 50]
        )
        with pytest.raises(InvalidTrafficPercentageError):
            controller.create_release("test", config)

        config2 = CanaryReleaseConfig(
            baseline_version="v1", candidate_version="v2", traffic_steps=[50, 101]
        )
        with pytest.raises(InvalidTrafficPercentageError):
            controller.create_release("test2", config2)

    def test_non_increasing_traffic_steps_raises(self):
        controller = CanaryController()
        config = CanaryReleaseConfig(
            baseline_version="v1", candidate_version="v2", traffic_steps=[50, 20, 100]
        )
        with pytest.raises(InvalidTrafficPercentageError, match="strictly increasing"):
            controller.create_release("test", config)

    def test_invalid_error_rate_raises(self):
        controller = CanaryController()
        config = CanaryReleaseConfig(
            baseline_version="v1", candidate_version="v2", max_error_rate=-0.1
        )
        with pytest.raises(InvalidMetricsThresholdError):
            controller.create_release("test", config)

        config2 = CanaryReleaseConfig(
            baseline_version="v1", candidate_version="v2", max_error_rate=1.5
        )
        with pytest.raises(InvalidMetricsThresholdError):
            controller.create_release("test2", config2)

    def test_invalid_latency_threshold_raises(self):
        controller = CanaryController()
        config = CanaryReleaseConfig(
            baseline_version="v1", candidate_version="v2", max_latency_p99_ms=0
        )
        with pytest.raises(InvalidMetricsThresholdError):
            controller.create_release("test", config)

    def test_invalid_min_requests_raises(self):
        controller = CanaryController()
        config = CanaryReleaseConfig(
            baseline_version="v1", candidate_version="v2", min_requests_for_evaluation=0
        )
        with pytest.raises(InvalidMetricsThresholdError):
            controller.create_release("test", config)


class TestCanaryReleaseLifecycle:
    def setup_method(self):
        self.controller = CanaryController()
        self.config = CanaryReleaseConfig(
            baseline_version="v1",
            candidate_version="v2",
            traffic_steps=[1, 5, 20, 50, 100],
            min_requests_for_evaluation=5,
        )
        self.controller.create_release("test", self.config)

    def test_start_release(self):
        release = self.controller.start_release("test")
        assert release.phase == CanaryPhase.RUNNING
        assert release.current_step_index == 0
        assert release.current_traffic_percentage == 1
        assert release.started_at is not None

    def test_start_nonexistent_release_raises(self):
        with pytest.raises(ReleaseNotFoundError):
            self.controller.start_release("nonexistent")

    def test_start_running_release_raises(self):
        self.controller.start_release("test")
        with pytest.raises(InvalidReleasePhaseError):
            self.controller.start_release("test")

    def test_pause_release(self):
        self.controller.start_release("test")
        release = self.controller.pause_release("test")
        assert release.phase == CanaryPhase.PAUSED

    def test_pause_non_running_release_raises(self):
        with pytest.raises(InvalidReleasePhaseError):
            self.controller.pause_release("test")

    def test_resume_release(self):
        self.controller.start_release("test")
        self.controller.pause_release("test")
        release = self.controller.resume_release("test")
        assert release.phase == CanaryPhase.RUNNING

    def test_resume_non_paused_release_raises(self):
        with pytest.raises(InvalidReleasePhaseError):
            self.controller.resume_release("test")

    def test_advance_traffic_steps(self):
        self.controller.start_release("test")
        expected_steps = [1, 5, 20, 50, 100]
        for idx, expected_pct in enumerate(expected_steps):
            release = self.controller.get_release("test")
            assert release.current_traffic_percentage == expected_pct
            assert release.current_step_index == idx
            if idx < len(expected_steps) - 1:
                self.controller.advance_traffic("test")

    def test_advance_final_step_promotes(self):
        self.controller.start_release("test")
        for _ in range(4):
            self.controller.advance_traffic("test")
        release = self.controller.advance_traffic("test")
        assert release.phase == CanaryPhase.PROMOTED
        assert release.current_traffic_percentage == 100
        assert release.promoted_at is not None

    def test_advance_non_running_release_raises(self):
        with pytest.raises(InvalidReleasePhaseError):
            self.controller.advance_traffic("test")

    def test_set_traffic_percentage(self):
        self.controller.start_release("test")
        release = self.controller.set_traffic_percentage("test", 33)
        assert release.current_traffic_percentage == 33

    def test_set_invalid_traffic_percentage_raises(self):
        self.controller.start_release("test")
        with pytest.raises(InvalidTrafficPercentageError):
            self.controller.set_traffic_percentage("test", -5)
        with pytest.raises(InvalidTrafficPercentageError):
            self.controller.set_traffic_percentage("test", 150)

    def test_set_traffic_in_invalid_phase_raises(self):
        with pytest.raises(InvalidReleasePhaseError):
            self.controller.set_traffic_percentage("test", 50)


class TestCanaryRollback:
    def setup_method(self):
        self.controller = CanaryController()
        self.config = CanaryReleaseConfig(
            baseline_version="v1",
            candidate_version="v2",
            traffic_steps=[10, 50, 100],
            min_requests_for_evaluation=5,
        )
        self.controller.create_release("test", self.config)

    def test_manual_rollback(self):
        self.controller.start_release("test")
        self.controller.advance_traffic("test")
        release = self.controller.rollback("test", reason="发现问题")
        assert release.phase == CanaryPhase.ROLLED_BACK
        assert release.current_traffic_percentage == 0
        assert release.rolled_back_at is not None
        assert len(release.rollback_records) == 1
        record = release.rollback_records[0]
        assert record.reason == RollbackReason.MANUAL
        assert record.detail == "发现问题"
        assert record.traffic_percentage_at_rollback == 0

    def test_rollback_paused_release(self):
        self.controller.start_release("test")
        self.controller.pause_release("test")
        release = self.controller.rollback("test", reason="暂停时回滚")
        assert release.phase == CanaryPhase.ROLLED_BACK

    def test_rollback_draft_raises(self):
        with pytest.raises(RollbackNotAllowedError):
            self.controller.rollback("test")

    def test_rollback_already_rolled_back_raises(self):
        self.controller.start_release("test")
        self.controller.rollback("test")
        with pytest.raises(RollbackNotAllowedError):
            self.controller.rollback("test")

    def test_rollback_promoted_raises(self):
        self.controller.start_release("test")
        for _ in range(3):
            self.controller.advance_traffic("test")
        with pytest.raises(RollbackNotAllowedError):
            self.controller.rollback("test")

    def test_get_rollback_history(self):
        self.controller.start_release("test")
        self.controller.rollback("test", reason="第一次回滚")
        history = self.controller.get_rollback_history("test")
        assert len(history) == 1
        assert history[0].reason == RollbackReason.MANUAL
        assert history[0].detail == "第一次回滚"


# ============================================================
# Boundary Conditions
# ============================================================


class TestBoundaryZeroAndHundredPercent:
    def test_zero_percent_release(self):
        controller = CanaryController()
        config = CanaryReleaseConfig(
            baseline_version="v1",
            candidate_version="v2",
            traffic_steps=[0, 100],
            min_requests_for_evaluation=5,
        )
        controller.create_release("zero-test", config)
        controller.start_release("zero-test")
        release = controller.get_release("zero-test")
        assert release.current_traffic_percentage == 0

        for i in range(1000):
            version, vtype = controller.route_request("zero-test", f"user-{i}")
            assert version == "v1"
            assert vtype == VersionType.BASELINE

    def test_single_step_100_percent(self):
        controller = CanaryController()
        config = CanaryReleaseConfig(
            baseline_version="v1",
            candidate_version="v2",
            traffic_steps=[100],
            min_requests_for_evaluation=5,
        )
        controller.create_release("full-test", config)
        controller.start_release("full-test")
        release = controller.get_release("full-test")
        assert release.current_traffic_percentage == 100
        assert release.phase == CanaryPhase.RUNNING

        for i in range(1000):
            version, vtype = controller.route_request("full-test", f"user-{i}")
            assert version == "v2"
            assert vtype == VersionType.CANDIDATE

    def test_promoted_release_routes_all_candidate(self):
        controller = CanaryController()
        config = CanaryReleaseConfig(
            baseline_version="v1",
            candidate_version="v2",
            traffic_steps=[100],
            min_requests_for_evaluation=5,
        )
        controller.create_release("promoted-test", config)
        controller.start_release("promoted-test")
        controller.advance_traffic("promoted-test")

        for i in range(500):
            version, vtype = controller.route_request("promoted-test", f"user-{i}")
            assert version == "v2"
            assert vtype == VersionType.CANDIDATE

    def test_rolled_back_release_routes_all_baseline(self):
        controller = CanaryController()
        config = CanaryReleaseConfig(
            baseline_version="v1",
            candidate_version="v2",
            traffic_steps=[100],
            min_requests_for_evaluation=5,
        )
        controller.create_release("rollback-test", config)
        controller.start_release("rollback-test")
        controller.rollback("rollback-test")

        for i in range(500):
            version, vtype = controller.route_request("rollback-test", f"user-{i}")
            assert version == "v1"
            assert vtype == VersionType.BASELINE


class TestMetricsThresholdBoundary:
    def test_error_rate_at_threshold_not_rolled_back(self):
        controller = CanaryController()
        config = CanaryReleaseConfig(
            baseline_version="v1",
            candidate_version="v2",
            traffic_steps=[100],
            max_error_rate=0.10,
            min_requests_for_evaluation=10,
        )
        controller.create_release("threshold-test", config)
        controller.start_release("threshold-test")

        for i in range(100):
            controller.route_request("threshold-test", f"user-{i}")
            is_error = i < 10
            controller.record_request_metrics("threshold-test", latency_ms=50.0, is_error=is_error)

        healthy, rollback_record = controller.evaluate_metrics("threshold-test")
        assert healthy is True
        assert rollback_record is None

    def test_error_rate_above_threshold_triggers_rollback(self):
        controller = CanaryController()
        config = CanaryReleaseConfig(
            baseline_version="v1",
            candidate_version="v2",
            traffic_steps=[100],
            max_error_rate=0.10,
            min_requests_for_evaluation=10,
        )
        controller.create_release("error-test", config)
        controller.start_release("error-test")

        for i in range(100):
            controller.route_request("error-test", f"user-{i}")
            is_error = i < 15
            controller.record_request_metrics("error-test", latency_ms=50.0, is_error=is_error)

        healthy, rollback_record = controller.evaluate_metrics("error-test")
        assert healthy is False
        assert rollback_record is not None
        assert rollback_record.reason == RollbackReason.ERROR_RATE_EXCEEDED
        release = controller.get_release("error-test")
        assert release.phase == CanaryPhase.ROLLED_BACK

    def test_latency_at_threshold_not_rolled_back(self):
        controller = CanaryController()
        config = CanaryReleaseConfig(
            baseline_version="v1",
            candidate_version="v2",
            traffic_steps=[100],
            max_latency_p99_ms=500.0,
            min_requests_for_evaluation=10,
        )
        controller.create_release("latency-threshold", config)
        controller.start_release("latency-threshold")

        for i in range(100):
            controller.route_request("latency-threshold", f"user-{i}")
            latency = 100.0 if i < 99 else 500.0
            controller.record_request_metrics("latency-threshold", latency_ms=latency, is_error=False)

        healthy, rollback_record = controller.evaluate_metrics("latency-threshold")
        assert healthy is True
        assert rollback_record is None

    def test_latency_above_threshold_triggers_rollback(self):
        controller = CanaryController()
        config = CanaryReleaseConfig(
            baseline_version="v1",
            candidate_version="v2",
            traffic_steps=[100],
            max_latency_p99_ms=500.0,
            min_requests_for_evaluation=10,
        )
        controller.create_release("latency-test", config)
        controller.start_release("latency-test")

        for i in range(100):
            controller.route_request("latency-test", f"user-{i}")
            latency = 100.0 if i < 99 else 600.0
            controller.record_request_metrics("latency-test", latency_ms=latency, is_error=False)

        healthy, rollback_record = controller.evaluate_metrics("latency-test")
        assert healthy is False
        assert rollback_record is not None
        assert rollback_record.reason == RollbackReason.LATENCY_EXCEEDED

    def test_below_min_requests_skips_evaluation(self):
        controller = CanaryController()
        config = CanaryReleaseConfig(
            baseline_version="v1",
            candidate_version="v2",
            traffic_steps=[100],
            max_error_rate=0.01,
            min_requests_for_evaluation=100,
        )
        controller.create_release("min-req-test", config)
        controller.start_release("min-req-test")

        for i in range(10):
            controller.route_request("min-req-test", f"user-{i}")
            controller.record_request_metrics("min-req-test", latency_ms=50.0, is_error=True)

        healthy, rollback_record = controller.evaluate_metrics("min-req-test")
        assert healthy is True
        assert rollback_record is None
        release = controller.get_release("min-req-test")
        assert release.phase == CanaryPhase.RUNNING


# ============================================================
# Error and Edge Cases
# ============================================================


class TestErrorCases:
    def test_get_nonexistent_release_raises(self):
        controller = CanaryController()
        with pytest.raises(ReleaseNotFoundError):
            controller.get_release("nonexistent")

    def test_route_request_invalid_phase_raises(self):
        controller = CanaryController()
        config = CanaryReleaseConfig(baseline_version="v1", candidate_version="v2")
        controller.create_release("draft-release", config)
        with pytest.raises(InvalidReleasePhaseError):
            controller.route_request("draft-release", "user-1")

    def test_record_negative_latency_raises(self):
        controller = CanaryController()
        config = CanaryReleaseConfig(baseline_version="v1", candidate_version="v2")
        controller.create_release("test", config)
        with pytest.raises(ValueError, match="latency_ms must not be negative"):
            controller.record_request_metrics("test", latency_ms=-10.0)

    def test_evaluate_metrics_non_running_raises(self):
        controller = CanaryController()
        config = CanaryReleaseConfig(baseline_version="v1", candidate_version="v2")
        controller.create_release("draft-test", config)
        with pytest.raises(InvalidReleasePhaseError):
            controller.evaluate_metrics("draft-test")

    def test_list_releases(self):
        controller = CanaryController()
        config = CanaryReleaseConfig(baseline_version="v1", candidate_version="v2")
        controller.create_release("rel-1", config)
        controller.create_release("rel-2", config)
        releases = controller.list_releases()
        assert len(releases) == 2
        names = {r.name for r in releases}
        assert names == {"rel-1", "rel-2"}


# ============================================================
# Full Integration Flow
# ============================================================


class TestFullCanaryWorkflow:
    def test_successful_canary_promotion(self):
        controller = CanaryController()
        config = CanaryReleaseConfig(
            baseline_version="v1.0.0",
            candidate_version="v2.0.0",
            traffic_steps=[10, 50, 100],
            max_error_rate=0.05,
            max_latency_p99_ms=500.0,
            min_requests_for_evaluation=10,
        )
        controller.create_release("full-flow", config)
        controller.start_release("full-flow")

        for step_idx in range(3):
            release = controller.get_release("full-flow")
            assert release.phase == CanaryPhase.RUNNING

            for i in range(50):
                controller.route_request("full-flow", f"step{step_idx}-user-{i}")
                controller.record_request_metrics(
                    "full-flow", latency_ms=50.0, is_error=False
                )

            healthy, rollback_record = controller.evaluate_metrics("full-flow")
            assert healthy is True
            assert rollback_record is None

            if step_idx < 2:
                controller.advance_traffic("full-flow")
            else:
                release = controller.advance_traffic("full-flow")
                assert release.phase == CanaryPhase.PROMOTED

    def test_canary_auto_rollback_on_high_error_rate(self):
        controller = CanaryController()
        config = CanaryReleaseConfig(
            baseline_version="v1",
            candidate_version="v2",
            traffic_steps=[50, 100],
            max_error_rate=0.05,
            min_requests_for_evaluation=20,
        )
        controller.create_release("auto-rollback", config)
        controller.start_release("full-flow" if False else "auto-rollback")
        controller.advance_traffic("auto-rollback")

        for i in range(100):
            controller.route_request("auto-rollback", f"user-{i}")
            is_error = i < 20
            controller.record_request_metrics(
                "auto-rollback", latency_ms=30.0, is_error=is_error
            )

        healthy, rollback_record = controller.evaluate_metrics("auto-rollback")
        assert healthy is False
        assert rollback_record is not None
        assert rollback_record.reason == RollbackReason.ERROR_RATE_EXCEEDED
        assert "Error rate" in rollback_record.detail
        release = controller.get_release("auto-rollback")
        assert release.phase == CanaryPhase.ROLLED_BACK
        assert len(release.rollback_records) == 1
        assert len(release.metrics_history) >= 1
