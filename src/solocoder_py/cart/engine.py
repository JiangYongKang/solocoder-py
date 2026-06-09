from __future__ import annotations

import threading
import uuid
from typing import Dict, List, Optional

from .exceptions import (
    CartError,
    CartItemNotFoundError,
    CartNotFoundError,
    InsufficientStockError,
    InvalidQuantityError,
    ProductNotFoundError,
    ProductOfflineError,
)
from .models import Cart, MergeResult, Product, TrimNotification


class CartEngine:
    def __init__(self) -> None:
        self._products: Dict[str, Product] = {}
        self._anonymous_carts: Dict[str, Cart] = {}
        self._user_carts: Dict[str, Cart] = {}
        self._lock = threading.RLock()

    def register_product(self, product: Product) -> Product:
        with self._lock:
            if product.id in self._products:
                raise CartError(f"Product already exists: {product.id}")
            self._products[product.id] = product
            return product

    def get_product(self, product_id: str) -> Product:
        product = self._products.get(product_id)
        if product is None:
            raise ProductNotFoundError(f"Product not found: {product_id}")
        return product

    def update_product_stock(self, product_id: str, stock: int) -> Product:
        if stock < 0:
            raise InvalidQuantityError("Stock cannot be negative")
        with self._lock:
            product = self.get_product(product_id)
            product.stock = stock
            return product

    def set_product_online(self, product_id: str, online: bool) -> Product:
        with self._lock:
            product = self.get_product(product_id)
            product.is_online = online
            return product

    def create_anonymous_cart(self) -> Cart:
        with self._lock:
            cart_id = str(uuid.uuid4())
            cart = Cart(id=cart_id, user_id=None)
            self._anonymous_carts[cart_id] = cart
            return cart

    def create_user_cart(self, user_id: str) -> Cart:
        with self._lock:
            if user_id in self._user_carts:
                raise CartError(f"User cart already exists for user: {user_id}")
            cart_id = str(uuid.uuid4())
            cart = Cart(id=cart_id, user_id=user_id)
            self._user_carts[user_id] = cart
            return cart

    def get_anonymous_cart(self, cart_id: str) -> Cart:
        cart = self._anonymous_carts.get(cart_id)
        if cart is None:
            raise CartNotFoundError(f"Anonymous cart not found: {cart_id}")
        return cart

    def get_user_cart(self, user_id: str) -> Cart:
        cart = self._user_carts.get(user_id)
        if cart is None:
            raise CartNotFoundError(f"User cart not found for user: {user_id}")
        return cart

    def get_or_create_user_cart(self, user_id: str) -> Cart:
        with self._lock:
            try:
                return self.get_user_cart(user_id)
            except CartNotFoundError:
                return self.create_user_cart(user_id)

    def _validate_product_available(self, product_id: str) -> Product:
        product = self.get_product(product_id)
        if not product.is_online:
            raise ProductOfflineError(f"Product is offline: {product_id}")
        if product.stock == 0:
            raise InsufficientStockError(
                f"Product {product_id} is out of stock"
            )
        return product

    def _validate_and_clip_quantity(
        self, product_id: str, quantity: int
    ) -> tuple[int, Optional[TrimNotification], Product]:
        product = self._validate_product_available(product_id)
        if quantity > product.stock:
            trimmed = quantity - product.stock
            notification = TrimNotification(
                product_id=product_id,
                product_name=product.name,
                requested_quantity=quantity,
                actual_quantity=product.stock,
                trimmed_quantity=trimmed,
                reason="Exceeds available stock",
            )
            return product.stock, notification, product
        return quantity, None, product

    def add_to_anonymous_cart(
        self, cart_id: str, product_id: str, quantity: int
    ) -> Cart:
        if quantity <= 0:
            raise InvalidQuantityError("Quantity must be positive")
        with self._lock:
            cart = self.get_anonymous_cart(cart_id)
            product = self._validate_product_available(product_id)
            existing_item = cart.get_item(product_id)
            if existing_item is not None:
                combined = existing_item.quantity + quantity
                final_quantity = min(combined, product.stock)
                cart.update_quantity(product_id, final_quantity)
            else:
                final_quantity = min(quantity, product.stock)
                cart.add_item(product_id, final_quantity)
            return cart

    def add_to_user_cart(
        self, user_id: str, product_id: str, quantity: int
    ) -> Cart:
        if quantity <= 0:
            raise InvalidQuantityError("Quantity must be positive")
        with self._lock:
            cart = self.get_or_create_user_cart(user_id)
            product = self._validate_product_available(product_id)
            existing_item = cart.get_item(product_id)
            if existing_item is not None:
                combined = existing_item.quantity + quantity
                final_quantity = min(combined, product.stock)
                cart.update_quantity(product_id, final_quantity)
            else:
                final_quantity = min(quantity, product.stock)
                cart.add_item(product_id, final_quantity)
            return cart

    def remove_from_anonymous_cart(self, cart_id: str, product_id: str) -> Cart:
        with self._lock:
            cart = self.get_anonymous_cart(cart_id)
            cart.remove_item(product_id)
            return cart

    def remove_from_user_cart(self, user_id: str, product_id: str) -> Cart:
        with self._lock:
            cart = self.get_user_cart(user_id)
            cart.remove_item(product_id)
            return cart

    def update_anonymous_cart_quantity(
        self, cart_id: str, product_id: str, quantity: int
    ) -> Cart:
        if quantity <= 0:
            raise InvalidQuantityError("Quantity must be positive")
        with self._lock:
            cart = self.get_anonymous_cart(cart_id)
            clipped_quantity, _, _ = self._validate_and_clip_quantity(product_id, quantity)
            cart.update_quantity(product_id, clipped_quantity)
            return cart

    def update_user_cart_quantity(
        self, user_id: str, product_id: str, quantity: int
    ) -> Cart:
        if quantity <= 0:
            raise InvalidQuantityError("Quantity must be positive")
        with self._lock:
            cart = self.get_user_cart(user_id)
            clipped_quantity, _, _ = self._validate_and_clip_quantity(product_id, quantity)
            cart.update_quantity(product_id, clipped_quantity)
            return cart

    def clear_anonymous_cart(self, cart_id: str) -> Cart:
        with self._lock:
            cart = self.get_anonymous_cart(cart_id)
            cart.clear()
            return cart

    def clear_user_cart(self, user_id: str) -> Cart:
        with self._lock:
            cart = self.get_user_cart(user_id)
            cart.clear()
            return cart

    def merge_anonymous_to_user_cart(
        self, anonymous_cart_id: str, user_id: str
    ) -> MergeResult:
        with self._lock:
            anonymous_cart = self.get_anonymous_cart(anonymous_cart_id)
            user_cart = self.get_or_create_user_cart(user_id)

            trims: List[TrimNotification] = []
            removed_unregistered: List[str] = []
            removed_offline: List[str] = []
            removed_out_of_stock: List[str] = []

            for product_id, anon_item in list(anonymous_cart.items.items()):
                product = self._products.get(product_id)
                if product is None:
                    removed_unregistered.append(product_id)
                    continue
                if not product.is_online:
                    removed_offline.append(product_id)
                    continue
                if product.stock == 0:
                    removed_out_of_stock.append(product_id)
                    continue

                existing_item = user_cart.get_item(product_id)
                if existing_item is not None:
                    combined_quantity = existing_item.quantity + anon_item.quantity
                else:
                    combined_quantity = anon_item.quantity

                if combined_quantity > product.stock:
                    trimmed = combined_quantity - product.stock
                    trims.append(
                        TrimNotification(
                            product_id=product_id,
                            product_name=product.name,
                            requested_quantity=combined_quantity,
                            actual_quantity=product.stock,
                            trimmed_quantity=trimmed,
                            reason="Exceeds available stock after merge",
                        )
                    )
                    final_quantity = product.stock
                else:
                    final_quantity = combined_quantity

                if existing_item is not None:
                    user_cart.update_quantity(product_id, final_quantity)
                else:
                    user_cart.add_item(product_id, final_quantity)

            user_cart.touch()

            anonymous_cart.clear()
            del self._anonymous_carts[anonymous_cart_id]

            return MergeResult(
                cart=user_cart,
                trims=trims,
                removed_unregistered_products=removed_unregistered,
                removed_offline_products=removed_offline,
                removed_out_of_stock_products=removed_out_of_stock,
            )
