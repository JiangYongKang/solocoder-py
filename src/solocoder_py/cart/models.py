from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from .exceptions import InvalidQuantityError


@dataclass
class Product:
    id: str
    name: str
    price: Decimal
    stock: int
    is_online: bool = True

    def __post_init__(self) -> None:
        if self.stock < 0:
            raise InvalidQuantityError(f"Product stock cannot be negative for product {self.id}")
        if self.price < 0:
            raise InvalidQuantityError(f"Product price cannot be negative for product {self.id}")


@dataclass
class CartItem:
    product_id: str
    quantity: int

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise InvalidQuantityError(
                f"Cart item quantity must be positive for product {self.product_id}"
            )


@dataclass
class Cart:
    id: str
    user_id: Optional[str]
    items: Dict[str, CartItem] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @property
    def is_anonymous(self) -> bool:
        return self.user_id is None

    @property
    def total_items(self) -> int:
        return sum(item.quantity for item in self.items.values())

    @property
    def unique_products(self) -> int:
        return len(self.items)

    def add_item(self, product_id: str, quantity: int) -> None:
        if quantity <= 0:
            raise InvalidQuantityError("Quantity must be positive")
        if product_id in self.items:
            self.items[product_id].quantity += quantity
        else:
            self.items[product_id] = CartItem(product_id=product_id, quantity=quantity)
        self.updated_at = datetime.now()

    def remove_item(self, product_id: str) -> None:
        if product_id in self.items:
            del self.items[product_id]
            self.updated_at = datetime.now()

    def update_quantity(self, product_id: str, quantity: int) -> None:
        if quantity <= 0:
            raise InvalidQuantityError("Quantity must be positive")
        if product_id not in self.items:
            return
        self.items[product_id].quantity = quantity
        self.updated_at = datetime.now()

    def clear(self) -> None:
        self.items.clear()
        self.updated_at = datetime.now()

    def get_item(self, product_id: str) -> Optional[CartItem]:
        return self.items.get(product_id)


@dataclass
class TrimNotification:
    product_id: str
    product_name: str
    requested_quantity: int
    actual_quantity: int
    trimmed_quantity: int
    reason: str


@dataclass
class MergeResult:
    cart: Cart
    trims: List[TrimNotification] = field(default_factory=list)
    removed_offline_products: List[str] = field(default_factory=list)
