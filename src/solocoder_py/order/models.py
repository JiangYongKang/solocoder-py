from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from .states import OrderState, OrderStateMachine, InvalidStateTransitionError
from .promotions import Promotion, PromotionEngine


class ShipmentQuantityError(Exception):
    pass


class OrderFulfillmentError(Exception):
    pass


@dataclass
class OrderLineItem:
    id: str
    product_id: str
    product_name: str
    unit_price: Decimal
    quantity: int
    fulfilled_quantity: int = 0

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.fulfilled_quantity < 0:
            raise ValueError("fulfilled_quantity cannot be negative")
        if self.fulfilled_quantity > self.quantity:
            raise ValueError("fulfilled_quantity cannot exceed quantity")
        if self.unit_price < 0:
            raise ValueError("unit_price cannot be negative")

    @property
    def subtotal(self) -> Decimal:
        return self.unit_price * Decimal(self.quantity)

    @property
    def is_fully_fulfilled(self) -> bool:
        return self.fulfilled_quantity >= self.quantity

    @property
    def remaining_quantity(self) -> int:
        return self.quantity - self.fulfilled_quantity


@dataclass
class ShipmentItem:
    line_item_id: str
    quantity: int


@dataclass
class Shipment:
    id: str
    items: List[ShipmentItem]
    created_at: datetime = field(default_factory=datetime.now)
    tracking_number: Optional[str] = None


@dataclass
class Order:
    id: str
    user_id: str
    line_items: List[OrderLineItem]
    promotions: List[Promotion] = field(default_factory=list)
    shipments: List[Shipment] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    _state_machine: OrderStateMachine = field(
        default_factory=lambda: OrderStateMachine(OrderState.PENDING_PAYMENT)
    )
    _final_amount: Optional[Decimal] = field(default=None, init=False)

    def __post_init__(self) -> None:
        if not self.line_items:
            raise ValueError("Order must have at least one line item")

    @property
    def state(self) -> OrderState:
        return self._state_machine.state

    @property
    def original_total_amount(self) -> Decimal:
        return sum(item.subtotal for item in self.line_items)

    @property
    def total_amount(self) -> Decimal:
        if self._final_amount is not None:
            return self._final_amount
        return self.original_total_amount

    @property
    def is_fully_fulfilled(self) -> bool:
        return all(item.is_fully_fulfilled for item in self.line_items)

    def pay(self) -> None:
        self._state_machine.transition_to(OrderState.PAID)

    def cancel(self) -> None:
        self._state_machine.transition_to(OrderState.CANCELLED)

    def ship(self, shipment_items: List[ShipmentItem], tracking_number: Optional[str] = None) -> Shipment:
        if self.state != OrderState.PAID and self.state != OrderState.SHIPPED:
            raise OrderFulfillmentError(
                f"Cannot ship order in state: {self.state.value}"
            )

        for si in shipment_items:
            line_item = self._find_line_item(si.line_item_id)
            if si.quantity <= 0:
                raise ShipmentQuantityError(
                    f"Shipment quantity must be positive for line item {si.line_item_id}"
                )
            if si.quantity > line_item.remaining_quantity:
                raise ShipmentQuantityError(
                    f"Shipment quantity {si.quantity} exceeds remaining quantity "
                    f"{line_item.remaining_quantity} for line item {si.line_item_id}"
                )

        for si in shipment_items:
            line_item = self._find_line_item(si.line_item_id)
            line_item.fulfilled_quantity += si.quantity

        shipment = Shipment(
            id=str(uuid.uuid4()),
            items=list(shipment_items),
            tracking_number=tracking_number,
        )
        self.shipments.append(shipment)

        if self.state == OrderState.PAID:
            self._state_machine.transition_to(OrderState.SHIPPED)

        return shipment

    def deliver(self) -> None:
        if not self.is_fully_fulfilled:
            raise OrderFulfillmentError(
                "Cannot mark as delivered: not all line items are fully fulfilled"
            )
        self._state_machine.transition_to(OrderState.DELIVERED)

    def complete(self) -> None:
        self._state_machine.transition_to(OrderState.COMPLETED)

    def request_refund(self) -> None:
        self._state_machine.transition_to(OrderState.REFUNDING)

    def confirm_refund(self) -> None:
        self._state_machine.transition_to(OrderState.REFUNDED)

    def request_after_sale(self) -> None:
        self._state_machine.transition_to(OrderState.AFTER_SALE)

    def apply_promotions(self, promotions: List[Promotion]) -> Decimal:
        engine = PromotionEngine()
        self.promotions = promotions
        final_price = engine.calculate_final_price(self.original_total_amount, promotions)
        self._final_amount = final_price
        return final_price

    def _find_line_item(self, line_item_id: str) -> OrderLineItem:
        for item in self.line_items:
            if item.id == line_item_id:
                return item
        raise ShipmentQuantityError(f"Line item not found: {line_item_id}")
