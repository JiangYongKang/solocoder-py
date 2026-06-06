from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional


class InventoryError(Exception):
    pass


class InsufficientStockError(InventoryError):
    pass


class ReservationNotFoundError(InventoryError):
    pass


class InvalidQuantityError(InventoryError):
    pass


class WarehouseNotFoundError(InventoryError):
    pass


class ReservationStatus(str, Enum):
    ACTIVE = "active"
    RELEASED = "released"
    EXPIRED = "expired"
    CONFIRMED = "confirmed"


@dataclass
class SkuStock:
    sku_id: str
    total: int = 0
    reserved: int = 0

    def __post_init__(self) -> None:
        if self.total < 0:
            raise InvalidQuantityError(f"Total stock cannot be negative for sku {self.sku_id}")
        if self.reserved < 0:
            raise InvalidQuantityError(f"Reserved stock cannot be negative for sku {self.sku_id}")
        if self.reserved > self.total:
            raise InvalidQuantityError(
                f"Reserved stock cannot exceed total for sku {self.sku_id}"
            )

    @property
    def available(self) -> int:
        return self.total - self.reserved

    def reserve(self, quantity: int) -> None:
        if quantity <= 0:
            raise InvalidQuantityError("Reserve quantity must be positive")
        if quantity > self.available:
            raise InsufficientStockError(
                f"Insufficient available stock for sku {self.sku_id}: "
                f"requested {quantity}, available {self.available}"
            )
        self.reserved += quantity

    def release(self, quantity: int) -> None:
        if quantity <= 0:
            raise InvalidQuantityError("Release quantity must be positive")
        if quantity > self.reserved:
            raise InvalidQuantityError(
                f"Release quantity {quantity} exceeds reserved {self.reserved} "
                f"for sku {self.sku_id}"
            )
        self.reserved -= quantity

    def add_stock(self, quantity: int) -> None:
        if quantity <= 0:
            raise InvalidQuantityError("Add quantity must be positive")
        self.total += quantity

    def remove_stock(self, quantity: int) -> None:
        if quantity <= 0:
            raise InvalidQuantityError("Remove quantity must be positive")
        if quantity > self.available:
            raise InsufficientStockError(
                f"Cannot remove {quantity} from available {self.available} for sku {self.sku_id}"
            )
        self.total -= quantity


@dataclass
class Warehouse:
    id: str
    name: str
    skus: Dict[str, SkuStock] = field(default_factory=dict)

    def get_or_create_sku(self, sku_id: str, initial_total: int = 0) -> SkuStock:
        if sku_id not in self.skus:
            self.skus[sku_id] = SkuStock(sku_id=sku_id, total=initial_total)
        return self.skus[sku_id]

    def get_sku(self, sku_id: str) -> Optional[SkuStock]:
        return self.skus.get(sku_id)


@dataclass
class ReservationItem:
    warehouse_id: str
    sku_id: str
    quantity: int
    released_quantity: int = 0

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise InvalidQuantityError("Reservation item quantity must be positive")
        if self.released_quantity < 0:
            raise InvalidQuantityError("Released quantity cannot be negative")
        if self.released_quantity > self.quantity:
            raise InvalidQuantityError("Released quantity cannot exceed reserved quantity")

    @property
    def remaining_quantity(self) -> int:
        return self.quantity - self.released_quantity


@dataclass
class Reservation:
    id: str
    items: List[ReservationItem]
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    status: ReservationStatus = ReservationStatus.ACTIVE

    @classmethod
    def create(
        cls,
        items: List[ReservationItem],
        ttl: Optional[timedelta] = None,
    ) -> "Reservation":
        now = datetime.now()
        return cls(
            id=str(uuid.uuid4()),
            items=items,
            created_at=now,
            expires_at=now + ttl if ttl else None,
            status=ReservationStatus.ACTIVE,
        )

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    @property
    def is_active(self) -> bool:
        return self.status == ReservationStatus.ACTIVE and not self.is_expired

    def total_quantity(self) -> int:
        return sum(item.quantity for item in self.items)

    def remaining_quantity(self) -> int:
        return sum(item.remaining_quantity for item in self.items)
