from __future__ import annotations


class CartError(Exception):
    pass


class ProductNotFoundError(CartError):
    pass


class ProductOfflineError(CartError):
    pass


class InsufficientStockError(CartError):
    pass


class InvalidQuantityError(CartError):
    pass


class CartNotFoundError(CartError):
    pass
