from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .percent import percent_decode, percent_encode


@dataclass
class QueryParam:
    key: str
    value: Optional[str] = None


class QueryParams:
    def __init__(self, params: Optional[list[QueryParam]] = None) -> None:
        self._params: list[QueryParam] = list(params) if params else []

    @classmethod
    def from_string(cls, query_string: Optional[str]) -> "QueryParams":
        if query_string is None or query_string == "":
            return cls()
        params: list[QueryParam] = []
        for part in query_string.split("&"):
            if not part:
                continue
            if "=" in part:
                key, value = part.split("=", 1)
                params.append(QueryParam(key=percent_decode(key), value=percent_decode(value)))
            else:
                params.append(QueryParam(key=percent_decode(part), value=None))
        return cls(params)

    def add_param(self, key: str, value: Optional[str] = None) -> None:
        self._params.append(QueryParam(key=key, value=value))

    def remove_param(self, key: str) -> int:
        original_len = len(self._params)
        self._params = [p for p in self._params if p.key != key]
        return original_len - len(self._params)

    def set_param(self, key: str, value: Optional[str] = None) -> None:
        self._params = [p for p in self._params if p.key != key]
        self._params.append(QueryParam(key=key, value=value))

    def get_param(self, key: str) -> Optional[str]:
        for p in reversed(self._params):
            if p.key == key:
                return p.value
        return None

    def get_param_all(self, key: str) -> list[Optional[str]]:
        return [p.value for p in self._params if p.key == key]

    def has_param(self, key: str) -> bool:
        return any(p.key == key for p in self._params)

    @property
    def params(self) -> list[QueryParam]:
        return list(self._params)

    def to_string(self) -> Optional[str]:
        if not self._params:
            return None
        parts: list[str] = []
        for p in self._params:
            encoded_key = percent_encode(p.key, safe="-._~")
            if p.value is not None:
                encoded_value = percent_encode(p.value, safe="-._~")
                parts.append(f"{encoded_key}={encoded_value}")
            else:
                parts.append(encoded_key)
        return "&".join(parts)

    def __len__(self) -> int:
        return len(self._params)

    def __repr__(self) -> str:
        return f"QueryParams({self._params!r})"
