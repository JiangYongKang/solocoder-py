from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import List, Set


class PromotionType(str, Enum):
    FULL_REDUCTION = "满减"
    DIRECT_REDUCTION = "直减"
    DISCOUNT = "折扣"
    SPECIAL_PRICE = "特价"


_MUTEX_GROUPS: List[Set[PromotionType]] = [
    {PromotionType.FULL_REDUCTION, PromotionType.DIRECT_REDUCTION},
    {PromotionType.DISCOUNT, PromotionType.SPECIAL_PRICE},
]


class MutuallyExclusivePromotionsError(Exception):
    def __init__(self, type1: PromotionType, type2: PromotionType) -> None:
        self.type1 = type1
        self.type2 = type2
        super().__init__(
            f"Promotions '{type1.value}' and '{type2.value}' are mutually exclusive"
        )


@dataclass
class Promotion:
    id: str
    name: str
    type: PromotionType
    value: Decimal
    threshold: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError("Promotion value cannot be negative")
        if self.threshold < 0:
            raise ValueError("Promotion threshold cannot be negative")

        if self.type == PromotionType.DISCOUNT:
            if not (Decimal("0") < self.value <= Decimal("1")):
                raise ValueError("Discount value must be between 0 and 1")
        elif self.type in (PromotionType.FULL_REDUCTION, PromotionType.DIRECT_REDUCTION):
            if self.value <= 0:
                raise ValueError("Reduction value must be positive")

    def is_applicable(self, price: Decimal) -> bool:
        return price >= self.threshold

    def apply(self, price: Decimal) -> Decimal:
        if not self.is_applicable(price):
            return price

        if self.type == PromotionType.FULL_REDUCTION:
            result = price - self.value
        elif self.type == PromotionType.DIRECT_REDUCTION:
            result = price - self.value
        elif self.type == PromotionType.DISCOUNT:
            result = price * self.value
        elif self.type == PromotionType.SPECIAL_PRICE:
            result = self.value
        else:
            result = price

        return max(result, Decimal("0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class PromotionEngine:
    @staticmethod
    def validate_promotions(promotions: List[Promotion]) -> None:
        types = [p.type for p in promotions]
        for i, t1 in enumerate(types):
            for t2 in types[i + 1 :]:
                for mutex_group in _MUTEX_GROUPS:
                    if t1 in mutex_group and t2 in mutex_group:
                        raise MutuallyExclusivePromotionsError(t1, t2)

    def calculate_final_price(self, original_price: Decimal, promotions: List[Promotion]) -> Decimal:
        if not promotions:
            return original_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        self.validate_promotions(promotions)

        applicable = sorted(
            [p for p in promotions if p.is_applicable(original_price)],
            key=lambda p: self._priority(p.type),
        )

        price = original_price
        for promo in applicable:
            price = promo.apply(price)

        return price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def _priority(promo_type: PromotionType) -> int:
        order = [
            PromotionType.SPECIAL_PRICE,
            PromotionType.DISCOUNT,
            PromotionType.FULL_REDUCTION,
            PromotionType.DIRECT_REDUCTION,
        ]
        return order.index(promo_type)
