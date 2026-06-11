import pytest

from solocoder_py.serializer import (
    FieldDef,
    FieldType,
    Schema,
    SchemaCompatibilityError,
    check_compatibility,
)
from .conftest import make_schema_v1, make_schema_v2, make_schema_v3_compatible


class TestSchemaBasic:
    def test_create_schema(self):
        schema = Schema(
            name="Test",
            version=1,
            fields=[
                FieldDef(field_id=1, field_type=FieldType.UINT64, name="id"),
            ],
        )
        assert schema.name == "Test"
        assert schema.version == 1
        assert len(schema.fields) == 1

    def test_schema_version_must_be_positive(self):
        with pytest.raises(ValueError):
            Schema(name="Bad", version=0, fields=[])
        with pytest.raises(ValueError):
            Schema(name="Bad", version=-1, fields=[])

    def test_field_id_must_be_positive(self):
        with pytest.raises(ValueError):
            FieldDef(field_id=0, field_type=FieldType.UINT64, name="bad")
        with pytest.raises(ValueError):
            FieldDef(field_id=-1, field_type=FieldType.UINT64, name="bad")

    def test_duplicate_field_ids_raises(self):
        with pytest.raises(ValueError):
            Schema(
                name="Bad",
                version=1,
                fields=[
                    FieldDef(field_id=1, field_type=FieldType.UINT64, name="a"),
                    FieldDef(field_id=1, field_type=FieldType.STRING, name="b"),
                ],
            )

    def test_field_defaults_assigned(self):
        f = FieldDef(field_id=1, field_type=FieldType.UINT64, name="x")
        assert f.default == 0
        f = FieldDef(field_id=2, field_type=FieldType.STRING, name="s")
        assert f.default == ""
        f = FieldDef(field_id=3, field_type=FieldType.BOOL, name="b")
        assert f.default is False
        f = FieldDef(field_id=4, field_type=FieldType.BYTES, name="by")
        assert f.default == b""

    def test_field_by_id(self):
        schema = make_schema_v1()
        f = schema.field_by_id(2)
        assert f is not None
        assert f.name == "name"
        assert schema.field_by_id(999) is None

    def test_field_by_name(self):
        schema = make_schema_v1()
        f = schema.field_by_name("active")
        assert f is not None
        assert f.field_id == 3
        assert schema.field_by_name("nonexistent") is None

    def test_max_field_id(self):
        schema = make_schema_v1()
        assert schema.max_field_id() == 3
        empty = Schema(name="Empty", version=1, fields=[])
        assert empty.max_field_id() == 0

    def test_sorted_fields(self):
        schema = Schema(
            name="Unsorted",
            version=1,
            fields=[
                FieldDef(field_id=5, field_type=FieldType.UINT64, name="e"),
                FieldDef(field_id=2, field_type=FieldType.UINT64, name="b"),
                FieldDef(field_id=8, field_type=FieldType.UINT64, name="h"),
            ],
        )
        sorted_fields = schema.sorted_fields()
        assert [f.field_id for f in sorted_fields] == [2, 5, 8]


class TestSchemaCompatibility:
    def test_same_schema_is_compatible(self):
        s1 = make_schema_v1()
        s2 = make_schema_v1()
        check_compatibility(s1, s2)

    def test_adding_fields_allowed(self):
        s1 = make_schema_v1()
        s2 = make_schema_v2()
        check_compatibility(s1, s2)

    def test_name_mismatch_raises(self):
        s1 = make_schema_v1()
        s2 = Schema(
            name="Different",
            version=2,
            fields=s1.fields + [
                FieldDef(field_id=4, field_type=FieldType.INT64, name="age"),
            ],
        )
        with pytest.raises(SchemaCompatibilityError, match="name mismatch"):
            check_compatibility(s1, s2)

    def test_older_version_raises(self):
        s1 = make_schema_v2()
        s2 = Schema(name="User", version=1, fields=make_schema_v1().fields)
        with pytest.raises(SchemaCompatibilityError, match="older than"):
            check_compatibility(s1, s2)

    def test_deleting_field_raises(self):
        s1 = make_schema_v1()
        s2 = Schema(
            name="User",
            version=2,
            fields=[
                FieldDef(field_id=1, field_type=FieldType.UINT64, name="id"),
                FieldDef(field_id=2, field_type=FieldType.STRING, name="name"),
            ],
        )
        with pytest.raises(SchemaCompatibilityError, match="missing in new schema"):
            check_compatibility(s1, s2)

    def test_changing_field_type_raises(self):
        s1 = make_schema_v1()
        s2 = Schema(
            name="User",
            version=2,
            fields=[
                FieldDef(field_id=1, field_type=FieldType.STRING, name="id"),
                FieldDef(field_id=2, field_type=FieldType.STRING, name="name"),
                FieldDef(field_id=3, field_type=FieldType.BOOL, name="active"),
            ],
        )
        with pytest.raises(SchemaCompatibilityError, match="type changed"):
            check_compatibility(s1, s2)

    def test_new_field_id_not_appended_raises(self):
        s1 = make_schema_v1()
        with pytest.raises(ValueError, match="duplicate field_id"):
            Schema(
                name="User",
                version=2,
                fields=[
                    FieldDef(field_id=1, field_type=FieldType.UINT64, name="id"),
                    FieldDef(field_id=2, field_type=FieldType.STRING, name="name"),
                    FieldDef(field_id=3, field_type=FieldType.BOOL, name="active"),
                    FieldDef(field_id=2, field_type=FieldType.INT64, name="dup"),
                ],
            )

    def test_new_field_id_less_than_old_max_raises(self):
        s1 = Schema(
            name="Gap",
            version=1,
            fields=[
                FieldDef(field_id=1, field_type=FieldType.UINT64, name="id"),
                FieldDef(field_id=3, field_type=FieldType.STRING, name="name"),
            ],
        )
        s2 = Schema(
            name="Gap",
            version=2,
            fields=[
                FieldDef(field_id=1, field_type=FieldType.UINT64, name="id"),
                FieldDef(field_id=3, field_type=FieldType.STRING, name="name"),
                FieldDef(field_id=2, field_type=FieldType.INT64, name="inserted_between"),
            ],
        )
        with pytest.raises(SchemaCompatibilityError, match="greater than old max field id"):
            check_compatibility(s1, s2)

    def test_multiple_version_upgrades(self):
        s1 = make_schema_v1()
        s2 = make_schema_v2()
        s3 = make_schema_v3_compatible()
        check_compatibility(s1, s3)
        check_compatibility(s2, s3)
