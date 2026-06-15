from __future__ import annotations

import pytest

from solocoder_py.schema_validator import (
    FieldSchema,
    FieldType,
    Schema,
    SchemaValidator,
)


@pytest.fixture
def simple_schema() -> Schema:
    return Schema(
        properties={
            "name": FieldSchema(type=FieldType.STRING, required=True),
            "age": FieldSchema(type=FieldType.INTEGER, required=True, min_value=0, max_value=150),
            "score": FieldSchema(type=FieldType.FLOAT, min_value=0.0, max_value=100.0),
            "active": FieldSchema(type=FieldType.BOOLEAN),
        }
    )


@pytest.fixture
def simple_validator(simple_schema: Schema) -> SchemaValidator:
    return SchemaValidator(simple_schema)


@pytest.fixture
def nested_schema() -> Schema:
    return Schema(
        properties={
            "user": FieldSchema(
                type=FieldType.OBJECT,
                required=True,
                properties={
                    "name": FieldSchema(type=FieldType.STRING, required=True),
                    "age": FieldSchema(type=FieldType.INTEGER, required=True, min_value=0),
                    "address": FieldSchema(
                        type=FieldType.OBJECT,
                        required=True,
                        properties={
                            "city": FieldSchema(type=FieldType.STRING, required=True),
                            "zipcode": FieldSchema(type=FieldType.STRING, required=True, min_length=5, max_length=10),
                        },
                    ),
                },
            ),
            "tags": FieldSchema(
                type=FieldType.LIST,
                items=FieldSchema(type=FieldType.STRING, min_length=1),
            ),
        }
    )


@pytest.fixture
def nested_validator(nested_schema: Schema) -> SchemaValidator:
    return SchemaValidator(nested_schema)


@pytest.fixture
def list_of_objects_schema() -> Schema:
    return Schema(
        properties={
            "users": FieldSchema(
                type=FieldType.LIST,
                items=FieldSchema(
                    type=FieldType.OBJECT,
                    properties={
                        "id": FieldSchema(type=FieldType.INTEGER, required=True, min_value=1),
                        "name": FieldSchema(type=FieldType.STRING, required=True),
                    },
                ),
            ),
        }
    )


@pytest.fixture
def list_of_objects_validator(list_of_objects_schema: Schema) -> SchemaValidator:
    return SchemaValidator(list_of_objects_schema)


@pytest.fixture
def shallow_depth_schema() -> Schema:
    return Schema(
        properties={
            "level1": FieldSchema(
                type=FieldType.OBJECT,
                properties={
                    "level2": FieldSchema(
                        type=FieldType.OBJECT,
                        properties={
                            "level3": FieldSchema(
                                type=FieldType.OBJECT,
                                properties={
                                    "value": FieldSchema(type=FieldType.STRING),
                                },
                            ),
                        },
                    ),
                },
            ),
        },
        max_depth=3,
    )


@pytest.fixture
def shallow_depth_validator(shallow_depth_schema: Schema) -> SchemaValidator:
    return SchemaValidator(shallow_depth_schema)
