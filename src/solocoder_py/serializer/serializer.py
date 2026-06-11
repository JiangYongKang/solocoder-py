from __future__ import annotations

import struct
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
            buf.write_bytes(encode_uvarint(field.field_id))
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

        fields = reader_schema.fields if reader_schema else self._schema.fields
        for f in fields:
            result[f.name] = f.default

        while buf.remaining > 0:
            try:
                field_id = decode_uvarint(buf)
            except Exception as e:
                raise DeserializationError(f"failed to read field id: {e}") from e

            field = self._fields_by_id.get(field_id)
            if reader_schema is not None:
                field = reader_schema.field_by_id(field_id)

            if field is None:
                try:
                    self._skip_unknown_field(buf)
                except Exception as e:
                    raise DeserializationError(
                        f"failed to skip unknown field id={field_id}: {e}"
                    ) from e
                continue

            try:
                value = self._read_field_value(buf, field)
                if field.name in result:
                    result[field.name] = value
            except Exception as e:
                raise DeserializationError(
                    f"failed to read field '{field.name}' (id={field_id}): {e}"
                ) from e

        return result

    def _write_field_value(self, buf: Buffer, field: FieldDef, value: Any) -> None:
        if field.field_type == FieldType.BOOL:
            buf.write_bytes(_encode_bool(bool(value)))
        elif field.field_type in (
            FieldType.INT32,
            FieldType.INT64,
            FieldType.UINT32,
            FieldType.UINT64,
        ):
            buf.write_bytes(_encode_integer(field.field_type, int(value)))
        elif field.field_type == FieldType.STRING:
            buf.write_bytes(_encode_string(str(value)))
        elif field.field_type == FieldType.BYTES:
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

    def _skip_unknown_field(self, buf: Buffer) -> None:
        marker = buf.peek_byte()
        if marker == 0x00 or marker == 0x01:
            buf.skip(1)
            return
        if marker < 0x80:
            decode_uvarint(buf)
            return
        try:
            decode_uvarint(buf)
            return
        except Exception:
            pass
        try:
            length = decode_uvarint(buf)
            buf.skip(length)
            return
        except Exception:
            pass
        raise DeserializationError("cannot determine unknown field encoding")


def deserialize_with_schema(
    raw: bytes,
    writer_schema: Schema,
    reader_schema: Schema,
) -> Dict[str, Any]:
    check_compatibility(writer_schema, reader_schema)
    serializer = BinarySerializer(writer_schema)
    return serializer.deserialize(raw, reader_schema=reader_schema)
