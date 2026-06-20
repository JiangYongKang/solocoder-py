# json_patch

JSON Patch (RFC 6902) 引擎，基于内存数据结构操作 JSON 文档。同时提供 RFC 6901 JSON Pointer 路径解析工具。

## 核心类与模块

### `pointer` 模块 — JSON Pointer (RFC 6901)

提供 JSON Pointer 字符串的解析与求值工具：

| 函数 | 说明 |
|------|------|
| `parse(pointer)` | 将 JSON Pointer 字符串解析为路径段列表 |
| `get(doc, pointer)` | 根据 JSON Pointer 从文档中获取值 |
| `set_value(doc, pointer, value)` | 根据 JSON Pointer 在文档中替换值（不可变，返回新文档） |
| `add_value(doc, pointer, value)` | 根据 JSON Pointer 在文档中添加值，数组路径使用插入语义，`"-"` 表示追加（不可变，返回新文档） |
| `delete(doc, pointer)` | 根据 JSON Pointer 从文档中删除值（不可变，返回新文档） |

### `engine` 模块 — JSON Patch (RFC 6902)

| 函数 | 说明 |
|------|------|
| `apply(doc, operations)` | 按顺序应用操作列表，失败时抛出异常 |
| `apply_atomic(doc, operations)` | 原子化应用操作列表，任意操作失败则整个序列回滚 |

### `exceptions` 模块

| 异常类 | 说明 |
|--------|------|
| `JsonPatchError` | 所有 JSON Patch 相关异常的基类 |
| `JsonPointerError` | JSON Pointer 相关异常的基类 |
| `InvalidPointerError` | 非法的 JSON Pointer 格式 |
| `PathNotFoundError` | 指定路径在文档中不存在 |
| `PatchOperationError` | Patch 操作执行异常的基类 |
| `PatchTestFailedError` | test 操作值不匹配 |
| `UnknownOperationError` | 未知的操作类型 |
| `AddOutOfBoundsError` | add 操作的数组索引越界 |

## RFC 6902 六种操作

### add

在指定路径添加新值。如果目标路径已存在，则覆盖该值。路径指向数组时，使用 `"-"` 表示追加到末尾。

```python
from solocoder_py.json_patch import apply

doc = {"foo": "bar"}
result = apply(doc, [{"op": "add", "path": "/baz", "value": "qux"}])
# result: {"foo": "bar", "baz": "qux"}

doc = {"items": [1, 3]}
result = apply(doc, [{"op": "add", "path": "/items/-", "value": 5}])
# result: {"items": [1, 3, 5]}

doc = {"items": [1, 3]}
result = apply(doc, [{"op": "add", "path": "/items/1", "value": 2}])
# result: {"items": [1, 2, 3]}
```

### remove

删除指定路径的值。如果路径不存在则报错。

```python
doc = {"foo": "bar", "baz": "qux"}
result = apply(doc, [{"op": "remove", "path": "/baz"}])
# result: {"foo": "bar"}
```

### replace

将指定路径的现有值替换为新值。语义等价于先 remove 再 add，如果路径不存在则报错。

```python
doc = {"foo": "bar"}
result = apply(doc, [{"op": "replace", "path": "/foo", "value": "baz"}])
# result: {"foo": "baz"}
```

### copy

将 `from` 路径的值复制到 `path` 路径。如果 `from` 路径不存在则报错。复制为深拷贝。

```python
doc = {"foo": {"x": 1}, "bar": None}
result = apply(doc, [{"op": "copy", "from": "/foo", "path": "/bar"}])
# result: {"foo": {"x": 1}, "bar": {"x": 1}}
```

### move

将 `from` 路径的值移动到 `path` 路径。语义等价于先 copy 再 remove from。如果 `from` 路径不存在则报错。

```python
doc = {"foo": 1, "bar": 2}
result = apply(doc, [{"op": "move", "from": "/foo", "path": "/baz"}])
# result: {"bar": 2, "baz": 1}
```

### test

检查指定路径的值是否等于预期值。相等则通过，不等则报错。

```python
doc = {"foo": "bar"}
result = apply(doc, [{"op": "test", "path": "/foo", "value": "bar"}])
# 通过，result: {"foo": "bar"}

# 值不匹配时抛出 PatchTestFailedError
```

## RFC 6901 JSON Pointer 路径语法

JSON Pointer 使用 `/` 分隔路径段，以 `/` 开头。空字符串 `""` 表示文档根。

### 转义规则

| 转义序列 | 实际字符 | 示例 |
|----------|----------|------|
| `~0` | `~` | `/a~0b` → 键 `"a~b"` |
| `~1` | `/` | `/a~1b` → 键 `"a/b"` |

转义顺序：先处理 `~1` 再处理 `~0`（或等价地，按顺序替换 `~1` → `/`，`~0` → `~`）。

### 数组索引

路径段为数字时表示数组索引。`"-"` 特殊标记表示数组末尾（仅用于 add 操作的追加）。

```python
from solocoder_py.json_patch import pointer_get, pointer_parse

doc = {"users": [{"name": "Alice"}, {"name": "Bob"}]}
pointer_parse("/users/0/name")  # ["users", "0", "name"]
pointer_get(doc, "/users/1/name")  # "Bob"
```

## 原子序列应用与回滚机制

`apply_atomic` 函数提供原子化操作：

1. 在应用操作之前，深拷贝原始文档作为备份
2. 按顺序逐个应用操作
3. 如果任意操作失败（抛出 `PatchOperationError` 或其子类），立即停止并返回原始文档
4. 只有全部操作成功才返回修改后的文档

```python
from solocoder_py.json_patch import apply_atomic

doc = {"foo": 1}
ops = [
    {"op": "add", "path": "/bar", "value": 2},
    {"op": "test", "path": "/foo", "value": 999},  # 此操作失败
]
result = apply_atomic(doc, ops)
# result: {"foo": 1}  — 回滚到原始状态
```

而 `apply` 函数在遇到错误时直接抛出异常，不做回滚。

## 使用示例

```python
from solocoder_py.json_patch import apply, apply_atomic, pointer_get

doc = {
    "users": [
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 25},
    ]
}

ops = [
    {"op": "test", "path": "/users/0/name", "value": "Alice"},
    {"op": "replace", "path": "/users/0/age", "value": 31},
    {"op": "add", "path": "/users/-", "value": {"name": "Charlie", "age": 35}},
    {"op": "remove", "path": "/users/1/age"},
    {"op": "copy", "from": "/users/0/name", "path": "/users/1/name"},
]

result = apply(doc, ops)

# 使用指针直接读取
pointer_get(result, "/users/0/age")  # 31
```
