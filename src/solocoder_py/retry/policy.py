from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, Optional, Set, Type


class RetryPolicy(ABC):
    @abstractmethod
    def is_retryable(self, exception: Exception) -> bool:
        ...


class RetryAllPolicy(RetryPolicy):
    def is_retryable(self, exception: Exception) -> bool:
        return True


class RetryNonePolicy(RetryPolicy):
    def is_retryable(self, exception: Exception) -> bool:
        return False


class ExceptionTypePolicy(RetryPolicy):
    def __init__(
        self,
        retryable_exceptions: Optional[Iterable[Type[Exception]]] = None,
        non_retryable_exceptions: Optional[Iterable[Type[Exception]]] = None,
    ) -> None:
        self._retryable: tuple[Type[Exception], ...] = (
            tuple(retryable_exceptions) if retryable_exceptions else ()
        )
        self._non_retryable: tuple[Type[Exception], ...] = (
            tuple(non_retryable_exceptions) if non_retryable_exceptions else ()
        )

    def is_retryable(self, exception: Exception) -> bool:
        for exc_type in self._non_retryable:
            if isinstance(exception, exc_type):
                return False

        if self._retryable:
            return any(isinstance(exception, t) for t in self._retryable)

        return True

    @property
    def retryable_types(self) -> tuple[Type[Exception], ...]:
        return self._retryable

    @property
    def non_retryable_types(self) -> tuple[Type[Exception], ...]:
        return self._non_retryable


_MISSING = object()


class ErrorCodePolicy(RetryPolicy):
    def __init__(
        self,
        retryable_codes: Optional[Iterable[str]] = None,
        non_retryable_codes: Optional[Iterable[str]] = None,
        code_attribute: str = "code",
    ) -> None:
        self._retryable_codes: Set[str] = (
            set(retryable_codes) if retryable_codes else set()
        )
        self._non_retryable_codes: Set[str] = (
            set(non_retryable_codes) if non_retryable_codes else set()
        )
        self._code_attribute = code_attribute

    def _get_code(self, exception: Exception) -> Optional[str]:
        code = getattr(exception, self._code_attribute, _MISSING)
        if code is _MISSING or code is None:
            return None
        return str(code)

    def is_retryable(self, exception: Exception) -> bool:
        code = self._get_code(exception)

        if code is None:
            if self._retryable_codes:
                return False
            return True

        if code in self._non_retryable_codes:
            return False

        if self._retryable_codes:
            return code in self._retryable_codes

        return True

    @property
    def retryable_codes(self) -> Set[str]:
        return set(self._retryable_codes)

    @property
    def non_retryable_codes(self) -> Set[str]:
        return set(self._non_retryable_codes)


class CompositePolicy(RetryPolicy):
    def __init__(self, policies: Iterable[RetryPolicy]) -> None:
        self._policies: list[RetryPolicy] = list(policies)

    def is_retryable(self, exception: Exception) -> bool:
        if not self._policies:
            return True
        return all(p.is_retryable(exception) for p in self._policies)

    @property
    def policies(self) -> list[RetryPolicy]:
        return list(self._policies)
