# Schema Validator (数据模式校验器)

一个基于内存数据结构的数据模式校验器，用于验证数据记录是否符合预定义的 Schema 规范。

## 功能概述

- **字段类型校验**: 支持字符串、整数、浮点数、布尔值、列表和对象类型的检查
- **必填约束校验**: 支持标记字段为必填，缺失或空值时报错
- **范围校验**: 数值型字段支持最小/最大值约束，字符串字段支持最小/最大长度约束
- **嵌套对象校验**: 支持嵌套对象和嵌套列表结构，递归应用校验规则
- **最大深度限制**: 可配置最大嵌套深度，防止无限递归导致性能问题

## 核心类

### SchemaValidator

校验器主类，负责执行数据校验。

- **构造参数**:
  - `schema: Schema` - 模式定义对象

- **方法**:
  - `validate(data: dict[str, Any]) -> ValidationResult` - 校验数据并返回结果

### Schema

模式定义，描述数据的结构和约束。

- **属性**:
  - `properties: dict[str, FieldSchema]` - 字段定义映射
  - `max_depth: int` - 最大嵌套深度，默认为 10

### FieldSchema

字段模式定义，描述单个字段的约束。

- **属性**:
  - `type: FieldType` - 字段类型
  - `required: bool` - 是否必填，默认为 False
  - `min_value: Optional[float]` - 数值最小值（仅数值类型有效）
  - `max_value: Optional[float]` - 数值最大值（仅数值类型有效）
  - `min_length: Optional[int]` - 字符串最小长度（仅字符串类型有效）
  - `max_length: Optional[int]` - 字符串最大长度（仅字符串类型有效）
  - `items: Optional[FieldSchema]` - 列表元素模式（仅列表类型有效）
  - `properties: Optional[dict[str, FieldSchema]]` - 对象属性模式（仅对象类型有效）

### FieldType

字段类型枚举。

- `STRING` - 字符串类型
- `INTEGER` - 整数类型
- `FLOAT` - 浮点数类型（整数也被视为合法的浮点数）
- `BOOLEAN` - 布尔值类型
- `LIST` - 列表类型
- `OBJECT` - 对象类型（字典）

### ValidationResult

校验结果。

- **属性**:
  - `valid: bool` - 校验是否通过
  - `errors: list[ValidationErrorItem]` - 错误列表

- **特殊方法**:
  - `__bool__() -> bool` - 支持直接用 `if result:` 语法判断

### ValidationErrorItem

单个校验错误项。

- **属性**:
  - `path: str` - 字段路径（如 `user.address.city` 或 `items[0].name`）
  - `error_type: str` - 错误类型
  - `message: str` - 错误描述
  - `expected: Optional[str]` - 期望值
  - `actual: Optional[str]` - 实际值

## Schema 定义语法

### 基本类型字段

```python
from solocoder_py.schema_validator import FieldSchema, FieldType

# 字符串字段
name_field = FieldSchema(type=FieldType.STRING)

# 整数字段
age_field = FieldSchema(type=FieldType.INTEGER)

# 浮点数字段
score_field = FieldSchema(type=FieldType.FLOAT)

# 布尔字段
active_field = FieldSchema(type=FieldType.BOOLEAN)
```

### 必填字段

```python
name_field = FieldSchema(type=FieldType.STRING, required=True)
```

### 数值范围约束

```python
# 年龄：0 到 150 岁
age_field = FieldSchema(
    type=FieldType.INTEGER,
    min_value=0,
    max_value=150,
)

# 分数：0.0 到 100.0
score_field = FieldSchema(
    type=FieldType.FLOAT,
    min_value=0.0,
    max_value=100.0,
)
```

### 字符串长度约束

```python
username_field = FieldSchema(
    type=FieldType.STRING,
    min_length=3,
    max_length=20,
)
```

### 列表类型

```python
# 字符串列表
tags_field = FieldSchema(
    type=FieldType.LIST,
    items=FieldSchema(type=FieldType.STRING),
)

# 整数列表，带范围约束
scores_field = FieldSchema(
    type=FieldType.LIST,
    items=FieldSchema(
        type=FieldType.INTEGER,
        min_value=0,
        max_value=100,
    ),
)
```

### 嵌套对象

```python
address_field = FieldSchema(
    type=FieldType.OBJECT,
    properties={
        "city": FieldSchema(type=FieldType.STRING, required=True),
        "zipcode": FieldSchema(
            type=FieldType.STRING,
            min_length=5,
            max_length=10,
        ),
    },
)
```

### 完整 Schema 示例

```python
from solocoder_py.schema_validator import Schema, FieldSchema, FieldType

user_schema = Schema(
    properties={
        "name": FieldSchema(type=FieldType.STRING, required=True),
        "age": FieldSchema(
            type=FieldType.INTEGER,
            required=True,
            min_value=0,
            max_value=150,
        ),
        "email": FieldSchema(type=FieldType.STRING),
        "address": FieldSchema(
            type=FieldType.OBJECT,
            required=True,
            properties={
                "city": FieldSchema(type=FieldType.STRING, required=True),
                "street": FieldSchema(type=FieldType.STRING),
                "zipcode": FieldSchema(
                    type=FieldType.STRING,
                    min_length=5,
                    max_length=10,
                ),
            },
        ),
        "tags": FieldSchema(
            type=FieldType.LIST,
            items=FieldSchema(type=FieldType.STRING, min_length=1),
        ),
    },
    max_depth=10,
)
```

## 嵌套对象的校验递归规则

### 递归校验规则

1. **对象递归**: 当遇到 `OBJECT` 类型的字段时，递归调用 `_validate_object` 方法校验子对象的属性
2. **列表递归**: 当遇到 `LIST` 类型的字段时，遍历列表元素，对每个元素应用 `items` 中定义的模式
3. **深度累加**: 每进入一层嵌套（对象或列表元素），深度计数器加 1
4. **深度检查**: 在递归入口处检查当前深度是否超过 `max_depth`，超过则报错并终止递归
5. **未知字段深度检查**: 对于未在 Schema 中定义的字段，如果是对象或列表类型，也会进行深度检查，防止恶意数据导致的深度攻击

### 深度计算规则

- 根对象深度为 0
- 每进入一层嵌套对象，深度 +1
- 每进入一层列表元素，深度 +1
- 当深度 > max_depth 时，校验失败

### 必填字段递归上报

- 如果必填的对象字段缺失或为 null，除了报告该字段本身缺失外，还会递归上报其所有子级必填字段的缺失
- 这确保了父对象缺失时，所有子级必填字段的错误都能被完整报告

## 使用示例

### 基本用法

```python
from solocoder_py.schema_validator import (
    Schema,
    SchemaValidator,
    FieldSchema,
    FieldType,
)

# 定义 Schema
schema = Schema(
    properties={
        "name": FieldSchema(type=FieldType.STRING, required=True),
        "age": FieldSchema(
            type=FieldType.INTEGER,
            required=True,
            min_value=0,
            max_value=150,
        ),
    }
)

# 创建校验器
validator = SchemaValidator(schema)

# 校验合法数据
valid_data = {"name": "Alice", "age": 30}
result = validator.validate(valid_data)
print(result.valid)  # True

# 校验非法数据
invalid_data = {"name": 123, "age": -1}
result = validator.validate(invalid_data)
print(result.valid)  # False
for error in result.errors:
    print(f"{error.path}: {error.message}")
    # name: Expected type 'string' but got 'int'
    # age: Value -1 is less than minimum 0
```

### 嵌套对象校验

```python
schema = Schema(
    properties={
        "user": FieldSchema(
            type=FieldType.OBJECT,
            required=True,
            properties={
                "name": FieldSchema(type=FieldType.STRING, required=True),
                "address": FieldSchema(
                    type=FieldType.OBJECT,
                    required=True,
                    properties={
                        "city": FieldSchema(type=FieldType.STRING, required=True),
                        "zipcode": FieldSchema(
                            type=FieldType.STRING,
                            required=True,
                            min_length=5,
                        ),
                    },
                ),
            },
        ),
    }
)

validator = SchemaValidator(schema)

data = {
    "user": {
        "name": "Alice",
        "address": {
            "city": "New York",
            "zipcode": "10001",
        },
    }
}

result = validator.validate(data)
assert result.valid
```

### 列表校验

```python
schema = Schema(
    properties={
        "scores": FieldSchema(
            type=FieldType.LIST,
            items=FieldSchema(
                type=FieldType.INTEGER,
                min_value=0,
                max_value=100,
            ),
        ),
    }
)

validator = SchemaValidator(schema)

# 合法数据
result = validator.validate({"scores": [85, 90, 95]})
assert result.valid

# 非法数据
result = validator.validate({"scores": [85, 150, "bad"]})
assert not result.valid
assert len(result.errors) == 2
```

### 最大深度限制

```python
schema = Schema(
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

validator = SchemaValidator(schema)

# 恰好达到最大深度，合法
data_valid = {
    "level1": {
        "level2": {
            "level3": {
                "value": "test",
            },
        },
    }
}
assert validator.validate(data_valid).valid

# 超出最大深度，非法
data_invalid = {
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
result = validator.validate(data_invalid)
assert not result.valid
assert result.errors[0].error_type == "max_depth_exceeded"
```

## 错误类型说明

| 错误类型 | 说明 |
|---------|------|
| `type_mismatch` | 字段类型不匹配 |
| `required_field_missing` | 必填字段缺失 |
| `required_field_null` | 必填字段为 null |
| `required_field_empty` | 必填字符串字段为空字符串 |
| `value_out_of_range` | 数值超出范围 |
| `length_out_of_range` | 字符串长度超出范围 |
| `max_depth_exceeded` | 超出最大嵌套深度 |

## 注意事项

1. **布尔值不是整数**: `True` 和 `False` 不会被视为合法的整数或浮点数
2. **整数是浮点数**: 整数值会被视为合法的浮点数（例如 `5` 可以通过 FLOAT 类型校验）
3. **空列表是合法的**: 空列表 `[]` 会通过 LIST 类型校验，因为列表本身存在，只是没有元素
4. **未知字段不校验**: 未在 Schema 中定义的字段不会进行类型、必填等校验，但会进行深度检查
5. **深度检查是全局的**: 即使字段未在 Schema 中定义，如果其嵌套深度超过限制，也会报错
