from decimal import Decimal
from typing import List
import uuid

from solocoder_py.order import (
    Order,
    OrderLineItem,
    OrderState,
    ShipmentItem,
)


def make_line_items(
    count: int = 1, quantity: int = 1, unit_price: Decimal = Decimal("100.00")
) -> List[OrderLineItem]:
    items = []
    for i in range(count):
        items.append(
            OrderLineItem(
                id=str(uuid.uuid4()),
                product_id=f"prod-{i}",
                product_name=f"商品{i + 1}",
                unit_price=unit_price,
                quantity=quantity,
            )
        )
    return items


def make_order(
    user_id: str = "user-1",
    line_items: List[OrderLineItem] | None = None,
) -> Order:
    if line_items is None:
        line_items = make_line_items(1)
    return Order(
        id=str(uuid.uuid4()),
        user_id=user_id,
        line_items=line_items,
    )


def ship_full(order: Order) -> None:
    shipment_items = [
        ShipmentItem(line_item_id=li.id, quantity=li.quantity)
        for li in order.line_items
    ]
    order.ship(shipment_items)


def pay_and_ship_full(order: Order) -> None:
    order.pay()
    ship_full(order)


def advance_to_state(order: Order, target: OrderState) -> None:
    path = {
        OrderState.PENDING_PAYMENT: [],
        OrderState.PAID: [lambda o: o.pay()],
        OrderState.SHIPPED: [
            lambda o: o.pay(),
            lambda o: ship_full(o),
        ],
        OrderState.DELIVERED: [
            lambda o: o.pay(),
            lambda o: ship_full(o),
            lambda o: o.deliver(),
        ],
        OrderState.COMPLETED: [
            lambda o: o.pay(),
            lambda o: ship_full(o),
            lambda o: o.deliver(),
            lambda o: o.complete(),
        ],
        OrderState.CANCELLED: [lambda o: o.cancel()],
        OrderState.REFUNDING: [
            lambda o: o.pay(),
            lambda o: o.request_refund(),
        ],
        OrderState.REFUNDED: [
            lambda o: o.pay(),
            lambda o: o.request_refund(),
            lambda o: o.confirm_refund(),
        ],
        OrderState.AFTER_SALE: [
            lambda o: o.pay(),
            lambda o: ship_full(o),
            lambda o: o.deliver(),
            lambda o: o.request_after_sale(),
        ],
    }
    for step in path[target]:
        step(order)
