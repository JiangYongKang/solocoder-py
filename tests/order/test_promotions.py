from decimal import Decimal
import pytest

from solocoder_py.order import (
    Promotion,
    PromotionEngine,
    PromotionType,
    MutuallyExclusivePromotionsError,
)


class TestPromotion:
    def test_full_reduction_applicable(self):
        promo = Promotion(
            id="p1",
            name="满100减20",
            type=PromotionType.FULL_REDUCTION,
            value=Decimal("20.00"),
            threshold=Decimal("100.00"),
        )
        assert promo.is_applicable(Decimal("100.00"))
        assert promo.is_applicable(Decimal("150.00"))
        assert not promo.is_applicable(Decimal("99.99"))

    def test_full_reduction_apply(self):
        promo = Promotion(
            id="p1",
            name="满100减20",
            type=PromotionType.FULL_REDUCTION,
            value=Decimal("20.00"),
            threshold=Decimal("100.00"),
        )
        assert promo.apply(Decimal("100.00")) == Decimal("80.00")
        assert promo.apply(Decimal("150.00")) == Decimal("130.00")

    def test_full_reduction_not_applicable_returns_original(self):
        promo = Promotion(
            id="p1",
            name="满100减20",
            type=PromotionType.FULL_REDUCTION,
            value=Decimal("20.00"),
            threshold=Decimal("100.00"),
        )
        assert promo.apply(Decimal("50.00")) == Decimal("50.00")

    def test_direct_reduction(self):
        promo = Promotion(
            id="p2",
            name="直减10元",
            type=PromotionType.DIRECT_REDUCTION,
            value=Decimal("10.00"),
        )
        assert promo.apply(Decimal("50.00")) == Decimal("40.00")

    def test_discount(self):
        promo = Promotion(
            id="p3",
            name="9折",
            type=PromotionType.DISCOUNT,
            value=Decimal("0.9"),
        )
        assert promo.apply(Decimal("100.00")) == Decimal("90.00")

    def test_special_price(self):
        promo = Promotion(
            id="p4",
            name="特价99元",
            type=PromotionType.SPECIAL_PRICE,
            value=Decimal("99.00"),
            threshold=Decimal("200.00"),
        )
        assert promo.apply(Decimal("300.00")) == Decimal("99.00")

    def test_reduction_cannot_make_price_negative(self):
        promo = Promotion(
            id="p5",
            name="直减100",
            type=PromotionType.DIRECT_REDUCTION,
            value=Decimal("100.00"),
        )
        assert promo.apply(Decimal("50.00")) == Decimal("0.00")

    def test_promotion_negative_value(self):
        with pytest.raises(ValueError, match="Promotion value cannot be negative"):
            Promotion(
                id="p1",
                name="无效",
                type=PromotionType.DIRECT_REDUCTION,
                value=Decimal("-1.00"),
            )

    def test_promotion_negative_threshold(self):
        with pytest.raises(ValueError, match="Promotion threshold cannot be negative"):
            Promotion(
                id="p1",
                name="无效",
                type=PromotionType.FULL_REDUCTION,
                value=Decimal("10.00"),
                threshold=Decimal("-1.00"),
            )

    def test_discount_value_must_be_between_zero_and_one(self):
        with pytest.raises(ValueError, match="Discount value must be between 0 and 1"):
            Promotion(
                id="p1",
                name="无效折扣",
                type=PromotionType.DISCOUNT,
                value=Decimal("1.5"),
            )

    def test_discount_value_cannot_be_zero(self):
        with pytest.raises(ValueError):
            Promotion(
                id="p1",
                name="无效折扣",
                type=PromotionType.DISCOUNT,
                value=Decimal("0"),
            )

    def test_reduction_value_must_be_positive(self):
        with pytest.raises(ValueError, match="Reduction value must be positive"):
            Promotion(
                id="p1",
                name="无效",
                type=PromotionType.FULL_REDUCTION,
                value=Decimal("0"),
            )


class TestPromotionEngineValidation:
    def test_full_reduction_and_direct_reduction_mutex(self):
        p1 = Promotion(
            id="p1",
            name="满100减20",
            type=PromotionType.FULL_REDUCTION,
            value=Decimal("20.00"),
            threshold=Decimal("100.00"),
        )
        p2 = Promotion(
            id="p2",
            name="直减10元",
            type=PromotionType.DIRECT_REDUCTION,
            value=Decimal("10.00"),
        )
        with pytest.raises(MutuallyExclusivePromotionsError):
            PromotionEngine.validate_promotions([p1, p2])

    def test_discount_and_special_price_mutex(self):
        p1 = Promotion(
            id="p1",
            name="9折",
            type=PromotionType.DISCOUNT,
            value=Decimal("0.9"),
        )
        p2 = Promotion(
            id="p2",
            name="特价99",
            type=PromotionType.SPECIAL_PRICE,
            value=Decimal("99.00"),
        )
        with pytest.raises(MutuallyExclusivePromotionsError):
            PromotionEngine.validate_promotions([p1, p2])

    def test_discount_and_full_reduction_compatible(self):
        p1 = Promotion(
            id="p1",
            name="9折",
            type=PromotionType.DISCOUNT,
            value=Decimal("0.9"),
        )
        p2 = Promotion(
            id="p2",
            name="满100减20",
            type=PromotionType.FULL_REDUCTION,
            value=Decimal("20.00"),
            threshold=Decimal("100.00"),
        )
        PromotionEngine.validate_promotions([p1, p2])

    def test_discount_and_direct_reduction_compatible(self):
        p1 = Promotion(
            id="p1",
            name="9折",
            type=PromotionType.DISCOUNT,
            value=Decimal("0.9"),
        )
        p2 = Promotion(
            id="p2",
            name="直减10元",
            type=PromotionType.DIRECT_REDUCTION,
            value=Decimal("10.00"),
        )
        PromotionEngine.validate_promotions([p1, p2])

    def test_special_price_and_full_reduction_compatible(self):
        p1 = Promotion(
            id="p1",
            name="特价99",
            type=PromotionType.SPECIAL_PRICE,
            value=Decimal("99.00"),
        )
        p2 = Promotion(
            id="p2",
            name="满100减20",
            type=PromotionType.FULL_REDUCTION,
            value=Decimal("20.00"),
            threshold=Decimal("100.00"),
        )
        PromotionEngine.validate_promotions([p1, p2])

    def test_empty_promotions_valid(self):
        PromotionEngine.validate_promotions([])


class TestPromotionEngineCalculation:
    def test_no_promotions(self):
        engine = PromotionEngine()
        result = engine.calculate_final_price(Decimal("100.00"), [])
        assert result == Decimal("100.00")

    def test_single_full_reduction(self):
        engine = PromotionEngine()
        promo = Promotion(
            id="p1",
            name="满100减20",
            type=PromotionType.FULL_REDUCTION,
            value=Decimal("20.00"),
            threshold=Decimal("100.00"),
        )
        assert engine.calculate_final_price(Decimal("200.00"), [promo]) == Decimal("180.00")

    def test_single_discount(self):
        engine = PromotionEngine()
        promo = Promotion(
            id="p1",
            name="8折",
            type=PromotionType.DISCOUNT,
            value=Decimal("0.8"),
        )
        assert engine.calculate_final_price(Decimal("100.00"), [promo]) == Decimal("80.00")

    def test_discount_then_full_reduction(self):
        engine = PromotionEngine()
        p_discount = Promotion(
            id="p1",
            name="9折",
            type=PromotionType.DISCOUNT,
            value=Decimal("0.9"),
        )
        p_reduction = Promotion(
            id="p2",
            name="满100减20",
            type=PromotionType.FULL_REDUCTION,
            value=Decimal("20.00"),
            threshold=Decimal("100.00"),
        )
        result = engine.calculate_final_price(Decimal("200.00"), [p_discount, p_reduction])
        assert result == Decimal("160.00")

    def test_threshold_not_met_promotion_skipped(self):
        engine = PromotionEngine()
        promo = Promotion(
            id="p1",
            name="满200减50",
            type=PromotionType.FULL_REDUCTION,
            value=Decimal("50.00"),
            threshold=Decimal("200.00"),
        )
        assert engine.calculate_final_price(Decimal("100.00"), [promo]) == Decimal("100.00")

    def test_multiple_compatible_promotions(self):
        engine = PromotionEngine()
        p_discount = Promotion(
            id="p1",
            name="9折",
            type=PromotionType.DISCOUNT,
            value=Decimal("0.9"),
        )
        p_direct = Promotion(
            id="p2",
            name="直减10元",
            type=PromotionType.DIRECT_REDUCTION,
            value=Decimal("10.00"),
        )
        result = engine.calculate_final_price(Decimal("100.00"), [p_discount, p_direct])
        assert result == Decimal("80.00")

    def test_price_rounded_to_two_decimals(self):
        engine = PromotionEngine()
        promo = Promotion(
            id="p1",
            name="3折",
            type=PromotionType.DISCOUNT,
            value=Decimal("0.333"),
        )
        result = engine.calculate_final_price(Decimal("100.00"), [promo])
        assert result == Decimal("33.30")

    def test_maximum_compatible_promotions_stack(self):
        engine = PromotionEngine()
        p_special = Promotion(
            id="p1",
            name="特价1000",
            type=PromotionType.SPECIAL_PRICE,
            value=Decimal("1000.00"),
            threshold=Decimal("500.00"),
        )
        p_reduction = Promotion(
            id="p2",
            name="满100减10",
            type=PromotionType.FULL_REDUCTION,
            value=Decimal("10.00"),
            threshold=Decimal("100.00"),
        )
        result = engine.calculate_final_price(Decimal("2000.00"), [p_special, p_reduction])
        assert result == Decimal("990.00")

    def test_discount_and_direct_reduction_max_stack(self):
        engine = PromotionEngine()
        p_discount = Promotion(
            id="p1",
            name="8折",
            type=PromotionType.DISCOUNT,
            value=Decimal("0.8"),
        )
        p_direct = Promotion(
            id="p2",
            name="直减50元",
            type=PromotionType.DIRECT_REDUCTION,
            value=Decimal("50.00"),
        )
        result = engine.calculate_final_price(Decimal("300.00"), [p_discount, p_direct])
        assert result == Decimal("190.00")
