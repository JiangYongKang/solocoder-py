from __future__ import annotations

import pytest

from solocoder_py.credential import (
    CredentialVersion,
    InvalidTrafficPercentageError,
    RotationNotFoundError,
    StableHashBucketer,
    TrafficRouter,
)


class TestStableHashBucketer:
    def test_hash_consistency_same_key(self):
        key = "user-12345"
        bucket1 = StableHashBucketer.get_bucket(key)
        bucket2 = StableHashBucketer.get_bucket(key)
        assert bucket1 == bucket2

    def test_hash_within_0_99_range(self):
        for i in range(1000):
            bucket = StableHashBucketer.get_bucket(f"request-{i}")
            assert 0 <= bucket <= 99

    def test_hash_distribution_approximately_uniform(self):
        buckets = {}
        for i in range(10000):
            b = StableHashBucketer.get_bucket(f"id-{i}")
            buckets[b] = buckets.get(b, 0) + 1
        for count in buckets.values():
            assert 50 <= count <= 150

    def test_empty_key_raises(self):
        with pytest.raises(ValueError, match="request_key must not be empty"):
            StableHashBucketer.get_bucket("")

    def test_different_keys_likely_different_buckets(self):
        buckets = set()
        for i in range(100):
            b = StableHashBucketer.get_bucket(f"diff-{i}")
            buckets.add(b)
        assert len(buckets) > 50


class TestTrafficRouterRegistration:
    def setup_method(self):
        self.router = TrafficRouter()

    def test_register_rotation_success(self):
        self.router.register_rotation("rot1", "old-cred", "new-cred")
        assert self.router.get_traffic_percentage("rot1") == 0

    def test_register_duplicate_raises(self):
        self.router.register_rotation("rot1", "old", "new")
        with pytest.raises(RotationNotFoundError, match="already registered"):
            self.router.register_rotation("rot1", "old2", "new2")

    def test_register_empty_name_raises(self):
        with pytest.raises(ValueError, match="rotation_name must not be empty"):
            self.router.register_rotation("", "old", "new")

    def test_register_empty_old_credential_raises(self):
        with pytest.raises(ValueError, match="old_credential must not be empty"):
            self.router.register_rotation("rot1", "", "new")

    def test_register_empty_new_credential_raises(self):
        with pytest.raises(ValueError, match="new_credential must not be empty"):
            self.router.register_rotation("rot1", "old", "")

    def test_register_same_old_new_raises(self):
        with pytest.raises(ValueError, match="must be different"):
            self.router.register_rotation("rot1", "same", "same")

    def test_unregister_rotation(self):
        self.router.register_rotation("rot1", "old", "new")
        self.router.unregister_rotation("rot1")
        with pytest.raises(RotationNotFoundError):
            self.router.get_traffic_percentage("rot1")

    def test_unregister_nonexistent_raises(self):
        with pytest.raises(RotationNotFoundError):
            self.router.unregister_rotation("nonexistent")


class TestTrafficRouterRouting:
    def setup_method(self):
        self.router = TrafficRouter()
        self.router.register_rotation("test", "v1", "v2")

    def test_route_zero_percent_all_old(self):
        self.router.set_traffic_percentage("test", 0)
        for i in range(1000):
            cred, version = self.router.route("test", f"req-{i}")
            assert cred == "v1"
            assert version == CredentialVersion.OLD

    def test_route_hundred_percent_all_new(self):
        self.router.set_traffic_percentage("test", 100)
        for i in range(1000):
            cred, version = self.router.route("test", f"req-{i}")
            assert cred == "v2"
            assert version == CredentialVersion.NEW

    def test_route_fifty_percent_split(self):
        self.router.set_traffic_percentage("test", 50)
        counts = {"v1": 0, "v2": 0}
        for i in range(10000):
            cred, _ = self.router.route("test", f"req-{i}")
            counts[cred] += 1
        assert 4000 <= counts["v1"] <= 6000
        assert 4000 <= counts["v2"] <= 6000

    def test_route_consistency_same_key(self):
        self.router.set_traffic_percentage("test", 30)
        results = set()
        for _ in range(50):
            cred, version = self.router.route("test", "same-user")
            results.add((cred, version))
        assert len(results) == 1

    def test_route_empty_key_raises(self):
        with pytest.raises(ValueError, match="request_key must not be empty"):
            self.router.route("test", "")

    def test_route_empty_rotation_name_raises(self):
        with pytest.raises(ValueError, match="rotation_name must not be empty"):
            self.router.route("", "req-1")

    def test_route_nonexistent_rotation_raises(self):
        with pytest.raises(RotationNotFoundError):
            self.router.route("nonexistent", "req-1")

    def test_force_version_old(self):
        self.router.set_traffic_percentage("test", 100)
        cred, version = self.router.route(
            "test", "req-1", force_version=CredentialVersion.OLD
        )
        assert cred == "v1"
        assert version == CredentialVersion.OLD

    def test_force_version_new(self):
        self.router.set_traffic_percentage("test", 0)
        cred, version = self.router.route(
            "test", "req-1", force_version=CredentialVersion.NEW
        )
        assert cred == "v2"
        assert version == CredentialVersion.NEW


class TestTrafficRouterTrafficPercentage:
    def setup_method(self):
        self.router = TrafficRouter()
        self.router.register_rotation("test", "v1", "v2")

    def test_set_valid_percentage(self):
        self.router.set_traffic_percentage("test", 33)
        assert self.router.get_traffic_percentage("test") == 33

    def test_set_negative_percentage_raises(self):
        with pytest.raises(InvalidTrafficPercentageError):
            self.router.set_traffic_percentage("test", -1)

    def test_set_over_100_percentage_raises(self):
        with pytest.raises(InvalidTrafficPercentageError):
            self.router.set_traffic_percentage("test", 101)

    def test_set_percentage_nonexistent_raises(self):
        with pytest.raises(RotationNotFoundError):
            self.router.set_traffic_percentage("nonexistent", 50)

    def test_get_percentage_nonexistent_raises(self):
        with pytest.raises(RotationNotFoundError):
            self.router.get_traffic_percentage("nonexistent")


class TestTrafficRouterMetrics:
    def setup_method(self):
        self.router = TrafficRouter()
        self.router.register_rotation("test", "v1", "v2")
        self.router.set_traffic_percentage("test", 100)

    def test_record_new_success(self):
        for _ in range(10):
            self.router.route("test", "req-x")
            self.router.record_new_metrics("test", is_error=False)
        stats = self.router.get_stats("test")
        assert stats.new_requests == 10
        assert stats.new_errors == 0
        assert stats.new_consecutive_failures == 0
        assert stats.total_requests == 10

    def test_record_new_errors(self):
        for i in range(20):
            self.router.route("test", f"req-{i}")
            is_error = i % 4 == 0
            self.router.record_new_metrics("test", is_error=is_error)
        stats = self.router.get_stats("test")
        assert stats.new_requests == 20
        assert stats.new_errors == 5
        assert stats.new_error_rate == pytest.approx(0.25)

    def test_consecutive_failures_counter(self):
        for _ in range(3):
            self.router.route("test", "r")
            self.router.record_new_metrics("test", is_error=True)
        stats = self.router.get_stats("test")
        assert stats.new_consecutive_failures == 3

        self.router.route("test", "r")
        self.router.record_new_metrics("test", is_error=False)
        stats = self.router.get_stats("test")
        assert stats.new_consecutive_failures == 0

    def test_old_metrics_reset_consecutive_failures(self):
        for _ in range(5):
            self.router.route("test", "r")
            self.router.record_new_metrics("test", is_error=True)
        self.router.record_old_metrics("test", is_error=True)
        stats = self.router.get_stats("test")
        assert stats.new_consecutive_failures == 0

    def test_record_old_metrics(self):
        self.router.set_traffic_percentage("test", 0)
        for i in range(100):
            self.router.route("test", f"req-{i}")
            self.router.record_old_metrics("test", is_error=(i < 10))
        stats = self.router.get_stats("test")
        assert stats.old_requests == 100
        assert stats.old_errors == 10
        assert stats.old_error_rate == pytest.approx(0.10)

    def test_metrics_separation_old_vs_new(self):
        self.router.set_traffic_percentage("test", 50)
        old_count = 0
        new_count = 0
        for i in range(200):
            _, vtype = self.router.route("test", f"req-{i}")
            if vtype == CredentialVersion.OLD:
                self.router.record_old_metrics("test", is_error=False)
                old_count += 1
            else:
                is_error = i % 10 == 0
                self.router.record_new_metrics("test", is_error=is_error)
                new_count += 1

        stats = self.router.get_stats("test")
        assert stats.old_requests == old_count
        assert stats.new_requests == new_count
        assert stats.old_errors == 0
        assert stats.new_errors > 0

    def test_empty_stats_properties(self):
        stats = self.router.get_stats("test")
        assert stats.total_requests == 0
        assert stats.old_error_rate == 0.0
        assert stats.new_error_rate == 0.0

    def test_reset_stats(self):
        for i in range(50):
            self.router.route("test", f"req-{i}")
            self.router.record_new_metrics("test", is_error=(i < 5))
        self.router.reset_stats("test")
        stats = self.router.get_stats("test")
        assert stats.total_requests == 0
        assert stats.new_requests == 0
        assert stats.new_consecutive_failures == 0

    def test_get_stats_nonexistent_raises(self):
        with pytest.raises(RotationNotFoundError):
            self.router.get_stats("nonexistent")

    def test_reset_stats_nonexistent_raises(self):
        with pytest.raises(RotationNotFoundError):
            self.router.reset_stats("nonexistent")


class TestMultipleRotationsIsolation:
    def setup_method(self):
        self.router = TrafficRouter()
        self.router.register_rotation("rot-a", "a-old", "a-new")
        self.router.register_rotation("rot-b", "b-old", "b-new")

    def test_traffic_percentage_isolated(self):
        self.router.set_traffic_percentage("rot-a", 100)
        self.router.set_traffic_percentage("rot-b", 0)

        for i in range(100):
            cred_a, v_a = self.router.route("rot-a", f"req-{i}")
            cred_b, v_b = self.router.route("rot-b", f"req-{i}")
            assert cred_a == "a-new"
            assert v_a == CredentialVersion.NEW
            assert cred_b == "b-old"
            assert v_b == CredentialVersion.OLD

    def test_metrics_isolated(self):
        self.router.set_traffic_percentage("rot-a", 100)
        self.router.set_traffic_percentage("rot-b", 100)

        for i in range(10):
            self.router.route("rot-a", f"a-{i}")
            self.router.record_new_metrics("rot-a", is_error=False)
        for i in range(5):
            self.router.route("rot-b", f"b-{i}")
            self.router.record_new_metrics("rot-b", is_error=True)

        stats_a = self.router.get_stats("rot-a")
        stats_b = self.router.get_stats("rot-b")

        assert stats_a.new_requests == 10
        assert stats_a.new_errors == 0
        assert stats_b.new_requests == 5
        assert stats_b.new_errors == 5
