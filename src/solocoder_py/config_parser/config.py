from __future__ import annotations

from typing import Any, List, Optional

from .exceptions import KeyNotFoundError, TypeConversionError
from .models import TomlTable


class Config:
    def __init__(self, root: Optional[TomlTable] = None) -> None:
        self.root = root if root is not None else TomlTable()

    def get(self, key: str, default: Any = None) -> Any:
        if key in self.root:
            return self.root[key]
        return default

    def get_bool(self, key: str) -> bool:
        value = self._get_value(key)
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            if value == 1:
                return True
            if value == 0:
                return False
        if isinstance(value, str):
            lower = value.strip().lower()
            if lower in ("true", "yes", "on", "1"):
                return True
            if lower in ("false", "no", "off", "0"):
                return False
        raise TypeConversionError(key, "bool", value)

    def get_int(self, key: str) -> int:
        value = self._get_value(key)
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            if value.is_integer():
                return int(value)
        if isinstance(value, str):
            try:
                return int(value.strip())
            except ValueError:
                pass
        raise TypeConversionError(key, "int", value)

    def get_float(self, key: str) -> float:
        value = self._get_value(key)
        if isinstance(value, bool):
            return float(value)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value.strip())
            except ValueError:
                pass
        raise TypeConversionError(key, "float", value)

    def get_str(self, key: str) -> str:
        value = self._get_value(key)
        if isinstance(value, str):
            return value
        return str(value)

    def get_array(self, key: str, element_type: Optional[str] = None) -> List[Any]:
        value = self._get_value(key)
        if not isinstance(value, list):
            raise TypeConversionError(key, "array", value)

        if element_type is not None:
            converters = {
                "bool": self._convert_bool_element,
                "int": self._convert_int_element,
                "float": self._convert_float_element,
                "str": self._convert_str_element,
            }
            if element_type not in converters:
                raise TypeConversionError(key, f"array[{element_type}]", value)
            converter = converters[element_type]
            try:
                return [converter(idx, element) for idx, element in enumerate(value)]
            except TypeConversionError:
                raise
            except Exception as e:
                raise TypeConversionError(key, f"array[{element_type}]", value) from e

        return value

    def get_table(self, key: str) -> "Config":
        value = self._get_value(key)
        if isinstance(value, TomlTable):
            return Config(value)
        raise TypeConversionError(key, "table", value)

    def get_array_table(self, key: str) -> List["Config"]:
        if key not in self.root:
            raise KeyNotFoundError(key)
        if not self.root.is_array_table(key):
            raise TypeConversionError(key, "array_table", self.root[key])
        return [Config(t) for t in self.root.get_array_table(key)]

    def get_comment(self, key: str) -> Optional[str]:
        return self.root.get_comment(key)

    def to_dict(self) -> dict:
        return self.root.to_dict()

    def _get_value(self, key: str) -> Any:
        if key not in self.root:
            raise KeyNotFoundError(key)
        return self.root[key]

    @staticmethod
    def _convert_bool_element(idx: int, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            if value == 1:
                return True
            if value == 0:
                return False
        if isinstance(value, str):
            lower = value.strip().lower()
            if lower in ("true", "yes", "on", "1"):
                return True
            if lower in ("false", "no", "off", "0"):
                return False
        raise TypeConversionError(f"element[{idx}]", "bool", value)

    @staticmethod
    def _convert_int_element(idx: int, value: Any) -> int:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            if value.is_integer():
                return int(value)
        if isinstance(value, str):
            try:
                return int(value.strip())
            except ValueError:
                pass
        raise TypeConversionError(f"element[{idx}]", "int", value)

    @staticmethod
    def _convert_float_element(idx: int, value: Any) -> float:
        if isinstance(value, bool):
            return float(value)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value.strip())
            except ValueError:
                pass
        raise TypeConversionError(f"element[{idx}]", "float", value)

    @staticmethod
    def _convert_str_element(idx: int, value: Any) -> str:
        if isinstance(value, str):
            return value
        return str(value)

    def __contains__(self, key: str) -> bool:
        return key in self.root

    def __getitem__(self, key: str) -> Any:
        return self.root[key]
