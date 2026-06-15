# Dedup 记录去重引擎

本模块提供基于内存数据结构的记录去重引擎，支持精确匹配去重、模糊匹配去重以及冲突字段合并，
适用于数据清洗、记录整合等场景。

## 模块功能

- **精确匹配去重**：支持配置一个或多个字段作为匹配键，按键值分组识别重复记录
- **模糊匹配去重**：基于编辑距离的相似度计算，支持多字段加权和阈值配置
- **传递性分组**：使用并查集（Union-Find）算法处理 A-B、B-C 的传递性重复问题
- **冲突合并策略**：提供多种字段冲突解决策略，支持按字段定制策略
- **混合模式**：支持精确匹配与模糊匹配组合使用，先按精确键分组再在组内模糊匹配

## 核心类与模块

### `DedupEngine`

去重引擎主类，整合精确匹配、模糊匹配和冲突合并功能。

主要方法：
- `add_record(record)`：添加单条记录
- `add_records(records)`：批量添加记录
- `clear()`：清空所有记录
- `dedup()`：执行去重，返回 `DedupResult`

主要配置参数：

| 参数 | 类型 | 说明 |
|------|------|------|
| `exact_match_keys` | `list[str] \| None` | 精确匹配的字段列表 |
| `use_fuzzy` | `bool` | 是否启用模糊匹配 |
| `fuzzy_fields` | `list[str] \| None` | 参与模糊匹配的字段 |
| `fuzzy_threshold` | `float` | 模糊匹配相似度阈值 (0, 1]，默认 0.8 |
| `fuzzy_field_weights` | `dict[str, float] \| None` | 各字段的权重 |
| `merge_strategy` | `str` | 默认合并策略，默认 `first` |
| `custom_merge` | `MergeFunction \| None` | 自定义合并函数 |
| `field_merge_strategies` | `dict[str, str] \| None` | 按字段指定合并策略 |
| `fallback_merge_strategy` | `str` | 兜底合并策略，默认 `last` |
| `record_selection_strategy` | `str` | 记录级保留策略，默认 `merge` |
| `record_selection_field` | `str \| None` | 按字段保留时的参考字段 |
| `record_selection_desc` | `bool` | 按字段保留时是否降序，默认 `True` |

### 记录级保留策略

当去重组内存在多条重复记录时，除了字段级冲突合并（`merge`）外，还可以选择直接保留组内某一条完整记录：

| 策略常量 | 说明 |
|----------|------|
| `KEEP_MERGE` | 字段级冲突合并（默认） |
| `KEEP_FIRST` | 保留组内最早出现的记录 |
| `KEEP_LAST` | 保留组内最后出现的记录 |
| `KEEP_MOST_COMPLETE` | 保留非空字段最多的记录 |
| `KEEP_BY_FIELD` | 按指定字段排序后保留首条（需配合 `record_selection_field` 使用） |

**示例：保留字段最完整的一条**

```python
from solocoder_py.dedup import DedupEngine, KEEP_MOST_COMPLETE

engine = DedupEngine(
    exact_match_keys=["id"],
    record_selection_strategy=KEEP_MOST_COMPLETE,
)
```

**示例：按更新时间保留最新一条**

```python
from solocoder_py.dedup import DedupEngine, KEEP_BY_FIELD

engine = DedupEngine(
    exact_match_keys=["user_id"],
    record_selection_strategy=KEEP_BY_FIELD,
    record_selection_field="updated_at",
    record_selection_desc=True,
)
```

### 数据模型

- `Record`：记录类型，别名 `dict[str, Any]`
- `DedupGroup`：去重分组，包含记录列表、原始索引、匹配得分等
- `DedupResult`：去重结果，包含唯一记录、分组、统计信息、兜底字段信息
  - `unique_records`：去重后的唯一记录列表
  - `groups`：所有分组列表
  - `total_input` / `total_unique` / `total_duplicates`：统计信息
  - `fallback_fields`：字典，key 为组索引，value 为该组使用兜底策略的字段列表
- `MergeResult`：合并结果，包含合并后的记录、冲突字段列表、成功合并字段列表、兜底字段列表
  - `record`：合并后的记录
  - `conflict_fields`：存在冲突的字段列表
  - `merged_fields`：成功应用合并策略的字段列表
  - `fallback_fields`：使用兜底策略的字段列表（调用方可感知哪些字段走了兜底）

### 子模块

- `exact_matcher`：精确匹配分组与保留策略
- `fuzzy_matcher`：模糊匹配、相似度计算、并查集算法
- `merge_strategies`：冲突合并策略实现
- `exceptions`：异常类定义

## 精确匹配与模糊匹配的协作方式

引擎支持三种工作模式：

### 1. 仅精确匹配

配置 `exact_match_keys` 即可。引擎按指定字段的组合键将记录分组，
同一组内的记录视为精确重复。

```python
engine = DedupEngine(exact_match_keys=["order_id"])
```

### 2. 仅模糊匹配

设置 `use_fuzzy=True` 并配置 `fuzzy_fields`。引擎对所有记录两两计算相似度，
超过阈值的记录对通过并查集算法聚合成组。

```python
engine = DedupEngine(
    use_fuzzy=True,
    fuzzy_fields=["name", "email"],
    fuzzy_threshold=0.8,
)
```

### 3. 混合模式

同时配置精确匹配键和模糊匹配。引擎先按精确键进行粗分组，
然后在每个精确组内部执行模糊匹配，进行更细粒度的去重。

```python
engine = DedupEngine(
    exact_match_keys=["city"],
    use_fuzzy=True,
    fuzzy_fields=["name"],
    fuzzy_threshold=0.7,
)
```

**协作流程**：
1. 先用 `exact_match_keys` 将记录分成若干精确组
2. 对每个精确组内的记录执行模糊匹配
3. 不同精确组之间的记录不会被模糊匹配到一起

这种模式适用于需要先按某个维度分区，再在分区内进行模糊去重的场景。

## 传递性分组策略

模糊匹配采用并查集（Union-Find）算法处理传递性问题：

- 若 A 匹配 B（相似度 ≥ 阈值），且 B 匹配 C，则 A、B、C 被分到同一组
- 即使 A 和 C 的相似度低于阈值，只要存在传递链，它们仍属同一组
- 每组的 `match_score` 为组内所有匹配对得分的平均值
- `fuzzy_pairs` 字段记录组内所有直接匹配的记录对

## 冲突合并策略

### 可用策略

| 策略名 | 说明 |
|--------|------|
| `first` | 保留组内第一条记录的值（默认） |
| `last` | 保留组内最后一条记录的值 |
| `longest_string` | 保留最长的字符串值 |
| `most_common` | 保留出现次数最多的值 |
| `first_non_empty` | 保留第一个非空（非 None/空字符串/空容器）的值 |
| `custom` | 使用自定义合并函数 |

### 策略优先级

冲突字段的合并策略按以下优先级确定：

1. **字段级策略**：`field_merge_strategies` 中为该字段指定的策略（最高优先级）
2. **全局默认策略**：`merge_strategy` 参数指定的默认策略
3. **兜底策略**：`fallback_merge_strategy`，当指定策略不可用时的回退方案

### 兜底策略与可观测性

当以下情况发生时，合并会自动回退到 `fallback_merge_strategy`：
- 指定 `custom` 策略但 `custom_merge` 函数抛出异常
- 指定 `custom` 策略但 `custom_merge` 为 `None`
- 指定的策略名称不存在
- 策略 resolver 执行时抛出异常

使用兜底策略的字段会被记录在 `MergeResult.fallback_fields` 列表中，调用方可通过该字段感知哪些字段走了兜底逻辑。

```python
from solocoder_py.dedup import DedupGroup, merge_group, STRATEGY_CUSTOM

def bad_merge(field, values):
    raise ValueError("oops")

group = DedupGroup(
    records=[{"id": 1, "name": "A"}, {"id": 1, "name": "B"}],
    indices=[0, 1],
    is_exact=True,
)
result = merge_group(group, strategy=STRATEGY_CUSTOM, custom_merge=bad_merge)
print(result.fallback_fields)  # ["id", "name"]
```

### 自定义合并函数

自定义函数签名：`(field_name: str, values: list[Any]) -> Any`

```python
def sum_amount(field, values):
    if field == "amount":
        return sum(v for v in values if v is not None)
    return values[0]

engine = DedupEngine(
    exact_match_keys=["order_id"],
    merge_strategy="custom",
    custom_merge=sum_amount,
)
```

## 使用示例

### 基本精确去重

```python
from solocoder_py.dedup import DedupEngine

engine = DedupEngine(exact_match_keys=["name", "phone"])
engine.add_records([
    {"name": "张三", "phone": "13800138000", "email": "zhang@a.com"},
    {"name": "张三", "phone": "13800138000", "email": "zhang@b.com"},
    {"name": "李四", "phone": "13900139000", "email": "li@c.com"},
])

result = engine.dedup()
print(f"输入: {result.total_input}, 唯一: {result.total_unique}, 重复: {result.total_duplicates}")
```

### 模糊去重

```python
from solocoder_py.dedup import DedupEngine, STRATEGY_LONGEST_STRING

engine = DedupEngine(
    use_fuzzy=True,
    fuzzy_fields=["name", "address"],
    fuzzy_threshold=0.75,
    fuzzy_field_weights={"name": 2, "address": 1},
    merge_strategy=STRATEGY_LONGEST_STRING,
)

engine.add_records([
    {"name": "阿里巴巴", "address": "杭州市文一西路"},
    {"name": "阿里吧吧", "address": "杭州市文一西路969号"},
    {"name": "腾讯", "address": "深圳市科技园"},
])

result = engine.dedup()
for group in result.groups:
    if len(group.records) > 1:
        print(f"发现模糊重复组，匹配度: {group.match_score:.2f}")
        for r in group.records:
            print(f"  - {r['name']}")
```

### 混合模式 + 字段级策略

```python
from solocoder_py.dedup import (
    DedupEngine,
    STRATEGY_LAST,
    STRATEGY_LONGEST_STRING,
    STRATEGY_MOST_COMMON,
)

engine = DedupEngine(
    exact_match_keys=["dept"],
    use_fuzzy=True,
    fuzzy_fields=["name"],
    fuzzy_threshold=0.6,
    merge_strategy=STRATEGY_LAST,
    field_merge_strategies={
        "name": STRATEGY_LONGEST_STRING,
        "title": STRATEGY_MOST_COMMON,
    },
)
```

### 自定义合并

```python
from solocoder_py.dedup import DedupEngine, STRATEGY_CUSTOM

def merge_tags(field, values):
    if field == "tags":
        merged = set()
        for v in values:
            if isinstance(v, list):
                merged.update(v)
        return sorted(merged)
    return values[0]

engine = DedupEngine(
    exact_match_keys=["user_id"],
    merge_strategy=STRATEGY_CUSTOM,
    custom_merge=merge_tags,
)
```

## 异常说明

- `InvalidConfigError`：配置无效
- `EmptyMatchKeysError`：匹配键为空
- `InvalidThresholdError`：阈值无效
- `UnknownStrategyError`：未知的合并策略
- `MergeConflictError`：合并冲突错误
