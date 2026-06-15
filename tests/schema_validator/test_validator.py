from __future__ import annotations

import pytest

from solocoder_py.schema_validator import (
    FieldSchema,
    FieldType,
    Schema,
    SchemaValidator,
    ValidationErrorItem,
)


class TestTypeValidation:
    def test_string_type_valid(self, simple_validator: SchemaValidator):
        data = {"name": "test", "age": 25}
        result = simple_validator.validate(data)
        assert result.valid

    def test_string_type_invalid(self, simple_validator: SchemaValidator):
        data = {"name": 123, "age": 25}
        result = simple_validator.validate(data)
        assert not result.valid
        assert len(result.errors) == 1
        error = result.errors[0]
        assert error.path == "name"
        assert error.error_type == "type_mismatch"
        assert error.expected == "string"
        assert error.actual == "int"

    def test_integer_type_valid(self, simple_validator: SchemaValidator):
        data = {"name": "test", "age": 30}
        result = simple_validator.validate(data)
        assert result.valid

    def test_integer_type_invalid_with_float(self, simple_validator: SchemaValidator):
        data = {"name": "test", "age": 30.5}
        result = simple_validator.validate(data)
        assert not result.valid
        assert len(result.errors) == 1
        error = result.errors[0]
        assert error.path == "age"
        assert error.error_type == "type_mismatch"
        assert error.expected == "integer"
        assert error.actual == "float"
        assert "Field 'age'" in error.message
        assert "integer" in error.message
        assert "float" in error.message

    def test_integer_type_invalid_with_string(self, simple_validator: SchemaValidator):
        data = {"name": "test", "age": "30"}
        result = simple_validator.validate(data)
        assert not result.valid
        assert len(result.errors) >= 1
        error = result.errors[0]
        assert error.error_type == "type_mismatch"
        assert error.path == "age"
        assert error.expected == "integer"
        assert error.actual == "str"

    def test_integer_type_rejects_boolean(self, simple_validator: SchemaValidator):
        data = {"name": "test", "age": True}
        result = simple_validator.validate(data)
        assert not result.valid
        assert len(result.errors) >= 1
        error = result.errors[0]
        assert error.error_type == "type_mismatch"
        assert error.path == "age"
        assert error.expected == "integer"
        assert error.actual == "bool"

    def test_float_type_valid(self, simple_validator: SchemaValidator):
        data = {"name": "test", "age": 25, "score": 95.5}
        result = simple_validator.validate(data)
        assert result.valid

    def test_float_type_valid_with_int(self, simple_validator: SchemaValidator):
        data = {"name": "test", "age": 25, "score": 95}
        result = simple_validator.validate(data)
        assert result.valid

    def test_float_type_invalid_with_string(self, simple_validator: SchemaValidator):
        data = {"name": "test", "age": 25, "score": "95.5"}
        result = simple_validator.validate(data)
        assert not result.valid
        assert len(result.errors) >= 1
        error = result.errors[0]
        assert error.error_type == "type_mismatch"
        assert error.path == "score"
        assert error.expected == "float"
        assert error.actual == "str"

    def test_boolean_type_valid(self, simple_validator: SchemaValidator):
        data = {"name": "test", "age": 25, "active": True}
        result = simple_validator.validate(data)
        assert result.valid

    def test_boolean_type_invalid(self, simple_validator: SchemaValidator):
        data = {"name": "test", "age": 25, "active": "true"}
        result = simple_validator.validate(data)
        assert not result.valid
        assert len(result.errors) >= 1
        error = result.errors[0]
        assert error.error_type == "type_mismatch"
        assert error.path == "active"
        assert error.expected == "boolean"
        assert error.actual == "str"

    def test_list_type_valid(self):
        schema = Schema(
            properties={
                "items": FieldSchema(
                    type=FieldType.LIST,
                    items=FieldSchema(type=FieldType.INTEGER),
                ),
            }
        )
        validator = SchemaValidator(schema)
        data = {"items": [1, 2, 3]}
        result = validator.validate(data)
        assert result.valid

    def test_list_type_invalid(self):
        schema = Schema(
            properties={
                "items": FieldSchema(
                    type=FieldType.LIST,
                    items=FieldSchema(type=FieldType.INTEGER),
                ),
            }
        )
        validator = SchemaValidator(schema)
        data = {"items": "not a list"}
        result = validator.validate(data)
        assert not result.valid
        assert len(result.errors) >= 1
        error = result.errors[0]
        assert error.error_type == "type_mismatch"
        assert error.path == "items"
        assert error.expected == "list"
        assert error.actual == "str"

    def test_object_type_valid(self, nested_validator: SchemaValidator):
        data = {
            "user": {
                "name": "Alice",
                "age": 30,
                "address": {
                    "city": "New York",
                    "zipcode": "10001",
                },
            },
            "tags": ["python", "java"],
        }
        result = nested_validator.validate(data)
        assert result.valid

    def test_object_type_invalid(self, nested_validator: SchemaValidator):
        data = {"user": "not an object", "tags": []}
        result = nested_validator.validate(data)
        assert not result.valid
        type_errors = [e for e in result.errors if e.error_type == "type_mismatch"]
        assert len(type_errors) >= 1
        assert type_errors[0].path == "user"
        assert type_errors[0].expected == "object"
        assert type_errors[0].actual == "str"
        missing_errors = [e for e in result.errors if e.error_type == "required_field_missing"]
        assert len(missing_errors) >= 4
        missing_paths = [e.path for e in missing_errors]
        assert "user.name" in missing_paths
        assert "user.age" in missing_paths
        assert "user.address" in missing_paths
        assert "user.address.city" in missing_paths


class TestRequiredValidation:
    def test_required_field_missing(self, simple_validator: SchemaValidator):
        data = {"age": 25}
        result = simple_validator.validate(data)
        assert not result.valid
        missing_errors = [e for e in result.errors if e.error_type == "required_field_missing"]
        assert len(missing_errors) == 1
        assert missing_errors[0].path == "name"

    def test_required_field_null(self, simple_validator: SchemaValidator):
        data = {"name": None, "age": 25}
        result = simple_validator.validate(data)
        assert not result.valid
        null_errors = [e for e in result.errors if e.error_type == "required_field_null"]
        assert len(null_errors) == 1
        assert null_errors[0].path == "name"

    def test_required_field_empty_string(self, simple_validator: SchemaValidator):
        data = {"name": "", "age": 25}
        result = simple_validator.validate(data)
        assert not result.valid
        empty_errors = [e for e in result.errors if e.error_type == "required_field_empty"]
        assert len(empty_errors) == 1
        assert empty_errors[0].path == "name"

    def test_optional_field_missing_ok(self, simple_validator: SchemaValidator):
        data = {"name": "test", "age": 25}
        result = simple_validator.validate(data)
        assert result.valid

    def test_nested_required_parent_missing_reports_all_subfields(self, nested_validator: SchemaValidator):
        data = {"tags": []}
        result = nested_validator.validate(data)
        assert not result.valid
        missing_errors = [e for e in result.errors if e.error_type == "required_field_missing"]
        paths = [e.path for e in missing_errors]
        assert "user" in paths
        assert "user.name" in paths
        assert "user.age" in paths
        assert "user.address" in paths
        assert "user.address.city" in paths
        assert "user.address.zipcode" in paths

    def test_nested_required_parent_null_reports_all_subfields(self, nested_validator: SchemaValidator):
        data = {"user": None, "tags": []}
        result = nested_validator.validate(data)
        assert not result.valid
        null_errors = [e for e in result.errors if e.error_type == "required_field_null"]
        assert null_errors[0].path == "user"
        missing_errors = [e for e in result.errors if e.error_type == "required_field_missing"]
        paths = [e.path for e in missing_errors]
        assert "user.name" in paths
        assert "user.age" in paths
        assert "user.address" in paths
        assert "user.address.city" in paths
        assert "user.address.zipcode" in paths


class TestRangeValidation:
    def test_numeric_min_value_valid(self, simple_validator: SchemaValidator):
        data = {"name": "test", "age": 0}
        result = simple_validator.validate(data)
        assert result.valid

    def test_numeric_min_value_invalid(self, simple_validator: SchemaValidator):
        data = {"name": "test", "age": -1}
        result = simple_validator.validate(data)
        assert not result.valid
        range_errors = [e for e in result.errors if e.error_type == "value_out_of_range"]
        assert len(range_errors) == 1
        assert range_errors[0].path == "age"
        assert "[0, 150]" in range_errors[0].expected
        assert range_errors[0].actual == "-1"
        assert "current value" in range_errors[0].message
        assert "allowed range" in range_errors[0].message

    def test_numeric_max_value_valid(self, simple_validator: SchemaValidator):
        data = {"name": "test", "age": 150}
        result = simple_validator.validate(data)
        assert result.valid

    def test_numeric_max_value_invalid(self, simple_validator: SchemaValidator):
        data = {"name": "test", "age": 151}
        result = simple_validator.validate(data)
        assert not result.valid
        range_errors = [e for e in result.errors if e.error_type == "value_out_of_range"]
        assert len(range_errors) == 1
        assert range_errors[0].path == "age"
        assert "[0, 150]" in range_errors[0].expected
        assert range_errors[0].actual == "151"
        assert "current value" in range_errors[0].message

    def test_float_range_valid(self, simple_validator: SchemaValidator):
        data = {"name": "test", "age": 25, "score": 50.0}
        result = simple_validator.validate(data)
        assert result.valid

    def test_float_range_min_boundary_valid(self, simple_validator: SchemaValidator):
        data = {"name": "test", "age": 25, "score": 0.0}
        result = simple_validator.validate(data)
        assert result.valid

    def test_float_range_max_boundary_valid(self, simple_validator: SchemaValidator):
        data = {"name": "test", "age": 25, "score": 100.0}
        result = simple_validator.validate(data)
        assert result.valid

    def test_float_range_min_invalid(self, simple_validator: SchemaValidator):
        data = {"name": "test", "age": 25, "score": -0.1}
        result = simple_validator.validate(data)
        assert not result.valid

    def test_float_range_max_invalid(self, simple_validator: SchemaValidator):
        data = {"name": "test", "age": 25, "score": 100.1}
        result = simple_validator.validate(data)
        assert not result.valid


class TestStringLengthValidation:
    def test_min_length_valid(self):
        schema = Schema(
            properties={
                "username": FieldSchema(
                    type=FieldType.STRING,
                    required=True,
                    min_length=3,
                    max_length=10,
                ),
            }
        )
        validator = SchemaValidator(schema)
        data = {"username": "abc"}
        result = validator.validate(data)
        assert result.valid

    def test_min_length_invalid(self):
        schema = Schema(
            properties={
                "username": FieldSchema(
                    type=FieldType.STRING,
                    required=True,
                    min_length=3,
                    max_length=10,
                ),
            }
        )
        validator = SchemaValidator(schema)
        data = {"username": "ab"}
        result = validator.validate(data)
        assert not result.valid
        assert len(result.errors) >= 1
        error = result.errors[0]
        assert error.error_type == "length_out_of_range"
        assert error.path == "username"
        assert "[3, 10]" in error.expected
        assert "length=2" in error.actual
        assert "allowed length range" in error.message
        assert "actual length" in error.message

    def test_max_length_valid(self):
        schema = Schema(
            properties={
                "username": FieldSchema(
                    type=FieldType.STRING,
                    required=True,
                    min_length=3,
                    max_length=10,
                ),
            }
        )
        validator = SchemaValidator(schema)
        data = {"username": "abcdefghij"}
        result = validator.validate(data)
        assert result.valid

    def test_max_length_invalid(self):
        schema = Schema(
            properties={
                "username": FieldSchema(
                    type=FieldType.STRING,
                    required=True,
                    min_length=3,
                    max_length=10,
                ),
            }
        )
        validator = SchemaValidator(schema)
        data = {"username": "abcdefghijk"}
        result = validator.validate(data)
        assert not result.valid
        assert len(result.errors) >= 1
        error = result.errors[0]
        assert error.error_type == "length_out_of_range"
        assert error.path == "username"
        assert "[3, 10]" in error.expected
        assert "length=11" in error.actual
        assert "allowed length range" in error.message

    def test_nested_zipcode_length_valid(self, nested_validator: SchemaValidator):
        data = {
            "user": {
                "name": "Alice",
                "age": 30,
                "address": {
                    "city": "NYC",
                    "zipcode": "12345",
                },
            },
            "tags": [],
        }
        result = nested_validator.validate(data)
        assert result.valid

    def test_nested_zipcode_length_invalid(self, nested_validator: SchemaValidator):
        data = {
            "user": {
                "name": "Alice",
                "age": 30,
                "address": {
                    "city": "NYC",
                    "zipcode": "1234",
                },
            },
            "tags": [],
        }
        result = nested_validator.validate(data)
        assert not result.valid
        length_errors = [e for e in result.errors if e.error_type == "length_out_of_range"]
        assert len(length_errors) == 1
        assert length_errors[0].path == "user.address.zipcode"
        assert "[5, 10]" in length_errors[0].expected
        assert "length=4" in length_errors[0].actual


class TestNestedObjects:
    def test_nested_object_valid(self, nested_validator: SchemaValidator):
        data = {
            "user": {
                "name": "Alice",
                "age": 30,
                "address": {
                    "city": "New York",
                    "zipcode": "10001",
                },
            },
            "tags": ["python", "testing"],
        }
        result = nested_validator.validate(data)
        assert result.valid

    def test_nested_object_type_error(self, nested_validator: SchemaValidator):
        data = {
            "user": {
                "name": "Alice",
                "age": "thirty",
                "address": {
                    "city": "New York",
                    "zipcode": "10001",
                },
            },
            "tags": [],
        }
        result = nested_validator.validate(data)
        assert not result.valid
        type_errors = [e for e in result.errors if e.error_type == "type_mismatch"]
        assert len(type_errors) == 1
        assert type_errors[0].path == "user.age"
        assert type_errors[0].expected == "integer"
        assert type_errors[0].actual == "str"

    def test_list_items_type_validation(self):
        schema = Schema(
            properties={
                "scores": FieldSchema(
                    type=FieldType.LIST,
                    items=FieldSchema(type=FieldType.INTEGER, min_value=0, max_value=100),
                ),
            }
        )
        validator = SchemaValidator(schema)
        data = {"scores": [10, 20, "thirty", 40]}
        result = validator.validate(data)
        assert not result.valid
        type_errors = [e for e in result.errors if e.error_type == "type_mismatch"]
        assert len(type_errors) == 1
        assert type_errors[0].path == "scores[2]"
        assert type_errors[0].expected == "integer"
        assert type_errors[0].actual == "str"

    def test_list_items_range_validation(self):
        schema = Schema(
            properties={
                "scores": FieldSchema(
                    type=FieldType.LIST,
                    items=FieldSchema(type=FieldType.INTEGER, min_value=0, max_value=100),
                ),
            }
        )
        validator = SchemaValidator(schema)
        data = {"scores": [10, 150, 50]}
        result = validator.validate(data)
        assert not result.valid
        range_errors = [e for e in result.errors if e.error_type == "value_out_of_range"]
        assert len(range_errors) == 1
        assert range_errors[0].path == "scores[1]"
        assert "[0, 100]" in range_errors[0].expected
        assert range_errors[0].actual == "150"
        assert "current value" in range_errors[0].message

    def test_list_of_objects_valid(self, list_of_objects_validator: SchemaValidator):
        data = {
            "users": [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
            ]
        }
        result = list_of_objects_validator.validate(data)
        assert result.valid

    def test_list_of_objects_missing_required(self, list_of_objects_validator: SchemaValidator):
        data = {
            "users": [
                {"id": 1, "name": "Alice"},
                {"name": "Bob"},
            ]
        }
        result = list_of_objects_validator.validate(data)
        assert not result.valid
        missing_errors = [e for e in result.errors if e.error_type == "required_field_missing"]
        assert len(missing_errors) == 1
        assert missing_errors[0].path == "users[1].id"
        assert missing_errors[0].expected == "present"
        assert missing_errors[0].actual == "missing"


class TestMaxDepth:
    def test_within_max_depth_valid(self, shallow_depth_validator: SchemaValidator):
        data = {
            "level1": {
                "level2": {
                    "value": "test",
                },
            }
        }
        result = shallow_depth_validator.validate(data)
        assert result.valid

    def test_exactly_at_max_depth_valid(self, shallow_depth_validator: SchemaValidator):
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "value": "test",
                    },
                },
            }
        }
        result = shallow_depth_validator.validate(data)
        assert result.valid

    def test_exceeds_max_depth(self, shallow_depth_validator: SchemaValidator):
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "value": "too deep",
                        },
                    },
                },
            }
        }
        result = shallow_depth_validator.validate(data)
        assert not result.valid
        depth_errors = [e for e in result.errors if e.error_type == "max_depth_exceeded"]
        assert len(depth_errors) == 1
        assert depth_errors[0].path == "level1.level2.level3.level4"
        assert depth_errors[0].expected == "3"
        assert depth_errors[0].actual == "4"
        assert "Maximum nesting depth" in depth_errors[0].message

    def test_list_increases_depth(self):
        schema = Schema(
            properties={
                "items": FieldSchema(
                    type=FieldType.LIST,
                    items=FieldSchema(
                        type=FieldType.OBJECT,
                        properties={
                            "name": FieldSchema(type=FieldType.STRING),
                        },
                    ),
                ),
            },
            max_depth=2,
        )
        validator = SchemaValidator(schema)
        data = {
            "items": [
                {"name": "test"},
            ]
        }
        result = validator.validate(data)
        assert result.valid

    def test_list_nested_deep_exceeds_depth(self):
        schema = Schema(
            properties={
                "items": FieldSchema(
                    type=FieldType.LIST,
                    items=FieldSchema(
                        type=FieldType.OBJECT,
                        properties={
                            "inner": FieldSchema(
                                type=FieldType.OBJECT,
                                properties={
                                    "value": FieldSchema(type=FieldType.STRING),
                                },
                            ),
                        },
                    ),
                ),
            },
            max_depth=2,
        )
        validator = SchemaValidator(schema)
        data = {
            "items": [
                {
                    "inner": {
                        "value": "too deep",
                    },
                },
            ]
        }
        result = validator.validate(data)
        assert not result.valid
        depth_errors = [e for e in result.errors if e.error_type == "max_depth_exceeded"]
        assert len(depth_errors) == 1
        assert depth_errors[0].expected == "2"
        assert depth_errors[0].actual == "3"


class TestEdgeCases:
    def test_empty_record_with_no_required_fields(self):
        schema = Schema(
            properties={
                "optional": FieldSchema(type=FieldType.STRING),
            }
        )
        validator = SchemaValidator(schema)
        result = validator.validate({})
        assert result.valid
        assert len(result.errors) == 0

    def test_empty_record_with_required_fields(self, simple_validator: SchemaValidator):
        result = simple_validator.validate({})
        assert not result.valid
        missing_errors = [e for e in result.errors if e.error_type == "required_field_missing"]
        assert len(missing_errors) == 2
        paths = [e.path for e in missing_errors]
        assert "name" in paths
        assert "age" in paths
        for err in missing_errors:
            assert err.expected == "present"
            assert err.actual == "missing"

    def test_numeric_exactly_at_boundary_pass(self, simple_validator: SchemaValidator):
        data = {"name": "test", "age": 0, "score": 0.0}
        result = simple_validator.validate(data)
        assert result.valid
        assert len(result.errors) == 0

        data2 = {"name": "test", "age": 150, "score": 100.0}
        result2 = simple_validator.validate(data2)
        assert result2.valid
        assert len(result2.errors) == 0

    def test_multiple_errors_collected(self, simple_validator: SchemaValidator):
        data = {"name": 123, "age": -5, "score": "bad"}
        result = simple_validator.validate(data)
        assert not result.valid
        assert len(result.errors) >= 2
        error_types = set(e.error_type for e in result.errors)
        assert "type_mismatch" in error_types
        assert "value_out_of_range" in error_types

    def test_mixed_errors_in_nested_structure(self, nested_validator: SchemaValidator):
        data = {
            "user": {
                "name": "",
                "age": -10,
                "address": {
                    "city": 123,
                    "zipcode": "12",
                },
            },
            "tags": [1, "valid", ""],
        }
        result = nested_validator.validate(data)
        assert not result.valid
        error_types = set(e.error_type for e in result.errors)
        assert "required_field_empty" in error_types
        assert "value_out_of_range" in error_types
        assert "length_out_of_range" in error_types
        assert "type_mismatch" in error_types

        type_mismatches = [e for e in result.errors if e.error_type == "type_mismatch"]
        assert len(type_mismatches) >= 2
        type_paths = [e.path for e in type_mismatches]
        assert "user.address.city" in type_paths
        assert "tags[0]" in type_paths

    def test_boolean_is_not_integer(self, simple_validator: SchemaValidator):
        data = {"name": "test", "age": True}
        result = simple_validator.validate(data)
        assert not result.valid
        type_errors = [e for e in result.errors if e.error_type == "type_mismatch"]
        assert len(type_errors) == 1
        assert type_errors[0].path == "age"
        assert type_errors[0].expected == "integer"
        assert type_errors[0].actual == "bool"

    def test_root_not_dict_returns_error(self):
        schema = Schema(
            properties={
                "name": FieldSchema(type=FieldType.STRING),
            }
        )
        validator = SchemaValidator(schema)
        result = validator.validate("not a dict")
        assert not result.valid
        type_errors = [e for e in result.errors if e.error_type == "type_mismatch"]
        assert len(type_errors) == 1
        assert type_errors[0].path == "<root>"
        assert type_errors[0].expected == "object"
        assert type_errors[0].actual == "str"

    def test_empty_list_valid(self):
        schema = Schema(
            properties={
                "items": FieldSchema(
                    type=FieldType.LIST,
                    items=FieldSchema(type=FieldType.INTEGER),
                ),
            }
        )
        validator = SchemaValidator(schema)
        result = validator.validate({"items": []})
        assert result.valid
        assert len(result.errors) == 0


class TestSchemaDefinition:
    def test_schema_max_depth_validation(self):
        with pytest.raises(ValueError):
            Schema(properties={}, max_depth=0)

    def test_schema_max_depth_one_valid(self):
        schema = Schema(properties={}, max_depth=1)
        assert schema.max_depth == 1

    def test_field_schema_list_requires_items(self):
        with pytest.raises(ValueError):
            FieldSchema(type=FieldType.LIST)

    def test_field_schema_object_requires_properties(self):
        with pytest.raises(ValueError):
            FieldSchema(type=FieldType.OBJECT)


class TestValidationResult:
    def test_valid_result_bool(self, simple_validator: SchemaValidator):
        data = {"name": "test", "age": 25}
        result = simple_validator.validate(data)
        assert bool(result) is True

    def test_invalid_result_bool(self, simple_validator: SchemaValidator):
        data = {"name": 123, "age": 25}
        result = simple_validator.validate(data)
        assert bool(result) is False

    def test_validation_error_item_equality(self):
        item1 = ValidationErrorItem(
            path="test",
            error_type="type_mismatch",
            message="test message",
        )
        item2 = ValidationErrorItem(
            path="test",
            error_type="type_mismatch",
            message="test message",
        )
        assert item1 == item2

    def test_validation_error_item_inequality(self):
        item1 = ValidationErrorItem(
            path="test",
            error_type="type_mismatch",
            message="test message",
        )
        item2 = ValidationErrorItem(
            path="other",
            error_type="type_mismatch",
            message="test message",
        )
        assert item1 != item2
