from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from .exceptions import InvalidTierConfigError


class BillingPeriodStatus(str, Enum):
    ACTIVE = "active"
    SETTLED = "settled"


@dataclass
class PricingTier:
    min_units: float
    max_units: Optional[float]
    unit_price: float

    def __post_init__(self) -> None:
        if self.min_units < 0:
            raise InvalidTierConfigError("Tier min_units cannot be negative")
        if self.unit_price < 0:
            raise InvalidTierConfigError("Tier unit_price cannot be negative")
        if self.max_units is not None and self.max_units <= self.min_units:
            raise InvalidTierConfigError(
                "Tier max_units must be greater than min_units"
            )

    @property
    def tier_size(self) -> float:
        if self.max_units is None:
            return float("inf")
        return self.max_units - self.min_units

    def overlap_with(self, other: "PricingTier") -> bool:
        a_start = self.min_units
        a_end = self.max_units if self.max_units is not None else float("inf")
        b_start = other.min_units
        b_end = other.max_units if other.max_units is not None else float("inf")
        return a_start < b_end and b_start < a_end


@dataclass
class TieredPricing:
    resource_type: str
    tiers: List[PricingTier] = field(default_factory=list)
    effective_from: datetime = field(default_factory=lambda: datetime.min)

    def __post_init__(self) -> None:
        self._validate_tiers()

    def _validate_tiers(self) -> None:
        if not self.tiers:
            raise InvalidTierConfigError(
                f"Resource {self.resource_type} must have at least one pricing tier"
            )

        sorted_tiers = sorted(self.tiers, key=lambda t: t.min_units)

        for i in range(len(sorted_tiers) - 1):
            current = sorted_tiers[i]
            next_tier = sorted_tiers[i + 1]

            if current.overlap_with(next_tier):
                raise InvalidTierConfigError(
                    f"Pricing tiers overlap: {current.min_units}-{current.max_units} "
                    f"and {next_tier.min_units}-{next_tier.max_units}"
                )

        if sorted_tiers[0].min_units != 0:
            raise InvalidTierConfigError(
                f"First tier must start from 0, got {sorted_tiers[0].min_units}"
            )

        for i in range(len(sorted_tiers) - 1):
            current = sorted_tiers[i]
            next_tier = sorted_tiers[i + 1]
            if current.max_units is None:
                raise InvalidTierConfigError(
                    "Only the last tier can have unbounded max_units"
                )
            if next_tier.min_units != current.max_units:
                raise InvalidTierConfigError(
                    f"Tiers are not contiguous: gap between "
                    f"[{current.min_units}, {current.max_units}) and "
                    f"[{next_tier.min_units}, {next_tier.max_units})"
                )

    def get_sorted_tiers(self) -> List[PricingTier]:
        return sorted(self.tiers, key=lambda t: t.min_units)

    def calculate_cost(self, total_units: float) -> tuple[float, List["TierCalculationDetail"]]:
        if total_units <= 0:
            return 0.0, []

        sorted_tiers = self.get_sorted_tiers()
        total_cost = 0.0
        details: List[TierCalculationDetail] = []
        remaining = total_units

        for tier in sorted_tiers:
            if remaining <= 0:
                break

            tier_start = tier.min_units
            tier_end = tier.max_units if tier.max_units is not None else float("inf")
            tier_capacity = tier_end - tier_start

            if total_units > tier_end:
                units_in_tier = tier_capacity
            elif total_units > tier_start:
                units_in_tier = total_units - tier_start
            else:
                units_in_tier = 0

            if units_in_tier > remaining:
                units_in_tier = remaining

            if units_in_tier > 0:
                tier_cost = units_in_tier * tier.unit_price
                total_cost += tier_cost
                details.append(
                    TierCalculationDetail(
                        tier_min=tier.min_units,
                        tier_max=tier.max_units,
                        unit_price=tier.unit_price,
                        units_applied=units_in_tier,
                        tier_cost=tier_cost,
                    )
                )
                remaining -= units_in_tier

        return total_cost, details


@dataclass
class TierCalculationDetail:
    tier_min: float
    tier_max: Optional[float]
    unit_price: float
    units_applied: float
    tier_cost: float


@dataclass
class PriceChange:
    resource_type: str
    new_pricing: TieredPricing
    effective_at: datetime


@dataclass
class UsageRecord:
    id: str
    account_id: str
    resource_type: str
    units: float
    reported_at: datetime

    @classmethod
    def create(
        cls,
        account_id: str,
        resource_type: str,
        units: float,
        reported_at: datetime,
    ) -> "UsageRecord":
        return cls(
            id=str(uuid.uuid4()),
            account_id=account_id,
            resource_type=resource_type,
            units=units,
            reported_at=reported_at,
        )


@dataclass
class BillingPeriod:
    id: str
    start_time: datetime
    end_time: datetime
    status: BillingPeriodStatus = BillingPeriodStatus.ACTIVE
    usage_records: List[UsageRecord] = field(default_factory=list)
    aggregated_usage: Dict[str, Dict[str, float]] = field(default_factory=dict)

    @classmethod
    def create(cls, start_time: datetime, end_time: datetime) -> "BillingPeriod":
        if end_time <= start_time:
            from .exceptions import InvalidPeriodError
            raise InvalidPeriodError("Period end_time must be after start_time")
        return cls(
            id=str(uuid.uuid4()),
            start_time=start_time,
            end_time=end_time,
        )

    @property
    def is_active(self) -> bool:
        return self.status == BillingPeriodStatus.ACTIVE

    @property
    def is_settled(self) -> bool:
        return self.status == BillingPeriodStatus.SETTLED

    def contains_time(self, when: datetime) -> bool:
        return self.start_time <= when < self.end_time

    def get_usage(self, account_id: str, resource_type: str) -> float:
        return (
            self.aggregated_usage.get(account_id, {}).get(resource_type, 0.0)
        )

    def add_usage(
        self, account_id: str, resource_type: str, units: float, reported_at: datetime
    ) -> UsageRecord:
        record = UsageRecord.create(
            account_id=account_id,
            resource_type=resource_type,
            units=units,
            reported_at=reported_at,
        )
        self.usage_records.append(record)
        if account_id not in self.aggregated_usage:
            self.aggregated_usage[account_id] = {}
        current = self.aggregated_usage[account_id].get(resource_type, 0.0)
        self.aggregated_usage[account_id][resource_type] = current + units
        return record


@dataclass
class ProportionalSplitDetail:
    pricing_effective_from: datetime
    pricing_effective_to: datetime
    time_ratio: float
    allocated_units: float
    tier_details: List[TierCalculationDetail]
    segment_cost: float


@dataclass
class BillingLineItem:
    account_id: str
    resource_type: str
    total_units: float
    proportional_splits: List[ProportionalSplitDetail] = field(default_factory=list)
    total_cost: float = 0.0


@dataclass
class Bill:
    id: str
    period_id: str
    period_start: datetime
    period_end: datetime
    account_id: str
    line_items: List[BillingLineItem] = field(default_factory=list)
    total_amount: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def create(
        cls,
        period: BillingPeriod,
        account_id: str,
    ) -> "Bill":
        return cls(
            id=str(uuid.uuid4()),
            period_id=period.id,
            period_start=period.start_time,
            period_end=period.end_time,
            account_id=account_id,
        )
