from decimal import Decimal

import pytest

from solocoder_py.cart import (
    CartEngine,
    CartError,
    CartItemNotFoundError,
    CartNotFoundError,
    InsufficientStockError,
    InvalidQuantityError,
    Product,
    ProductNotFoundError,
    ProductOfflineError,
)
from datetime import datetime

from .conftest import build_engine_with_products


class TestProductManagement:
    def test_register_product(self):
        engine = CartEngine()
        product = engine.register_product(Product(
            id="sku-001",
            name="Test Product",
            price=Decimal("99.99"),
            stock=100,
        ))
        assert product.id == "sku-001"
        assert product.name == "Test Product"
        assert product.stock == 100
        assert product.is_online is True

    def test_register_duplicate_product_raises(self):
        engine, p1, _, _ = build_engine_with_products()
        with pytest.raises(CartError):
            engine.register_product(Product(
                id=p1,
                name="Duplicate",
                price=Decimal("10.00"),
                stock=10,
            ))

    def test_get_product(self):
        engine, p1, _, _ = build_engine_with_products()
        product = engine.get_product(p1)
        assert product.id == p1
        assert product.name == "iPhone 15"

    def test_get_nonexistent_product_raises(self):
        engine = CartEngine()
        with pytest.raises(ProductNotFoundError):
            engine.get_product("no-such-product")

    def test_update_product_stock(self):
        engine, p1, _, _ = build_engine_with_products()
        updated = engine.update_product_stock(p1, 50)
        assert updated.stock == 50

    def test_update_product_stock_negative_raises(self):
        engine, p1, _, _ = build_engine_with_products()
        with pytest.raises(InvalidQuantityError):
            engine.update_product_stock(p1, -1)

    def test_set_product_online(self):
        engine, p1, _, _ = build_engine_with_products()
        product = engine.set_product_online(p1, False)
        assert product.is_online is False
        product = engine.set_product_online(p1, True)
        assert product.is_online is True


class TestCartCreation:
    def test_create_anonymous_cart(self):
        engine = CartEngine()
        cart = engine.create_anonymous_cart()
        assert cart.user_id is None
        assert cart.is_anonymous is True
        assert cart.unique_products == 0
        assert cart.total_items == 0

    def test_get_anonymous_cart(self):
        engine = CartEngine()
        cart = engine.create_anonymous_cart()
        found = engine.get_anonymous_cart(cart.id)
        assert found is cart

    def test_get_nonexistent_anonymous_cart_raises(self):
        engine = CartEngine()
        with pytest.raises(CartNotFoundError):
            engine.get_anonymous_cart("no-such-cart")

    def test_create_user_cart(self):
        engine = CartEngine()
        cart = engine.create_user_cart("user-001")
        assert cart.user_id == "user-001"
        assert cart.is_anonymous is False

    def test_create_duplicate_user_cart_raises(self):
        engine = CartEngine()
        engine.create_user_cart("user-001")
        with pytest.raises(CartError):
            engine.create_user_cart("user-001")

    def test_get_user_cart(self):
        engine = CartEngine()
        engine.create_user_cart("user-001")
        cart = engine.get_user_cart("user-001")
        assert cart.user_id == "user-001"

    def test_get_nonexistent_user_cart_raises(self):
        engine = CartEngine()
        with pytest.raises(CartNotFoundError):
            engine.get_user_cart("no-such-user")

    def test_get_or_create_user_cart(self):
        engine = CartEngine()
        cart1 = engine.get_or_create_user_cart("user-001")
        cart2 = engine.get_or_create_user_cart("user-001")
        assert cart1 is cart2


class TestAnonymousCartOperations:
    def test_add_item_to_anonymous_cart(self):
        engine, p1, p2, _ = build_engine_with_products()
        cart = engine.create_anonymous_cart()

        updated = engine.add_to_anonymous_cart(cart.id, p1, 2)
        assert updated.get_item(p1).quantity == 2
        assert updated.total_items == 2

        updated = engine.add_to_anonymous_cart(cart.id, p2, 3)
        assert updated.unique_products == 2
        assert updated.total_items == 5

    def test_add_item_quantity_accumulates(self):
        engine, p1, _, _ = build_engine_with_products()
        cart = engine.create_anonymous_cart()

        engine.add_to_anonymous_cart(cart.id, p1, 2)
        updated = engine.add_to_anonymous_cart(cart.id, p1, 3)
        assert updated.get_item(p1).quantity == 5

    def test_add_item_invalid_quantity_raises(self):
        engine, p1, _, _ = build_engine_with_products()
        cart = engine.create_anonymous_cart()

        with pytest.raises(InvalidQuantityError):
            engine.add_to_anonymous_cart(cart.id, p1, 0)
        with pytest.raises(InvalidQuantityError):
            engine.add_to_anonymous_cart(cart.id, p1, -1)

    def test_add_item_exceeds_stock_is_clipped(self):
        engine, p1, _, _ = build_engine_with_products()
        cart = engine.create_anonymous_cart()

        updated = engine.add_to_anonymous_cart(cart.id, p1, 100)
        assert updated.get_item(p1).quantity == 10

    def test_add_item_to_nonexistent_cart_raises(self):
        engine, p1, _, _ = build_engine_with_products()
        with pytest.raises(CartNotFoundError):
            engine.add_to_anonymous_cart("fake-cart", p1, 1)

    def test_add_out_of_stock_product_raises(self):
        engine, p1, _, _ = build_engine_with_products()
        engine.update_product_stock(p1, 0)
        cart = engine.create_anonymous_cart()
        with pytest.raises(InsufficientStockError):
            engine.add_to_anonymous_cart(cart.id, p1, 1)

    def test_add_offline_product_raises(self):
        engine, p1, _, _ = build_engine_with_products()
        engine.set_product_online(p1, False)
        cart = engine.create_anonymous_cart()
        with pytest.raises(ProductOfflineError):
            engine.add_to_anonymous_cart(cart.id, p1, 1)

    def test_remove_item_from_anonymous_cart(self):
        engine, p1, p2, _ = build_engine_with_products()
        cart = engine.create_anonymous_cart()
        engine.add_to_anonymous_cart(cart.id, p1, 2)
        engine.add_to_anonymous_cart(cart.id, p2, 3)

        updated = engine.remove_from_anonymous_cart(cart.id, p1)
        assert updated.get_item(p1) is None
        assert updated.unique_products == 1
        assert updated.total_items == 3

    def test_remove_nonexistent_item_no_op(self):
        engine, p1, _, _ = build_engine_with_products()
        cart = engine.create_anonymous_cart()
        updated = engine.remove_from_anonymous_cart(cart.id, p1)
        assert updated.unique_products == 0

    def test_update_anonymous_cart_quantity(self):
        engine, p1, _, _ = build_engine_with_products()
        cart = engine.create_anonymous_cart()
        engine.add_to_anonymous_cart(cart.id, p1, 2)

        updated = engine.update_anonymous_cart_quantity(cart.id, p1, 5)
        assert updated.get_item(p1).quantity == 5

    def test_update_quantity_invalid_raises(self):
        engine, p1, _, _ = build_engine_with_products()
        cart = engine.create_anonymous_cart()
        engine.add_to_anonymous_cart(cart.id, p1, 2)

        with pytest.raises(InvalidQuantityError):
            engine.update_anonymous_cart_quantity(cart.id, p1, 0)
        with pytest.raises(InvalidQuantityError):
            engine.update_anonymous_cart_quantity(cart.id, p1, -1)

    def test_update_quantity_exceeds_stock_is_clipped(self):
        engine, p1, _, _ = build_engine_with_products()
        cart = engine.create_anonymous_cart()
        engine.add_to_anonymous_cart(cart.id, p1, 2)

        updated = engine.update_anonymous_cart_quantity(cart.id, p1, 100)
        assert updated.get_item(p1).quantity == 10

    def test_update_quantity_nonexistent_item_raises(self):
        engine, p1, _, _ = build_engine_with_products()
        cart = engine.create_anonymous_cart()
        with pytest.raises(CartItemNotFoundError):
            engine.update_anonymous_cart_quantity(cart.id, p1, 5)

    def test_clear_anonymous_cart(self):
        engine, p1, p2, _ = build_engine_with_products()
        cart = engine.create_anonymous_cart()
        engine.add_to_anonymous_cart(cart.id, p1, 2)
        engine.add_to_anonymous_cart(cart.id, p2, 3)

        updated = engine.clear_anonymous_cart(cart.id)
        assert updated.unique_products == 0
        assert updated.total_items == 0


class TestUserCartOperations:
    def test_add_item_to_user_cart(self):
        engine, p1, p2, _ = build_engine_with_products()
        engine.create_user_cart("user-001")

        updated = engine.add_to_user_cart("user-001", p1, 2)
        assert updated.get_item(p1).quantity == 2

        updated = engine.add_to_user_cart("user-001", p2, 3)
        assert updated.unique_products == 2

    def test_add_item_accumulates_in_user_cart(self):
        engine, p1, _, _ = build_engine_with_products()
        engine.create_user_cart("user-001")

        engine.add_to_user_cart("user-001", p1, 2)
        updated = engine.add_to_user_cart("user-001", p1, 3)
        assert updated.get_item(p1).quantity == 5

    def test_add_item_auto_creates_user_cart(self):
        engine, p1, _, _ = build_engine_with_products()
        updated = engine.add_to_user_cart("user-new", p1, 2)
        assert updated.get_item(p1).quantity == 2

    def test_remove_item_from_user_cart(self):
        engine, p1, p2, _ = build_engine_with_products()
        engine.create_user_cart("user-001")
        engine.add_to_user_cart("user-001", p1, 2)
        engine.add_to_user_cart("user-001", p2, 3)

        updated = engine.remove_from_user_cart("user-001", p1)
        assert updated.get_item(p1) is None
        assert updated.unique_products == 1

    def test_update_user_cart_quantity(self):
        engine, p1, _, _ = build_engine_with_products()
        engine.create_user_cart("user-001")
        engine.add_to_user_cart("user-001", p1, 2)

        updated = engine.update_user_cart_quantity("user-001", p1, 7)
        assert updated.get_item(p1).quantity == 7

    def test_clear_user_cart(self):
        engine, p1, p2, _ = build_engine_with_products()
        engine.create_user_cart("user-001")
        engine.add_to_user_cart("user-001", p1, 2)
        engine.add_to_user_cart("user-001", p2, 3)

        updated = engine.clear_user_cart("user-001")
        assert updated.unique_products == 0


class TestCartMergeNormalFlow:
    def test_merge_anonymous_to_empty_user_cart(self):
        engine, p1, p2, _ = build_engine_with_products()
        anon_cart = engine.create_anonymous_cart()
        engine.add_to_anonymous_cart(anon_cart.id, p1, 2)
        engine.add_to_anonymous_cart(anon_cart.id, p2, 3)

        result = engine.merge_anonymous_to_user_cart(anon_cart.id, "user-001")

        assert result.cart.user_id == "user-001"
        assert result.cart.get_item(p1).quantity == 2
        assert result.cart.get_item(p2).quantity == 3
        assert len(result.trims) == 0
        assert len(result.removed_unregistered_products) == 0
        assert len(result.removed_offline_products) == 0
        assert len(result.removed_out_of_stock_products) == 0

    def test_merge_with_same_products_quantity_accumulates(self):
        engine, p1, _, _ = build_engine_with_products()
        anon_cart = engine.create_anonymous_cart()
        engine.add_to_anonymous_cart(anon_cart.id, p1, 2)

        engine.create_user_cart("user-001")
        engine.add_to_user_cart("user-001", p1, 3)

        result = engine.merge_anonymous_to_user_cart(anon_cart.id, "user-001")

        assert result.cart.get_item(p1).quantity == 5

    def test_merge_different_products_combined(self):
        engine, p1, p2, p3 = build_engine_with_products()
        anon_cart = engine.create_anonymous_cart()
        engine.add_to_anonymous_cart(anon_cart.id, p1, 2)
        engine.add_to_anonymous_cart(anon_cart.id, p2, 3)

        engine.create_user_cart("user-001")
        engine.add_to_user_cart("user-001", p3, 1)

        result = engine.merge_anonymous_to_user_cart(anon_cart.id, "user-001")

        assert result.cart.unique_products == 3
        assert result.cart.get_item(p1).quantity == 2
        assert result.cart.get_item(p2).quantity == 3
        assert result.cart.get_item(p3).quantity == 1

    def test_merge_clears_anonymous_cart(self):
        engine, p1, _, _ = build_engine_with_products()
        anon_cart = engine.create_anonymous_cart()
        engine.add_to_anonymous_cart(anon_cart.id, p1, 2)
        anon_cart_id = anon_cart.id

        engine.merge_anonymous_to_user_cart(anon_cart_id, "user-001")

        with pytest.raises(CartNotFoundError):
            engine.get_anonymous_cart(anon_cart_id)

    def test_merge_nonexistent_anonymous_cart_raises(self):
        engine = CartEngine()
        with pytest.raises(CartNotFoundError):
            engine.merge_anonymous_to_user_cart("fake-cart", "user-001")


class TestCartMergeStockTrimming:
    def test_merge_exceeds_stock_is_trimmed(self):
        engine, p1, _, _ = build_engine_with_products()
        anon_cart = engine.create_anonymous_cart()
        engine.add_to_anonymous_cart(anon_cart.id, p1, 8)

        engine.create_user_cart("user-001")
        engine.add_to_user_cart("user-001", p1, 5)

        result = engine.merge_anonymous_to_user_cart(anon_cart.id, "user-001")

        assert result.cart.get_item(p1).quantity == 10
        assert len(result.trims) == 1
        trim = result.trims[0]
        assert trim.product_id == p1
        assert trim.requested_quantity == 13
        assert trim.actual_quantity == 10
        assert trim.trimmed_quantity == 3

    def test_merge_exactly_at_stock_limit_no_trim(self):
        engine, p1, _, _ = build_engine_with_products()
        anon_cart = engine.create_anonymous_cart()
        engine.add_to_anonymous_cart(anon_cart.id, p1, 4)

        engine.create_user_cart("user-001")
        engine.add_to_user_cart("user-001", p1, 6)

        result = engine.merge_anonymous_to_user_cart(anon_cart.id, "user-001")

        assert result.cart.get_item(p1).quantity == 10
        assert len(result.trims) == 0

    def test_merge_anonymous_cart_alone_exceeds_stock(self):
        engine, p1, _, _ = build_engine_with_products()
        anon_cart = engine.create_anonymous_cart()
        anon_cart.add_item(p1, 50)

        result = engine.merge_anonymous_to_user_cart(anon_cart.id, "user-001")

        assert result.cart.get_item(p1).quantity == 10
        assert len(result.trims) == 1
        assert result.trims[0].trimmed_quantity == 40

    def test_multiple_products_some_trimmed(self):
        engine, p1, p2, p3 = build_engine_with_products()
        anon_cart = engine.create_anonymous_cart()
        anon_cart.add_item(p1, 50)
        anon_cart.add_item(p2, 5)
        anon_cart.add_item(p3, 10)

        result = engine.merge_anonymous_to_user_cart(anon_cart.id, "user-001")

        assert result.cart.get_item(p1).quantity == 10
        assert result.cart.get_item(p2).quantity == 5
        assert result.cart.get_item(p3).quantity == 5
        assert len(result.trims) == 2
        trimmed_ids = {t.product_id for t in result.trims}
        assert p1 in trimmed_ids
        assert p3 in trimmed_ids


class TestCartMergeBoundaryConditions:
    def test_merge_empty_anonymous_cart(self):
        engine, p1, _, _ = build_engine_with_products()
        anon_cart = engine.create_anonymous_cart()

        engine.create_user_cart("user-001")
        engine.add_to_user_cart("user-001", p1, 3)

        result = engine.merge_anonymous_to_user_cart(anon_cart.id, "user-001")

        assert result.cart.get_item(p1).quantity == 3
        assert len(result.trims) == 0
        assert len(result.removed_unregistered_products) == 0
        assert len(result.removed_offline_products) == 0
        assert len(result.removed_out_of_stock_products) == 0

    def test_merge_into_empty_user_cart(self):
        engine, p1, _, _ = build_engine_with_products()
        anon_cart = engine.create_anonymous_cart()
        engine.add_to_anonymous_cart(anon_cart.id, p1, 3)

        result = engine.merge_anonymous_to_user_cart(anon_cart.id, "user-001")

        assert result.cart.get_item(p1).quantity == 3
        assert result.cart.user_id == "user-001"

    def test_merge_both_empty_carts(self):
        engine = CartEngine()
        anon_cart = engine.create_anonymous_cart()

        result = engine.merge_anonymous_to_user_cart(anon_cart.id, "user-001")

        assert result.cart.unique_products == 0
        assert len(result.trims) == 0
        assert len(result.removed_unregistered_products) == 0
        assert len(result.removed_offline_products) == 0
        assert len(result.removed_out_of_stock_products) == 0

    def test_merge_stock_exactly_zero_removes_product(self):
        engine, p1, _, _ = build_engine_with_products()
        anon_cart = engine.create_anonymous_cart()
        anon_cart.add_item(p1, 2)
        engine.update_product_stock(p1, 0)

        result = engine.merge_anonymous_to_user_cart(anon_cart.id, "user-001")

        assert result.cart.get_item(p1) is None
        assert p1 not in result.removed_unregistered_products
        assert p1 not in result.removed_offline_products
        assert p1 in result.removed_out_of_stock_products


class TestCartMergeOfflineProducts:
    def test_merge_removes_offline_products(self):
        engine, p1, p2, _ = build_engine_with_products()
        anon_cart = engine.create_anonymous_cart()
        anon_cart.add_item(p1, 2)
        anon_cart.add_item(p2, 3)
        engine.set_product_online(p1, False)

        result = engine.merge_anonymous_to_user_cart(anon_cart.id, "user-001")

        assert result.cart.get_item(p1) is None
        assert result.cart.get_item(p2).quantity == 3
        assert p1 not in result.removed_unregistered_products
        assert p1 in result.removed_offline_products
        assert p1 not in result.removed_out_of_stock_products

    def test_merge_with_unregistered_product_removes_it(self):
        engine, p1, _, _ = build_engine_with_products()
        anon_cart = engine.create_anonymous_cart()
        anon_cart.add_item(p1, 2)
        anon_cart.items["sku-999"] = type("Item", (), {"product_id": "sku-999", "quantity": 1})()
        anon_cart.items["sku-999"].product_id = "sku-999"
        anon_cart.items["sku-999"].quantity = 1

        result = engine.merge_anonymous_to_user_cart(anon_cart.id, "user-001")

        assert result.cart.get_item(p1).quantity == 2
        assert "sku-999" in result.removed_unregistered_products
        assert "sku-999" not in result.removed_offline_products
        assert "sku-999" not in result.removed_out_of_stock_products

    def test_merge_mixed_offline_online_products(self):
        engine, p1, p2, p3 = build_engine_with_products()
        anon_cart = engine.create_anonymous_cart()
        anon_cart.add_item(p1, 2)
        anon_cart.add_item(p2, 3)
        anon_cart.add_item(p3, 1)
        engine.set_product_online(p2, False)

        result = engine.merge_anonymous_to_user_cart(anon_cart.id, "user-001")

        assert result.cart.get_item(p1).quantity == 2
        assert result.cart.get_item(p2) is None
        assert result.cart.get_item(p3).quantity == 1
        assert len(result.removed_unregistered_products) == 0
        assert p2 in result.removed_offline_products
        assert len(result.removed_offline_products) == 1
        assert len(result.removed_out_of_stock_products) == 0

    def test_merge_distinguishes_all_three_removal_reasons(self):
        engine, p1, p2, p3 = build_engine_with_products()
        anon_cart = engine.create_anonymous_cart()
        anon_cart.add_item(p1, 2)
        anon_cart.add_item(p2, 3)
        anon_cart.add_item(p3, 1)
        anon_cart.items["sku-unreg"] = type("Item", (), {"product_id": "sku-unreg", "quantity": 1})()
        anon_cart.items["sku-unreg"].product_id = "sku-unreg"
        anon_cart.items["sku-unreg"].quantity = 1
        engine.set_product_online(p1, False)
        engine.update_product_stock(p3, 0)

        result = engine.merge_anonymous_to_user_cart(anon_cart.id, "user-001")

        assert "sku-unreg" in result.removed_unregistered_products
        assert len(result.removed_unregistered_products) == 1
        assert p1 in result.removed_offline_products
        assert len(result.removed_offline_products) == 1
        assert p3 in result.removed_out_of_stock_products
        assert len(result.removed_out_of_stock_products) == 1
        assert result.cart.get_item(p2).quantity == 3
        assert result.cart.get_item(p1) is None
        assert result.cart.get_item(p3) is None


class TestCartDataModelValidation:
    def test_product_negative_stock_raises(self):
        with pytest.raises(InvalidQuantityError):
            Product(id="p1", name="Test", price=Decimal("10.00"), stock=-1)

    def test_product_negative_price_raises(self):
        with pytest.raises(InvalidQuantityError):
            Product(id="p1", name="Test", price=Decimal("-1.00"), stock=10)

    def test_cart_item_zero_quantity_raises(self):
        from solocoder_py.cart import CartItem
        with pytest.raises(InvalidQuantityError):
            CartItem(product_id="p1", quantity=0)

    def test_cart_item_negative_quantity_raises(self):
        from solocoder_py.cart import CartItem
        with pytest.raises(InvalidQuantityError):
            CartItem(product_id="p1", quantity=-1)

    def test_cart_add_item_invalid_quantity_raises(self):
        from solocoder_py.cart import Cart
        cart = Cart(id="cart-1", user_id=None)
        with pytest.raises(InvalidQuantityError):
            cart.add_item("p1", 0)

    def test_cart_update_quantity_invalid_raises(self):
        from solocoder_py.cart import Cart
        cart = Cart(id="cart-1", user_id=None)
        cart.add_item("p1", 2)
        with pytest.raises(InvalidQuantityError):
            cart.update_quantity("p1", 0)

    def test_cart_update_quantity_nonexistent_raises(self):
        from solocoder_py.cart import Cart
        cart = Cart(id="cart-1", user_id=None)
        with pytest.raises(CartItemNotFoundError):
            cart.update_quantity("p-not-exist", 5)

    def test_cart_properties(self):
        from solocoder_py.cart import Cart
        cart = Cart(id="cart-1", user_id=None)
        cart.add_item("p1", 2)
        cart.add_item("p2", 3)
        assert cart.total_items == 5
        assert cart.unique_products == 2
        assert cart.is_anonymous is True

        user_cart = Cart(id="cart-2", user_id="user-1")
        assert user_cart.is_anonymous is False


class TestMergeTimestampUpdate:
    def test_merge_updates_user_cart_timestamp(self):
        import time
        engine, p1, _, _ = build_engine_with_products()
        anon_cart = engine.create_anonymous_cart()
        engine.add_to_anonymous_cart(anon_cart.id, p1, 2)

        engine.create_user_cart("user-001")
        user_cart = engine.get_user_cart("user-001")
        original_updated_at = user_cart.updated_at
        time.sleep(0.01)

        result = engine.merge_anonymous_to_user_cart(anon_cart.id, "user-001")

        assert result.cart.updated_at > original_updated_at

    def test_merge_empty_anonymous_cart_updates_timestamp(self):
        import time
        engine = CartEngine()
        anon_cart = engine.create_anonymous_cart()

        engine.create_user_cart("user-001")
        user_cart = engine.get_user_cart("user-001")
        original_updated_at = user_cart.updated_at
        time.sleep(0.01)

        result = engine.merge_anonymous_to_user_cart(anon_cart.id, "user-001")

        assert result.cart.updated_at > original_updated_at

    def test_merge_with_existing_items_updates_timestamp(self):
        import time
        engine, p1, p2, _ = build_engine_with_products()
        anon_cart = engine.create_anonymous_cart()
        engine.add_to_anonymous_cart(anon_cart.id, p1, 2)

        engine.create_user_cart("user-001")
        engine.add_to_user_cart("user-001", p2, 3)
        user_cart = engine.get_user_cart("user-001")
        original_updated_at = user_cart.updated_at
        time.sleep(0.01)

        result = engine.merge_anonymous_to_user_cart(anon_cart.id, "user-001")

        assert result.cart.updated_at > original_updated_at


class TestUpdateQuantityNotFound:
    def test_update_user_cart_quantity_nonexistent_raises(self):
        engine, p1, _, _ = build_engine_with_products()
        engine.create_user_cart("user-001")
        with pytest.raises(CartItemNotFoundError):
            engine.update_user_cart_quantity("user-001", p1, 5)

    def test_update_user_cart_quantity_after_remove_raises(self):
        engine, p1, _, _ = build_engine_with_products()
        engine.create_user_cart("user-001")
        engine.add_to_user_cart("user-001", p1, 2)
        engine.remove_from_user_cart("user-001", p1)
        with pytest.raises(CartItemNotFoundError):
            engine.update_user_cart_quantity("user-001", p1, 3)


class TestCartItemNotFoundErrorExists:
    def test_cart_item_not_found_error_inherits_from_cart_error(self):
        assert issubclass(CartItemNotFoundError, CartError)

    def test_cart_item_not_found_error_message(self):
        from solocoder_py.cart import Cart
        cart = Cart(id="cart-1", user_id=None)
        with pytest.raises(CartItemNotFoundError, match="not found in cart"):
            cart.update_quantity("missing-product", 1)
