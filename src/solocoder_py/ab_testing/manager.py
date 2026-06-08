from __future__ import annotations

import threading
import time
from typing import Optional

from .bucket import BUCKET_COUNT, StableHashBucketer
from .enums import ExperimentStatus
from .exceptions import (
    ExperimentAlreadyExistsError,
    ExperimentNotFoundError,
    InvalidExperimentStatusError,
    InvalidTrafficPercentageError,
    TrafficOverflowError,
)
from .models import (
    BucketAllocation,
    BucketOccupancy,
    Experiment,
    ExperimentStats,
    TrafficReport,
)


class _MutexGroupInfo:
    def __init__(self, name: str) -> None:
        self.name = name
        self.buckets: list[int] = []
        self.total_traffic: int = 0
        self.experiments: list[str] = []


class ABTestManager:
    def __init__(self) -> None:
        self._experiments: dict[str, Experiment] = {}
        self._mutex_groups: dict[str, _MutexGroupInfo] = {}
        self._bucket_owner: list[Optional[dict]] = [None] * BUCKET_COUNT
        self._user_stats: dict[str, int] = {}
        self._lock = threading.RLock()
        self._experiment_counter: int = 0

    def create_experiment(
        self,
        name: str,
        traffic_percentage: int,
        mutex_group: Optional[str] = None,
        priority: Optional[int] = None,
    ) -> Experiment:
        if not name:
            raise ValueError("experiment name must not be empty")
        if traffic_percentage < 0 or traffic_percentage > 100:
            raise InvalidTrafficPercentageError(
                "traffic_percentage must be between 0 and 100"
            )

        with self._lock:
            if name in self._experiments:
                raise ExperimentAlreadyExistsError(
                    f"experiment '{name}' already exists"
                )

            self._experiment_counter += 1
            effective_priority = (
                priority if priority is not None else self._experiment_counter
            )

            experiment = Experiment(
                name=name,
                traffic_percentage=traffic_percentage,
                status=ExperimentStatus.DRAFT,
                priority=effective_priority,
                created_at=time.time(),
                mutex_group=mutex_group,
            )
            self._experiments[name] = experiment
            return experiment

    def start_experiment(self, name: str) -> None:
        with self._lock:
            experiment = self._get_experiment_or_raise(name)
            if experiment.status == ExperimentStatus.RUNNING:
                return
            if experiment.status == ExperimentStatus.ENDED:
                raise InvalidExperimentStatusError(
                    f"cannot start ended experiment '{name}'"
                )

            if experiment.traffic_percentage == 0:
                experiment.status = ExperimentStatus.RUNNING
                return

            previous_status = experiment.status
            experiment.status = ExperimentStatus.RUNNING
            try:
                self._allocate_buckets(experiment)
            except Exception:
                experiment.status = previous_status
                raise

    def stop_experiment(self, name: str) -> None:
        with self._lock:
            experiment = self._get_experiment_or_raise(name)
            if experiment.status == ExperimentStatus.DRAFT:
                raise InvalidExperimentStatusError(
                    f"cannot stop draft experiment '{name}'"
                )
            if experiment.status == ExperimentStatus.ENDED:
                return

            self._release_buckets(experiment)
            experiment.status = ExperimentStatus.ENDED

    def get_experiment(self, name: str) -> Experiment:
        with self._lock:
            return self._get_experiment_or_raise(name)

    def list_experiments(self) -> list[Experiment]:
        with self._lock:
            return list(self._experiments.values())

    def get_user_allocation(self, user_id: str) -> BucketAllocation:
        if not user_id:
            raise ValueError("user_id must not be empty")

        with self._lock:
            return self._compute_allocation(user_id)

    def record_user_allocation(self, user_id: str) -> BucketAllocation:
        if not user_id:
            raise ValueError("user_id must not be empty")

        with self._lock:
            allocation = self._compute_allocation(user_id)
            key = allocation.experiment_name or "__control__"
            self._user_stats[key] = self._user_stats.get(key, 0) + 1
            return allocation

    def _compute_allocation(self, user_id: str) -> BucketAllocation:
        bucket = StableHashBucketer.get_global_bucket(user_id)
        owner = self._bucket_owner[bucket]

        if owner is None:
            return BucketAllocation(experiment_name=None, bucket=bucket)
        elif owner["type"] == "experiment":
            return BucketAllocation(experiment_name=owner["name"], bucket=bucket)
        else:
            group_name = owner["name"]
            exp_name = self._resolve_within_mutex_group(user_id, group_name)
            return BucketAllocation(experiment_name=exp_name, bucket=bucket)

    def get_bucket_occupancy(self) -> list[BucketOccupancy]:
        with self._lock:
            result: list[BucketOccupancy] = []
            for bucket_idx in range(BUCKET_COUNT):
                owner = self._bucket_owner[bucket_idx]
                if owner is None:
                    result.append(
                        BucketOccupancy(bucket=bucket_idx, experiment_name=None)
                    )
                elif owner["type"] == "experiment":
                    result.append(
                        BucketOccupancy(
                            bucket=bucket_idx, experiment_name=owner["name"]
                        )
                    )
                else:
                    group_name = owner["name"]
                    group = self._mutex_groups[group_name]
                    total = group.total_traffic
                    if total == 0:
                        result.append(
                            BucketOccupancy(bucket=bucket_idx, experiment_name=None)
                        )
                    else:
                        within_bucket = group.buckets.index(bucket_idx)
                        exp_name = self._map_within_bucket_to_experiment(
                            group_name, within_bucket
                        )
                        result.append(
                            BucketOccupancy(
                                bucket=bucket_idx, experiment_name=exp_name
                            )
                        )
            return result

    def get_traffic_report(self) -> TrafficReport:
        with self._lock:
            total_users = sum(self._user_stats.values())
            control_count = self._user_stats.get("__control__", 0)
            control_ratio = control_count / total_users if total_users > 0 else 0.0

            exp_stats: list[ExperimentStats] = []
            for exp in self._experiments.values():
                actual = self._user_stats.get(exp.name, 0)
                actual_ratio = actual / total_users if total_users > 0 else 0.0
                exp_stats.append(
                    ExperimentStats(
                        experiment_name=exp.name,
                        expected_traffic_percentage=exp.traffic_percentage,
                        actual_user_count=actual,
                        actual_traffic_ratio=actual_ratio,
                    )
                )

            return TrafficReport(
                control_user_count=control_count,
                control_traffic_ratio=control_ratio,
                experiments=exp_stats,
                bucket_occupancy=self.get_bucket_occupancy(),
            )

    def reset_stats(self) -> None:
        with self._lock:
            self._user_stats.clear()

    def _get_experiment_or_raise(self, name: str) -> Experiment:
        if name not in self._experiments:
            raise ExperimentNotFoundError(f"experiment '{name}' not found")
        return self._experiments[name]

    def _allocate_buckets(self, experiment: Experiment) -> None:
        traffic = experiment.traffic_percentage

        if experiment.mutex_group:
            self._allocate_mutex_group_buckets(experiment)
            return

        used = self._get_used_traffic()
        if used + traffic > 100:
            raise TrafficOverflowError(
                f"cannot allocate {traffic}% traffic, only {100 - used}% available"
            )

        start = self._find_contiguous_free_buckets(traffic)
        if start is None:
            raise TrafficOverflowError(
                f"cannot find {traffic} contiguous free buckets"
            )

        experiment.bucket_start = start
        experiment.bucket_end = start + traffic - 1
        for i in range(traffic):
            self._bucket_owner[start + i] = {"type": "experiment", "name": experiment.name}

    def _allocate_mutex_group_buckets(self, experiment: Experiment) -> None:
        group_name = experiment.mutex_group
        traffic = experiment.traffic_percentage

        if group_name not in self._mutex_groups:
            group = _MutexGroupInfo(group_name)
            used = self._get_used_traffic()
            if used + traffic > 100:
                raise TrafficOverflowError(
                    f"cannot allocate {traffic}% traffic for mutex group '{group_name}', "
                    f"only {100 - used}% available"
                )
            start = self._find_contiguous_free_buckets(traffic)
            if start is None:
                raise TrafficOverflowError(
                    f"cannot find {traffic} contiguous free buckets for mutex group"
                )
            for i in range(traffic):
                bucket = start + i
                self._bucket_owner[bucket] = {"type": "mutex_group", "name": group_name}
                group.buckets.append(bucket)
            group.total_traffic = traffic
            self._mutex_groups[group_name] = group
        else:
            group = self._mutex_groups[group_name]
            extra_needed = traffic

            if extra_needed > 0:
                used = self._get_used_traffic()
                if used + extra_needed > 100:
                    raise TrafficOverflowError(
                        f"cannot expand mutex group '{group_name}' by {traffic}%, "
                        f"only {100 - used}% available"
                    )
                extra_start = self._find_contiguous_free_buckets(extra_needed)
                if extra_start is None:
                    raise TrafficOverflowError(
                        f"cannot find {extra_needed} contiguous free buckets to expand mutex group"
                    )
                for i in range(extra_needed):
                    bucket = extra_start + i
                    self._bucket_owner[bucket] = {
                        "type": "mutex_group",
                        "name": group_name,
                    }
                    group.buckets.append(bucket)
                group.total_traffic += extra_needed

        group.experiments.append(experiment.name)
        self._recalc_group_experiment_bucket_ranges(group_name)

    def _release_buckets(self, experiment: Experiment) -> None:
        if experiment.mutex_group:
            self._release_mutex_group_buckets(experiment)
        else:
            if experiment.bucket_start is not None and experiment.bucket_end is not None:
                for i in range(experiment.bucket_start, experiment.bucket_end + 1):
                    self._bucket_owner[i] = None
        experiment.bucket_start = None
        experiment.bucket_end = None
        experiment.group_bucket_start = None
        experiment.group_bucket_end = None

    def _release_mutex_group_buckets(self, experiment: Experiment) -> None:
        group_name = experiment.mutex_group
        if group_name not in self._mutex_groups:
            return

        group = self._mutex_groups[group_name]
        if experiment.name in group.experiments:
            group.experiments.remove(experiment.name)

        if not group.experiments:
            for bucket in group.buckets:
                if (
                    self._bucket_owner[bucket] is not None
                    and self._bucket_owner[bucket].get("type") == "mutex_group"
                    and self._bucket_owner[bucket].get("name") == group_name
                ):
                    self._bucket_owner[bucket] = None
            del self._mutex_groups[group_name]
        else:
            self._recalc_group_experiment_bucket_ranges(group_name)

    def _recalc_group_experiment_bucket_ranges(self, group_name: str) -> None:
        group = self._mutex_groups[group_name]
        sorted_experiments = sorted(
            group.experiments,
            key=lambda n: (-self._experiments[n].priority, self._experiments[n].created_at),
        )

        offset = 0
        for exp_name in sorted_experiments:
            exp = self._experiments[exp_name]
            if exp.status == ExperimentStatus.RUNNING:
                exp.group_bucket_start = offset
                exp.group_bucket_end = offset + exp.traffic_percentage - 1
                offset += exp.traffic_percentage
            else:
                exp.group_bucket_start = None
                exp.group_bucket_end = None

    def _get_used_traffic(self) -> int:
        used = 0
        for owner in self._bucket_owner:
            if owner is not None:
                used += 1
        return used

    def _find_contiguous_free_buckets(self, count: int) -> Optional[int]:
        if count == 0:
            return None
        consecutive = 0
        for i in range(BUCKET_COUNT):
            if self._bucket_owner[i] is None:
                consecutive += 1
                if consecutive == count:
                    return i - count + 1
            else:
                consecutive = 0
        return None

    def _resolve_within_mutex_group(self, user_id: str, group_name: str) -> Optional[str]:
        group = self._mutex_groups[group_name]
        if not group.experiments:
            return None

        total_traffic = sum(
            self._experiments[name].traffic_percentage for name in group.experiments
        )
        if total_traffic == 0:
            return None

        within_bucket = StableHashBucketer.get_within_group_bucket(
            user_id, total_traffic
        )
        return self._map_within_bucket_to_experiment(group_name, within_bucket)

    def _map_within_bucket_to_experiment(
        self, group_name: str, within_bucket: int
    ) -> Optional[str]:
        group = self._mutex_groups[group_name]
        sorted_experiments = sorted(
            group.experiments,
            key=lambda n: (-self._experiments[n].priority, self._experiments[n].created_at),
        )

        offset = 0
        for exp_name in sorted_experiments:
            exp = self._experiments[exp_name]
            if exp.status != ExperimentStatus.RUNNING:
                continue
            if within_bucket < offset + exp.traffic_percentage:
                return exp_name
            offset += exp.traffic_percentage
        return None
