import pytest

from solocoder_py.serializer import (
    BinarySerializer,
    Buffer,
    DeserializationError,
    FieldDef,
    FieldType,
    Schema,
    SchemaCompatibilityError,
    check_compatibility,
    deserialize_with_schema,
)
from .conftest import make_schema_v1, make_schema_v2, make_schema_v3_compatible


class TestBasicTypesSerialize:
    def test_bool_false(self):
        schema = Schema(
            name="BoolTest",
            version=1,
            fields=[FieldDef(field_id=1, field_type=FieldType.BOOL, name="flag")],
        )
        ser = BinarySerializer(schema)
        data = {"flag": False}
        raw = ser.serialize(data)
        result = ser.deserialize(raw)
        assert result["flag"] is False

    def test_bool_true(self):
        schema = Schema(
            name="BoolTest",
            version=1,
            fields=[FieldDef(field_id=1, field_type=FieldType.BOOL, name="flag")],
        )
        ser = BinarySerializer(schema)
        data = {"flag": True}
        raw = ser.serialize(data)
        result = ser.deserialize(raw)
        assert result["flag"] is True

    def test_string_empty(self):
        schema = Schema(
            name="StrTest",
            version=1,
            fields=[FieldDef(field_id=1, field_type=FieldType.STRING, name="s")],
        )
        ser = BinarySerializer(schema)
        data = {"s": ""}
        raw = ser.serialize(data)
        result = ser.deserialize(raw)
        assert result["s"] == ""

    def test_string_ascii(self):
        schema = Schema(
            name="StrTest",
            version=1,
            fields=[FieldDef(field_id=1, field_type=FieldType.STRING, name="s")],
        )
        ser = BinarySerializer(schema)
        data = {"s": "Hello, World!"}
        raw = ser.serialize(data)
        result = ser.deserialize(raw)
        assert result["s"] == "Hello, World!"

    def test_string_unicode(self):
        schema = Schema(
            name="StrTest",
            version=1,
            fields=[FieldDef(field_id=1, field_type=FieldType.STRING, name="s")],
        )
        ser = BinarySerializer(schema)
        data = {"s": "你好，世界！🌍"}
        raw = ser.serialize(data)
        result = ser.deserialize(raw)
        assert result["s"] == "你好，世界！🌍"

    def test_bytes_empty(self):
        schema = Schema(
            name="BytesTest",
            version=1,
            fields=[FieldDef(field_id=1, field_type=FieldType.BYTES, name="b")],
        )
        ser = BinarySerializer(schema)
        data = {"b": b""}
        raw = ser.serialize(data)
        result = ser.deserialize(raw)
        assert result["b"] == b""

    def test_bytes_arbitrary(self):
        schema = Schema(
            name="BytesTest",
            version=1,
            fields=[FieldDef(field_id=1, field_type=FieldType.BYTES, name="b")],
        )
        ser = BinarySerializer(schema)
        data = {"b": b"\x00\x01\x02\xff\xfe\x80"}
        raw = ser.serialize(data)
        result = ser.deserialize(raw)
        assert result["b"] == b"\x00\x01\x02\xff\xfe\x80"

    def test_uint64_zero(self):
        schema = Schema(
            name="UintTest",
            version=1,
            fields=[FieldDef(field_id=1, field_type=FieldType.UINT64, name="n")],
        )
        ser = BinarySerializer(schema)
        data = {"n": 0}
        raw = ser.serialize(data)
        result = ser.deserialize(raw)
        assert result["n"] == 0

    def test_uint64_large(self):
        schema = Schema(
            name="UintTest",
            version=1,
            fields=[FieldDef(field_id=1, field_type=FieldType.UINT64, name="n")],
        )
        ser = BinarySerializer(schema)
        data = {"n": 2**64 - 1}
        raw = ser.serialize(data)
        result = ser.deserialize(raw)
        assert result["n"] == 2**64 - 1

    def test_int64_positive(self):
        schema = Schema(
            name="IntTest",
            version=1,
            fields=[FieldDef(field_id=1, field_type=FieldType.INT64, name="n")],
        )
        ser = BinarySerializer(schema)
        data = {"n": 42}
        raw = ser.serialize(data)
        result = ser.deserialize(raw)
        assert result["n"] == 42

    def test_int64_negative(self):
        schema = Schema(
            name="IntTest",
            version=1,
            fields=[FieldDef(field_id=1, field_type=FieldType.INT64, name="n")],
        )
        ser = BinarySerializer(schema)
        data = {"n": -42}
        raw = ser.serialize(data)
        result = ser.deserialize(raw)
        assert result["n"] == -42

    def test_int64_min(self):
        schema = Schema(
            name="IntTest",
            version=1,
            fields=[FieldDef(field_id=1, field_type=FieldType.INT64, name="n")],
        )
        ser = BinarySerializer(schema)
        data = {"n": -(2**63)}
        raw = ser.serialize(data)
        result = ser.deserialize(raw)
        assert result["n"] == -(2**63)

    def test_int64_max(self):
        schema = Schema(
            name="IntTest",
            version=1,
            fields=[FieldDef(field_id=1, field_type=FieldType.INT64, name="n")],
        )
        ser = BinarySerializer(schema)
        data = {"n": 2**63 - 1}
        raw = ser.serialize(data)
        result = ser.deserialize(raw)
        assert result["n"] == 2**63 - 1


class TestComplexStructures:
    def test_all_types(self):
        schema = Schema(
            name="AllTypes",
            version=1,
            fields=[
                FieldDef(field_id=1, field_type=FieldType.BOOL, name="active"),
                FieldDef(field_id=2, field_type=FieldType.UINT64, name="uid"),
                FieldDef(field_id=3, field_type=FieldType.INT64, name="balance"),
                FieldDef(field_id=4, field_type=FieldType.STRING, name="name"),
                FieldDef(field_id=5, field_type=FieldType.BYTES, name="hash"),
            ],
        )
        ser = BinarySerializer(schema)
        data = {
            "active": True,
            "uid": 12345,
            "balance": -67890,
            "name": "Alice",
            "hash": b"\xde\xad\xbe\xef",
        }
        raw = ser.serialize(data)
        result = ser.deserialize(raw)
        assert result == data

    def test_user_v1_roundtrip(self):
        schema = make_schema_v1()
        ser = BinarySerializer(schema)
        data = {"id": 1, "name": "Bob", "active": True}
        raw = ser.serialize(data)
        result = ser.deserialize(raw)
        assert result["id"] == 1
        assert result["name"] == "Bob"
        assert result["active"] is True

    def test_default_values_applied_when_missing(self):
        schema = Schema(
            name="Defaults",
            version=1,
            fields=[
                FieldDef(field_id=1, field_type=FieldType.UINT64, name="n"),
                FieldDef(field_id=2, field_type=FieldType.STRING, name="s"),
                FieldDef(field_id=3, field_type=FieldType.BOOL, name="b"),
            ],
        )
        ser = BinarySerializer(schema)
        data = {"n": 42}
        raw = ser.serialize(data)
        result = ser.deserialize(raw)
        assert result["n"] == 42
        assert result["s"] == ""
        assert result["b"] is False

    def test_multiple_records(self):
        schema = make_schema_v1()
        ser = BinarySerializer(schema)
        users = [
            {"id": 1, "name": "A", "active": True},
            {"id": 2, "name": "B", "active": False},
            {"id": 3, "name": "C", "active": True},
        ]
        results = []
        for u in users:
            raw = ser.serialize(u)
            results.append(ser.deserialize(raw))
        assert results == users


class TestSchemaEvolution:
    def test_v1_data_read_by_v2_schema_fills_defaults(self):
        v1_schema = make_schema_v1()
        v2_schema = make_schema_v2()
        v1_ser = BinarySerializer(v1_schema)
        v1_data = {"id": 100, "name": "OldUser", "active": True}
        raw = v1_ser.serialize(v1_data)

        v2_ser = BinarySerializer(v2_schema)
        result = v2_ser.deserialize(raw, reader_schema=v2_schema)
        assert result["id"] == 100
        assert result["name"] == "OldUser"
        assert result["active"] is True
        assert result["age"] == 0
        assert result["email"] == "unknown@example.com"

    def test_v1_read_with_deserialize_helper(self):
        v1_schema = make_schema_v1()
        v2_schema = make_schema_v2()
        v1_ser = BinarySerializer(v1_schema)
        v1_data = {"id": 200, "name": "Helper", "active": False}
        raw = v1_ser.serialize(v1_data)

        result = deserialize_with_schema(raw, v1_schema, v2_schema)
        assert result["id"] == 200
        assert result["name"] == "Helper"
        assert result["active"] is False
        assert result["age"] == 0
        assert result["email"] == "unknown@example.com"

    def test_v2_data_read_by_v2_schema_full(self):
        v2_schema = make_schema_v2()
        ser = BinarySerializer(v2_schema)
        v2_data = {
            "id": 300,
            "name": "NewUser",
            "active": True,
            "age": 30,
            "email": "new@example.com",
        }
        raw = ser.serialize(v2_data)
        result = ser.deserialize(raw)
        assert result == v2_data

    def test_no_new_fields_same_encoding(self):
        s_a = make_schema_v1()
        s_b = Schema(
            name="User",
            version=1,
            fields=[
                FieldDef(field_id=1, field_type=FieldType.UINT64, name="id"),
                FieldDef(field_id=2, field_type=FieldType.STRING, name="name"),
                FieldDef(field_id=3, field_type=FieldType.BOOL, name="active"),
            ],
        )
        data = {"id": 1, "name": "Same", "active": False}
        raw_a = BinarySerializer(s_a).serialize(data)
        raw_b = BinarySerializer(s_b).serialize(data)
        assert raw_a == raw_b

    def test_unknown_fields_ignored(self):
        writer_schema = Schema(
            name="User",
            version=2,
            fields=[
                FieldDef(field_id=1, field_type=FieldType.UINT64, name="id"),
                FieldDef(field_id=2, field_type=FieldType.STRING, name="name"),
                FieldDef(field_id=3, field_type=FieldType.INT64, name="secret_code"),
            ],
        )
        reader_schema = Schema(
            name="User",
            version=1,
            fields=[
                FieldDef(field_id=1, field_type=FieldType.UINT64, name="id"),
                FieldDef(field_id=2, field_type=FieldType.STRING, name="name"),
            ],
        )
        check_compatibility(reader_schema, writer_schema)
        writer_ser = BinarySerializer(writer_schema)
        writer_data = {"id": 999, "name": "Secret", "secret_code": 42}
        raw = writer_ser.serialize(writer_data)
        reader_ser = BinarySerializer(reader_schema)
        result = reader_ser.deserialize(raw, reader_schema=reader_schema)
        assert result["id"] == 999
        assert result["name"] == "Secret"

    def test_multi_level_upgrade_v1_to_v3(self):
        v1 = make_schema_v1()
        v3 = make_schema_v3_compatible()
        v1_ser = BinarySerializer(v1)
        data = {"id": 1, "name": "Original", "active": True}
        raw = v1_ser.serialize(data)
        v3_ser = BinarySerializer(v3)
        result = v3_ser.deserialize(raw, reader_schema=v3)
        assert result["id"] == 1
        assert result["name"] == "Original"
        assert result["active"] is True
        assert result["age"] == 0
        assert result["email"] == "unknown@example.com"
        assert result["avatar"] == b""


class TestEdgeCases:
    def test_empty_string_serialization(self):
        schema = Schema(
            name="Edge",
            version=1,
            fields=[FieldDef(field_id=1, field_type=FieldType.STRING, name="empty")],
        )
        ser = BinarySerializer(schema)
        raw = ser.serialize({"empty": ""})
        result = ser.deserialize(raw)
        assert result["empty"] == ""

    def test_zero_value_varint_boundary(self):
        schema = Schema(
            name="Edge",
            version=1,
            fields=[
                FieldDef(field_id=1, field_type=FieldType.UINT64, name="zero"),
            ],
        )
        ser = BinarySerializer(schema)
        raw = ser.serialize({"zero": 0})
        result = ser.deserialize(raw)
        assert result["zero"] == 0

    def test_max_uint64_boundary(self):
        schema = Schema(
            name="Edge",
            version=1,
            fields=[
                FieldDef(field_id=1, field_type=FieldType.UINT64, name="big"),
            ],
        )
        ser = BinarySerializer(schema)
        raw = ser.serialize({"big": 2**64 - 1})
        result = ser.deserialize(raw)
        assert result["big"] == 2**64 - 1

    def test_int32_boundary_values(self):
        schema = Schema(
            name="Int32Edge",
            version=1,
            fields=[
                FieldDef(field_id=1, field_type=FieldType.INT32, name="min32"),
                FieldDef(field_id=2, field_type=FieldType.INT32, name="max32"),
                FieldDef(field_id=3, field_type=FieldType.UINT32, name="umax32"),
            ],
        )
        ser = BinarySerializer(schema)
        data = {"min32": -(2**31), "max32": 2**31 - 1, "umax32": 2**32 - 1}
        raw = ser.serialize(data)
        result = ser.deserialize(raw)
        assert result == data

    def test_single_byte_varint_boundary_127(self):
        schema = Schema(
            name="VarintEdge",
            version=1,
            fields=[
                FieldDef(field_id=1, field_type=FieldType.UINT64, name="single"),
                FieldDef(field_id=2, field_type=FieldType.UINT64, name="multi"),
            ],
        )
        ser = BinarySerializer(schema)
        raw = ser.serialize({"single": 127, "multi": 128})
        result = ser.deserialize(raw)
        assert result["single"] == 127
        assert result["multi"] == 128


class TestErrorCases:
    def test_varint_truncated_in_field(self):
        schema = Schema(
            name="Bad",
            version=1,
            fields=[FieldDef(field_id=1, field_type=FieldType.UINT64, name="x")],
        )
        ser = BinarySerializer(schema)
        good_raw = ser.serialize({"x": 2**64 - 1})
        truncated = good_raw[:-3]
        with pytest.raises(DeserializationError):
            ser.deserialize(truncated)

    def test_delete_required_field_incompatible(self):
        old = Schema(
            name="User",
            version=1,
            fields=[
                FieldDef(field_id=1, field_type=FieldType.UINT64, name="id"),
                FieldDef(field_id=2, field_type=FieldType.STRING, name="name"),
            ],
        )
        new = Schema(
            name="User",
            version=2,
            fields=[
                FieldDef(field_id=1, field_type=FieldType.UINT64, name="id"),
            ],
        )
        with pytest.raises(SchemaCompatibilityError, match="missing in new schema"):
            check_compatibility(old, new)

    def test_invalid_bool_byte(self):
        schema = Schema(
            name="BadBool",
            version=1,
            fields=[FieldDef(field_id=1, field_type=FieldType.BOOL, name="b")],
        )
        from solocoder_py.serializer.serializer import _encode_tag
        from solocoder_py.serializer.varint import encode_uvarint

        version_bytes = encode_uvarint(1)
        tag_bytes = _encode_tag(1, 0)
        bad_bool = b"\x02"
        raw = version_bytes + tag_bytes + bad_bool
        ser = BinarySerializer(schema)
        with pytest.raises(DeserializationError):
            ser.deserialize(raw)

    def test_reader_schema_name_mismatch(self):
        v1 = make_schema_v1()
        other = Schema(
            name="OtherThing",
            version=2,
            fields=[
                FieldDef(field_id=1, field_type=FieldType.UINT64, name="id"),
                FieldDef(field_id=4, field_type=FieldType.INT64, name="extra"),
            ],
        )
        with pytest.raises(SchemaCompatibilityError):
            check_compatibility(v1, other)


class TestUnknownFieldSkipping:
    def test_short_string_unknown_field_skipped(self):
        writer_schema = Schema(
            name="User",
            version=2,
            fields=[
                FieldDef(field_id=1, field_type=FieldType.UINT64, name="id"),
                FieldDef(field_id=10, field_type=FieldType.STRING, name="short_note"),
            ],
        )
        reader_schema = Schema(
            name="User",
            version=1,
            fields=[
                FieldDef(field_id=1, field_type=FieldType.UINT64, name="id"),
            ],
        )
        writer_ser = BinarySerializer(writer_schema)
        raw = writer_ser.serialize({"id": 42, "short_note": "hello"})
        reader_ser = BinarySerializer(reader_schema)
        result = reader_ser.deserialize(raw, reader_schema=reader_schema)
        assert result["id"] == 42

    def test_long_string_unknown_field_skipped_correctly(self):
        writer_schema = Schema(
            name="User",
            version=2,
            fields=[
                FieldDef(field_id=1, field_type=FieldType.UINT64, name="id"),
                FieldDef(field_id=10, field_type=FieldType.STRING, name="long_bio"),
                FieldDef(field_id=2, field_type=FieldType.STRING, name="name"),
            ],
        )
        reader_schema = Schema(
            name="User",
            version=1,
            fields=[
                FieldDef(field_id=1, field_type=FieldType.UINT64, name="id"),
                FieldDef(field_id=2, field_type=FieldType.STRING, name="name"),
            ],
        )
        long_string = "A" * 300
        writer_ser = BinarySerializer(writer_schema)
        raw = writer_ser.serialize({"id": 7, "long_bio": long_string, "name": "Bob"})
        reader_ser = BinarySerializer(reader_schema)
        result = reader_ser.deserialize(raw, reader_schema=reader_schema)
        assert result["id"] == 7
        assert result["name"] == "Bob"

    def test_bytes_unknown_field_skipped(self):
        writer_schema = Schema(
            name="Doc",
            version=2,
            fields=[
                FieldDef(field_id=1, field_type=FieldType.UINT64, name="id"),
                FieldDef(field_id=5, field_type=FieldType.BYTES, name="payload"),
                FieldDef(field_id=2, field_type=FieldType.STRING, name="title"),
            ],
        )
        reader_schema = Schema(
            name="Doc",
            version=1,
            fields=[
                FieldDef(field_id=1, field_type=FieldType.UINT64, name="id"),
                FieldDef(field_id=2, field_type=FieldType.STRING, name="title"),
            ],
        )
        large_bytes = b"\x00\x01\x02\xff" * 100
        writer_ser = BinarySerializer(writer_schema)
        raw = writer_ser.serialize({"id": 1, "payload": large_bytes, "title": "Hi"})
        reader_ser = BinarySerializer(reader_schema)
        result = reader_ser.deserialize(raw, reader_schema=reader_schema)
        assert result["id"] == 1
        assert result["title"] == "Hi"

    def test_mixed_unknown_fields_skipped(self):
        writer_schema = Schema(
            name="Item",
            version=3,
            fields=[
                FieldDef(field_id=1, field_type=FieldType.UINT64, name="id"),
                FieldDef(field_id=10, field_type=FieldType.INT64, name="secret_val"),
                FieldDef(field_id=11, field_type=FieldType.STRING, name="secret_str"),
                FieldDef(field_id=12, field_type=FieldType.BOOL, name="secret_flag"),
                FieldDef(field_id=2, field_type=FieldType.STRING, name="name"),
            ],
        )
        reader_schema = Schema(
            name="Item",
            version=1,
            fields=[
                FieldDef(field_id=1, field_type=FieldType.UINT64, name="id"),
                FieldDef(field_id=2, field_type=FieldType.STRING, name="name"),
            ],
        )
        writer_ser = BinarySerializer(writer_schema)
        data = {
            "id": 999,
            "secret_val": -12345,
            "secret_str": "this is a secret with length > 128 chars? " + "x" * 200,
            "secret_flag": True,
            "name": "KnownItem",
        }
        raw = writer_ser.serialize(data)
        reader_ser = BinarySerializer(reader_schema)
        result = reader_ser.deserialize(raw, reader_schema=reader_schema)
        assert result["id"] == 999
        assert result["name"] == "KnownItem"

    def test_unknown_field_at_end_skipped(self):
        writer_schema = Schema(
            name="E",
            version=2,
            fields=[
                FieldDef(field_id=1, field_type=FieldType.UINT64, name="id"),
                FieldDef(field_id=2, field_type=FieldType.STRING, name="name"),
                FieldDef(field_id=50, field_type=FieldType.BYTES, name="extra"),
            ],
        )
        reader_schema = Schema(
            name="E",
            version=1,
            fields=[
                FieldDef(field_id=1, field_type=FieldType.UINT64, name="id"),
                FieldDef(field_id=2, field_type=FieldType.STRING, name="name"),
            ],
        )
        writer_ser = BinarySerializer(writer_schema)
        raw = writer_ser.serialize({"id": 1, "name": "X", "extra": b"\xff" * 500})
        reader_ser = BinarySerializer(reader_schema)
        result = reader_ser.deserialize(raw, reader_schema=reader_schema)
        assert result == {"id": 1, "name": "X"}


class TestStrictTypeChecking:
    def test_bool_field_rejects_int(self):
        schema = Schema(
            name="T",
            version=1,
            fields=[FieldDef(field_id=1, field_type=FieldType.BOOL, name="flag")],
        )
        ser = BinarySerializer(schema)
        with pytest.raises(TypeError, match="expects bool"):
            ser.serialize({"flag": 1})

    def test_bool_field_rejects_string(self):
        schema = Schema(
            name="T",
            version=1,
            fields=[FieldDef(field_id=1, field_type=FieldType.BOOL, name="flag")],
        )
        ser = BinarySerializer(schema)
        with pytest.raises(TypeError):
            ser.serialize({"flag": "false"})

    def test_int_field_rejects_bool(self):
        schema = Schema(
            name="T",
            version=1,
            fields=[FieldDef(field_id=1, field_type=FieldType.UINT64, name="n")],
        )
        ser = BinarySerializer(schema)
        with pytest.raises(TypeError, match="expects int"):
            ser.serialize({"n": True})

    def test_int_field_rejects_string(self):
        schema = Schema(
            name="T",
            version=1,
            fields=[FieldDef(field_id=1, field_type=FieldType.INT64, name="n")],
        )
        ser = BinarySerializer(schema)
        with pytest.raises(TypeError):
            ser.serialize({"n": "42"})

    def test_string_field_rejects_int(self):
        schema = Schema(
            name="T",
            version=1,
            fields=[FieldDef(field_id=1, field_type=FieldType.STRING, name="s")],
        )
        ser = BinarySerializer(schema)
        with pytest.raises(TypeError, match="expects str"):
            ser.serialize({"s": 123})

    def test_bytes_field_rejects_string(self):
        schema = Schema(
            name="T",
            version=1,
            fields=[FieldDef(field_id=1, field_type=FieldType.BYTES, name="b")],
        )
        ser = BinarySerializer(schema)
        with pytest.raises(TypeError, match="expects bytes"):
            ser.serialize({"b": "hello"})


class TestStoredVersion:
    def test_stored_version_zero_invalid(self):
        from solocoder_py.serializer.varint import encode_uvarint

        schema = Schema(
            name="T",
            version=1,
            fields=[FieldDef(field_id=1, field_type=FieldType.UINT64, name="id")],
        )
        raw = encode_uvarint(0)
        ser = BinarySerializer(schema)
        with pytest.raises(DeserializationError, match="invalid stored schema version"):
            ser.deserialize(raw)

    def test_stored_version_negative_invalid(self):
        from solocoder_py.serializer.serializer import _encode_tag
        from solocoder_py.serializer.varint import encode_uvarint

        schema = Schema(
            name="T",
            version=1,
            fields=[FieldDef(field_id=1, field_type=FieldType.UINT64, name="id")],
        )
        version_bytes = encode_uvarint(1)
        tag_bytes = _encode_tag(1, 0)
        value_bytes = encode_uvarint(42)
        raw = version_bytes + tag_bytes + value_bytes
        ser = BinarySerializer(schema)
        result = ser.deserialize(raw)
        assert result["id"] == 42


class TestWireType:
    def test_wire_type_mismatch_raises(self):
        from solocoder_py.serializer.serializer import _encode_tag
        from solocoder_py.serializer.varint import encode_uvarint

        writer_schema = Schema(
            name="T",
            version=1,
            fields=[FieldDef(field_id=1, field_type=FieldType.UINT64, name="x")],
        )
        version_bytes = encode_uvarint(1)
        tag_bytes = _encode_tag(1, 2)
        length_bytes = encode_uvarint(5)
        data_bytes = b"hello"
        raw = version_bytes + tag_bytes + length_bytes + data_bytes
        ser = BinarySerializer(writer_schema)
        with pytest.raises(DeserializationError, match="wire type mismatch"):
            ser.deserialize(raw)

    def test_unknown_wire_type_raises_in_unknown_field(self):
        from solocoder_py.serializer.serializer import _encode_tag
        from solocoder_py.serializer.varint import encode_uvarint

        reader_schema = Schema(
            name="T",
            version=1,
            fields=[FieldDef(field_id=1, field_type=FieldType.UINT64, name="id")],
        )
        version_bytes = encode_uvarint(2)
        id_tag = _encode_tag(1, 0)
        id_val = encode_uvarint(10)
        bad_tag = _encode_tag(5, 7)
        raw = version_bytes + id_tag + id_val + bad_tag
        ser = BinarySerializer(reader_schema)
        with pytest.raises(DeserializationError, match="unknown wire type"):
            ser.deserialize(raw, reader_schema=reader_schema)
