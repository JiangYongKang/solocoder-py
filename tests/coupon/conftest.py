from datetime import datetime, timedelta
from typing import List

from solocoder_py.coupon import (
    CouponEngine,
    FixedAmountCoupon,
    PercentageCoupon,
    Tier,
    TierDiscountType,
    TieredCoupon,
)


def base_time() -> datetime:
    return datetime(2025, 6, 1, 12, 0, 0)


def valid_range() -> tuple[datetime, datetime]:
    t = base_time()
    return t - timedelta(days=30), t + timedelta(days=30)


def past_range() -> tuple[datetime, datetime]:
    t = base_time()
    return t - timedelta(days=60), t - timedelta(days=30)


def future_range() -> tuple[datetime, datetime]:
    t = base_time()
    return t + timedelta(days=30), t + timedelta(days=60)


def make_fixed_coupon(
    coupon_id: str,
    threshold: float,
    discount_amount: float,
    **kwargs,
) -> FixedAmountCoupon:
    vf, vu = valid_range()
    return FixedAmountCoupon(
        coupon_id=coupon_id,
        name=f"满减券-{coupon_id}",
        valid_from=vf,
        valid_until=vu,
        threshold=threshold,
        discount_amount=discount_amount,
        **kwargs,
    )


def make_percentage_coupon(
    coupon_id: str,
    threshold: float,
    discount_rate: float,
    **kwargs,
) -> PercentageCoupon:
    vf, vu = valid_range()
    return PercentageCoupon(
        coupon_id=coupon_id,
        name=f"折扣券-{coupon_id}",
        valid_from=vf,
        valid_until=vu,
        threshold=threshold,
        discount_rate=discount_rate,
        **kwargs,
    )


def make_tiered_coupon(
    coupon_id: str,
    tiers: List[Tier],
    **kwargs,
) -> TieredCoupon:
    vf, vu = valid_range()
    return TieredCoupon(
        coupon_id=coupon_id,
        name=f"阶梯券-{coupon_id}",
        valid_from=vf,
        valid_until=vu,
        tiers=tiers,
        **kwargs,
    )


def make_expired_fixed_coupon(
    coupon_id: str, threshold: float, discount_amount: float
) -> FixedAmountCoupon:
    vf, vu = past_range()
    return FixedAmountCoupon(
        coupon_id=coupon_id,
        name=f"过期满减券-{coupon_id}",
        valid_from=vf,
        valid_until=vu,
        threshold=threshold,
        discount_amount=discount_amount,
    )


def make_future_fixed_coupon(
    coupon_id: str, threshold: float, discount_amount: float
) -> FixedAmountCoupon:
    return FixedAmountCoupon(
        coupon_id=coupon_id,
        name=f"未生效满减券-{coupon_id}",
        valid_from=future_range()[0],
        valid_until=future_range()[1],
        threshold=threshold,
        discount_amount=discount_amount,
    )


def make_engine(**kwargs) -> CouponEngine:
    if "check_time" not in kwargs:
        kwargs["check_time"] = base_time()
    return CouponEngine(**kwargs)
