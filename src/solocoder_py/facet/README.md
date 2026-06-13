# Facet Search Engine

分面搜索引擎模块，使用内存数据结构实现商品或文档的多维检索与分面导航。

## 模块功能

- **布尔过滤器组合**：支持多字段过滤，字段内部取"或"逻辑，字段之间取"与"逻辑
- **数值区间分面**：支持数值型字段的区间分面统计，可配置桶（buckets）划分
- **多选下钻导航**：支持分面多勾选，即时更新搜索结果和分面计数
- **动态条目增删**：支持运行时添加/删除条目，分面计数自动更新

## 核心类职责

### FacetSearchEngine
分面搜索引擎核心类，负责：
- 管理索引数据和过滤状态
- 执行布尔过滤逻辑
- 计算分面统计
- 维护导航状态

### FacetConfig
分面字段配置类，定义：
- 字段名称
- 字段类型（分类/数值）
- 数值桶配置（仅数值字段）

### NumericBucket
数值区间桶定义：
- 区间最小值（可选）
- 区间最大值（可选）
- 桶标签

### SearchResult
搜索结果封装：
- 匹配条目总数
- 匹配条目列表
- 各分面统计结果
- 当前激活的过滤条件

### FacetResult
单个分面的统计结果：
- 字段名称
- 字段类型
- 各值的计数和选中状态

## 布尔组合逻辑

分面过滤采用"字段内 OR，字段间 AND"的组合逻辑：

```
结果 = (字段A值1 OR 字段A值2) AND (字段B值1 OR 字段B值2)
```

**示例**：
- 过滤条件：`类别=手机 AND (品牌=苹果 OR 品牌=华为)`
- 返回：所有类别为"手机"且品牌为"苹果"或"华为"的条目

## 数值区间分面策略

### 桶定义规则
- 每个数值字段需配置若干桶（buckets）
- 桶的区间为 **[min, max)**，左闭右开
- 支持无下限桶（`min=None`）和无上限桶（`max=None`）

### 边界值归属
- 左边界值（min）归属当前桶
- 右边界值（max）归属下一个桶

**示例**：
```python
buckets = [
    NumericBucket(min=None, max=1000, label="0-1000"),   # [0, 1000)
    NumericBucket(min=1000, max=3000, label="1000-3000"), # [1000, 3000)
    NumericBucket(min=3000, max=None, label="3000+"),     # [3000, +∞)
]
```
- `value = 1000` → 归属 "1000-3000" 桶
- `value = 999` → 归属 "0-1000" 桶
- `value = 3000` → 归属 "3000+" 桶

### 分面计数联动
分面计数计算时会排除当前字段自身的过滤条件，确保：
- 勾选某个分面值后，该分面的其他选项仍显示正确的可选项计数
- 用户可以看到如果取消当前选择后能获得多少结果

## 多选下钻导航

### 导航状态管理
- 激活的过滤条件存储在 `_active_filters: Dict[str, Set[Any]]` 中
- 每个字段维护一个选中值的集合
- 字段的选中值之间为 OR 关系

### 操作接口
- `add_filter(field, value)`：添加过滤条件
- `remove_filter(field, value)`：移除单个过滤值
- `clear_field_filter(field)`：清除某个字段的所有过滤
- `clear_all_filters()`：清除所有过滤条件
- `get_active_filters()`：获取当前激活的过滤条件

### 下钻流程
1. 初始搜索：无过滤条件，返回全部结果
2. 勾选分面值：添加过滤条件，结果集收缩
3. 继续勾选：进一步缩小结果范围
4. 取消勾选：结果集回退到对应状态

## 使用示例

```python
from solocoder_py.facet import (
    FacetConfig,
    FacetFieldType,
    FacetSearchEngine,
    NumericBucket,
)

# 1. 配置分面字段
configs = [
    FacetConfig(
        field_name="category",
        field_type=FacetFieldType.CATEGORICAL,
    ),
    FacetConfig(
        field_name="brand",
        field_type=FacetFieldType.CATEGORICAL,
    ),
    FacetConfig(
        field_name="price",
        field_type=FacetFieldType.NUMERIC,
        buckets=[
            NumericBucket(min=None, max=1000, label="0-1000"),
            NumericBucket(min=1000, max=3000, label="1000-3000"),
            NumericBucket(min=3000, max=None, label="3000+"),
        ],
    ),
]

# 2. 创建搜索引擎
engine = FacetSearchEngine(configs)

# 3. 添加数据条目
products = [
    {"id": "p1", "category": "手机", "brand": "苹果", "price": 5999},
    {"id": "p2", "category": "手机", "brand": "华为", "price": 4999},
    {"id": "p3", "category": "笔记本", "brand": "苹果", "price": 8999},
]
for product in products:
    engine.add_item(product)

# 4. 初始搜索
result = engine.search()
print(f"总商品数: {result.total_count}")  # 3

# 5. 添加过滤条件：类别=手机
engine.add_filter("category", "手机")
result = engine.search()
print(f"手机数量: {result.total_count}")  # 2

# 6. 添加过滤条件：品牌=苹果 OR 品牌=华为
engine.add_filter("brand", "苹果")
engine.add_filter("brand", "华为")
result = engine.search()
print(f"苹果或华为手机: {result.total_count}")  # 2

# 7. 添加数值过滤：价格 3000+
engine.add_filter("price", "3000+")
result = engine.search()
print(f"3000+的苹果/华为手机: {result.total_count}")  # 2

# 8. 查看分面统计
for facet in result.facets:
    print(f"\n{facet.field_name}:")
    for value in facet.values:
        selected = "✓" if value.selected else " "
        print(f"  {selected} {value.value}: {value.count}")

# 9. 取消过滤
engine.remove_filter("brand", "苹果")
result = engine.search()
print(f"\n移除苹果后: {result.total_count}")  # 1

# 10. 清除所有过滤
engine.clear_all_filters()
result = engine.search()
print(f"清除后: {result.total_count}")  # 3

# 11. 删除条目
engine.remove_item("p1")
result = engine.search()
print(f"删除p1后: {result.total_count}")  # 2
```

## 异常处理

| 异常类型 | 触发场景 |
|---------|---------|
| `FieldNotFoundError` | 过滤未配置的字段 |
| `ItemNotFoundError` | 删除不存在的条目 |
| `DuplicateItemError` | 添加重复ID的条目 |
| `InvalidFilterError` | 无效的过滤操作 |
| `InvalidBucketError` | 无效的桶配置 |
| `FacetError` | 通用错误（如条目缺少字段） |

## 线程安全

`FacetSearchEngine` 使用 `threading.RLock` 保证线程安全，支持多线程并发操作。
