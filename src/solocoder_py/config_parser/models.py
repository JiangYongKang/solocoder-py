from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Any, Dict, List, Optional, Union


TomlValue = Union[str, int, float, bool, datetime, date, time, List[Any], "TomlTable"]


@dataclass
class TomlTable:
    _data: Dict[str, Any] = field(default_factory=dict)
    _comments: Dict[str, str] = field(default_factory=dict)
    _is_array_table: bool = False
    _array_tables: Dict[str, List["TomlTable"]] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        if "." in key:
            parts = key.split(".", 1)
            sub = self._data.get(parts[0])
            if isinstance(sub, TomlTable):
                return sub.get(parts[1], default)
            return default
        return self._data.get(key, default)

    def __getitem__(self, key: str) -> Any:
        if "." in key:
            parts = key.split(".", 1)
            sub = self._data[parts[0]]
            if isinstance(sub, TomlTable):
                return sub[parts[1]]
            raise KeyError(key)
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        if "." in key:
            parts = key.split(".", 1)
            if parts[0] not in self._data:
                self._data[parts[0]] = TomlTable()
            sub = self._data[parts[0]]
            if isinstance(sub, TomlTable):
                sub[parts[1]] = value
            else:
                raise KeyError(parts[0])
        else:
            self._data[key] = value

    def __contains__(self, key: str) -> bool:
        if "." in key:
            parts = key.split(".", 1)
            sub = self._data.get(parts[0])
            if isinstance(sub, TomlTable):
                return parts[1] in sub
            return False
        return key in self._data

    def __iter__(self):
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for k, v in self._data.items():
            if isinstance(v, TomlTable):
                result[k] = v.to_dict()
            elif isinstance(v, list):
                result[k] = [
                    i.to_dict() if isinstance(i, TomlTable) else i for i in v
                ]
            else:
                result[k] = v
        return result

    def get_comment(self, key: str) -> Optional[str]:
        if "." in key:
            parts = key.split(".", 1)
            sub = self._data.get(parts[0])
            if isinstance(sub, TomlTable):
                return sub.get_comment(parts[1])
            return None
        return self._comments.get(key)

    def set_comment(self, key: str, comment: str) -> None:
        if "." in key:
            parts = key.split(".", 1)
            if parts[0] not in self._data:
                self._data[parts[0]] = TomlTable()
            sub = self._data[parts[0]]
            if isinstance(sub, TomlTable):
                sub.set_comment(parts[1], comment)
        else:
            self._comments[key] = comment

    def get_array_table(self, key: str) -> List["TomlTable"]:
        return self._array_tables.get(key, [])

    def add_array_table_element(self, key: str, table: "TomlTable") -> None:
        if key not in self._array_tables:
            self._array_tables[key] = []
            self._data[key] = self._array_tables[key]
        self._array_tables[key].append(table)

    def is_array_table(self, key: str) -> bool:
        return key in self._array_tables
