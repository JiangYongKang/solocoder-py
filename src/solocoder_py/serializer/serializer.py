from __future__ import annotations

from typing import Any, Dict

from .buffer import Buffer
from .exceptions import (
    BufferOverflowError,
    DeserializationError,
    SchemaError,
)
from .models import (
    FieldDef,
    FieldType,
    Schema,
    SIGNED_INT_TYPES,
    UNSIGNED_INT_TYPES,
    check_compatibility,
)
from .varint import decode_uvarint, decode_varint, encode_uvarint, encode_varint

WIRE_TYPE_VARINT = 0
WIRE_TYPE_LEN = 2


def _field_type_to_wire_type(field_type: FieldType) -> int:
    if field_type == FieldType.BOOL or field_type in SIGNED_INT_TYPES or field_type in UNSIGNED_INT_TYPES:
        return WIRE_TYPE_VARINT
    elif field_type == FieldType.STRING or field_type == FieldType.BYTES:
        return WIRE_TYPE_LEN
    else:
        raise SchemaError(f"unsupported field type: {field_type}")


def _encode_tag(field_id: int, wire_type: int) -> bytes:
    tag = (field_id << 3) | wire_type
    return encode_uvarint(tag)


def _decode_tag(buf: Buffer) -> tuple[int, int]:
    tag = decode_uvarint(buf)
    field_id = tag >> 3
    wire_type = tag & 0x07
    if field_id <= 0:
        raise DeserializationError(f"invalid field id in tag: {field_id}")
    return field_id, wire_type


def _encode_string(value: str) -> bytes:
    encoded = value.encode("utf-8")
    length = encode_uvarint(len(encoded))
    return length + encoded


def _decode_string(buf: Buffer) -> str:
    length = decode_uvarint(buf)
    raw = buf.read_bytes(length)
    return raw.decode("utf-8")


def _encode_bytes(value: bytes) -> bytes:
    length = encode_uvarint(len(value))
    return length + value


def _decode_bytes(buf: Buffer) -> bytes:
    length = decode_uvarint(buf)
    return buf.read_bytes(length)


def _encode_bool(value: bool) -> bytes:
    return b"\x01" if value else b"\x00"


def _decode_bool(buf: Buffer) -> bool:
    b = buf.read_byte()
    if b == 0:
        return False
    elif b == 1:
        return True
    else:
        raise DeserializationError(f"invalid boolean byte: {b}")


def _encode_integer(field_type: FieldType, value: int) -> bytes:
    if field_type in SIGNED_INT_TYPES:
        bits = 32 if field_type == FieldType.INT32 else 64
        return encode_varint(value, bits)
    elif field_type in UNSIGNED_INT_TYPES:
        return encode_uvarint(value)
    else:
        raise SchemaError(f"not an integer field type: {field_type}")


def _decode_integer(field_type: FieldType, buf: Buffer) -> int:
    if field_type in SIGNED_INT_TYPES:
        bits = 32 if field_type == FieldType.INT32 else 64
        return decode_varint(buf, bits)
    elif field_type in UNSIGNED_INT_TYPES:
        return decode_uvarint(buf)
    else:
        raise SchemaError(f"not an integer field type: {field_type}")


def _skip_by_wire_type(buf: Buffer, wire_type: int) -> None:
    if wire_type == WIRE_TYPE_VARINT:
        while True:
            b = buf.read_byte()
            if (b & 0x80) == 0:
                break
    elif wire_type == WIRE_TYPE_LEN:
        length = decode_uvarint(buf)
        buf.skip(length)
    else:
        raise DeserializationError(f"unknown wire type: {wire_type}")


class BinarySerializer:
    def __init__(self, schema: Schema) -> None:
        self._schema = schema
        self._fields_by_id = {f.field_id: f for f in schema.fields}
        self._fields_by_name = {f.name: f for f in schema.fields}

    @property
    def schema(self) -> Schema:
        return self._schema

    def serialize(self, data: Dict[str, Any]) -> bytes:
        buf = Buffer()
        buf.write_bytes(encode_uvarint(self._schema.version))
        for field in self._schema.sorted_fields():
            wire_type = _field_type_to_wire_type(field.field_type)
            buf.write_bytes(_encode_tag(field.field_id, wire_type))
            value = data.get(field.name, field.default)
            self._write_field_value(buf, field, value)
        return buf.data

    def deserialize(
        self,
        raw: bytes,
        reader_schema: Schema | None = None,
    ) -> Dict[str, Any]:
        if reader_schema is not None:
            check_compatibility(self._schema, reader_schema)

        buf = Buffer(raw)
        result: Dict[str, Any] = {}

        try:
            stored_version = decode_uvarint(buf)
        except Exception as e:
            raise DeserializationError(f"failed to read schema version: {e}") from e

        if stored_version < 1:
            raise DeserializationError(f"invalid stored schema version: {stored_version}")

        active_schema = reader_schema if reader_schema is not None else self._schema
        for f in active_schema.fields:
            result[f.name] = f.default

        reader_fields = (
            {f.field_id: f for f in reader_schema.fields}
            if reader_schema is not None
            else self._fields_by_id
        )

        while buf.remaining > 0:
            try:
                field_id, wire_type = _decode_tag(buf)
            except Exception as e:
                raise DeserializationError(f"failed to read field tag: {e}") from e

            field = reader_fields.get(field_id)

            if field is None:
                try:
                    _skip_by_wire_type(buf, wire_type)
                except Exception as e:
                    raise DeserializationError(
                        f"failed to skip unknown field id={field_id}: {e}"
                    ) from e
                continue

            actual_wire_type = _field_type_to_wire_type(field.field_type)
            if wire_type != actual_wire_type:
                raise DeserializationError(
                    f"wire type mismatch for field '{field.name}' (id={field_id}): "
                    f"expected {actual_wire_type}, got {wire_type}"
                )

            try:
                value = self._read_field_value(buf, field)
                result[field.name] = value
            except Exception as e:
                raise DeserializationError(
                    f"failed to read field '{field.name}' (id={field_id}): {e}"
                ) from e

        return result

    def _write_field_value(self, buf: Buffer, field: FieldDef, value: Any) -> None:
        if field.field_type == FieldType.BOOL:
            if not isinstance(value, bool):
                raise TypeError(
                    f"field '{field.name}' expects bool, got {type(value).__name__}"
                )
            buf.write_bytes(_encode_bool(value))
        elif field.field_type in (
            FieldType.INT32,
            FieldType.INT64,
            FieldType.UINT32,
            FieldType.UINT64,
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(
                    f"field '{field.name}' expects int, got {type(value).__name__}"
                )
            buf.write_bytes(_encode_integer(field.field_type, value))
        elif field.field_type == FieldType.STRING:
            if not isinstance(value, str):
                raise TypeError(
                    f"field '{field.name}' expects str, got {type(value).__name__}"
                )
            buf.write_bytes(_encode_string(value))
        elif field.field_type == FieldType.BYTES:
            if not isinstance(value, (bytes, bytearray)):
                raise TypeError(
                    f"field '{field.name}' expects bytes, got {type(value).__name__}"
                )
            buf.write_bytes(_encode_bytes(bytes(value)))
        else:
            raise SchemaError(f"unsupported field type: {field.field_type}")

    def _read_field_value(self, buf: Buffer, field: FieldDef) -> Any:
        if field.field_type == FieldType.BOOL:
            return _decode_bool(buf)
        elif field.field_type in (
            FieldType.INT32,
            FieldType.INT64,
            FieldType.UINT32,
            FieldType.UINT64,
        ):
            return _decode_integer(field.field_type, buf)
        elif field.field_type == FieldType.STRING:
            return _decode_string(buf)
        elif field.field_type == FieldType.BYTES:
            return _decode_bytes(buf)
        else:
            raise SchemaError(f"unsupported field type: {field.field_type}")


def deserialize_with_schema(
    raw: bytes,
    writer_schema: Schema,
    reader_schema: Schema,
) -> Dict[str, Any]:
    check_compatibility(writer_schema, reader_schema)
    serializer = BinarySerializer(writer_schema)
    return serializer.deserialize(raw, reader_schema=reader_schema)
