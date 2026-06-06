from decimal import Decimal
import pytest

from solocoder_py.order import (
    InvalidStateTransitionError,
    Order,
    OrderLineItem,
    OrderRepository,
    OrderState,
    Promotion,
    PromotionEngine,
    PromotionType,
    ShipmentItem,
    ShipmentQuantityError,
    MutuallyExclusivePromotionsError,
)
from .conftest import make_line_items, make_order, advance_to_state


class TestOrderFullLifecycle:
    def test_complete_lifecycle(self):
        items = make_line_items(2, quantity=2, unit_price=Decimal("100.00"))
        order = make_order(line_items=items)
        assert order.state == OrderState.PENDING_PAYMENT

        order.pay()
        assert order.state == OrderState.PAID

        order.ship([
            ShipmentItem(line_item_id=items[0].id, quantity=2),
            ShipmentItem(line_item_id=items[1].id, quantity=2),
        ])
        assert order.state == OrderState.SHIPPED
        assert order.is_fully_fulfilled

        order.deliver()
        assert order.state == OrderState.DELIVERED

        order.complete()
        assert order.state == OrderState.COMPLETED

    def test_cancel_flow(self):
        order = make_order()
        order.cancel()
        assert order.state == OrderState.CANCELLED

    def test_refund_flow(self):
        order = make_order()
        order.pay()
        order.request_refund()
        assert order.state == OrderState.REFUNDING
        order.confirm_refund()
        assert order.state == OrderState.REFUNDED

    def test_after_sale_flow(self):
        items = make_line_items(1, quantity=1)
        order = make_order(line_items=items)
        order.pay()
        order.ship([ShipmentItem(line_item_id=items[0].id, quantity=1)])
        order.deliver()
        order.request_after_sale()
        assert order.state == OrderState.AFTER_SALE
        order.confirm_refund()
        assert order.state == OrderState.REFUNDED


class TestIllegalStateTransitions:
    def test_cancelled_order_cannot_pay(self):
        order = make_order()
        order.cancel()
        with pytest.raises(InvalidStateTransitionError):
            order.pay()

    def test_cancelled_order_cannot_ship(self):
        items = make_line_items(1, quantity=1)
        order = make_order(line_items=items)
        order.cancel()
        from solocoder_py.order.models import OrderFulfillmentError
        with pytest.raises(OrderFulfillmentError):
            order.ship([ShipmentItem(line_item_id=items[0].id, quantity=1)])

    def test_pending_payment_cannot_ship_directly(self):
        items = make_line_items(1, quantity=1)
        order = make_order(line_items=items)
        from solocoder_py.order.models import OrderFulfillmentError
        with pytest.raises(OrderFulfillmentError):
            order.ship([ShipmentItem(line_item_id=items[0].id, quantity=1)])

    def test_completed_order_cannot_go_back(self):
        order = make_order()
        advance_to_state(order, OrderState.COMPLETED)
        with pytest.raises(InvalidStateTransitionError):
            order.deliver()

    def test_cannot_request_refund_before_payment(self):
        order = make_order()
        with pytest.raises(InvalidStateTransitionError):
            order.request_refund()

    def test_cannot_request_after_sale_before_delivery(self):
        order = make_order()
        order.pay()
        with pytest.raises(InvalidStateTransitionError):
            order.request_after_sale()


class TestBoundaryConditions:
    def test_single_line_item_single_quantity(self):
        items = make_line_items(1, quantity=1, unit_price=Decimal("1.00"))
        order = make_order(line_items=items)
        assert order.total_amount == Decimal("1.00")

    def test_large_quantity(self):
        items = make_line_items(1, quantity=10000, unit_price=Decimal("0.01"))
        order = make_order(line_items=items)
        assert order.total_amount == Decimal("100.00")

    def test_zero_unit_price(self):
        items = make_line_items(1, quantity=10, unit_price=Decimal("0.00"))
        order = make_order(line_items=items)
        assert order.total_amount == Decimal("0.00")

    def test_shipment_exactly_remaining(self):
        items = make_line_items(1, quantity=5)
        order = make_order(line_items=items)
        order.pay()
        order.ship([ShipmentItem(line_item_id=items[0].id, quantity=2)])
        order.ship([ShipmentItem(line_item_id=items[0].id, quantity=3)])
        assert items[0].fulfilled_quantity == 5
        assert order.is_fully_fulfilled

    def test_maximum_promotions_compatible(self):
        engine = PromotionEngine()
        p_special = Promotion(
            id="p1", name="特价", type=PromotionType.SPECIAL_PRICE,
            value=Decimal("500.00"), threshold=Decimal("100.00"),
        )
        p_reduction = Promotion(
            id="p2", name="满减", type=PromotionType.FULL_REDUCTION,
            value=Decimal("50.00"), threshold=Decimal("100.00"),
        )
        result = engine.calculate_final_price(Decimal("1000.00"), [p_special, p_reduction])
        assert result == Decimal("450.00")

    def test_promotion_applies_exactly_at_threshold(self):
        promo = Promotion(
            id="p1", name="满100减10", type=PromotionType.FULL_REDUCTION,
            value=Decimal("10.00"), threshold=Decimal("100.00"),
        )
        assert promo.apply(Decimal("100.00")) == Decimal("90.00")

    def test_promotion_fails_just_below_threshold(self):
        promo = Promotion(
            id="p1", name="满100减10", type=PromotionType.FULL_REDUCTION,
            value=Decimal("10.00"), threshold=Decimal("100.00"),
        )
        assert promo.apply(Decimal("99.99")) == Decimal("99.99")


class TestOrderWithPromotions:
    def test_apply_promotions_to_order(self):
        items = make_line_items(1, quantity=1, unit_price=Decimal("200.00"))
        order = make_order(line_items=items)
        promo = Promotion(
            id="p1", name="满100减30", type=PromotionType.FULL_REDUCTION,
            value=Decimal("30.00"), threshold=Decimal("100.00"),
        )
        final_price = order.apply_promotions([promo])
        assert final_price == Decimal("170.00")
        assert len(order.promotions) == 1

    def test_apply_mutex_promotions_to_order_raises(self):
        items = make_line_items(1, quantity=1, unit_price=Decimal("200.00"))
        order = make_order(line_items=items)
        p1 = Promotion(
            id="p1", name="满减", type=PromotionType.FULL_REDUCTION,
            value=Decimal("20.00"), threshold=Decimal("100.00"),
        )
        p2 = Promotion(
            id="p2", name="直减", type=PromotionType.DIRECT_REDUCTION,
            value=Decimal("10.00"),
        )
        with pytest.raises(MutuallyExclusivePromotionsError):
            order.apply_promotions([p1, p2])


class TestOrderRepository:
    def test_save_and_find(self):
        repo = OrderRepository()
        order = make_order()
        repo.save(order)
        found = repo.find_by_id(order.id)
        assert found is order

    def test_find_nonexistent_returns_none(self):
        repo = OrderRepository()
        assert repo.find_by_id("nonexistent") is None

    def test_find_all(self):
        repo = OrderRepository()
        o1 = make_order()
        o2 = make_order()
        repo.save(o1)
        repo.save(o2)
        all_orders = repo.find_all()
        assert len(all_orders) == 2

    def test_delete(self):
        repo = OrderRepository()
        order = make_order()
        repo.save(order)
        assert repo.delete(order.id) is True
        assert repo.find_by_id(order.id) is None

    def test_delete_nonexistent(self):
        repo = OrderRepository()
        assert repo.delete("nonexistent") is False

    def test_clear(self):
        repo = OrderRepository()
        repo.save(make_order())
        repo.save(make_order())
        repo.clear()
        assert repo.count() == 0

    def test_count(self):
        repo = OrderRepository()
        assert repo.count() == 0
        repo.save(make_order())
        assert repo.count() == 1
