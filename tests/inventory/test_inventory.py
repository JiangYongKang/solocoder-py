from datetime import timedelta
import threading
import time

import pytest

from solocoder_py.inventory import (
    InsufficientStockError,
    InventoryEngine,
    InventoryError,
    InvalidQuantityError,
    ReservationNotFoundError,
    ReservationStatus,
    ReserveRequestItem,
    WarehouseNotFoundError,
)

from .conftest import (
    build_engine_two_warehouses,
    build_engine_with_stock,
    make_reserve_items,
    short_ttl,
)


class TestWarehouseManagement:
    def test_add_and_get_warehouse(self):
        engine = InventoryEngine()
        wh = engine.add_warehouse("wh-1", "主仓库")
        assert wh.id == "wh-1"
        assert wh.name == "主仓库"
        found = engine.get_warehouse("wh-1")
        assert found is wh

    def test_get_nonexistent_warehouse_raises(self):
        engine = InventoryEngine()
        with pytest.raises(WarehouseNotFoundError):
            engine.get_warehouse("no-such-warehouse")

    def test_add_duplicate_warehouse_raises(self):
        engine = InventoryEngine()
        engine.add_warehouse("wh-1", "仓库1")
        with pytest.raises(InventoryError):
            engine.add_warehouse("wh-1", "仓库1重复")

    def test_list_warehouses(self):
        engine, wh_a, wh_b = build_engine_two_warehouses()
        warehouses = engine.list_warehouses()
        assert len(warehouses) == 2
        ids = {w.id for w in warehouses}
        assert wh_a in ids and wh_b in ids


class TestStockManagement:
    def test_add_stock_and_get_available(self):
        engine, wh_a, wh_b = build_engine_two_warehouses()
        sku = engine.add_stock(wh_a, "SKU-001", 100)
        assert sku.total == 100
        assert sku.available == 100
        assert sku.reserved == 0

    def test_add_stock_invalid_quantity(self):
        engine, wh_a, _ = build_engine_two_warehouses()
        with pytest.raises(InvalidQuantityError):
            engine.add_stock(wh_a, "SKU-001", 0)
        with pytest.raises(InvalidQuantityError):
            engine.add_stock(wh_a, "SKU-001", -5)

    def test_get_stock_returns_none_when_sku_not_found(self):
        engine, wh_a, _ = build_engine_two_warehouses()
        assert engine.get_stock(wh_a, "NO-SUCH-SKU") is None

    def test_get_total_available_across_warehouses(self):
        engine = build_engine_with_stock({
            "wh-a": {"SKU-001": 60},
            "wh-b": {"SKU-001": 50, "SKU-002": 30},
            "wh-c": {"SKU-001": 20},
        })
        assert engine.get_total_available("SKU-001") == 130
        assert engine.get_total_available("SKU-002") == 30
        assert engine.get_total_available("SKU-003") == 0

    def test_get_total_available_filtered_warehouses(self):
        engine = build_engine_with_stock({
            "wh-a": {"SKU-001": 60},
            "wh-b": {"SKU-001": 50},
            "wh-c": {"SKU-001": 20},
        })
        assert engine.get_total_available("SKU-001", ["wh-a", "wh-b"]) == 110
        assert engine.get_total_available("SKU-001", ["wh-c"]) == 20


class TestSingleWarehouseReserveAndRelease:
    def test_reserve_single_sku_single_warehouse(self):
        engine, wh_a, _ = build_engine_two_warehouses()
        engine.add_stock(wh_a, "SKU-001", 100)

        reservation = engine.reserve(make_reserve_items("SKU-001", 30))
        assert reservation.status == ReservationStatus.ACTIVE
        assert len(reservation.items) == 1
        assert reservation.items[0].warehouse_id == wh_a
        assert reservation.items[0].sku_id == "SKU-001"
        assert reservation.items[0].quantity == 30

        sku = engine.get_stock(wh_a, "SKU-001")
        assert sku.total == 100
        assert sku.reserved == 30
        assert sku.available == 70

    def test_reserve_and_full_release(self):
        engine, wh_a, _ = build_engine_two_warehouses()
        engine.add_stock(wh_a, "SKU-001", 100)

        reservation = engine.reserve(make_reserve_items("SKU-001", 30))
        released = engine.release(reservation.id)
        assert released == 30

        sku = engine.get_stock(wh_a, "SKU-001")
        assert sku.available == 100
        assert sku.reserved == 0
        updated = engine.get_reservation(reservation.id)
        assert updated.status == ReservationStatus.RELEASED

    def test_reserve_and_partial_release(self):
        engine, wh_a, _ = build_engine_two_warehouses()
        engine.add_stock(wh_a, "SKU-001", 100)

        reservation = engine.reserve(make_reserve_items("SKU-001", 50))
        released = engine.release(reservation.id, quantity=20)
        assert released == 20

        sku = engine.get_stock(wh_a, "SKU-001")
        assert sku.available == 70
        assert sku.reserved == 30

        reservation_updated = engine.get_reservation(reservation.id)
        assert reservation_updated.remaining_quantity() == 30
        assert reservation_updated.status == ReservationStatus.ACTIVE

        released2 = engine.release(reservation.id, quantity=30)
        assert released2 == 30
        sku = engine.get_stock(wh_a, "SKU-001")
        assert sku.available == 100
        assert sku.reserved == 0

    def test_release_more_than_reserved_raises(self):
        engine, wh_a, _ = build_engine_two_warehouses()
        engine.add_stock(wh_a, "SKU-001", 100)
        reservation = engine.reserve(make_reserve_items("SKU-001", 30))
        with pytest.raises(InvalidQuantityError):
            engine.release(reservation.id, quantity=50)

    def test_release_invalid_quantity_raises(self):
        engine, wh_a, _ = build_engine_two_warehouses()
        engine.add_stock(wh_a, "SKU-001", 100)
        reservation = engine.reserve(make_reserve_items("SKU-001", 30))
        with pytest.raises(InvalidQuantityError):
            engine.release(reservation.id, quantity=0)
        with pytest.raises(InvalidQuantityError):
            engine.release(reservation.id, quantity=-10)

    def test_release_nonexistent_reservation_raises(self):
        engine = InventoryEngine()
        with pytest.raises(ReservationNotFoundError):
            engine.release("no-such-reservation")


class TestInsufficientStock:
    def test_reserve_more_than_available_raises(self):
        engine, wh_a, _ = build_engine_two_warehouses()
        engine.add_stock(wh_a, "SKU-001", 10)
        with pytest.raises(InsufficientStockError):
            engine.reserve(make_reserve_items("SKU-001", 20))

    def test_reserve_empty_items_raises(self):
        engine = InventoryEngine()
        with pytest.raises(InvalidQuantityError):
            engine.reserve([])

    def test_reserve_zero_quantity_raises(self):
        engine, wh_a, _ = build_engine_two_warehouses()
        engine.add_stock(wh_a, "SKU-001", 10)
        with pytest.raises(InvalidQuantityError):
            engine.reserve([ReserveRequestItem(sku_id="SKU-001", quantity=0)])


class TestCrossWarehouseSplit:
    def test_cross_warehouse_split_prefers_largest_stock(self):
        engine = build_engine_with_stock({
            "wh-a": {"SKU-001": 40},
            "wh-b": {"SKU-001": 60},
            "wh-c": {"SKU-001": 20},
        })
        reservation = engine.reserve(make_reserve_items("SKU-001", 100))
        assert reservation.total_quantity() == 100

        allocations = {item.warehouse_id: item.quantity for item in reservation.items}
        assert allocations["wh-b"] == 60
        assert allocations["wh-a"] == 40
        assert "wh-c" not in allocations

        assert engine.get_stock("wh-b", "SKU-001").available == 0
        assert engine.get_stock("wh-a", "SKU-001").available == 0
        assert engine.get_stock("wh-c", "SKU-001").available == 20

    def test_cross_warehouse_split_three_warehouses(self):
        engine = build_engine_with_stock({
            "wh-a": {"SKU-001": 60},
            "wh-b": {"SKU-001": 50},
        })
        reservation = engine.reserve(make_reserve_items("SKU-001", 100))
        assert reservation.total_quantity() == 100

        allocations = {item.warehouse_id: item.quantity for item in reservation.items}
        assert allocations["wh-a"] == 60
        assert allocations["wh-b"] == 40

    def test_cross_warehouse_total_insufficient_rollback(self):
        engine = build_engine_with_stock({
            "wh-a": {"SKU-001": 30},
            "wh-b": {"SKU-001": 20},
        })
        with pytest.raises(InsufficientStockError):
            engine.reserve(make_reserve_items("SKU-001", 100))

        assert engine.get_stock("wh-a", "SKU-001").available == 30
        assert engine.get_stock("wh-a", "SKU-001").reserved == 0
        assert engine.get_stock("wh-b", "SKU-001").available == 20
        assert engine.get_stock("wh-b", "SKU-001").reserved == 0

    def test_cross_warehouse_multi_sku_atomic_rollback(self):
        engine = build_engine_with_stock({
            "wh-a": {"SKU-001": 100, "SKU-002": 5},
            "wh-b": {"SKU-001": 50, "SKU-002": 3},
        })
        items = [
            ReserveRequestItem(sku_id="SKU-001", quantity=10),
            ReserveRequestItem(sku_id="SKU-002", quantity=100),
        ]
        with pytest.raises(InsufficientStockError):
            engine.reserve(items)

        assert engine.get_stock("wh-a", "SKU-001").available == 100
        assert engine.get_stock("wh-a", "SKU-001").reserved == 0
        assert engine.get_stock("wh-b", "SKU-001").available == 50
        assert engine.get_stock("wh-b", "SKU-001").reserved == 0

    def test_release_cross_warehouse_reservation(self):
        engine = build_engine_with_stock({
            "wh-a": {"SKU-001": 60},
            "wh-b": {"SKU-001": 50},
        })
        reservation = engine.reserve(make_reserve_items("SKU-001", 100))
        engine.release(reservation.id)
        assert engine.get_stock("wh-a", "SKU-001").available == 60
        assert engine.get_stock("wh-a", "SKU-001").reserved == 0
        assert engine.get_stock("wh-b", "SKU-001").available == 50
        assert engine.get_stock("wh-b", "SKU-001").reserved == 0


class TestTtlExpiration:
    def test_ttl_expired_reservation_released_on_next_access(self):
        engine, wh_a, _ = build_engine_two_warehouses()
        engine.add_stock(wh_a, "SKU-001", 100)
        reservation = engine.reserve(make_reserve_items("SKU-001", 30), ttl=short_ttl(0.05))

        time.sleep(0.1)

        reservation_after = engine.get_reservation(reservation.id)
        assert reservation_after.status == ReservationStatus.EXPIRED
        sku = engine.get_stock(wh_a, "SKU-001")
        assert sku.available == 100
        assert sku.reserved == 0

    def test_ttl_not_expired_reservation_still_active(self):
        engine, wh_a, _ = build_engine_two_warehouses()
        engine.add_stock(wh_a, "SKU-001", 100)
        reservation = engine.reserve(make_reserve_items("SKU-001", 30), ttl=timedelta(minutes=5))

        reservation_after = engine.get_reservation(reservation.id)
        assert reservation_after.is_active is True
        sku = engine.get_stock(wh_a, "SKU-001")
        assert sku.available == 70
        assert sku.reserved == 30

    def test_no_ttl_never_expires(self):
        engine, wh_a, _ = build_engine_two_warehouses()
        engine.add_stock(wh_a, "SKU-001", 100)
        reservation = engine.reserve(make_reserve_items("SKU-001", 30))
        assert reservation.expires_at is None
        assert reservation.is_expired is False
        assert reservation.is_active is True

    def test_expired_reservation_cannot_be_confirmed(self):
        engine, wh_a, _ = build_engine_two_warehouses()
        engine.add_stock(wh_a, "SKU-001", 100)
        reservation = engine.reserve(make_reserve_items("SKU-001", 30), ttl=short_ttl(0.05))

        time.sleep(0.1)
        with pytest.raises(InventoryError):
            engine.confirm(reservation.id)

    def test_confirm_active_reservation_reduces_total_stock(self):
        engine, wh_a, _ = build_engine_two_warehouses()
        engine.add_stock(wh_a, "SKU-001", 100)
        reservation = engine.reserve(make_reserve_items("SKU-001", 30))
        engine.confirm(reservation.id)

        sku = engine.get_stock(wh_a, "SKU-001")
        assert sku.total == 70
        assert sku.reserved == 0
        assert sku.available == 70

        updated = engine.get_reservation(reservation.id)
        assert updated.status == ReservationStatus.CONFIRMED

    def test_release_already_expired_reservation(self):
        engine, wh_a, _ = build_engine_two_warehouses()
        engine.add_stock(wh_a, "SKU-001", 100)
        reservation = engine.reserve(make_reserve_items("SKU-001", 30), ttl=short_ttl(0.05))
        time.sleep(0.1)

        released = engine.release(reservation.id)
        assert released == 30
        sku = engine.get_stock(wh_a, "SKU-001")
        assert sku.available == 100


class TestBoundaryConditions:
    def test_exact_stock_fully_reserved(self):
        engine, wh_a, _ = build_engine_two_warehouses()
        engine.add_stock(wh_a, "SKU-001", 10)
        reservation = engine.reserve(make_reserve_items("SKU-001", 10))
        assert reservation.total_quantity() == 10
        sku = engine.get_stock(wh_a, "SKU-001")
        assert sku.available == 0
        assert sku.reserved == 10

    def test_empty_warehouse_cannot_reserve(self):
        engine, wh_a, _ = build_engine_two_warehouses()
        with pytest.raises(InsufficientStockError):
            engine.reserve(make_reserve_items("SKU-001", 1))

    def test_concurrent_reserve_no_oversell(self):
        engine = build_engine_with_stock({"wh-a": {"SKU-001": 100}})
        errors = []
        successful = []

        def worker(idx):
            try:
                reservation = engine.reserve(make_reserve_items("SKU-001", 20))
                successful.append(reservation)
            except InsufficientStockError as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        total_reserved = sum(r.total_quantity() for r in successful)
        assert total_reserved == 100
        assert len(successful) == 5
        assert len(errors) == 5

        sku = engine.get_stock("wh-a", "SKU-001")
        assert sku.available == 0
        assert sku.reserved == 100
        assert sku.total == 100

    def test_concurrent_reserve_cross_warehouse_no_oversell(self):
        engine = build_engine_with_stock({
            "wh-a": {"SKU-001": 60},
            "wh-b": {"SKU-001": 40},
        })
        errors = []
        successful = []

        def worker():
            try:
                reservation = engine.reserve(make_reserve_items("SKU-001", 25))
                successful.append(reservation)
            except InsufficientStockError as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        total_reserved = sum(r.total_quantity() for r in successful)
        assert total_reserved == 100
        assert len(successful) == 4
        assert len(errors) == 4

        sku_a = engine.get_stock("wh-a", "SKU-001")
        sku_b = engine.get_stock("wh-b", "SKU-001")
        assert sku_a.available + sku_b.available == 0
        assert sku_a.reserved + sku_b.reserved == 100

    def test_preferred_warehouse_ids(self):
        engine = build_engine_with_stock({
            "wh-a": {"SKU-001": 100},
            "wh-b": {"SKU-001": 100},
        })
        reservation = engine.reserve([
            ReserveRequestItem(sku_id="SKU-001", quantity=50, preferred_warehouse_ids=["wh-b"])
        ])
        assert len(reservation.items) == 1
        assert reservation.items[0].warehouse_id == "wh-b"

        assert engine.get_stock("wh-b", "SKU-001").available == 50
        assert engine.get_stock("wh-a", "SKU-001").available == 100

    def test_multi_sku_reservation(self):
        engine = build_engine_with_stock({
            "wh-a": {"SKU-001": 50, "SKU-002": 30},
        })
        reservation = engine.reserve([
            ReserveRequestItem(sku_id="SKU-001", quantity=10),
            ReserveRequestItem(sku_id="SKU-002", quantity=5),
        ])
        assert reservation.total_quantity() == 15
        assert engine.get_stock("wh-a", "SKU-001").reserved == 10
        assert engine.get_stock("wh-a", "SKU-002").reserved == 5


class TestConfirmEdgeCases:
    def test_confirm_nonexistent_reservation(self):
        engine = InventoryEngine()
        with pytest.raises(ReservationNotFoundError):
            engine.confirm("no-such-reservation")

    def test_confirm_already_confirmed_reservation(self):
        engine, wh_a, _ = build_engine_two_warehouses()
        engine.add_stock(wh_a, "SKU-001", 100)
        reservation = engine.reserve(make_reserve_items("SKU-001", 30))
        engine.confirm(reservation.id)
        with pytest.raises(InventoryError):
            engine.confirm(reservation.id)

    def test_confirm_already_released_reservation(self):
        engine, wh_a, _ = build_engine_two_warehouses()
        engine.add_stock(wh_a, "SKU-001", 100)
        reservation = engine.reserve(make_reserve_items("SKU-001", 30))
        engine.release(reservation.id)
        with pytest.raises(InventoryError):
            engine.confirm(reservation.id)

    def test_confirm_after_partial_release_only_deducts_remaining(self):
        engine, wh_a, _ = build_engine_two_warehouses()
        engine.add_stock(wh_a, "SKU-001", 100)
        reservation = engine.reserve(make_reserve_items("SKU-001", 50))

        engine.release(reservation.id, quantity=20)

        engine.confirm(reservation.id)

        sku = engine.get_stock(wh_a, "SKU-001")
        assert sku.total == 70
        assert sku.reserved == 0
        assert sku.available == 70

        updated = engine.get_reservation(reservation.id)
        assert updated.status == ReservationStatus.CONFIRMED
        assert updated.remaining_quantity() == 0


class TestReleaseEdgeCases:
    def test_release_already_confirmed_reservation(self):
        engine, wh_a, _ = build_engine_two_warehouses()
        engine.add_stock(wh_a, "SKU-001", 100)
        reservation = engine.reserve(make_reserve_items("SKU-001", 30))
        engine.confirm(reservation.id)
        with pytest.raises(InventoryError):
            engine.release(reservation.id)

    def test_release_already_released_reservation(self):
        engine, wh_a, _ = build_engine_two_warehouses()
        engine.add_stock(wh_a, "SKU-001", 100)
        reservation = engine.reserve(make_reserve_items("SKU-001", 30))
        engine.release(reservation.id)
        with pytest.raises(InventoryError):
            engine.release(reservation.id)


class TestPreferredWarehouseInsufficient:
    def test_preferred_warehouses_insufficient_total_stock(self):
        engine = build_engine_with_stock({
            "wh-a": {"SKU-001": 30},
            "wh-b": {"SKU-001": 100},
        })
        with pytest.raises(InsufficientStockError):
            engine.reserve([
                ReserveRequestItem(sku_id="SKU-001", quantity=50, preferred_warehouse_ids=["wh-a"])
            ])

        assert engine.get_stock("wh-a", "SKU-001").available == 30
        assert engine.get_stock("wh-a", "SKU-001").reserved == 0
        assert engine.get_stock("wh-b", "SKU-001").available == 100
        assert engine.get_stock("wh-b", "SKU-001").reserved == 0

    def test_preferred_warehouses_partial_split(self):
        engine = build_engine_with_stock({
            "wh-a": {"SKU-001": 30},
            "wh-b": {"SKU-001": 30},
            "wh-c": {"SKU-001": 100},
        })
        reservation = engine.reserve([
            ReserveRequestItem(sku_id="SKU-001", quantity=50, preferred_warehouse_ids=["wh-a", "wh-b"])
        ])
        allocations = {item.warehouse_id: item.quantity for item in reservation.items}
        assert allocations["wh-a"] == 30
        assert allocations["wh-b"] == 20
        assert "wh-c" not in allocations


class TestTtlPartialReleaseCross:
    def test_partial_release_then_ttl_expired_release_returns_remaining(self):
        engine, wh_a, _ = build_engine_two_warehouses()
        engine.add_stock(wh_a, "SKU-001", 100)
        reservation = engine.reserve(make_reserve_items("SKU-001", 30), ttl=short_ttl(0.05))

        released1 = engine.release(reservation.id, quantity=10)
        assert released1 == 10
        sku = engine.get_stock(wh_a, "SKU-001")
        assert sku.available == 80
        assert sku.reserved == 20

        time.sleep(0.1)

        released2 = engine.release(reservation.id)
        assert released2 == 20

        sku = engine.get_stock(wh_a, "SKU-001")
        assert sku.available == 100
        assert sku.reserved == 0

        updated = engine.get_reservation(reservation.id)
        assert updated.status == ReservationStatus.EXPIRED
        assert updated.remaining_quantity() == 0

    def test_partial_release_then_ttl_expired_lazy_cleanup(self):
        engine, wh_a, _ = build_engine_two_warehouses()
        engine.add_stock(wh_a, "SKU-001", 100)
        reservation = engine.reserve(make_reserve_items("SKU-001", 30), ttl=short_ttl(0.05))

        engine.release(reservation.id, quantity=10)
        assert engine.get_stock(wh_a, "SKU-001").available == 80
        assert engine.get_stock(wh_a, "SKU-001").reserved == 20

        time.sleep(0.1)

        engine.get_total_available("SKU-001")

        updated = engine.get_reservation(reservation.id)
        assert updated.status == ReservationStatus.EXPIRED
        assert updated.remaining_quantity() == 0
        sku = engine.get_stock(wh_a, "SKU-001")
        assert sku.available == 100
        assert sku.reserved == 0

