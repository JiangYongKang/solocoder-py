from __future__ import annotations

from .config import Config
from .exceptions import (
    ConfigParserError,
    DuplicateKeyError,
    DuplicateTableError,
    InvalidDateTimeError,
    InvalidNumberError,
    InvalidTableNameError,
    InvalidValueTypeError,
    KeyNotFoundError,
    ParseError,
    TypeConversionError,
    UnclosedStringError,
)
from .models import TomlTable
from .parser import ConfigParser


def parse_toml(text: str) -> Config:
    parser = ConfigParser(strict=True)
    root = parser.parse(text)
    return Config(root)


def parse_ini(text: str) -> Config:
    parser = ConfigParser(strict=False)
    root = parser.parse(text)
    return Config(root)


__all__ = [
    "Config",
    "ConfigParser",
    "TomlTable",
    "ConfigParserError",
    "ParseError",
    "DuplicateKeyError",
    "DuplicateTableError",
    "InvalidTableNameError",
    "UnclosedStringError",
    "InvalidNumberError",
    "InvalidDateTimeError",
    "InvalidValueTypeError",
    "TypeConversionError",
    "KeyNotFoundError",
    "parse_toml",
    "parse_ini",
]
