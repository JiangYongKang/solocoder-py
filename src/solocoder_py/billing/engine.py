from __future__ import annotations

import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from .exceptions import (
    BillingError,
    FutureUsageError,
    InvalidPeriodError,
    InvalidTierConfigError,
    PeriodSettledError,
    PricingNotFoundError,
)
from .models import (
    Bill,
    BillingLineItem,
    BillingPeriod,
    BillingPeriodStatus,
    PriceChange,
    PricingTier,
    ProportionalSplitDetail,
    TieredPricing,
    UsageRecord,
)


class BillingEngine:
    def __init__(self) -> None:
        self._pricing_configs: Dict[str, List[Tuple[datetime, TieredPricing]]] = {}
        self._periods: List[BillingPeriod] = []
        self._bills: Dict[str, List[Bill]] = {}
        self._current_period: Optional[BillingPeriod] = None
        self._lock = threading.RLock()

    def _now(self) -> datetime:
        return datetime.now()

    def configure_tiered_pricing(
        self,
        resource_type: str,
        tiers: List[PricingTier],
        effective_from: Optional[datetime] = None,
    ) -> TieredPricing:
        with self._lock:
            if effective_from is None:
                effective_from = self._now()

            pricing = TieredPricing(
                resource_type=resource_type,
                tiers=tiers,
                effective_from=effective_from,
            )

            if resource_type not in self._pricing_configs:
                self._pricing_configs[resource_type] = []

            self._pricing_configs[resource_type].append((effective_from, pricing))
            self._pricing_configs[resource_type].sort(key=lambda x: x[0])

            return pricing

    def get_pricing_at(
        self, resource_type: str, when: datetime
    ) -> Optional[TieredPricing]:
        if resource_type not in self._pricing_configs:
            return None

        configs = self._pricing_configs[resource_type]
        result: Optional[TieredPricing] = None
        for effective_at, pricing in configs:
            if effective_at <= when:
                result = pricing
            else:
                break
        return result

    def _require_pricing_at(self, resource_type: str, when: datetime) -> TieredPricing:
        pricing = self.get_pricing_at(resource_type, when)
        if pricing is None:
            raise PricingNotFoundError(
                f"No pricing configured for resource {resource_type} at {when}"
            )
        return pricing

    def open_period(self, start_time: datetime, duration: timedelta) -> BillingPeriod:
        with self._lock:
            if self._current_period is not None and self._current_period.is_active:
                raise BillingError(
                    "Cannot open a new period while current period is still active"
                )

            end_time = start_time + duration
            period = BillingPeriod.create(start_time, end_time)
            self._periods.append(period)
            self._current_period = period
            return period

    def get_current_period(self) -> Optional[BillingPeriod]:
        return self._current_period

    def get_period(self, period_id: str) -> Optional[BillingPeriod]:
        for p in self._periods:
            if p.id == period_id:
                return p
        return None

    def list_periods(self) -> List[BillingPeriod]:
        return list(self._periods)

    def report_usage(
        self,
        account_id: str,
        resource_type: str,
        units: float,
        reported_at: Optional[datetime] = None,
    ) -> UsageRecord:
        with self._lock:
            if reported_at is None:
                reported_at = self._now()

            if reported_at > self._now():
                raise FutureUsageError(
                    f"Cannot report usage with future timestamp: {reported_at}"
                )

            if self._current_period is None:
                raise BillingError("No active billing period")

            if not self._current_period.is_active:
                raise PeriodSettledError(
                    "Cannot report usage to a settled period"
                )

            period = self._current_period

            if not period.contains_time(reported_at):
                if reported_at < period.start_time:
                    raise InvalidPeriodError(
                        f"Usage timestamp {reported_at} is before period start {period.start_time}"
                    )
                else:
                    raise InvalidPeriodError(
                        f"Usage timestamp {reported_at} is after period end {period.end_time}. "
                        f"Please settle the current period first."
                    )

            self._require_pricing_at(resource_type, period.start_time)

            return period.add_usage(
                account_id=account_id,
                resource_type=resource_type,
                units=units,
                reported_at=reported_at,
            )

    def get_current_usage(
        self, account_id: str, resource_type: str
    ) -> float:
        if self._current_period is None:
            return 0.0
        if not self._current_period.is_active:
            return 0.0
        return self._current_period.get_usage(account_id, resource_type)

    def _get_pricing_segments(
        self, resource_type: str, period: BillingPeriod
    ) -> List[Tuple[datetime, datetime, TieredPricing]]:
        if resource_type not in self._pricing_configs:
            raise PricingNotFoundError(
                f"No pricing configured for resource {resource_type}"
            )

        all_configs = self._pricing_configs[resource_type]

        relevant_configs: List[Tuple[datetime, TieredPricing]] = []
        for effective_at, pricing in all_configs:
            if effective_at < period.end_time and pricing.effective_from <= period.end_time:
                relevant_configs.append((effective_at, pricing))

        if not relevant_configs:
            first_effective, first_pricing = all_configs[0]
            relevant_configs.append((first_effective, first_pricing))

        segments: List[Tuple[datetime, datetime, TieredPricing]] = []
        for i, (effective_at, pricing) in enumerate(relevant_configs):
            seg_start = max(effective_at, period.start_time)
            if i + 1 < len(relevant_configs):
                next_effective = relevant_configs[i + 1][0]
                seg_end = min(next_effective, period.end_time)
            else:
                seg_end = period.end_time

            if seg_start < seg_end:
                segments.append((seg_start, seg_end, pricing))

        if not segments:
            first_effective, first_pricing = relevant_configs[0]
            segments.append((period.start_time, period.end_time, first_pricing))

        return segments

    def _calculate_line_item(
        self,
        account_id: str,
        resource_type: str,
        total_units: float,
        period: BillingPeriod,
    ) -> BillingLineItem:
        line_item = BillingLineItem(
            account_id=account_id,
            resource_type=resource_type,
            total_units=total_units,
        )

        if total_units <= 0:
            return line_item

        segments = self._get_pricing_segments(resource_type, period)
        period_duration = (period.end_time - period.start_time).total_seconds()

        if period_duration <= 0:
            return line_item

        total_cost = 0.0

        for seg_start, seg_end, pricing in segments:
            seg_duration = (seg_end - seg_start).total_seconds()
            time_ratio = seg_duration / period_duration if period_duration > 0 else 0.0
            allocated_units = total_units * time_ratio

            if allocated_units > 0:
                seg_cost, tier_details = pricing.calculate_cost(allocated_units)
                total_cost += seg_cost
                line_item.proportional_splits.append(
                    ProportionalSplitDetail(
                        pricing_effective_from=seg_start,
                        pricing_effective_to=seg_end,
                        time_ratio=time_ratio,
                        allocated_units=allocated_units,
                        tier_details=tier_details,
                        segment_cost=seg_cost,
                    )
                )

        line_item.total_cost = total_cost
        return line_item

    def estimate_current_cost(
        self, account_id: str
    ) -> Dict[str, BillingLineItem]:
        with self._lock:
            if self._current_period is None:
                return {}
            if not self._current_period.is_active:
                return {}

            period = self._current_period
            account_usage = period.aggregated_usage.get(account_id, {})

            result: Dict[str, BillingLineItem] = {}
            for resource_type, total_units in account_usage.items():
                line_item = self._calculate_line_item(
                    account_id, resource_type, total_units, period
                )
                result[resource_type] = line_item

            return result

    def settle_period(
        self, period_id: Optional[str] = None, end_time: Optional[datetime] = None
    ) -> List[Bill]:
        with self._lock:
            if period_id is None:
                if self._current_period is None:
                    raise BillingError("No active period to settle")
                period = self._current_period
            else:
                period = self.get_period(period_id)
                if period is None:
                    raise InvalidPeriodError(f"Period {period_id} not found")

            if period.is_settled:
                raise PeriodSettledError(f"Period {period.id} is already settled")

            if end_time is not None:
                if end_time < period.start_time:
                    raise InvalidPeriodError(
                        "Settlement end_time cannot be before period start"
                    )
                if end_time > period.end_time:
                    raise InvalidPeriodError(
                        "Settlement end_time cannot exceed period end_time"
                    )
                period.end_time = end_time

            period.status = BillingPeriodStatus.SETTLED

            bills: List[Bill] = []
            account_ids = list(period.aggregated_usage.keys())

            for account_id in account_ids:
                bill = Bill.create(period, account_id)
                account_usage = period.aggregated_usage.get(account_id, {})

                for resource_type, total_units in account_usage.items():
                    line_item = self._calculate_line_item(
                        account_id, resource_type, total_units, period
                    )
                    bill.line_items.append(line_item)
                    bill.total_amount += line_item.total_cost

                if account_id not in self._bills:
                    self._bills[account_id] = []
                self._bills[account_id].append(bill)
                bills.append(bill)

            if period is self._current_period:
                pass

            return bills

    def get_bills(self, account_id: str) -> List[Bill]:
        return list(self._bills.get(account_id, []))

    def get_bill(self, account_id: str, bill_id: str) -> Optional[Bill]:
        for bill in self._bills.get(account_id, []):
            if bill.id == bill_id:
                return bill
        return None

    def list_bills(self) -> List[Bill]:
        all_bills: List[Bill] = []
        for bills in self._bills.values():
            all_bills.extend(bills)
        return all_bills
