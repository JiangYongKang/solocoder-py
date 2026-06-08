from __future__ import annotations

import pytest

from solocoder_py.ab_testing import (
    ABTestManager,
    BucketAllocation,
    ExperimentAlreadyExistsError,
    ExperimentNotFoundError,
    ExperimentStatus,
    InvalidExperimentStatusError,
    InvalidTrafficPercentageError,
    TrafficOverflowError,
)
from solocoder_py.ab_testing.bucket import StableHashBucketer


class TestExperimentLifecycle:
    def test_create_experiment(self):
        manager = ABTestManager()
        exp = manager.create_experiment("test_exp", traffic_percentage=30)
        assert exp.name == "test_exp"
        assert exp.traffic_percentage == 30
        assert exp.status == ExperimentStatus.DRAFT
        assert exp.mutex_group is None
        assert exp.bucket_start is None
        assert exp.bucket_end is None

    def test_create_experiment_with_priority(self):
        manager = ABTestManager()
        exp = manager.create_experiment("test_exp", traffic_percentage=30, priority=100)
        assert exp.priority == 100

    def test_create_experiment_with_mutex_group(self):
        manager = ABTestManager()
        exp = manager.create_experiment("test_exp", traffic_percentage=30, mutex_group="group1")
        assert exp.mutex_group == "group1"

    def test_start_experiment(self):
        manager = ABTestManager()
        manager.create_experiment("test_exp", traffic_percentage=30)
        manager.start_experiment("test_exp")
        exp = manager.get_experiment("test_exp")
        assert exp.status == ExperimentStatus.RUNNING
        assert exp.bucket_start is not None
        assert exp.bucket_end is not None
        assert exp.bucket_end - exp.bucket_start + 1 == 30

    def test_stop_experiment(self):
        manager = ABTestManager()
        manager.create_experiment("test_exp", traffic_percentage=30)
        manager.start_experiment("test_exp")
        manager.stop_experiment("test_exp")
        exp = manager.get_experiment("test_exp")
        assert exp.status == ExperimentStatus.ENDED
        assert exp.bucket_start is None
        assert exp.bucket_end is None

    def test_start_already_running_experiment(self):
        manager = ABTestManager()
        manager.create_experiment("test_exp", traffic_percentage=30)
        manager.start_experiment("test_exp")
        manager.start_experiment("test_exp")
        assert manager.get_experiment("test_exp").status == ExperimentStatus.RUNNING

    def test_stop_already_ended_experiment(self):
        manager = ABTestManager()
        manager.create_experiment("test_exp", traffic_percentage=30)
        manager.start_experiment("test_exp")
        manager.stop_experiment("test_exp")
        manager.stop_experiment("test_exp")
        assert manager.get_experiment("test_exp").status == ExperimentStatus.ENDED

    def test_stop_draft_experiment_raises(self):
        manager = ABTestManager()
        manager.create_experiment("test_exp", traffic_percentage=30)
        with pytest.raises(InvalidExperimentStatusError):
            manager.stop_experiment("test_exp")

    def test_start_ended_experiment_raises(self):
        manager = ABTestManager()
        manager.create_experiment("test_exp", traffic_percentage=30)
        manager.start_experiment("test_exp")
        manager.stop_experiment("test_exp")
        with pytest.raises(InvalidExperimentStatusError):
            manager.start_experiment("test_exp")

    def test_list_experiments(self):
        manager = ABTestManager()
        manager.create_experiment("exp1", traffic_percentage=10)
        manager.create_experiment("exp2", traffic_percentage=20)
        exps = manager.list_experiments()
        assert len(exps) == 2
        names = {e.name for e in exps}
        assert names == {"exp1", "exp2"}


class TestExperimentErrors:
    def test_create_duplicate_experiment_raises(self):
        manager = ABTestManager()
        manager.create_experiment("test_exp", traffic_percentage=30)
        with pytest.raises(ExperimentAlreadyExistsError):
            manager.create_experiment("test_exp", traffic_percentage=20)

    def test_get_nonexistent_experiment_raises(self):
        manager = ABTestManager()
        with pytest.raises(ExperimentNotFoundError):
            manager.get_experiment("nonexistent")

    def test_start_nonexistent_experiment_raises(self):
        manager = ABTestManager()
        with pytest.raises(ExperimentNotFoundError):
            manager.start_experiment("nonexistent")

    def test_stop_nonexistent_experiment_raises(self):
        manager = ABTestManager()
        with pytest.raises(ExperimentNotFoundError):
            manager.stop_experiment("nonexistent")

    def test_create_empty_name_raises(self):
        manager = ABTestManager()
        with pytest.raises(ValueError, match="experiment name must not be empty"):
            manager.create_experiment("", traffic_percentage=30)

    def test_create_invalid_traffic_percentage_negative(self):
        manager = ABTestManager()
        with pytest.raises(InvalidTrafficPercentageError):
            manager.create_experiment("test", traffic_percentage=-1)

    def test_create_invalid_traffic_percentage_over_100(self):
        manager = ABTestManager()
        with pytest.raises(InvalidTrafficPercentageError):
            manager.create_experiment("test", traffic_percentage=101)


class TestTrafficOverflow:
    def test_start_experiment_over_100_raises(self):
        manager = ABTestManager()
        manager.create_experiment("exp1", traffic_percentage=60)
        manager.create_experiment("exp2", traffic_percentage=50)
        manager.start_experiment("exp1")
        with pytest.raises(TrafficOverflowError):
            manager.start_experiment("exp2")

    def test_start_multiple_experiments_exactly_100(self):
        manager = ABTestManager()
        manager.create_experiment("exp1", traffic_percentage=40)
        manager.create_experiment("exp2", traffic_percentage=60)
        manager.start_experiment("exp1")
        manager.start_experiment("exp2")
        assert manager.get_experiment("exp1").status == ExperimentStatus.RUNNING
        assert manager.get_experiment("exp2").status == ExperimentStatus.RUNNING

    def test_stop_frees_traffic(self):
        manager = ABTestManager()
        manager.create_experiment("exp1", traffic_percentage=60)
        manager.create_experiment("exp2", traffic_percentage=50)
        manager.start_experiment("exp1")
        with pytest.raises(TrafficOverflowError):
            manager.start_experiment("exp2")
        manager.stop_experiment("exp1")
        manager.start_experiment("exp2")
        assert manager.get_experiment("exp2").status == ExperimentStatus.RUNNING


class TestStableHashBucketing:
    def test_hash_consistency(self):
        user_id = "user-12345"
        bucket1 = StableHashBucketer.get_global_bucket(user_id)
        bucket2 = StableHashBucketer.get_global_bucket(user_id)
        assert bucket1 == bucket2

    def test_hash_within_0_99(self):
        for i in range(1000):
            bucket = StableHashBucketer.get_global_bucket(f"user-{i}")
            assert 0 <= bucket <= 99

    def test_hash_distribution_approx_uniform(self):
        buckets = {}
        for i in range(10000):
            b = StableHashBucketer.get_global_bucket(f"user-{i}")
            buckets[b] = buckets.get(b, 0) + 1
        for count in buckets.values():
            assert 50 <= count <= 150

    def test_within_group_hash_consistency(self):
        user_id = "user-abc"
        b1 = StableHashBucketer.get_within_group_bucket(user_id, 50)
        b2 = StableHashBucketer.get_within_group_bucket(user_id, 50)
        assert b1 == b2

    def test_within_group_hash_range(self):
        for size in [10, 30, 50, 100]:
            for i in range(500):
                b = StableHashBucketer.get_within_group_bucket(f"u-{i}", size)
                assert 0 <= b < size

    def test_different_users_map_to_different_buckets(self):
        buckets = set()
        for i in range(200):
            buckets.add(StableHashBucketer.get_global_bucket(f"user-{i}"))
        assert len(buckets) > 50


class TestUserAllocation:
    def test_empty_user_id_raises(self):
        manager = ABTestManager()
        with pytest.raises(ValueError, match="user_id must not be empty"):
            manager.get_user_allocation("")

    def test_user_allocated_to_control_when_no_experiments(self):
        manager = ABTestManager()
        allocation = manager.get_user_allocation("user-1")
        assert allocation.experiment_name is None
        assert 0 <= allocation.bucket <= 99

    def test_user_allocated_to_running_experiment(self):
        manager = ABTestManager()
        manager.create_experiment("exp1", traffic_percentage=100)
        manager.start_experiment("exp1")
        allocation = manager.get_user_allocation("user-1")
        assert allocation.experiment_name == "exp1"

    def test_user_not_allocated_to_draft_experiment(self):
        manager = ABTestManager()
        manager.create_experiment("exp1", traffic_percentage=100)
        allocation = manager.get_user_allocation("user-1")
        assert allocation.experiment_name is None

    def test_user_not_allocated_to_ended_experiment(self):
        manager = ABTestManager()
        manager.create_experiment("exp1", traffic_percentage=100)
        manager.start_experiment("exp1")
        manager.stop_experiment("exp1")
        allocation = manager.get_user_allocation("user-1")
        assert allocation.experiment_name is None

    def test_allocation_consistency(self):
        manager = ABTestManager()
        manager.create_experiment("exp1", traffic_percentage=50)
        manager.start_experiment("exp1")
        allocations = set()
        for _ in range(50):
            alloc = manager.get_user_allocation("user-consistent")
            allocations.add((alloc.experiment_name, alloc.bucket))
        assert len(allocations) == 1

    def test_multiple_experiments_traffic_split(self):
        manager = ABTestManager()
        manager.create_experiment("exp_a", traffic_percentage=30)
        manager.create_experiment("exp_b", traffic_percentage=30)
        manager.start_experiment("exp_a")
        manager.start_experiment("exp_b")

        counts = {"exp_a": 0, "exp_b": 0, None: 0}
        for i in range(10000):
            alloc = manager.record_user_allocation(f"user-{i}")
            counts[alloc.experiment_name] += 1

        assert 2500 <= counts["exp_a"] <= 3500
        assert 2500 <= counts["exp_b"] <= 3500
        assert 3000 <= counts[None] <= 5000

    def test_get_user_allocation_is_read_only_no_side_effects(self):
        manager = ABTestManager()
        manager.create_experiment("exp", traffic_percentage=100)
        manager.start_experiment("exp")

        for _ in range(100):
            manager.get_user_allocation("user-readonly")

        report = manager.get_traffic_report()
        assert report.control_user_count == 0
        for e in report.experiments:
            assert e.actual_user_count == 0

    def test_record_user_allocation_counts(self):
        manager = ABTestManager()
        manager.create_experiment("exp", traffic_percentage=100)
        manager.start_experiment("exp")

        for i in range(50):
            manager.record_user_allocation(f"user-{i}")

        report = manager.get_traffic_report()
        exp_stat = next(e for e in report.experiments if e.experiment_name == "exp")
        assert exp_stat.actual_user_count == 50
        assert report.control_user_count == 0


class TestBoundaryConditions:
    def test_zero_percent_traffic(self):
        manager = ABTestManager()
        manager.create_experiment("exp_zero", traffic_percentage=0)
        manager.start_experiment("exp_zero")
        exp = manager.get_experiment("exp_zero")
        assert exp.status == ExperimentStatus.RUNNING
        assert exp.bucket_start is None
        assert exp.bucket_end is None

        for i in range(1000):
            alloc = manager.get_user_allocation(f"user-{i}")
            assert alloc.experiment_name is None

    def test_hundred_percent_traffic(self):
        manager = ABTestManager()
        manager.create_experiment("exp_full", traffic_percentage=100)
        manager.start_experiment("exp_full")
        for i in range(1000):
            alloc = manager.get_user_allocation(f"user-{i}")
            assert alloc.experiment_name == "exp_full"

    def test_all_buckets_filled(self):
        manager = ABTestManager()
        manager.create_experiment("exp1", traffic_percentage=50)
        manager.create_experiment("exp2", traffic_percentage=50)
        manager.start_experiment("exp1")
        manager.start_experiment("exp2")

        occupancy = manager.get_bucket_occupancy()
        for occ in occupancy:
            assert occ.experiment_name is not None

        for i in range(2000):
            alloc = manager.get_user_allocation(f"user-{i}")
            assert alloc.experiment_name in {"exp1", "exp2"}

    def test_last_bucket_boundary(self):
        manager = ABTestManager()
        manager.create_experiment("exp99", traffic_percentage=100)
        manager.start_experiment("exp99")
        exp = manager.get_experiment("exp99")
        assert exp.bucket_start == 0
        assert exp.bucket_end == 99

    def test_single_bucket_experiment(self):
        manager = ABTestManager()
        manager.create_experiment("tiny", traffic_percentage=1)
        manager.start_experiment("tiny")
        exp = manager.get_experiment("tiny")
        assert exp.bucket_end - exp.bucket_start + 1 == 1


class TestMutexGroup:
    def test_mutex_group_single_experiment(self):
        manager = ABTestManager()
        manager.create_experiment("exp_g", traffic_percentage=100, mutex_group="g1")
        manager.start_experiment("exp_g")
        for i in range(100):
            alloc = manager.get_user_allocation(f"user-{i}")
            assert alloc.experiment_name == "exp_g"

    def test_mutex_group_multiple_experiments_isolation(self):
        manager = ABTestManager()
        manager.create_experiment("exp_a", traffic_percentage=30, mutex_group="buttons")
        manager.create_experiment("exp_b", traffic_percentage=30, mutex_group="buttons")
        manager.start_experiment("exp_a")
        manager.start_experiment("exp_b")

        user_to_exp = {}
        for i in range(1000):
            uid = f"user-{i}"
            alloc = manager.get_user_allocation(uid)
            user_to_exp[uid] = alloc.experiment_name

        for exp_name in user_to_exp.values():
            assert exp_name in {"exp_a", "exp_b", None}

    def test_mutex_group_priority_order(self):
        manager = ABTestManager()
        manager.create_experiment(
            "exp_low", traffic_percentage=50, mutex_group="grp", priority=1
        )
        manager.create_experiment(
            "exp_high", traffic_percentage=50, mutex_group="grp", priority=100
        )
        manager.start_experiment("exp_low")
        manager.start_experiment("exp_high")

        occupancy = manager.get_bucket_occupancy()
        in_group = [o for o in occupancy if o.experiment_name in {"exp_low", "exp_high"}]
        assert len(in_group) == 100

        exp_high_count = sum(1 for o in in_group if o.experiment_name == "exp_high")
        exp_low_count = sum(1 for o in in_group if o.experiment_name == "exp_low")
        assert exp_high_count == 50
        assert exp_low_count == 50

    def test_mutex_group_user_gets_only_one_experiment(self):
        manager = ABTestManager()
        manager.create_experiment("exp_x", traffic_percentage=50, mutex_group="mg")
        manager.create_experiment("exp_y", traffic_percentage=50, mutex_group="mg")
        manager.start_experiment("exp_x")
        manager.start_experiment("exp_y")

        for i in range(500):
            uid = f"user-{i}"
            alloc1 = manager.get_user_allocation(uid)
            alloc2 = manager.get_user_allocation(uid)
            assert alloc1.experiment_name == alloc2.experiment_name

    def test_mutex_group_traffic_distribution(self):
        manager = ABTestManager()
        manager.create_experiment("exp_1", traffic_percentage=20, mutex_group="test")
        manager.create_experiment("exp_2", traffic_percentage=20, mutex_group="test")
        manager.start_experiment("exp_1")
        manager.start_experiment("exp_2")

        counts = {"exp_1": 0, "exp_2": 0, None: 0}
        for i in range(10000):
            alloc = manager.record_user_allocation(f"u-{i}")
            counts[alloc.experiment_name] += 1

        assert 1500 <= counts["exp_1"] <= 2500
        assert 1500 <= counts["exp_2"] <= 2500
        assert 5000 <= counts[None] <= 7000

    def test_mutex_group_stop_one_experiment(self):
        manager = ABTestManager()
        manager.create_experiment("exp_a", traffic_percentage=30, mutex_group="g")
        manager.create_experiment("exp_b", traffic_percentage=30, mutex_group="g")
        manager.start_experiment("exp_a")
        manager.start_experiment("exp_b")
        manager.stop_experiment("exp_a")

        exp_a = manager.get_experiment("exp_a")
        exp_b = manager.get_experiment("exp_b")
        assert exp_a.status == ExperimentStatus.ENDED
        assert exp_b.status == ExperimentStatus.RUNNING

        counts = {"exp_a": 0, "exp_b": 0, None: 0}
        for i in range(2000):
            alloc = manager.get_user_allocation(f"u-{i}")
            counts[alloc.experiment_name] += 1
        assert counts["exp_a"] == 0
        assert counts["exp_b"] > 0

    def test_mutex_group_stop_all_releases_buckets(self):
        manager = ABTestManager()
        manager.create_experiment("exp_a", traffic_percentage=30, mutex_group="g")
        manager.create_experiment("exp_b", traffic_percentage=30, mutex_group="g")
        manager.start_experiment("exp_a")
        manager.start_experiment("exp_b")
        manager.stop_experiment("exp_a")
        manager.stop_experiment("exp_b")

        occupancy = manager.get_bucket_occupancy()
        for occ in occupancy:
            assert occ.experiment_name is None


class TestMutexGroupNonContiguousBuckets:
    @staticmethod
    def _build_noncontiguous_mutex_group() -> tuple[ABTestManager, list[int], list[int]]:
        manager = ABTestManager()

        manager.create_experiment("mutex_a", traffic_percentage=20, mutex_group="mg")
        manager.start_experiment("mutex_a")

        manager.create_experiment("filler1", traffic_percentage=20)
        manager.start_experiment("filler1")
        manager.create_experiment("filler2", traffic_percentage=20)
        manager.start_experiment("filler2")
        manager.create_experiment("filler3", traffic_percentage=20)
        manager.start_experiment("filler3")

        manager.create_experiment("mutex_b", traffic_percentage=20, mutex_group="mg")
        manager.start_experiment("mutex_b")

        occupancy = manager.get_bucket_occupancy()
        mutex_buckets = sorted(o.bucket for o in occupancy if o.experiment_name in {"mutex_a", "mutex_b"})
        filler_buckets = sorted(
            o.bucket for o in occupancy if o.experiment_name in {"filler1", "filler2", "filler3"}
        )

        assert len(mutex_buckets) == 40
        assert len(filler_buckets) == 60

        has_gap = False
        for i in range(len(mutex_buckets) - 1):
            if mutex_buckets[i + 1] - mutex_buckets[i] > 1:
                has_gap = True
                break
        assert has_gap, "mutual exclusion group buckets should be non-contiguous with a gap"

        return manager, mutex_buckets, filler_buckets

    def test_mutex_group_noncontiguous_release_does_not_hurt_others(self):
        manager, mutex_buckets, filler_buckets = self._build_noncontiguous_mutex_group()

        occupancy_before = manager.get_bucket_occupancy()
        filler_experiments_before = {
            o.bucket: o.experiment_name
            for o in occupancy_before
            if o.experiment_name in {"filler1", "filler2", "filler3"}
        }

        manager.stop_experiment("mutex_a")
        manager.stop_experiment("mutex_b")

        occupancy_after = manager.get_bucket_occupancy()
        filler_experiments_after = {
            o.bucket: o.experiment_name
            for o in occupancy_after
            if o.experiment_name is not None
        }

        assert len(filler_experiments_after) == 60
        assert filler_experiments_before == filler_experiments_after

        mutex_remaining = [
            o for o in occupancy_after if o.experiment_name in {"mutex_a", "mutex_b"}
        ]
        assert len(mutex_remaining) == 0

    def test_mutex_group_noncontiguous_bucket_occupancy_correct(self):
        manager, mutex_buckets, filler_buckets = self._build_noncontiguous_mutex_group()

        occupancy = manager.get_bucket_occupancy()
        by_bucket = {o.bucket: o.experiment_name for o in occupancy}

        for b in mutex_buckets:
            assert by_bucket[b] in {"mutex_a", "mutex_b"}

        mutex_a_count = sum(1 for b in mutex_buckets if by_bucket[b] == "mutex_a")
        mutex_b_count = sum(1 for b in mutex_buckets if by_bucket[b] == "mutex_b")
        assert mutex_a_count == 20
        assert mutex_b_count == 20

        for b in filler_buckets:
            assert by_bucket[b] in {"filler1", "filler2", "filler3"}

    def test_mutex_group_noncontiguous_user_allocation_in_all_group_buckets(self):
        manager, mutex_buckets, filler_buckets = self._build_noncontiguous_mutex_group()

        seen_mutex_a = False
        seen_mutex_b = False
        seen_filler = False
        seen_control = False

        for i in range(10000):
            alloc = manager.get_user_allocation(f"user-{i}")
            exp = alloc.experiment_name
            if exp == "mutex_a":
                seen_mutex_a = True
            elif exp == "mutex_b":
                seen_mutex_b = True
            elif exp in {"filler1", "filler2", "filler3"}:
                seen_filler = True
            elif exp is None:
                seen_control = True
            else:
                pytest.fail(f"unexpected experiment: {exp}")

        assert seen_mutex_a
        assert seen_mutex_b
        assert seen_filler

        mutex_a_exp = manager.get_experiment("mutex_a")
        mutex_b_exp = manager.get_experiment("mutex_b")
        assert mutex_a_exp.bucket_start is None
        assert mutex_a_exp.bucket_end is None
        assert mutex_b_exp.bucket_start is None
        assert mutex_b_exp.bucket_end is None
        assert mutex_a_exp.group_bucket_start is not None
        assert mutex_a_exp.group_bucket_end is not None
        assert mutex_b_exp.group_bucket_start is not None
        assert mutex_b_exp.group_bucket_end is not None
        assert (
            mutex_a_exp.group_bucket_end - mutex_a_exp.group_bucket_start + 1
            == mutex_a_exp.traffic_percentage
        )
        assert (
            mutex_b_exp.group_bucket_end - mutex_b_exp.group_bucket_start + 1
            == mutex_b_exp.traffic_percentage
        )


class TestBucketOccupancy:
    def test_empty_occupancy(self):
        manager = ABTestManager()
        occupancy = manager.get_bucket_occupancy()
        assert len(occupancy) == 100
        for occ in occupancy:
            assert occ.experiment_name is None
            assert 0 <= occ.bucket <= 99

    def test_single_experiment_occupancy(self):
        manager = ABTestManager()
        manager.create_experiment("exp", traffic_percentage=25)
        manager.start_experiment("exp")
        occupancy = manager.get_bucket_occupancy()
        occupied = [o for o in occupancy if o.experiment_name == "exp"]
        assert len(occupied) == 25
        free = [o for o in occupancy if o.experiment_name is None]
        assert len(free) == 75

    def test_multiple_experiments_occupancy(self):
        manager = ABTestManager()
        manager.create_experiment("exp1", traffic_percentage=20)
        manager.create_experiment("exp2", traffic_percentage=30)
        manager.start_experiment("exp1")
        manager.start_experiment("exp2")
        occupancy = manager.get_bucket_occupancy()
        exp1_count = sum(1 for o in occupancy if o.experiment_name == "exp1")
        exp2_count = sum(1 for o in occupancy if o.experiment_name == "exp2")
        free_count = sum(1 for o in occupancy if o.experiment_name is None)
        assert exp1_count == 20
        assert exp2_count == 30
        assert free_count == 50

    def test_occupancy_contiguous(self):
        manager = ABTestManager()
        manager.create_experiment("exp", traffic_percentage=40)
        manager.start_experiment("exp")
        exp = manager.get_experiment("exp")
        occupancy = manager.get_bucket_occupancy()
        for b in range(exp.bucket_start, exp.bucket_end + 1):
            assert occupancy[b].experiment_name == "exp"


class TestTrafficReport:
    def test_empty_report(self):
        manager = ABTestManager()
        report = manager.get_traffic_report()
        assert report.control_user_count == 0
        assert report.control_traffic_ratio == 0.0
        assert len(report.experiments) == 0
        assert len(report.bucket_occupancy) == 100

    def test_report_after_allocations(self):
        manager = ABTestManager()
        manager.create_experiment("exp1", traffic_percentage=50)
        manager.start_experiment("exp1")

        for i in range(1000):
            manager.record_user_allocation(f"u-{i}")

        report = manager.get_traffic_report()
        assert report.control_user_count + sum(e.actual_user_count for e in report.experiments) == 1000
        assert report.control_traffic_ratio + sum(e.actual_traffic_ratio for e in report.experiments) == pytest.approx(1.0)

        exp1_stat = next(e for e in report.experiments if e.experiment_name == "exp1")
        assert exp1_stat.expected_traffic_percentage == 50
        assert 400 <= exp1_stat.actual_user_count <= 600

    def test_reset_stats(self):
        manager = ABTestManager()
        manager.create_experiment("exp", traffic_percentage=100)
        manager.start_experiment("exp")
        for i in range(100):
            manager.record_user_allocation(f"u-{i}")
        manager.reset_stats()
        report = manager.get_traffic_report()
        assert report.control_user_count == 0
        for e in report.experiments:
            assert e.actual_user_count == 0

    def test_get_user_allocation_does_not_affect_report(self):
        manager = ABTestManager()
        manager.create_experiment("exp", traffic_percentage=100)
        manager.start_experiment("exp")

        for i in range(1000):
            manager.get_user_allocation(f"u-{i}")

        report = manager.get_traffic_report()
        exp_stat = next(e for e in report.experiments if e.experiment_name == "exp")
        assert exp_stat.actual_user_count == 0
        assert report.control_user_count == 0


class TestExperimentStopFallbackToControl:
    def test_stopped_experiment_users_go_to_control(self):
        manager = ABTestManager()
        manager.create_experiment("exp", traffic_percentage=100)
        manager.start_experiment("exp")

        before = manager.get_user_allocation("user-x")
        assert before.experiment_name == "exp"

        manager.stop_experiment("exp")
        after = manager.get_user_allocation("user-x")
        assert after.experiment_name is None

    def test_partial_still_running(self):
        manager = ABTestManager()
        manager.create_experiment("exp1", traffic_percentage=30)
        manager.create_experiment("exp2", traffic_percentage=30)
        manager.start_experiment("exp1")
        manager.start_experiment("exp2")
        manager.stop_experiment("exp1")

        for i in range(500):
            alloc = manager.get_user_allocation(f"u-{i}")
            assert alloc.experiment_name in {"exp2", None}


class TestHashIndependenceFromExperimentOrder:
    def test_user_bucket_independent_of_experiment_creation_order(self):
        bucket1 = StableHashBucketer.get_global_bucket("user-alpha")

        manager1 = ABTestManager()
        manager1.create_experiment("a", traffic_percentage=30)
        manager1.create_experiment("b", traffic_percentage=30)
        manager1.start_experiment("a")
        manager1.start_experiment("b")
        alloc1 = manager1.get_user_allocation("user-alpha")

        bucket2 = StableHashBucketer.get_global_bucket("user-alpha")
        assert bucket1 == bucket2

        manager2 = ABTestManager()
        manager2.create_experiment("b", traffic_percentage=30)
        manager2.create_experiment("a", traffic_percentage=30)
        manager2.start_experiment("b")
        manager2.start_experiment("a")
        alloc2 = manager2.get_user_allocation("user-alpha")

        assert alloc1.bucket == alloc2.bucket
