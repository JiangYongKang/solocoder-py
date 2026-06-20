from __future__ import annotations

import copy
from typing import Any

from .exceptions import AddOutOfBoundsError, InvalidPointerError, PathNotFoundError


def parse(pointer: str) -> list[str]:
    if pointer == "":
        return []
    if not pointer.startswith("/"):
        raise InvalidPointerError(
            f"JSON Pointer must be empty or start with '/': {pointer!r}"
        )
    tokens = pointer[1:].split("/")
    return [_unescape(t) for t in tokens]


def _unescape(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def _escape(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def get(doc: Any, pointer: str) -> Any:
    tokens = parse(pointer)
    current = doc
    for token in tokens:
        if isinstance(current, dict):
            if token not in current:
                raise PathNotFoundError(
                    f"Key {token!r} not found in object at pointer {pointer!r}"
                )
            current = current[token]
        elif isinstance(current, list):
            if token == "-":
                raise PathNotFoundError(
                    f"Cannot use '-' index for get operation at pointer {pointer!r}"
                )
            try:
                idx = int(token)
            except ValueError:
                raise PathNotFoundError(
                    f"Invalid array index {token!r} at pointer {pointer!r}"
                )
            if idx < 0 or idx >= len(current):
                raise PathNotFoundError(
                    f"Array index {idx} out of range at pointer {pointer!r}"
                )
            current = current[idx]
        else:
            raise PathNotFoundError(
                f"Cannot traverse into non-container value at pointer {pointer!r}"
            )
    return current


def set_value(doc: Any, pointer: str, value: Any) -> Any:
    tokens = parse(pointer)
    if not tokens:
        return copy.deepcopy(value)
    return _set_in(doc, tokens, 0, value)


def _set_in(current: Any, tokens: list[str], depth: int, value: Any) -> Any:
    token = tokens[depth]
    is_last = depth == len(tokens) - 1

    if is_last:
        if isinstance(current, dict):
            result = dict(current)
            result[token] = copy.deepcopy(value)
            return result
        elif isinstance(current, list):
            if token == "-":
                raise PathNotFoundError(
                    f"Cannot use '-' for set operation on arrays"
                )
            try:
                idx = int(token)
            except ValueError:
                raise PathNotFoundError(
                    f"Invalid array index {token!r}"
                )
            if idx < 0 or idx >= len(current):
                raise PathNotFoundError(
                    f"Array index {idx} out of range"
                )
            result = list(current)
            result[idx] = copy.deepcopy(value)
            return result
        else:
            raise PathNotFoundError(
                f"Cannot set value in non-container"
            )

    if isinstance(current, dict):
        if token not in current:
            raise PathNotFoundError(
                f"Key {token!r} not found in object"
            )
        result = dict(current)
        result[token] = _set_in(current[token], tokens, depth + 1, value)
        return result
    elif isinstance(current, list):
        if token == "-":
            raise PathNotFoundError(
                f"Cannot traverse '-' for intermediate path segment"
            )
        try:
            idx = int(token)
        except ValueError:
            raise PathNotFoundError(
                f"Invalid array index {token!r}"
            )
        if idx < 0 or idx >= len(current):
            raise PathNotFoundError(
                f"Array index {idx} out of range"
            )
        result = list(current)
        result[idx] = _set_in(current[idx], tokens, depth + 1, value)
        return result
    else:
        raise PathNotFoundError(
            f"Cannot traverse into non-container value"
        )


def add_value(doc: Any, pointer: str, value: Any) -> Any:
    tokens = parse(pointer)
    if not tokens:
        return copy.deepcopy(value)
    return _add_in(doc, tokens, 0, value)


def _add_in(current: Any, tokens: list[str], depth: int, value: Any) -> Any:
    token = tokens[depth]
    is_last = depth == len(tokens) - 1

    if is_last:
        if isinstance(current, dict):
            result = dict(current)
            result[token] = copy.deepcopy(value)
            return result
        elif isinstance(current, list):
            result = list(current)
            if token == "-":
                result.append(copy.deepcopy(value))
                return result
            try:
                idx = int(token)
            except ValueError:
                raise PathNotFoundError(
                    f"Invalid array index {token!r}"
                )
            if idx < 0 or idx > len(result):
                raise AddOutOfBoundsError(
                    f"Array index {idx} out of range for add (valid: 0-{len(result)})"
                )
            result.insert(idx, copy.deepcopy(value))
            return result
        else:
            raise PathNotFoundError(
                f"Cannot add value to non-container"
            )

    if isinstance(current, dict):
        if token not in current:
            raise PathNotFoundError(
                f"Key {token!r} not found in object"
            )
        result = dict(current)
        result[token] = _add_in(current[token], tokens, depth + 1, value)
        return result
    elif isinstance(current, list):
        if token == "-":
            raise PathNotFoundError(
                f"Cannot traverse '-' for intermediate path segment"
            )
        try:
            idx = int(token)
        except ValueError:
            raise PathNotFoundError(
                f"Invalid array index {token!r}"
            )
        if idx < 0 or idx >= len(current):
            raise PathNotFoundError(
                f"Array index {idx} out of range"
            )
        result = list(current)
        result[idx] = _add_in(current[idx], tokens, depth + 1, value)
        return result
    else:
        raise PathNotFoundError(
            f"Cannot traverse into non-container value"
        )


def delete(doc: Any, pointer: str) -> Any:
    tokens = parse(pointer)
    if not tokens:
        raise PathNotFoundError("Cannot delete root document")
    return _delete_in(doc, tokens, 0)


def _delete_in(current: Any, tokens: list[str], depth: int) -> Any:
    token = tokens[depth]
    is_last = depth == len(tokens) - 1

    if is_last:
        if isinstance(current, dict):
            if token not in current:
                raise PathNotFoundError(
                    f"Key {token!r} not found in object"
                )
            result = dict(current)
            del result[token]
            return result
        elif isinstance(current, list):
            try:
                idx = int(token)
            except ValueError:
                raise PathNotFoundError(
                    f"Invalid array index {token!r}"
                )
            if idx < 0 or idx >= len(current):
                raise PathNotFoundError(
                    f"Array index {idx} out of range"
                )
            result = list(current)
            del result[idx]
            return result
        else:
            raise PathNotFoundError(
                f"Cannot delete from non-container"
            )

    if isinstance(current, dict):
        if token not in current:
            raise PathNotFoundError(
                f"Key {token!r} not found in object"
            )
        result = dict(current)
        result[token] = _delete_in(current[token], tokens, depth + 1)
        return result
    elif isinstance(current, list):
        if token == "-":
            raise PathNotFoundError(
                f"Cannot traverse '-' for intermediate path segment"
            )
        try:
            idx = int(token)
        except ValueError:
            raise PathNotFoundError(
                f"Invalid array index {token!r}"
            )
        if idx < 0 or idx >= len(current):
            raise PathNotFoundError(
                f"Array index {idx} out of range"
            )
        result = list(current)
        result[idx] = _delete_in(current[idx], tokens, depth + 1)
        return result
    else:
        raise PathNotFoundError(
            f"Cannot traverse into non-container value"
        )
