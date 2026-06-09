from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .enums import ExperimentStatus


@dataclass
class Experiment:
    name: str
    traffic_percentage: int
    status: ExperimentStatus
    priority: int
    created_at: float
    mutex_group: Optional[str] = None
    bucket_start: Optional[int] = None
    bucket_end: Optional[int] = None


@dataclass
class BucketAllocation:
    experiment_name: Optional[str]
    bucket: int


@dataclass
class ExperimentStats:
    experiment_name: str
    expected_traffic_percentage: int
    actual_user_count: int
    actual_traffic_ratio: float


@dataclass
class BucketOccupancy:
    bucket: int
    experiment_name: Optional[str]


@dataclass
class TrafficReport:
    control_user_count: int
    control_traffic_ratio: float
    experiments: list[ExperimentStats]
    bucket_occupancy: list[BucketOccupancy]
