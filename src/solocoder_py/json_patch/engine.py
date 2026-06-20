from __future__ import annotations

import copy
from typing import Any

from .exceptions import (
    JsonPatchError,
    PatchOperationError,
    PatchTestFailedError,
    PathNotFoundError,
    UnknownOperationError,
)
from . import pointer as ptr


def _values_equal(a: Any, b: Any) -> bool:
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        if set(a.keys()) != set(b.keys()):
            return False
        return all(_values_equal(a[k], b[k]) for k in a)
    if isinstance(a, list):
        if len(a) != len(b):
            return False
        return all(_values_equal(x, y) for x, y in zip(a, b))
    return a == b


def apply(doc: Any, operations: list[dict[str, Any]]) -> Any:
    current = copy.deepcopy(doc)
    for op in operations:
        current = _apply_one(current, op)
    return current


def apply_atomic(doc: Any, operations: list[dict[str, Any]]) -> Any:
    original = copy.deepcopy(doc)
    current = copy.deepcopy(doc)
    try:
        for op in operations:
            current = _apply_one(current, op)
    except JsonPatchError:
        return original
    return current


def _apply_one(doc: Any, op: dict[str, Any]) -> Any:
    op_type = op.get("op")
    if op_type not in ("add", "remove", "replace", "copy", "move", "test"):
        raise UnknownOperationError(f"Unknown operation: {op_type!r}")

    path = op.get("path")
    if path is None:
        raise PatchOperationError(f"Missing 'path' in operation: {op}")

    if op_type == "add":
        value = op.get("value")
        return _op_add(doc, path, value)
    elif op_type == "remove":
        return _op_remove(doc, path)
    elif op_type == "replace":
        value = op.get("value")
        return _op_replace(doc, path, value)
    elif op_type == "copy":
        from_path = op.get("from")
        if from_path is None:
            raise PatchOperationError(f"Missing 'from' in copy operation: {op}")
        return _op_copy(doc, from_path, path)
    elif op_type == "move":
        from_path = op.get("from")
        if from_path is None:
            raise PatchOperationError(f"Missing 'from' in move operation: {op}")
        return _op_move(doc, from_path, path)
    elif op_type == "test":
        value = op.get("value")
        return _op_test(doc, path, value)


def _op_add(doc: Any, path: str, value: Any) -> Any:
    return ptr.add_value(doc, path, value)


def _op_remove(doc: Any, path: str) -> Any:
    return ptr.delete(doc, path)


def _op_replace(doc: Any, path: str, value: Any) -> Any:
    try:
        ptr.get(doc, path)
    except PathNotFoundError:
        raise PathNotFoundError(
            f"Cannot replace non-existent path {path!r}"
        )
    doc = ptr.delete(doc, path)
    return ptr.add_value(doc, path, value)


def _op_copy(doc: Any, from_path: str, path: str) -> Any:
    value = ptr.get(doc, from_path)
    return ptr.add_value(doc, path, value)


def _op_move(doc: Any, from_path: str, path: str) -> Any:
    value = ptr.get(doc, from_path)
    value_copy = copy.deepcopy(value)
    doc = ptr.delete(doc, from_path)
    return ptr.add_value(doc, path, value_copy)


def _op_test(doc: Any, path: str, value: Any) -> Any:
    try:
        actual = ptr.get(doc, path)
    except PathNotFoundError:
        raise PatchTestFailedError(
            f"Test failed: path {path!r} does not exist"
        )
    if not _values_equal(actual, value):
        raise PatchTestFailedError(
            f"Test failed at {path!r}: expected {value!r}, got {actual!r}"
        )
    return doc
