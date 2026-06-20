from __future__ import annotations


class ConfigParserError(Exception):
    pass


class ParseError(ConfigParserError):
    def __init__(self, line: int, message: str) -> None:
        self.line = line
        self.message = message
        super().__init__(f"Parse error at line {line}: {message}")


class DuplicateKeyError(ParseError):
    def __init__(self, line: int, key: str) -> None:
        self.key = key
        super().__init__(line, f"Duplicate key '{key}'")


class DuplicateTableError(ParseError):
    def __init__(self, line: int, table_name: str) -> None:
        self.table_name = table_name
        super().__init__(line, f"Duplicate table '{table_name}'")


class InvalidTableNameError(ParseError):
    def __init__(self, line: int, table_name: str) -> None:
        self.table_name = table_name
        super().__init__(line, f"Invalid table name '{table_name}'")


class UnclosedStringError(ParseError):
    def __init__(self, line: int) -> None:
        super().__init__(line, "Unclosed string literal")


class InvalidNumberError(ParseError):
    def __init__(self, line: int, value: str) -> None:
        self.value = value
        super().__init__(line, f"Invalid number '{value}'")


class InvalidDateTimeError(ParseError):
    def __init__(self, line: int, value: str) -> None:
        self.value = value
        super().__init__(line, f"Invalid date/time value '{value}'")


class InvalidValueTypeError(ParseError):
    def __init__(self, line: int, value: str) -> None:
        self.value = value
        super().__init__(line, f"Invalid value '{value}'")


class TypeConversionError(ConfigParserError):
    def __init__(self, key: str, target_type: str, value: object) -> None:
        self.key = key
        self.target_type = target_type
        self.value = value
        super().__init__(
            f"Cannot convert value '{value}' for key '{key}' to type '{target_type}'"
        )


class KeyNotFoundError(ConfigParserError):
    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(f"Key '{key}' not found in configuration")
