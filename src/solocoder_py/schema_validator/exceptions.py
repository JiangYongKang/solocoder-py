from __future__ import annotations


class SchemaValidatorError(Exception):
    pass


class SchemaDefinitionError(SchemaValidatorError):
    pass


class ValidationError(SchemaValidatorError):
    def __init__(self, errors: list[ValidationErrorItem]) -> None:
        self.errors = errors
        super().__init__(f"Validation failed with {len(errors)} error(s)")


class ValidationErrorItem:
    def __init__(
        self,
        path: str,
        error_type: str,
        message: str,
        expected: str | None = None,
        actual: str | None = None,
    ) -> None:
        self.path = path
        self.error_type = error_type
        self.message = message
        self.expected = expected
        self.actual = actual

    def __repr__(self) -> str:
        return (
            f"ValidationErrorItem(path={self.path!r}, "
            f"error_type={self.error_type!r}, message={self.message!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ValidationErrorItem):
            return NotImplemented
        return (
            self.path == other.path
            and self.error_type == other.error_type
            and self.message == other.message
        )


__all__ = [
    "SchemaValidatorError",
    "SchemaDefinitionError",
    "ValidationError",
    "ValidationErrorItem",
]
