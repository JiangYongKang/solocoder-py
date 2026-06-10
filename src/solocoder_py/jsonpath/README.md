# JSONPath 查询模块

本模块实现了 JSONPath 查询引擎，使用内存数据结构模拟数据源，支持对 Python 字典/列表进行灵活的路径查询。

---

## 模块功能

| 功能 | 描述 |
|------|------|
| 字段选择 | 支持点号 (`$.field`) 和方括号 (`$['field']` / `$["field"]`) 语法访问对象字段 |
| 数组下标选择 | 支持按数字下标 (`[0]`) 和负数下标 (`[-1]`) 访问数组元素 |
| 通配符选择 | 使用星号 (`*`) 选择对象的所有子字段或数组的所有元素 |
| 递归下降搜索 | 使用双点号 (`..`) 在整个文档树中递归搜索指定字段名 |
| 多结果集合返回 | 查询结果统一以列表形式返回，保持文档中的原始顺序 |

---

## 核心类职责

### JSONPathQuery

查询引擎主类，接收数据源并在其上执行路径查询。

| 方法 | 描述 |
|------|------|
| `__init__(data)` | 构造查询器，绑定数据源 |
| `query(path)` | 执行 JSONPath 查询，返回结果列表 |

### JSONPathParser

路径解析器，将 JSONPath 字符串解析为段（Segment）序列。

| 类 | 描述 |
|----|------|
| `Segment` | 表示路径中的一个段，包含段类型、字段名、下标等信息 |
| `SegmentType` | 段类型枚举：`ROOT`、`CHILD`、`INDEX`、`WILDCARD`、`RECURSIVE` |

### 异常类

| 异常类 | 描述 |
|--------|------|
| `JSONPathError` | 模块基础异常 |
| `InvalidPathError` | 路径语法错误（空路径、缺少字段名等） |
| `UnexpectedTokenError` | 遇到非预期字符（如未闭合的方括号） |

### 便捷函数

| 函数 | 描述 |
|------|------|
| `jsonpath(data, path)` | 一次性查询快捷函数，等价于 `JSONPathQuery(data).query(path)` |

---

## 支持的 JSONPath 语法规范

| 语法 | 含义 | 示例 |
|------|------|------|
| `$` | 根节点引用 | `$` |
| `.field` | 子字段选择（点号语法） | `$.store.name` |
| `['field']` | 子字段选择（单引号方括号语法） | `$['store']['name']` |
| `["field"]` | 子字段选择（双引号方括号语法） | `$["store"]["name"]` |
| `[index]` | 数组下标选择 | `$.items[0]` |
| `[-index]` | 数组负数下标（从末尾计数） | `$.items[-1]` |
| `.*` 或 `[*]` | 通配符选择所有子字段/元素 | `$.store.*` |
| `..field` | 递归下降搜索字段 | `$..price` |

语法组合示例：

- `$.store.book[0].title` — 点号 + 下标 + 点号
- `$['store']['book'][2]['title']` — 纯方括号语法
- `$.store.book[*].author` — 通配符获取所有书的作者
- `$..price` — 递归搜索所有 price 字段

---

## 查询结果类型约定

1. **返回类型**：所有查询结果统一返回 `list`，即使只匹配到一个值也包含在列表中。
2. **空结果**：字段不存在、下标越界、在非数组上使用下标、在标量上使用通配符等场景均返回空列表 `[]`，不抛出异常。
3. **值保留**：结果中的值保留原始类型（`int`、`float`、`str`、`bool`、`None`、`dict`、`list`），不做类型转换。
4. **顺序保证**：多个匹配结果保持文档中的出现顺序（字典按插入顺序遍历，数组按下标顺序遍历）。

---

## 使用示例

### 示例 1：字段选择

```python
from solocoder_py.jsonpath import jsonpath

data = {"store": {"name": "BookShop", "location": "NYC"}}
result = jsonpath(data, "$.store.name")
# result == ["BookShop"]
```

### 示例 2：方括号语法与特殊字符字段

```python
from solocoder_py.jsonpath import jsonpath

data = {"key with spaces": 42, "a.b": "dotted"}
result1 = jsonpath(data, "$['key with spaces']")
# result1 == [42]
result2 = jsonpath(data, "$['a.b']")
# result2 == ["dotted"]
```

### 示例 3：数组下标选择

```python
from solocoder_py.jsonpath import jsonpath

data = {"items": [10, 20, 30]}
result = jsonpath(data, "$.items[1]")
# result == [20]

# 负数下标
result = jsonpath(data, "$.items[-1]")
# result == [30]

# 下标越界返回空列表
result = jsonpath(data, "$.items[10]")
# result == []
```

### 示例 4：通配符选择

```python
from solocoder_py.jsonpath import jsonpath

data = {"store": {"book": [
    {"title": "Book A", "price": 10},
    {"title": "Book B", "price": 20},
]}}
result = jsonpath(data, "$.store.book[*].title")
# result == ["Book A", "Book B"]

result = jsonpath(data, "$.store.*")
# result == [{"book": [...]}]
```

### 示例 5：递归下降搜索

```python
from solocoder_py.jsonpath import jsonpath

data = {
    "price": 100,
    "store": {
        "price": 50,
        "book": [
            {"price": 10},
            {"price": 20},
        ],
    },
}
result = jsonpath(data, "$..price")
# result == [100, 50, 10, 20]
```

### 示例 6：JSONPathQuery 可复用查询

```python
from solocoder_py.jsonpath import JSONPathQuery

data = {"a": {"x": 1}, "b": {"x": 2}}
q = JSONPathQuery(data)
result1 = q.query("$.a.x")
# result1 == [1]
result2 = q.query("$.b.x")
# result2 == [2]
```

### 示例 7：非法路径语法

```python
from solocoder_py.jsonpath import jsonpath, InvalidPathError

try:
    jsonpath({"a": 1}, "$.")
except InvalidPathError as e:
    print(e)  # Expected field name after '.' at position 2
```
