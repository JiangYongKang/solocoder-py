from datetime import datetime, timedelta
from typing import List, Tuple

from solocoder_py.billing import BillingEngine, BillingPeriod, PricingTier


DEFAULT_EFFECTIVE_FROM = datetime(2023, 12, 1)


def make_simple_tier(price: float) -> List[PricingTier]:
    return [PricingTier(min_units=0, max_units=None, unit_price=price)]


def make_three_tiers() -> List[PricingTier]:
    return [
        PricingTier(min_units=0, max_units=100, unit_price=1.0),
        PricingTier(min_units=100, max_units=500, unit_price=0.8),
        PricingTier(min_units=500, max_units=None, unit_price=0.6),
    ]


def build_engine_with_single_tier(resource_type: str, price: float) -> BillingEngine:
    engine = BillingEngine()
    engine.configure_tiered_pricing(
        resource_type, make_simple_tier(price), effective_from=DEFAULT_EFFECTIVE_FROM
    )
    return engine


def build_engine_with_three_tiers(resource_type: str) -> BillingEngine:
    engine = BillingEngine()
    engine.configure_tiered_pricing(
        resource_type, make_three_tiers(), effective_from=DEFAULT_EFFECTIVE_FROM
    )
    return engine


def open_standard_period(
    engine: BillingEngine, base_day: int = 1
) -> Tuple[BillingEngine, BillingPeriod]:
    start = datetime(2024, 1, base_day)
    duration = timedelta(days=30)
    period = engine.open_period(start, duration)
    return engine, period


def in_period(period: BillingPeriod, offset_days: float = 1) -> datetime:
    return period.start_time + timedelta(days=offset_days)
