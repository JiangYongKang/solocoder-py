from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from .models import (
    InsufficientStockError,
    InventoryError,
    InvalidQuantityError,
    Reservation,
    ReservationItem,
    ReservationNotFoundError,
    ReservationStatus,
    SkuStock,
    Warehouse,
    WarehouseNotFoundError,
)


@dataclass
class ReserveRequestItem:
    sku_id: str
    quantity: int
    preferred_warehouse_ids: Optional[List[str]] = None


class InventoryEngine:
    def __init__(self) -> None:
        self._warehouses: Dict[str, Warehouse] = {}
        self._reservations: Dict[str, Reservation] = {}
        self._lock = threading.RLock()

    def _cleanup_expired(self) -> None:
        now = datetime.now()
        expired_ids = [
            rid
            for rid, r in self._reservations.items()
            if r.status == ReservationStatus.ACTIVE
            and r.expires_at is not None
            and r.expires_at < now
        ]
        for rid in expired_ids:
            self._release_reservation_internal(rid, force_expired=True)

    def add_warehouse(self, warehouse_id: str, name: str) -> Warehouse:
        with self._lock:
            if warehouse_id in self._warehouses:
                raise InventoryError(f"Warehouse already exists: {warehouse_id}")
            warehouse = Warehouse(id=warehouse_id, name=name)
            self._warehouses[warehouse_id] = warehouse
            return warehouse

    def get_warehouse(self, warehouse_id: str) -> Warehouse:
        warehouse = self._warehouses.get(warehouse_id)
        if warehouse is None:
            raise WarehouseNotFoundError(f"Warehouse not found: {warehouse_id}")
        return warehouse

    def list_warehouses(self) -> List[Warehouse]:
        return list(self._warehouses.values())

    def add_stock(self, warehouse_id: str, sku_id: str, quantity: int) -> SkuStock:
        if quantity <= 0:
            raise InvalidQuantityError("Add quantity must be positive")
        with self._lock:
            self._cleanup_expired()
            warehouse = self.get_warehouse(warehouse_id)
            sku = warehouse.get_or_create_sku(sku_id)
            sku.add_stock(quantity)
            return sku

    def get_stock(self, warehouse_id: str, sku_id: str) -> Optional[SkuStock]:
        with self._lock:
            self._cleanup_expired()
            warehouse = self.get_warehouse(warehouse_id)
            return warehouse.get_sku(sku_id)

    def get_total_available(self, sku_id: str, warehouse_ids: Optional[List[str]] = None) -> int:
        with self._lock:
            self._cleanup_expired()
            total = 0
            warehouses = (
                [self.get_warehouse(wid) for wid in warehouse_ids]
                if warehouse_ids
                else list(self._warehouses.values())
            )
            for wh in warehouses:
                sku = wh.get_sku(sku_id)
                if sku is not None:
                    total += sku.available
            return total

    def reserve(
        self,
        items: List[ReserveRequestItem],
        ttl: Optional[timedelta] = None,
    ) -> Reservation:
        if not items:
            raise InvalidQuantityError("Reservation must have at least one item")
        for item in items:
            if item.quantity <= 0:
                raise InvalidQuantityError("Reserve quantity must be positive")

        with self._lock:
            self._cleanup_expired()
            reservation_items: List[ReservationItem] = []
            applied_ops: List[Tuple[str, str, int]] = []

            try:
                for req_item in items:
                    sku_id = req_item.sku_id
                    quantity_needed = req_item.quantity

                    candidate_warehouses: List[Warehouse]
                    if req_item.preferred_warehouse_ids:
                        candidate_warehouses = [
                            self.get_warehouse(wid)
                            for wid in req_item.preferred_warehouse_ids
                        ]
                    else:
                        candidate_warehouses = list(self._warehouses.values())

                    warehouses_with_stock = []
                    for wh in candidate_warehouses:
                        sku = wh.get_sku(sku_id)
                        if sku is not None and sku.available > 0:
                            warehouses_with_stock.append((wh, sku.available))

                    warehouses_with_stock.sort(key=lambda x: x[1], reverse=True)

                    total_available = sum(av for _, av in warehouses_with_stock)
                    if total_available < quantity_needed:
                        raise InsufficientStockError(
                            f"Insufficient total stock for sku {sku_id}: "
                            f"requested {quantity_needed}, total available {total_available}"
                        )

                    remaining = quantity_needed
                    for wh, _ in warehouses_with_stock:
                        if remaining <= 0:
                            break
                        sku = wh.get_sku(sku_id)
                        if sku is None or sku.available <= 0:
                            continue
                        take = min(remaining, sku.available)
                        sku.reserve(take)
                        applied_ops.append((wh.id, sku_id, take))
                        reservation_items.append(
                            ReservationItem(
                                warehouse_id=wh.id,
                                sku_id=sku_id,
                                quantity=take,
                            )
                        )
                        remaining -= take

                    if remaining > 0:
                        raise InsufficientStockError(
                            f"Could not fulfill reservation for sku {sku_id}: "
                            f"short {remaining} units after warehouse allocation"
                        )

                reservation = Reservation.create(items=reservation_items, ttl=ttl)
                self._reservations[reservation.id] = reservation
                return reservation

            except Exception:
                for wh_id, sku_id, qty in reversed(applied_ops):
                    wh = self._warehouses.get(wh_id)
                    if wh is not None:
                        sku = wh.get_sku(sku_id)
                        if sku is not None:
                            sku.release(qty)
                raise

    def release(self, reservation_id: str, quantity: Optional[int] = None) -> int:
        with self._lock:
            reservation = self._reservations.get(reservation_id)
            if reservation is None:
                raise ReservationNotFoundError(
                    f"Reservation not found: {reservation_id}"
                )

            if reservation.status in (ReservationStatus.RELEASED, ReservationStatus.CONFIRMED):
                raise InventoryError(
                    f"Cannot release reservation in status {reservation.status.value}"
                )

            if reservation.status == ReservationStatus.EXPIRED or reservation.is_expired:
                remaining = reservation.remaining_quantity()
                self._release_reservation_internal(reservation_id, force_expired=True)
                self._cleanup_expired()
                return remaining

            self._cleanup_expired()

            remaining_total = reservation.remaining_quantity()
            release_qty = quantity if quantity is not None else remaining_total

            if release_qty <= 0:
                raise InvalidQuantityError("Release quantity must be positive")
            if release_qty > remaining_total:
                raise InvalidQuantityError(
                    f"Release quantity {release_qty} exceeds remaining "
                    f"{remaining_total} for reservation {reservation_id}"
                )

            still_to_release = release_qty
            for item in reservation.items:
                if still_to_release <= 0:
                    break
                item_remaining = item.remaining_quantity
                if item_remaining <= 0:
                    continue
                take = min(still_to_release, item_remaining)
                wh = self._warehouses.get(item.warehouse_id)
                if wh is not None:
                    sku = wh.get_sku(item.sku_id)
                    if sku is not None:
                        sku.release(take)
                item.released_quantity += take
                still_to_release -= take

            if reservation.remaining_quantity() == 0:
                reservation.status = ReservationStatus.RELEASED

            return release_qty

    def confirm(self, reservation_id: str) -> None:
        with self._lock:
            self._cleanup_expired()
            reservation = self._reservations.get(reservation_id)
            if reservation is None:
                raise ReservationNotFoundError(
                    f"Reservation not found: {reservation_id}"
                )
            if not reservation.is_active:
                if reservation.is_expired:
                    raise InventoryError(
                        f"Cannot confirm expired reservation {reservation_id}"
                    )
                raise InventoryError(
                    f"Cannot confirm reservation in status {reservation.status.value}"
                )

            for item in reservation.items:
                remaining = item.remaining_quantity
                if remaining > 0:
                    wh = self._warehouses.get(item.warehouse_id)
                    if wh is not None:
                        sku = wh.get_sku(item.sku_id)
                        if sku is not None:
                            sku.release(remaining)
                            sku.remove_stock(remaining)
                            item.released_quantity += remaining

            reservation.status = ReservationStatus.CONFIRMED

    def get_reservation(self, reservation_id: str) -> Optional[Reservation]:
        with self._lock:
            self._cleanup_expired()
            return self._reservations.get(reservation_id)

    def _release_reservation_internal(
        self, reservation_id: str, force_expired: bool = False
    ) -> None:
        reservation = self._reservations.get(reservation_id)
        if reservation is None:
            return
        if reservation.status in (ReservationStatus.RELEASED, ReservationStatus.CONFIRMED):
            return

        for item in reservation.items:
            remaining = item.remaining_quantity
            if remaining > 0:
                wh = self._warehouses.get(item.warehouse_id)
                if wh is not None:
                    sku = wh.get_sku(item.sku_id)
                    if sku is not None and sku.reserved >= remaining:
                        sku.release(remaining)
                        item.released_quantity += remaining

        reservation.status = (
            ReservationStatus.EXPIRED if force_expired else ReservationStatus.RELEASED
        )
