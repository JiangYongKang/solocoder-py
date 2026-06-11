from solocoder_py.serializer import (
    BinarySerializer,
    Buffer,
    FieldDef,
    FieldType,
    Schema,
)


def make_buffer(initial: bytes | None = None) -> Buffer:
    return Buffer(initial)


def make_schema_v1() -> Schema:
    return Schema(
        name="User",
        version=1,
        fields=[
            FieldDef(field_id=1, field_type=FieldType.UINT64, name="id"),
            FieldDef(field_id=2, field_type=FieldType.STRING, name="name"),
            FieldDef(field_id=3, field_type=FieldType.BOOL, name="active"),
        ],
    )


def make_schema_v2() -> Schema:
    return Schema(
        name="User",
        version=2,
        fields=[
            FieldDef(field_id=1, field_type=FieldType.UINT64, name="id"),
            FieldDef(field_id=2, field_type=FieldType.STRING, name="name"),
            FieldDef(field_id=3, field_type=FieldType.BOOL, name="active"),
            FieldDef(field_id=4, field_type=FieldType.INT64, name="age"),
            FieldDef(field_id=5, field_type=FieldType.STRING, name="email", default="unknown@example.com"),
        ],
    )


def make_schema_v3_compatible() -> Schema:
    return Schema(
        name="User",
        version=3,
        fields=[
            FieldDef(field_id=1, field_type=FieldType.UINT64, name="id"),
            FieldDef(field_id=2, field_type=FieldType.STRING, name="name"),
            FieldDef(field_id=3, field_type=FieldType.BOOL, name="active"),
            FieldDef(field_id=4, field_type=FieldType.INT64, name="age"),
            FieldDef(field_id=5, field_type=FieldType.STRING, name="email", default="unknown@example.com"),
            FieldDef(field_id=6, field_type=FieldType.BYTES, name="avatar", default=b""),
        ],
    )
