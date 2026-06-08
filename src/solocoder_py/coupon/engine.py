from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from .exceptions import (
    CouponExpiredError,
    CouponMutexError,
    DuplicateCouponError,
    InvalidCouponError,
)
from .models import (
    CalculationResult,
    Coupon,
    CouponDetail,
    CouponType,
    FixedAmountCoupon,
    PercentageCoupon,
    TieredCoupon,
)


DEFAULT_FIXED_MUTEX_GROUP = "amount_based"
DEFAULT_PERCENTAGE_MUTEX_GROUP = "amount_based"
DEFAULT_TIERED_MUTEX_GROUP = "tiered"


def _apply_default_mutex_groups(coupons: List[Coupon]) -> List[Coupon]:
    for c in coupons:
        if not c.mutex_groups:
            if isinstance(c, FixedAmountCoupon):
                c.mutex_groups = [DEFAULT_FIXED_MUTEX_GROUP]
            elif isinstance(c, PercentageCoupon):
                c.mutex_groups = [DEFAULT_PERCENTAGE_MUTEX_GROUP]
            elif isinstance(c, TieredCoupon):
                c.mutex_groups = [DEFAULT_TIERED_MUTEX_GROUP]
    return coupons


@dataclass
class CouponEngine:
    check_time: Optional[datetime] = None
    global_max_discount: Optional[float] = None
    auto_resolve_mutex: bool = False

    def _get_check_time(self) -> datetime:
        return self.check_time if self.check_time is not None else datetime.now()

    def _validate_no_duplicates(self, coupons: List[Coupon]) -> None:
        seen: set[str] = set()
        for c in coupons:
            if c.coupon_id in seen:
                raise DuplicateCouponError(c.coupon_id)
            seen.add(c.coupon_id)

    def _find_mutex_conflicts(
        self, coupons: List[Coupon]
    ) -> Optional[tuple[Coupon, Coupon, str]]:
        for i in range(len(coupons)):
            for j in range(i + 1, len(coupons)):
                a = coupons[i]
                b = coupons[j]
                common = set(a.mutex_groups) & set(b.mutex_groups)
                if common:
                    return (a, b, next(iter(common)))
        return None

    def _resolve_mutex_by_priority(self, coupons: List[Coupon]) -> tuple[List[Coupon], List[Coupon]]:
        sorted_coupons = sorted(coupons, key=lambda c: (-c.priority, c.coupon_id))
        accepted: List[Coupon] = []
        excluded: List[Coupon] = []
        used_groups: set[str] = set()
        for c in sorted_coupons:
            conflict = set(c.mutex_groups) & used_groups
            if conflict:
                excluded.append(c)
            else:
                accepted.append(c)
                used_groups.update(c.mutex_groups)
        return accepted, excluded

    def calculate(
        self,
        order_amount: float,
        coupons: List[Coupon],
    ) -> CalculationResult:
        if order_amount < 0:
            raise InvalidCouponError("Order amount cannot be negative")

        coupons = list(coupons)
        coupons = _apply_default_mutex_groups(coupons)

        self._validate_no_duplicates(coupons)

        check_time = self._get_check_time()
        details: List[CouponDetail] = []
        expired_coupons: List[Coupon] = []
        active_coupons: List[Coupon] = []

        for c in coupons:
            if not c.is_valid_at(check_time):
                expired_coupons.append(c)
            else:
                active_coupons.append(c)

        for c in expired_coupons:
            details.append(CouponDetail(
                coupon_id=c.coupon_id,
                coupon_name=c.name,
                coupon_type=c.coupon_type,
                applied=False,
                excluded_by_mutex=False,
                excluded_by_expiry=True,
                excluded_by_threshold=False,
                discount_amount=0.0,
                amount_before=order_amount,
                amount_after=order_amount,
                capped=False,
                exclusion_reason="Coupon expired or not yet valid",
            ))

        mutex_excluded: List[Coupon] = []
        if self.auto_resolve_mutex:
            resolved, mutex_excluded = self._resolve_mutex_by_priority(active_coupons)
            computing_coupons = resolved
        else:
            conflict = self._find_mutex_conflicts(active_coupons)
            if conflict is not None:
                a, b, group = conflict
                raise CouponMutexError(a.coupon_id, b.coupon_id, group)
            computing_coupons = active_coupons

        for c in mutex_excluded:
            details.append(CouponDetail(
                coupon_id=c.coupon_id,
                coupon_name=c.name,
                coupon_type=c.coupon_type,
                applied=False,
                excluded_by_mutex=True,
                excluded_by_expiry=False,
                excluded_by_threshold=False,
                discount_amount=0.0,
                amount_before=order_amount,
                amount_after=order_amount,
                capped=False,
                exclusion_reason="Excluded by mutual exclusion (lower priority)",
            ))

        computing_coupons = sorted(
            computing_coupons, key=lambda c: (-c.priority, c.coupon_id)
        )

        current_amount = order_amount
        total_discount = 0.0

        for c in computing_coupons:
            amount_before = current_amount
            discount, capped = c.calculate_discount(current_amount, check_time)
            excluded_by_threshold = discount == 0.0 and not capped
            if excluded_by_threshold:
                details.append(CouponDetail(
                    coupon_id=c.coupon_id,
                    coupon_name=c.name,
                    coupon_type=c.coupon_type,
                    applied=False,
                    excluded_by_mutex=False,
                    excluded_by_expiry=False,
                    excluded_by_threshold=True,
                    discount_amount=0.0,
                    amount_before=amount_before,
                    amount_after=amount_before,
                    capped=False,
                    exclusion_reason="Order amount below threshold",
                ))
                continue

            new_amount = current_amount - discount
            if new_amount < 0:
                discount = current_amount
                new_amount = 0.0

            details.append(CouponDetail(
                coupon_id=c.coupon_id,
                coupon_name=c.name,
                coupon_type=c.coupon_type,
                applied=True,
                excluded_by_mutex=False,
                excluded_by_expiry=False,
                excluded_by_threshold=False,
                discount_amount=discount,
                amount_before=amount_before,
                amount_after=new_amount,
                capped=capped,
            ))
            current_amount = new_amount
            total_discount += discount

        global_capped = False
        if self.global_max_discount is not None and total_discount >= self.global_max_discount and total_discount > 0:
            excess = total_discount - self.global_max_discount
            total_discount = self.global_max_discount
            current_amount = order_amount - total_discount
            if current_amount < 0:
                current_amount = 0.0
                total_discount = order_amount
            global_capped = True

            applied_details = [d for d in details if d.applied]
            if applied_details:
                remaining_excess = excess
                for d in reversed(applied_details):
                    if remaining_excess <= 0:
                        break
                    reduce = min(d.discount_amount, remaining_excess)
                    d.discount_amount -= reduce
                    d.amount_after += reduce
                    remaining_excess -= reduce
                    if reduce > 0:
                        d.capped = True

        return CalculationResult(
            original_amount=order_amount,
            final_amount=current_amount,
            total_discount=total_discount,
            global_capped=global_capped,
            details=details,
        )
