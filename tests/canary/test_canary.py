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


class TestTrafficRouterPerReleaseIsolation:
    def test_multiple_releases_have_independent_versions(self):
        router = TrafficRouter()
        router.register_release("release-a", "v1", "v2")
        router.register_release("release-b", "v3", "v4")

        router.set_traffic_percentage("release-a", 100)
        router.set_traffic_percentage("release-b", 0)

        for i in range(100):
            version_a, type_a = router.route("release-a", f"user-{i}")
            version_b, type_b = router.route("release-b", f"user-{i}")
            assert version_a == "v2"
            assert type_a == VersionType.CANDIDATE
            assert version_b == "v3"
            assert type_b == VersionType.BASELINE

    def test_multiple_releases_have_independent_traffic_percentage(self):
        router = TrafficRouter()
        router.register_release("r1", "base1", "cand1")
        router.register_release("r2", "base2", "cand2")

        router.set_traffic_percentage("r1", 10)
        router.set_traffic_percentage("r2", 90)

        assert router.get_traffic_percentage("r1") == 10
        assert router.get_traffic_percentage("r2") == 90

    def test_multiple_releases_have_independent_stats(self):
        router = TrafficRouter()
        router.register_release("r1", "b1", "c1")
        router.register_release("r2", "b2", "c2")

        router.set_traffic_percentage("r1", 100)
        router.set_traffic_percentage("r2", 100)

        for i in range(10):
            router.route("r1", f"u-{i}")
            router.record_metrics("r1", VersionType.CANDIDATE, latency_ms=50.0, is_error=False)
        for i in range(5):
            router.route("r2", f"u-{i}")
            router.record_metrics("r2", VersionType.CANDIDATE, latency_ms=100.0, is_error=True)

        stats1 = router.get_stats("r1")
        stats2 = router.get_stats("r2")

        assert stats1.candidate_requests == 10
        assert stats1.candidate_errors == 0
        assert stats1.candidate_avg_latency_ms == pytest.approx(50.0)

        assert stats2.candidate_requests == 5
        assert stats2.candidate_errors == 5
        assert stats2.candidate_avg_latency_ms == pytest.approx(100.0)

    def test_register_release_same_version_shared(self):
        router = TrafficRouter()
        router.register_release("r1", "v1", "v2")
        router.register_release("r2", "v1", "v2")
        assert len(router.list_versions()) == 2

    def test_route_nonexistent_release_raises(self):
        router = TrafficRouter()
        with pytest.raises(ReleaseNotFoundError):
            router.route("nonexistent", "user-1")

    def test_set_traffic_nonexistent_release_raises(self):
        router = TrafficRouter()
        with pytest.raises(ReleaseNotFoundError):
            router.set_traffic_percentage("nonexistent", 50)


class TestTrafficRouterMetricsSeparation:
    def setup_method(self):
        self.router = TrafficRouter()
        self.router.register_release("test", "v1", "v2")
        self.router.set_traffic_percentage("test", 50)

    def test_baseline_and_candidate_metrics_separated(self):
        for i in range(200):
            _, vtype = self.router.route("test", f"user-{i}")
            if vtype == VersionType.BASELINE:
                self.router.record_metrics("test", VersionType.BASELINE, latency_ms=10.0, is_error=False)
            else:
                self.router.record_metrics("test", VersionType.CANDIDATE, latency_ms=100.0, is_error=(i % 10 == 0))

        stats = self.router.get_stats("test")
        assert stats.total_requests == 200
        assert stats.baseline_requests + stats.candidate_requests == 200
        assert stats.baseline_avg_latency_ms == pytest.approx(10.0, abs=1.0)
        assert stats.candidate_avg_latency_ms == pytest.approx(100.0, abs=5.0)
        assert stats.baseline_errors == 0
        assert stats.candidate_error_rate > 0

    def test_baseline_p99_latency(self):
        self.router.set_traffic_percentage("test", 0)
        for i in range(100):
            _, vtype = self.router.route("test", f"u-{i}")
            assert vtype == VersionType.BASELINE
            self.router.record_metrics(
                "test",
                VersionType.BASELINE,
                latency_ms=5.0 if i < 99 else 500.0,
                is_error=False,
            )
        stats = self.router.get_stats("test")
        assert stats.baseline_requests == 100
        assert stats.baseline_p99_latency_ms >= 400.0

    def test_baseline_error_rate(self):
        self.router.set_traffic_percentage("test", 0)
        for i in range(100):
            _, vtype = self.router.route("test", f"u-{i}")
            assert vtype == VersionType.BASELINE
            self.router.record_metrics(
                "test",
                VersionType.BASELINE,
                latency_ms=10.0,
                is_error=(i < 10),
            )
        stats = self.router.get_stats("test")
        assert stats.baseline_requests == 100
        assert stats.baseline_error_rate == pytest.approx(0.10)

    def test_empty_stats_properties_return_zero(self):
        stats = self.router.get_stats("test")
        assert stats.baseline_error_rate == 0.0
        assert stats.baseline_avg_latency_ms == 0.0
        assert stats.baseline_p99_latency_ms == 0.0
        assert stats.candidate_error_rate == 0.0
        assert stats.candidate_avg_latency_ms == 0.0
        assert stats.candidate_p99_latency_ms == 0.0


class TestTrafficRouterVersionManagement:
    def test_register_release(self):
        router = TrafficRouter()
        router.register_release(
            "rel-1",
            baseline_version="v1.0.0",
            candidate_version="v2.0.0",
            baseline_description="stable baseline",
            candidate_description="new candidate",
        )
        versions = router.list_versions()
        assert len(versions) == 2
        version_names = {v.version for v in versions}
        assert version_names == {"v1.0.0", "v2.0.0"}

    def test_register_release_same_baseline_candidate_raises(self):
        router = TrafficRouter()
        with pytest.raises(ValueError, match="must be different"):
            router.register_release("rel", "v1", "v1")

    def test_list_versions(self):
        router = TrafficRouter()
        router.register_release("r1", "v1", "v2")
        router.register_release("r2", "v3", "v4")
        assert len(router.list_versions()) == 4

    def test_get_version(self):
        router = TrafficRouter()
        router.register_release("r", "v1", "v2")
        info = router.get_version("v1")
        assert info.version == "v1"

    def test_get_nonexistent_version_raises(self):
        router = TrafficRouter()
        with pytest.raises(VersionNotFoundError):
            router.get_version("nonexistent")


class TestTrafficRouterRouting:
    def setup_method(self):
        self.router = TrafficRouter()
        self.router.register_release("test", "v1", "v2")

    def test_route_empty_key_raises(self):
        with pytest.raises(ValueError, match="request_key must not be empty"):
            self.router.route("test", "")

    def test_route_empty_release_name_raises(self):
        with pytest.raises(ValueError, match="release_name must not be empty"):
            self.router.route("", "user-1")

    def test_zero_percent_all_baseline(self):
        self.router.set_traffic_percentage("test", 0)
        for i in range(1000):
            version, vtype = self.router.route("test", f"user-{i}")
            assert version == "v1"
            assert vtype == VersionType.BASELINE

    def test_hundred_percent_all_candidate(self):
        self.router.set_traffic_percentage("test", 100)
        for i in range(1000):
            version, vtype = self.router.route("test", f"user-{i}")
            assert version == "v2"
            assert vtype == VersionType.CANDIDATE

    def test_fifty_percent_split(self):
        self.router.set_traffic_percentage("test", 50)
        counts = {"v1": 0, "v2": 0}
        for i in range(10000):
            version, _ = self.router.route("test", f"user-{i}")
            counts[version] += 1
        assert 4000 <= counts["v1"] <= 6000
        assert 4000 <= counts["v2"] <= 6000

    def test_route_consistency_same_key(self):
        self.router.set_traffic_percentage("test", 30)
        results = set()
        for _ in range(50):
            version, vtype = self.router.route("test", "same-user")
            results.add((version, vtype))
        assert len(results) == 1

    def test_set_invalid_traffic_percentage_raises(self):
        with pytest.raises(InvalidTrafficPercentageError):
            self.router.set_traffic_percentage("test", -1)
        with pytest.raises(InvalidTrafficPercentageError):
            self.router.set_traffic_percentage("test", 101)


class TestTrafficRouterStats:
    def setup_method(self):
        self.router = TrafficRouter()
        self.router.register_release("test", "v1", "v2")
        self.router.set_traffic_percentage("test", 100)

    def test_record_candidate_metrics(self):
        for _ in range(10):
            self.router.route("test", "user-x")
            self.router.record_candidate_metrics("test", latency_ms=100.0, is_error=False)
        stats = self.router.get_stats("test")
        assert stats.candidate_requests == 10
        assert stats.candidate_errors == 0
        assert stats.candidate_avg_latency_ms == pytest.approx(100.0)

    def test_record_candidate_errors(self):
        for i in range(20):
            self.router.route("test", f"user-{i}")
            is_error = i % 4 == 0
            self.router.record_candidate_metrics("test", latency_ms=50.0, is_error=is_error)
        stats = self.router.get_stats("test")
        assert stats.candidate_requests == 20
        assert stats.candidate_errors == 5
        assert stats.candidate_error_rate == pytest.approx(0.25)

    def test_candidate_p99_latency(self):
        for i in range(100):
            self.router.route("test", f"user-{i}")
            latency = 10.0 if i < 99 else 1000.0
            self.router.record_candidate_metrics("test", latency_ms=latency, is_error=False)
        stats = self.router.get_stats("test")
        assert stats.candidate_p99_latency_ms >= 900.0

    def test_empty_stats(self):
        stats = self.router.get_stats("test")
        assert stats.total_requests == 0
        assert stats.candidate_error_rate == 0.0
        assert stats.candidate_avg_latency_ms == 0.0
        assert stats.candidate_p99_latency_ms == 0.0

    def test_reset_stats(self):
        for i in range(50):
            self.router.route("test", f"user-{i}")
            self.router.record_candidate_metrics("test", latency_ms=30.0, is_error=False)
        self.router.reset_stats("test")
        stats = self.router.get_stats("test")
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


class TestCanaryRollbackAuditRecords:
    def setup_method(self):
        self.controller = CanaryController()
        self.config = CanaryReleaseConfig(
            baseline_version="v1",
            candidate_version="v2",
            traffic_steps=[10, 50, 100],
            min_requests_for_evaluation=5,
        )
        self.controller.create_release("test", self.config)

    def test_manual_rollback_preserves_traffic_percentage(self):
        self.controller.start_release("test")
        self.controller.advance_traffic("test")
        release_before = self.controller.get_release("test")
        traffic_before = release_before.current_traffic_percentage
        assert traffic_before == 50

        release = self.controller.rollback("test", reason="发现问题")
        assert release.phase == CanaryPhase.ROLLED_BACK
        assert release.current_traffic_percentage == 0
        assert release.rolled_back_at is not None
        assert len(release.rollback_records) == 1

        record = release.rollback_records[0]
        assert record.reason == RollbackReason.MANUAL
        assert record.detail == "发现问题"
        assert record.traffic_percentage_at_rollback == 50
        assert record.metrics_snapshot is not None
        assert record.metrics_snapshot.current_traffic_percentage == 50

    def test_rollback_at_first_step_preserves_traffic(self):
        self.controller.start_release("test")
        release = self.controller.rollback("test", reason="early rollback")
        record = release.rollback_records[0]
        assert record.traffic_percentage_at_rollback == 10

    def test_rollback_at_100_percent_preserves_100_percent(self):
        self.controller.start_release("test")
        for _ in range(2):
            self.controller.advance_traffic("test")
        release = self.controller.rollback("test", reason="late rollback")
        record = release.rollback_records[0]
        assert record.traffic_percentage_at_rollback == 100

    def test_metrics_triggered_rollback_preserves_traffic_percentage(self):
        controller = CanaryController()
        config = CanaryReleaseConfig(
            baseline_version="v1",
            candidate_version="v2",
            traffic_steps=[20, 100],
            max_error_rate=0.10,
            min_requests_for_evaluation=10,
        )
        controller.create_release("metrics-rb", config)
        controller.start_release("metrics-rb")

        for i in range(100):
            controller.route_request("metrics-rb", f"user-{i}")
            controller.record_candidate_metrics(
                "metrics-rb", latency_ms=50.0, is_error=(i < 20)
            )

        release_before = controller.get_release("metrics-rb")
        traffic_before = release_before.current_traffic_percentage

        healthy, rollback_record = controller.evaluate_metrics("metrics-rb")
        assert healthy is False
        assert rollback_record is not None
        assert rollback_record.reason == RollbackReason.ERROR_RATE_EXCEEDED
        assert rollback_record.traffic_percentage_at_rollback == traffic_before
        assert rollback_record.traffic_percentage_at_rollback == 20

        release = controller.get_release("metrics-rb")
        assert release.phase == CanaryPhase.ROLLED_BACK
        assert len(release.rollback_records) == 1
        assert release.rollback_records[0].traffic_percentage_at_rollback == 20

    def test_latency_triggered_rollback_preserves_traffic_percentage(self):
        controller = CanaryController()
        config = CanaryReleaseConfig(
            baseline_version="v1",
            candidate_version="v2",
            traffic_steps=[50],
            max_latency_p99_ms=500.0,
            min_requests_for_evaluation=10,
        )
        controller.create_release("latency-rb", config)
        controller.start_release("latency-rb")

        for i in range(100):
            controller.route_request("latency-rb", f"user-{i}")
            latency = 50.0 if i < 99 else 600.0
            controller.record_candidate_metrics("latency-rb", latency_ms=latency, is_error=False)

        healthy, rollback_record = controller.evaluate_metrics("latency-rb")
        assert healthy is False
        assert rollback_record is not None
        assert rollback_record.reason == RollbackReason.LATENCY_EXCEEDED
        assert rollback_record.traffic_percentage_at_rollback == 50

    def test_rollback_paused_release_preserves_traffic(self):
        self.controller.start_release("test")
        self.controller.advance_traffic("test")
        self.controller.pause_release("test")

        release_before = self.controller.get_release("test")
        traffic_before = release_before.current_traffic_percentage

        release = self.controller.rollback("test", reason="暂停时回滚")
        assert release.phase == CanaryPhase.ROLLED_BACK
        record = release.rollback_records[0]
        assert record.traffic_percentage_at_rollback == traffic_before

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
        for _ in range(2):
            self.controller.advance_traffic("test")
        self.controller.advance_traffic("test")
        with pytest.raises(RollbackNotAllowedError):
            self.controller.rollback("test")

    def test_get_rollback_history(self):
        self.controller.start_release("test")
        self.controller.advance_traffic("test")
        self.controller.rollback("test", reason="第一次回滚")
        history = self.controller.get_rollback_history("test")
        assert len(history) == 1
        assert history[0].reason == RollbackReason.MANUAL
        assert history[0].detail == "第一次回滚"
        assert history[0].traffic_percentage_at_rollback == 50


class TestCanaryMetricsRecordingSeparation:
    def test_record_baseline_and_candidate_metrics_separated(self):
        controller = CanaryController()
        config = CanaryReleaseConfig(
            baseline_version="v1",
            candidate_version="v2",
            traffic_steps=[50],
            min_requests_for_evaluation=10,
        )
        controller.create_release("separated", config)
        controller.start_release("separated")

        baseline_count = 0
        candidate_count = 0
        for i in range(200):
            version, vtype = controller.route_request("separated", f"user-{i}")
            if vtype == VersionType.BASELINE:
                controller.record_baseline_metrics(
                    "separated", latency_ms=10.0, is_error=False
                )
                baseline_count += 1
            else:
                controller.record_candidate_metrics(
                    "separated", latency_ms=100.0, is_error=(i % 10 == 0)
                )
                candidate_count += 1

        stats = controller.get_traffic_stats("separated")
        assert stats.total_requests == 200
        assert stats.baseline_requests == baseline_count
        assert stats.candidate_requests == candidate_count
        assert stats.baseline_avg_latency_ms == pytest.approx(10.0)
        assert stats.candidate_avg_latency_ms == pytest.approx(100.0)
        assert stats.baseline_errors == 0
        assert stats.candidate_error_rate > 0

    def test_record_request_metrics_with_version_type(self):
        controller = CanaryController()
        config = CanaryReleaseConfig(
            baseline_version="v1",
            candidate_version="v2",
            traffic_steps=[100],
            min_requests_for_evaluation=10,
        )
        controller.create_release("vt", config)
        controller.start_release("vt")

        for i in range(50):
            controller.route_request("vt", f"u-{i}")
            controller.record_request_metrics(
                "vt", VersionType.CANDIDATE, latency_ms=30.0, is_error=False
            )

        stats = controller.get_traffic_stats("vt")
        assert stats.candidate_requests == 50
        assert stats.candidate_avg_latency_ms == pytest.approx(30.0)

    def test_record_negative_latency_raises(self):
        controller = CanaryController()
        config = CanaryReleaseConfig(baseline_version="v1", candidate_version="v2")
        controller.create_release("test", config)
        with pytest.raises(ValueError, match="latency_ms must not be negative"):
            controller.record_request_metrics(
                "test", VersionType.CANDIDATE, latency_ms=-10.0
            )

    def test_baseline_metrics_do_not_affect_candidate_evaluation(self):
        controller = CanaryController()
        config = CanaryReleaseConfig(
            baseline_version="v1",
            candidate_version="v2",
            traffic_steps=[50],
            max_error_rate=0.05,
            min_requests_for_evaluation=10,
        )
        controller.create_release("isolated", config)
        controller.start_release("isolated")

        baseline_count = 0
        candidate_count = 0
        for i in range(400):
            _, vtype = controller.route_request("isolated", f"u-{i}")
            if vtype == VersionType.CANDIDATE:
                controller.record_candidate_metrics(
                    "isolated", latency_ms=50.0, is_error=False
                )
                candidate_count += 1
            else:
                controller.record_baseline_metrics(
                    "isolated", latency_ms=10.0, is_error=True
                )
                baseline_count += 1

        stats = controller.get_traffic_stats("isolated")
        assert stats.candidate_requests == candidate_count
        assert stats.baseline_requests == baseline_count
        assert stats.candidate_error_rate == 0.0
        assert stats.baseline_error_rate == 1.0

        healthy, rollback_record = controller.evaluate_metrics("isolated")
        assert healthy is True
        assert rollback_record is None


# ============================================================
# Multiple Releases Concurrent Routing
# ============================================================


class TestMultipleReleasesConcurrentRouting:
    def test_two_releases_with_different_versions_routed_independently(self):
        controller = CanaryController()

        config_a = CanaryReleaseConfig(
            baseline_version="service-a-v1",
            candidate_version="service-a-v2",
            traffic_steps=[100],
            min_requests_for_evaluation=10,
        )
        config_b = CanaryReleaseConfig(
            baseline_version="service-b-v1",
            candidate_version="service-b-v2",
            traffic_steps=[0],
            min_requests_for_evaluation=10,
        )

        controller.create_release("service-a", config_a)
        controller.create_release("service-b", config_b)

        controller.start_release("service-a")
        controller.start_release("service-b")

        for i in range(100):
            version_a, type_a = controller.route_request("service-a", f"req-{i}")
            version_b, type_b = controller.route_request("service-b", f"req-{i}")

            assert version_a == "service-a-v2"
            assert type_a == VersionType.CANDIDATE
            assert version_b == "service-b-v1"
            assert type_b == VersionType.BASELINE

    def test_three_releases_different_traffic_percentages(self):
        controller = CanaryController()

        for idx, (name, baseline, candidate, step) in enumerate([
            ("rel-1", "b1", "c1", 100),
            ("rel-2", "b2", "c2", 0),
            ("rel-3", "b3", "c3", 50),
        ]):
            config = CanaryReleaseConfig(
                baseline_version=baseline,
                candidate_version=candidate,
                traffic_steps=[step],
                min_requests_for_evaluation=5,
            )
            controller.create_release(name, config)
            controller.start_release(name)

        for i in range(200):
            v1, t1 = controller.route_request("rel-1", f"u-{i}")
            v2, t2 = controller.route_request("rel-2", f"u-{i}")
            v3, t3 = controller.route_request("rel-3", f"u-{i}")
            assert v1 == "c1" and t1 == VersionType.CANDIDATE
            assert v2 == "b2" and t2 == VersionType.BASELINE
            controller.record_candidate_metrics("rel-1", latency_ms=10.0)
            controller.record_baseline_metrics("rel-2", latency_ms=5.0)
            if t3 == VersionType.CANDIDATE:
                assert v3 == "c3"
                controller.record_candidate_metrics("rel-3", latency_ms=10.0)
            else:
                assert v3 == "b3"
                controller.record_baseline_metrics("rel-3", latency_ms=5.0)

        rel1_stats = controller.get_traffic_stats("rel-1")
        rel2_stats = controller.get_traffic_stats("rel-2")
        rel3_stats = controller.get_traffic_stats("rel-3")

        assert rel1_stats.candidate_requests == 200
        assert rel2_stats.baseline_requests == 200
        assert rel3_stats.baseline_requests + rel3_stats.candidate_requests == 200

    def test_one_release_rolled_back_does_not_affect_others(self):
        controller = CanaryController()

        config_a = CanaryReleaseConfig(
            baseline_version="a-v1", candidate_version="a-v2",
            traffic_steps=[100], min_requests_for_evaluation=5,
        )
        config_b = CanaryReleaseConfig(
            baseline_version="b-v1", candidate_version="b-v2",
            traffic_steps=[100], min_requests_for_evaluation=5,
        )

        controller.create_release("rel-a", config_a)
        controller.create_release("rel-b", config_b)
        controller.start_release("rel-a")
        controller.start_release("rel-b")

        controller.rollback("rel-a", reason="rollback a")

        for i in range(50):
            va, ta = controller.route_request("rel-a", f"u-{i}")
            vb, tb = controller.route_request("rel-b", f"u-{i}")
            assert va == "a-v1" and ta == VersionType.BASELINE
            assert vb == "b-v2" and tb == VersionType.CANDIDATE


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
            controller.record_candidate_metrics("threshold-test", latency_ms=50.0, is_error=is_error)

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
            controller.record_candidate_metrics("error-test", latency_ms=50.0, is_error=is_error)

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
            controller.record_candidate_metrics("latency-threshold", latency_ms=latency, is_error=False)

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
            controller.record_candidate_metrics("latency-test", latency_ms=latency, is_error=False)

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
            controller.record_candidate_metrics("min-req-test", latency_ms=50.0, is_error=True)

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
                version, vtype = controller.route_request("full-flow", f"step{step_idx}-user-{i}")
                controller.record_request_metrics(
                    "full-flow", vtype, latency_ms=50.0, is_error=False
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
        controller.start_release("auto-rollback")

        for i in range(100):
            version, vtype = controller.route_request("auto-rollback", f"user-{i}")
            is_error = vtype == VersionType.CANDIDATE and i < 20
            controller.record_request_metrics(
                "auto-rollback", vtype, latency_ms=30.0, is_error=is_error
            )

        release_before = controller.get_release("auto-rollback")
        traffic_before = release_before.current_traffic_percentage

        healthy, rollback_record = controller.evaluate_metrics("auto-rollback")
        assert healthy is False
        assert rollback_record is not None
        assert rollback_record.reason == RollbackReason.ERROR_RATE_EXCEEDED
        assert rollback_record.traffic_percentage_at_rollback == traffic_before
        assert "Error rate" in rollback_record.detail

        release = controller.get_release("auto-rollback")
        assert release.phase == CanaryPhase.ROLLED_BACK
        assert len(release.rollback_records) == 1
        assert len(release.metrics_history) >= 1
