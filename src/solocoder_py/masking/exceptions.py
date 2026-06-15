from __future__ import annotations


class MaskingError(Exception):
    pass


class InvalidConfigurationError(MaskingError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidFieldError(MaskingError):
    def __init__(self, field: str, message: str) -> None:
        super().__init__(f"Field '{field}': {message}")
        self.field = field
        self.message = message


class InvalidValueError(MaskingError):
    def __init__(self, value: str, message: str) -> None:
        super().__init__(f"Invalid value '{value}': {message}")
        self.value = value
        self.message = message


class TokenizationError(MaskingError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class GeneralizationError(MaskingError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class KAnonymityError(MaskingError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class DataSourceError(MaskingError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


__all__ = [
    "MaskingError",
    "InvalidConfigurationError",
    "InvalidFieldError",
    "InvalidValueError",
    "TokenizationError",
    "GeneralizationError",
    "KAnonymityError",
    "DataSourceError",
]
