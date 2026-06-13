from __future__ import annotations


class AnomalyError(Exception):
    pass


class AnomalyConfigError(AnomalyError):
    pass


__all__ = [
    "AnomalyError",
    "AnomalyConfigError",
]
