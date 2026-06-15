from __future__ import annotations

from typing import Any

from .exceptions import SchemaDefinitionError, ValidationErrorItem
from .models import FieldType, FieldSchema, Schema, ValidationResult


class SchemaValidator:
    def __init__(self, schema: Schema) -> None:
        self._schema = schema

    @property
    def schema(self) -> Schema:
        return self._schema

    def validate(self, data: dict[str, Any]) -> ValidationResult:
        errors: list[ValidationErrorItem] = []
        self._validate_object(
            data=data,
            properties=self._schema.properties,
            path="",
            depth=0,
            errors=errors,
        )
        return ValidationResult(valid=len(errors) == 0, errors=errors)

    def _validate_object(
        self,
        data: Any,
        properties: dict[str, FieldSchema],
        path: str,
        depth: int,
        errors: list[ValidationErrorItem],
    ) -> None:
        if depth > self._schema.max_depth:
            errors.append(
                ValidationErrorItem(
                    path=path or "<root>",
                    error_type="max_depth_exceeded",
                    message=f"Maximum nesting depth of {self._schema.max_depth} exceeded",
                    expected=str(self._schema.max_depth),
                    actual=str(depth),
                )
            )
            return

        if not isinstance(data, dict):
            errors.append(
                ValidationErrorItem(
                    path=path or "<root>",
                    error_type="type_mismatch",
                    message=f"Expected object but got {type(data).__name__}",
                    expected="object",
                    actual=type(data).__name__,
                )
            )
            return

        for field_name, field_schema in properties.items():
            field_path = f"{path}.{field_name}" if path else field_name

            if field_name not in data:
                if field_schema.required:
                    errors.append(
                        ValidationErrorItem(
                            path=field_path,
                            error_type="required_field_missing",
                            message=f"Required field '{field_name}' is missing",
                            expected="present",
                            actual="missing",
                        )
                    )
                    if field_schema.type == FieldType.OBJECT and field_schema.properties:
                        self._report_nested_required_missing(
                            parent_path=field_path,
                            properties=field_schema.properties,
                            errors=errors,
                        )
                continue

            value = data[field_name]

            if value is None:
                if field_schema.required:
                    errors.append(
                        ValidationErrorItem(
                            path=field_path,
                            error_type="required_field_null",
                            message=f"Required field '{field_name}' is null",
                            expected="non-null",
                            actual="null",
                        )
                    )
                    if field_schema.type == FieldType.OBJECT and field_schema.properties:
                        self._report_nested_required_missing(
                            parent_path=field_path,
                            properties=field_schema.properties,
                            errors=errors,
                        )
                continue

            if field_schema.type == FieldType.STRING and isinstance(value, str) and value == "":
                if field_schema.required:
                    errors.append(
                        ValidationErrorItem(
                            path=field_path,
                            error_type="required_field_empty",
                            message=f"Required field '{field_name}' is empty",
                            expected="non-empty",
                            actual="empty",
                        )
                    )
                    continue

            if not self._check_type(value, field_schema.type):
                errors.append(
                    ValidationErrorItem(
                        path=field_path,
                        error_type="type_mismatch",
                        message=(
                            f"Field '{field_path}' expected type '{field_schema.type.value}' "
                            f"but got '{type(value).__name__}'"
                        ),
                        expected=field_schema.type.value,
                        actual=type(value).__name__,
                    )
                )
                if field_schema.type == FieldType.OBJECT and field_schema.properties:
                    self._report_nested_required_missing(
                        parent_path=field_path,
                        properties=field_schema.properties,
                        errors=errors,
                    )
                continue

            if field_schema.type in (FieldType.INTEGER, FieldType.FLOAT):
                self._validate_numeric_range(
                    value=value,
                    field_schema=field_schema,
                    field_path=field_path,
                    errors=errors,
                )

            if field_schema.type == FieldType.STRING:
                self._validate_string_length(
                    value=value,
                    field_schema=field_schema,
                    field_path=field_path,
                    errors=errors,
                )

            if field_schema.type == FieldType.LIST and field_schema.items is not None:
                self._validate_list(
                    value=value,
                    item_schema=field_schema.items,
                    field_path=field_path,
                    depth=depth + 1,
                    errors=errors,
                )

            if field_schema.type == FieldType.OBJECT and field_schema.properties is not None:
                self._validate_object(
                    data=value,
                    properties=field_schema.properties,
                    path=field_path,
                    depth=depth + 1,
                    errors=errors,
                )

        for field_name in data:
            if field_name in properties:
                continue
            field_path = f"{path}.{field_name}" if path else field_name
            value = data[field_name]
            if isinstance(value, dict):
                self._check_depth_for_unknown_object(
                    data=value,
                    path=field_path,
                    depth=depth + 1,
                    errors=errors,
                )
            elif isinstance(value, list):
                self._check_depth_for_unknown_list(
                    value=value,
                    path=field_path,
                    depth=depth + 1,
                    errors=errors,
                )

    def _check_depth_for_unknown_object(
        self,
        data: dict[str, Any],
        path: str,
        depth: int,
        errors: list[ValidationErrorItem],
    ) -> None:
        if depth > self._schema.max_depth:
            errors.append(
                ValidationErrorItem(
                    path=path,
                    error_type="max_depth_exceeded",
                    message=f"Maximum nesting depth of {self._schema.max_depth} exceeded",
                    expected=str(self._schema.max_depth),
                    actual=str(depth),
                )
            )
            return
        for key, value in data.items():
            child_path = f"{path}.{key}"
            if isinstance(value, dict):
                self._check_depth_for_unknown_object(
                    data=value,
                    path=child_path,
                    depth=depth + 1,
                    errors=errors,
                )
            elif isinstance(value, list):
                self._check_depth_for_unknown_list(
                    value=value,
                    path=child_path,
                    depth=depth + 1,
                    errors=errors,
                )

    def _check_depth_for_unknown_list(
        self,
        value: list[Any],
        path: str,
        depth: int,
        errors: list[ValidationErrorItem],
    ) -> None:
        if depth > self._schema.max_depth:
            errors.append(
                ValidationErrorItem(
                    path=path,
                    error_type="max_depth_exceeded",
                    message=f"Maximum nesting depth of {self._schema.max_depth} exceeded",
                    expected=str(self._schema.max_depth),
                    actual=str(depth),
                )
            )
            return
        for idx, item in enumerate(value):
            item_path = f"{path}[{idx}]"
            if isinstance(item, dict):
                self._check_depth_for_unknown_object(
                    data=item,
                    path=item_path,
                    depth=depth + 1,
                    errors=errors,
                )
            elif isinstance(item, list):
                self._check_depth_for_unknown_list(
                    value=item,
                    path=item_path,
                    depth=depth + 1,
                    errors=errors,
                )

    def _report_nested_required_missing(
        self,
        parent_path: str,
        properties: dict[str, FieldSchema],
        errors: list[ValidationErrorItem],
    ) -> None:
        for field_name, field_schema in properties.items():
            field_path = f"{parent_path}.{field_name}"
            if field_schema.required:
                errors.append(
                    ValidationErrorItem(
                        path=field_path,
                        error_type="required_field_missing",
                        message=f"Required field '{field_name}' is missing (parent object missing)",
                        expected="present",
                        actual="missing",
                    )
                )
            if field_schema.type == FieldType.OBJECT and field_schema.properties:
                self._report_nested_required_missing(
                    parent_path=field_path,
                    properties=field_schema.properties,
                    errors=errors,
                )

    def _check_type(self, value: Any, expected_type: FieldType) -> bool:
        if expected_type == FieldType.STRING:
            return isinstance(value, str)
        elif expected_type == FieldType.INTEGER:
            return isinstance(value, int) and not isinstance(value, bool)
        elif expected_type == FieldType.FLOAT:
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        elif expected_type == FieldType.BOOLEAN:
            return isinstance(value, bool)
        elif expected_type == FieldType.LIST:
            return isinstance(value, list)
        elif expected_type == FieldType.OBJECT:
            return isinstance(value, dict)
        return False

    def _validate_numeric_range(
        self,
        value: int | float,
        field_schema: FieldSchema,
        field_path: str,
        errors: list[ValidationErrorItem],
    ) -> None:
        has_min = field_schema.min_value is not None
        has_max = field_schema.max_value is not None
        if has_min and has_max:
            range_str = f"[{field_schema.min_value}, {field_schema.max_value}]"
        elif has_min:
            range_str = f"[{field_schema.min_value}, +∞)"
        elif has_max:
            range_str = f"(-∞, {field_schema.max_value}]"
        else:
            range_str = "(-∞, +∞)"

        if has_min and value < field_schema.min_value:
            errors.append(
                ValidationErrorItem(
                    path=field_path,
                    error_type="value_out_of_range",
                    message=(
                        f"Value {value} is less than minimum {field_schema.min_value} "
                        f"(allowed range: {range_str}, current value: {value})"
                    ),
                    expected=range_str,
                    actual=str(value),
                )
            )
        if has_max and value > field_schema.max_value:
            errors.append(
                ValidationErrorItem(
                    path=field_path,
                    error_type="value_out_of_range",
                    message=(
                        f"Value {value} is greater than maximum {field_schema.max_value} "
                        f"(allowed range: {range_str}, current value: {value})"
                    ),
                    expected=range_str,
                    actual=str(value),
                )
            )

    def _validate_string_length(
        self,
        value: str,
        field_schema: FieldSchema,
        field_path: str,
        errors: list[ValidationErrorItem],
    ) -> None:
        length = len(value)
        has_min = field_schema.min_length is not None
        has_max = field_schema.max_length is not None
        if has_min and has_max:
            range_str = f"[{field_schema.min_length}, {field_schema.max_length}]"
        elif has_min:
            range_str = f"[{field_schema.min_length}, +∞)"
        elif has_max:
            range_str = f"[0, {field_schema.max_length}]"
        else:
            range_str = "[0, +∞)"

        if has_min and length < field_schema.min_length:
            errors.append(
                ValidationErrorItem(
                    path=field_path,
                    error_type="length_out_of_range",
                    message=(
                        f"String length {length} is less than minimum {field_schema.min_length} "
                        f"(allowed length range: {range_str}, actual length: {length})"
                    ),
                    expected=range_str,
                    actual=f"length={length}",
                )
            )
        if has_max and length > field_schema.max_length:
            errors.append(
                ValidationErrorItem(
                    path=field_path,
                    error_type="length_out_of_range",
                    message=(
                        f"String length {length} is greater than maximum {field_schema.max_length} "
                        f"(allowed length range: {range_str}, actual length: {length})"
                    ),
                    expected=range_str,
                    actual=f"length={length}",
                )
            )

    def _validate_list(
        self,
        value: list[Any],
        item_schema: FieldSchema,
        field_path: str,
        depth: int,
        errors: list[ValidationErrorItem],
    ) -> None:
        for idx, item in enumerate(value):
            item_path = f"{field_path}[{idx}]"
            if not self._check_type(item, item_schema.type):
                errors.append(
                    ValidationErrorItem(
                        path=item_path,
                        error_type="type_mismatch",
                        message=(
                            f"Expected type '{item_schema.type.value}' "
                            f"but got '{type(item).__name__}'"
                        ),
                        expected=item_schema.type.value,
                        actual=type(item).__name__,
                    )
                )
                continue

            if item_schema.type in (FieldType.INTEGER, FieldType.FLOAT):
                self._validate_numeric_range(
                    value=item,
                    field_schema=item_schema,
                    field_path=item_path,
                    errors=errors,
                )

            if item_schema.type == FieldType.STRING:
                self._validate_string_length(
                    value=item,
                    field_schema=item_schema,
                    field_path=item_path,
                    errors=errors,
                )

            if item_schema.type == FieldType.LIST and item_schema.items is not None:
                self._validate_list(
                    value=item,
                    item_schema=item_schema.items,
                    field_path=item_path,
                    depth=depth + 1,
                    errors=errors,
                )

            if item_schema.type == FieldType.OBJECT and item_schema.properties is not None:
                self._validate_object(
                    data=item,
                    properties=item_schema.properties,
                    path=item_path,
                    depth=depth + 1,
                    errors=errors,
                )


__all__ = [
    "SchemaValidator",
]
