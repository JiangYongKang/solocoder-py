from __future__ import annotations

from typing import Optional


class InterceptorChainError(Exception):
    pass


class InterceptorError(InterceptorChainError):
    def __init__(self, interceptor_name: str, message: str) -> None:
        self.interceptor_name = interceptor_name
        self.message = message
        super().__init__(f"[{interceptor_name}] {message}")


class ShortCircuitError(InterceptorChainError):
    def __init__(self, interceptor_name: str, response: Optional[Response] = None) -> None:
        from .models import Response

        self.interceptor_name = interceptor_name
        self.response = response
        super().__init__(
            f"Interceptor '{interceptor_name}' short-circuited the chain"
        )
