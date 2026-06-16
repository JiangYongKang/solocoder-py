# Cursor Pagination Engine

基于游标的内存分页引擎，用于高效地对内存数据集进行前后向分页查询。

## 功能特性

1. **基于游标的前后翻页**：支持"获取下一页"和"获取上一页"操作，游标包含排序字段值和分页方向信息
2. **不透明游标编码**：游标经过 Base64 + HMAC 签名编码，对客户端完全不透明，可检测篡改
3. **页大小强制上限**：内置最大页大小限制（默认 100），超过上限自动降级
4. **总数提示**：支持可选的总记录数计算，不影响分页查询本身性能
5. **多字段排序**：支持任意数量排序字段，每个字段可独立指定升序/降序
6. **游标过期机制**：可选的 TTL 配置，支持游标过期自动失效

## 核心类职责

### `CursorPaginationEngine`
分页引擎主类，负责：
- 数据源加载和排序索引构建
- 游标编码与解码（含签名验证）
- 分页查询执行（正向/反向）
- 页大小验证和降级
- 结果页元数据计算（has_next/has_prev、cursors）

### 数据模型类

| 类名 | 职责 |
|------|------|
| `SortField` | 排序字段定义，包含字段名和排序方向（ASC/DESC） |
| `PaginationConfig` | 分页配置，包含最大页大小、默认页大小、游标 TTL、密钥等 |
| `Direction` | 枚举，分页方向：`NEXT`（下一页）、`PREV`（上一页） |
| `SortOrder` | 枚举，排序方向：`ASC`（升序）、`DESC`（降序） |
| `DecodedCursor` | 解码后的游标结构，包含排序值、方向、创建时间、版本号 |
| `PageResult` | 分页结果，包含数据、游标、has_next/has_prev、总数等 |

### 异常类

| 异常类 | 抛出场景 |
|--------|----------|
| `CursorPaginationError` | 所有分页异常的基类 |
| `InvalidCursorError` | 游标格式无效或解码失败 |
| `CursorTamperedError` | 游标 HMAC 签名验证失败（被篡改） |
| `CursorExpiredError` | 游标超过 TTL 有效期 |
| `InvalidPageSizeError` | 页大小 <= 0 或类型错误 |
| `InvalidDirectionError` | 方向参数不是 `next` 或 `prev` |
| `InvalidSortFieldError` | 排序字段定义无效或为空 |

## 游标编解码机制

### 编码流程

```
原始结构 -> JSON序列化 -> Base64编码 -> (可选) HMAC-SHA256签名 -> 最终游标字符串
```

**游标内部结构（JSON payload）**：
```json
{
  "v": 1,
  "sv": [
    {"__type__": "int", "v": 42},
    {"__type__": "str", "v": "hello"}
  ],
  "d": "next",
  "t": 1718500000.0,
  "sf": [["id", "asc"], ["name", "desc"]]
}
```

字段说明：
- `v`：游标格式版本号，用于未来兼容性
- `sv`：排序字段值数组，每项为带类型标记的序列化值（支持 None/int/float/bool/str/bytes）
- `d`：该游标对应的分页方向（`next` 或 `prev`）
- `t`：游标创建时间戳（用于 TTL 检查）
- `sf`：排序字段列表（名称+方向），用于调试和兼容性检查

### 防篡改机制

当 `PaginationConfig.enable_hmac = True`（默认）时：
- 使用 HMAC-SHA256 对 Base64 编码的 payload 计算签名
- 最终游标格式：`{base64_payload}.{hmac_signature}`
- 解码时使用 `hmac.compare_digest` 进行恒时比较，防止时序攻击

### 类型序列化

为保证跨平台一致性，所有排序值在序列化时保留类型信息：
- `None` → `{"__type__": "none"}`
- `int` → `{"__type__": "int", "v": <value>}`
- `float` → `{"__type__": "float", "v": <value>}`
- `bool` → `{"__type__": "bool", "v": <value>}`
- `str` → `{"__type__": "str", "v": <value>}`
- `bytes` → `{"__type__": "bytes", "v": <base64_encoded>}`

## 使用示例

### 基本用法

```python
from solocoder_py.cursor_pagination import (
    CursorPaginationEngine,
    PaginationConfig,
    SortField,
    SortOrder,
)

# 1. 准备数据
data = [
    {"id": 1, "name": "Alice", "score": 85},
    {"id": 2, "name": "Bob", "score": 92},
    {"id": 3, "name": "Charlie", "score": 78},
    {"id": 4, "name": "David", "score": 92},
    {"id": 5, "name": "Eve", "score": 88},
]

# 2. 创建引擎（按 score 降序，再按 id 升序）
config = PaginationConfig(max_page_size=100, default_page_size=2)
engine = CursorPaginationEngine(
    data=data,
    sort_fields=[
        SortField("score", SortOrder.DESC),
        SortField("id", SortOrder.ASC),
    ],
    config=config,
)

# 3. 获取首页（第一页，2条/页）
page1 = engine.paginate(page_size=2, include_total=True)
print(f"Page 1: {len(page1.data)} items")
print(f"Total: {page1.total}")
print(f"Has next: {page1.has_next}")
print(f"End cursor: {page1.end_cursor}")

# 4. 获取下一页
page2 = engine.paginate(
    page_size=2,
    cursor=page1.end_cursor,
    direction="next",
)
print(f"Page 2: {len(page2.data)} items")

# 5. 反向翻页（返回上一页）
page_prev = engine.paginate(
    page_size=2,
    cursor=page2.start_cursor,
    direction="prev",
)
assert page_prev.data == page1.data  # 回到第一页
```

### 简化排序字段定义

```python
# 使用字符串（默认升序）
engine = CursorPaginationEngine(data=data, sort_fields=["id", "name"])

# 使用元组 (name, order)
engine = CursorPaginationEngine(
    data=data,
    sort_fields=[("score", "desc"), ("id", "asc")],
)

# 混合使用
engine = CursorPaginationEngine(
    data=data,
    sort_fields=["id", ("score", SortOrder.DESC)],
)
```

### 空数据集与边界处理

```python
# 空数据集
engine = CursorPaginationEngine(data=[], sort_fields=["id"])
page = engine.paginate(page_size=10)
assert page.data == []
assert page.has_next is False
assert page.has_prev is False
assert page.start_cursor is None
assert page.end_cursor is None

# 页大小超过上限（自动降级到上限值）
config = PaginationConfig(max_page_size=5)
engine = CursorPaginationEngine(data=large_data, sort_fields=["id"], config=config)
page = engine.paginate(page_size=1000)  # 请求 1000 条
assert page.page_size == 5  # 实际使用 5 条
assert len(page.data) <= 5
```

### 游标过期设置

```python
config = PaginationConfig(
    cursor_ttl_seconds=3600,  # 1 小时后过期
    cursor_secret="my-secret-key",
)
engine = CursorPaginationEngine(data=data, sort_fields=["id"], config=config)
```
