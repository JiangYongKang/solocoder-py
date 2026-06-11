from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Type

from .exceptions import SchemaCompatibilityError


class FieldType(str, Enum):
    BOOL = "bool"
    INT32 = "int32"
    INT64 = "int64"
    UINT32 = "uint32"
    UINT64 = "uint64"
    STRING = "string"
    BYTES = "bytes"


TYPE_DEFAULTS: Dict[FieldType, Any] = {
    FieldType.BOOL: False,
    FieldType.INT32: 0,
    FieldType.INT64: 0,
    FieldType.UINT32: 0,
    FieldType.UINT64: 0,
    FieldType.STRING: "",
    FieldType.BYTES: b"",
}

SIGNED_INT_TYPES = {FieldType.INT32, FieldType.INT64}
UNSIGNED_INT_TYPES = {FieldType.UINT32, FieldType.UINT64}


@dataclass
class FieldDef:
    field_id: int
    field_type: FieldType
    name: str
    default: Any = None

    def __post_init__(self) -> None:
        if self.field_id <= 0:
            raise ValueError(f"field_id must be positive, got {self.field_id}")
        if self.default is None:
            self.default = TYPE_DEFAULTS[self.field_type]


@dataclass
class Schema:
    name: str
    version: int
    fields: List[FieldDef] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError(f"schema version must be >= 1, got {self.version}")
        seen_ids = set()
        for f in self.fields:
            if f.field_id in seen_ids:
                raise ValueError(f"duplicate field_id: {f.field_id}")
            seen_ids.add(f.field_id)

    def field_by_id(self, field_id: int) -> Optional[FieldDef]:
        for f in self.fields:
            if f.field_id == field_id:
                return f
        return None

    def field_by_name(self, name: str) -> Optional[FieldDef]:
        for f in self.fields:
            if f.name == name:
                return f
        return None

    def max_field_id(self) -> int:
        if not self.fields:
            return 0
        return max(f.field_id for f in self.fields)

    def sorted_fields(self) -> List[FieldDef]:
        return sorted(self.fields, key=lambda f: f.field_id)


def check_compatibility(old_schema: Schema, new_schema: Schema) -> None:
    if new_schema.name != old_schema.name:
        raise SchemaCompatibilityError(
            f"schema name mismatch: old='{old_schema.name}', new='{new_schema.name}'"
        )
    if new_schema.version < old_schema.version:
        raise SchemaCompatibilityError(
            f"new schema version {new_schema.version} is older than old version {old_schema.version}"
        )

    old_fields_by_id = {f.field_id: f for f in old_schema.fields}
    new_fields_by_id = {f.field_id: f for f in new_schema.fields}

    for fid, old_field in old_fields_by_id.items():
        if fid not in new_fields_by_id:
            raise SchemaCompatibilityError(
                f"field '{old_field.name}' (id={fid}) present in old schema v{old_schema.version} "
                f"but missing in new schema v{new_schema.version}; fields cannot be deleted"
            )
        new_field = new_fields_by_id[fid]
        if new_field.field_type != old_field.field_type:
            raise SchemaCompatibilityError(
                f"field id={fid} type changed from {old_field.field_type} to {new_field.field_type}; "
                f"field types cannot be modified"
            )

    new_ids = set(new_fields_by_id.keys()) - set(old_fields_by_id.keys())
    old_max_id = old_schema.max_field_id()
    for new_id in new_ids:
        if new_id <= old_max_id:
            raise SchemaCompatibilityError(
                f"new field id={new_id} must be greater than old max field id={old_max_id}; "
                f"new fields can only be appended"
            )
