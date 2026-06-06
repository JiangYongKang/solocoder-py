from decimal import Decimal
import pytest

from solocoder_py.order import (
    Order,
    OrderLineItem,
    OrderState,
    ShipmentItem,
    ShipmentQuantityError,
    OrderFulfillmentError,
)
from .conftest import make_line_items, make_order


class TestOrderLineItem:
    def test_line_item_basic(self):
        item = OrderLineItem(
            id="li-1",
            product_id="prod-1",
            product_name="测试商品",
            unit_price=Decimal("99.99"),
            quantity=2,
        )
        assert item.subtotal == Decimal("199.98")
        assert item.fulfilled_quantity == 0
        assert item.is_fully_fulfilled is False
        assert item.remaining_quantity == 2

    def test_line_item_fully_fulfilled(self):
        item = OrderLineItem(
            id="li-1",
            product_id="prod-1",
            product_name="测试商品",
            unit_price=Decimal("10.00"),
            quantity=3,
            fulfilled_quantity=3,
        )
        assert item.is_fully_fulfilled is True
        assert item.remaining_quantity == 0

    def test_line_item_quantity_must_be_positive(self):
        with pytest.raises(ValueError, match="quantity must be positive"):
            OrderLineItem(
                id="li-1",
                product_id="prod-1",
                product_name="测试商品",
                unit_price=Decimal("10.00"),
                quantity=0,
            )

    def test_line_item_negative_quantity(self):
        with pytest.raises(ValueError):
            OrderLineItem(
                id="li-1",
                product_id="prod-1",
                product_name="测试商品",
                unit_price=Decimal("10.00"),
                quantity=-1,
            )

    def test_line_item_negative_fulfilled_quantity(self):
        with pytest.raises(ValueError, match="fulfilled_quantity cannot be negative"):
            OrderLineItem(
                id="li-1",
                product_id="prod-1",
                product_name="测试商品",
                unit_price=Decimal("10.00"),
                quantity=5,
                fulfilled_quantity=-1,
            )

    def test_line_item_fulfilled_exceeds_quantity(self):
        with pytest.raises(ValueError, match="fulfilled_quantity cannot exceed quantity"):
            OrderLineItem(
                id="li-1",
                product_id="prod-1",
                product_name="测试商品",
                unit_price=Decimal("10.00"),
                quantity=5,
                fulfilled_quantity=6,
            )

    def test_line_item_negative_unit_price(self):
        with pytest.raises(ValueError, match="unit_price cannot be negative"):
            OrderLineItem(
                id="li-1",
                product_id="prod-1",
                product_name="测试商品",
                unit_price=Decimal("-1.00"),
                quantity=1,
            )


class TestOrderCreation:
    def test_order_basic(self):
        items = make_line_items(2, quantity=1, unit_price=Decimal("50.00"))
        order = make_order(line_items=items)
        assert order.state == OrderState.PENDING_PAYMENT
        assert order.total_amount == Decimal("100.00")
        assert len(order.line_items) == 2
        assert order.is_fully_fulfilled is False

    def test_order_must_have_line_items(self):
        with pytest.raises(ValueError, match="Order must have at least one line item"):
            Order(id="order-1", user_id="user-1", line_items=[])


class TestOrderFulfillment:
    def test_single_shipment_full_fulfillment(self):
        items = make_line_items(1, quantity=5)
        order = make_order(line_items=items)
        order.pay()

        shipment = order.ship([ShipmentItem(line_item_id=items[0].id, quantity=5)])

        assert len(order.shipments) == 1
        assert order.state == OrderState.SHIPPED
        assert order.is_fully_fulfilled is True
        assert shipment.id is not None
        assert len(shipment.items) == 1

    def test_partial_shipment(self):
        items = make_line_items(1, quantity=10)
        order = make_order(line_items=items)
        order.pay()

        order.ship([ShipmentItem(line_item_id=items[0].id, quantity=3)])
        assert items[0].fulfilled_quantity == 3
        assert items[0].remaining_quantity == 7
        assert order.state == OrderState.SHIPPED
        assert order.is_fully_fulfilled is False

    def test_multiple_partial_shipments(self):
        items = make_line_items(1, quantity=10)
        order = make_order(line_items=items)
        order.pay()

        order.ship([ShipmentItem(line_item_id=items[0].id, quantity=3)])
        order.ship([ShipmentItem(line_item_id=items[0].id, quantity=4)])
        order.ship([ShipmentItem(line_item_id=items[0].id, quantity=3)])

        assert items[0].fulfilled_quantity == 10
        assert items[0].is_fully_fulfilled is True
        assert len(order.shipments) == 3

    def test_multiple_line_items_partial_shipment(self):
        items = make_line_items(3, quantity=5)
        order = make_order(line_items=items)
        order.pay()

        order.ship([
            ShipmentItem(line_item_id=items[0].id, quantity=5),
            ShipmentItem(line_item_id=items[1].id, quantity=2),
        ])

        assert items[0].is_fully_fulfilled is True
        assert items[1].fulfilled_quantity == 2
        assert items[2].fulfilled_quantity == 0
        assert order.is_fully_fulfilled is False

    def test_deliver_requires_full_fulfillment(self):
        items = make_line_items(1, quantity=5)
        order = make_order(line_items=items)
        order.pay()
        order.ship([ShipmentItem(line_item_id=items[0].id, quantity=3)])

        with pytest.raises(OrderFulfillmentError, match="not all line items are fully fulfilled"):
            order.deliver()

    def test_deliver_after_full_fulfillment(self):
        items = make_line_items(2, quantity=3)
        order = make_order(line_items=items)
        order.pay()
        order.ship([
            ShipmentItem(line_item_id=items[0].id, quantity=3),
            ShipmentItem(line_item_id=items[1].id, quantity=3),
        ])
        order.deliver()
        assert order.state == OrderState.DELIVERED

    def test_shipment_zero_quantity_rejected(self):
        items = make_line_items(1, quantity=5)
        order = make_order(line_items=items)
        order.pay()

        with pytest.raises(ShipmentQuantityError, match="Shipment quantity must be positive"):
            order.ship([ShipmentItem(line_item_id=items[0].id, quantity=0)])

    def test_shipment_negative_quantity_rejected(self):
        items = make_line_items(1, quantity=5)
        order = make_order(line_items=items)
        order.pay()

        with pytest.raises(ShipmentQuantityError):
            order.ship([ShipmentItem(line_item_id=items[0].id, quantity=-1)])

    def test_shipment_exceeds_remaining_quantity(self):
        items = make_line_items(1, quantity=5)
        order = make_order(line_items=items)
        order.pay()
        order.ship([ShipmentItem(line_item_id=items[0].id, quantity=3)])

        with pytest.raises(ShipmentQuantityError, match="exceeds remaining quantity"):
            order.ship([ShipmentItem(line_item_id=items[0].id, quantity=3)])

    def test_cannot_ship_before_payment(self):
        items = make_line_items(1, quantity=1)
        order = make_order(line_items=items)

        with pytest.raises(OrderFulfillmentError, match="Cannot ship order in state"):
            order.ship([ShipmentItem(line_item_id=items[0].id, quantity=1)])

    def test_cannot_ship_cancelled_order(self):
        items = make_line_items(1, quantity=1)
        order = make_order(line_items=items)
        order.cancel()

        with pytest.raises(OrderFulfillmentError):
            order.ship([ShipmentItem(line_item_id=items[0].id, quantity=1)])

    def test_shipment_records_tracking_number(self):
        items = make_line_items(1, quantity=1)
        order = make_order(line_items=items)
        order.pay()

        shipment = order.ship(
            [ShipmentItem(line_item_id=items[0].id, quantity=1)],
            tracking_number="SF123456789",
        )
        assert shipment.tracking_number == "SF123456789"

    def test_find_nonexistent_line_item(self):
        order = make_order()
        with pytest.raises(ValueError, match="Line item not found"):
            order._find_line_item("nonexistent")
