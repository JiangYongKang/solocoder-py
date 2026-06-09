from decimal import Decimal
from typing import Tuple

from solocoder_py.cart import CartEngine, Product


def build_engine_with_products() -> Tuple[CartEngine, str, str, str]:
    engine = CartEngine()
    p1 = engine.register_product(Product(
        id="sku-001",
        name="iPhone 15",
        price=Decimal("5999.00"),
        stock=10,
    ))
    p2 = engine.register_product(Product(
        id="sku-002",
        name="AirPods Pro",
        price=Decimal("1899.00"),
        stock=20,
    ))
    p3 = engine.register_product(Product(
        id="sku-003",
        name="MacBook Pro",
        price=Decimal("14999.00"),
        stock=5,
    ))
    return engine, p1.id, p2.id, p3.id
