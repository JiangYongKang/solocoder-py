from datetime import timedelta
from typing import Dict, Tuple

from solocoder_py.inventory import InventoryEngine, ReserveRequestItem


def build_engine_two_warehouses() -> Tuple[InventoryEngine, str, str]:
    engine = InventoryEngine()
    wh_a = engine.add_warehouse("wh-a", "仓库A")
    wh_b = engine.add_warehouse("wh-b", "仓库B")
    return engine, wh_a.id, wh_b.id


def build_engine_with_stock(
    stock_map: Dict[str, Dict[str, int]]
) -> InventoryEngine:
    engine = InventoryEngine()
    for wh_id, skus in stock_map.items():
        engine.add_warehouse(wh_id, f"仓库-{wh_id}")
        for sku_id, qty in skus.items():
            engine.add_stock(wh_id, sku_id, qty)
    return engine


def make_reserve_items(
    sku_id: str, quantity: int, preferred: list[str] | None = None
) -> list[ReserveRequestItem]:
    return [ReserveRequestItem(sku_id=sku_id, quantity=quantity, preferred_warehouse_ids=preferred)]


def short_ttl(seconds: float = 0.05) -> timedelta:
    return timedelta(seconds=seconds)
