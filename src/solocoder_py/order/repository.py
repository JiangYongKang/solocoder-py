from __future__ import annotations

from typing import Dict, List, Optional

from .models import Order


class OrderRepository:
    def __init__(self) -> None:
        self._orders: Dict[str, Order] = {}

    def save(self, order: Order) -> None:
        self._orders[order.id] = order

    def find_by_id(self, order_id: str) -> Optional[Order]:
        return self._orders.get(order_id)

    def find_all(self) -> List[Order]:
        return list(self._orders.values())

    def delete(self, order_id: str) -> bool:
        if order_id in self._orders:
            del self._orders[order_id]
            return True
        return False

    def clear(self) -> None:
        self._orders.clear()

    def count(self) -> int:
        return len(self._orders)
