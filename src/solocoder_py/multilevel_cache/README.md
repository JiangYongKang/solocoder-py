# MultiLevelCache 模块

本模块提供了一个两级（L1/L2）内存缓存实现，支持读穿透回填、写直接写入、失效传播和各级独立容量淘汰策略。

## 模块功能

- **两级缓存架构**：L1（小容量、高速）+ L2（大容量、低速）的层次化缓存设计
- **读穿透回填**：L1 未命中时自动查询 L2，两级都未命中时从数据源加载并依次回填
- **写直接写入**：写入操作将新值同时写入 L1 和 L2 两级缓存；失效操作通过 `invalidate`/`delete` 执行
- **独立淘汰策略**：L1 和 L2 各自维护独立的容量限制和 LRU 淘汰策略，互不影响
- **线程安全**：内置锁机制，支持多线程并发安全访问
- **统计监控**：提供命中次数、未命中次数、数据源加载次数、淘汰次数等统计信息

## 核心类

### MultiLevelCache[K, V]

多级缓存的主 orchestrator 类，协调 L1 和 L2 缓存的交互。

**构造参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `l1_capacity` | `int` | L1 缓存容量，必须为正数且小于 L2 容量 |
| `l2_capacity` | `int` | L2 缓存容量，必须为正数且大于 L1 容量 |
| `data_source` | `Optional[DataSource[K, V]]` | 可注入的数据源，用于缓存未命中时加载数据 |

**核心方法：**

| 方法 | 说明 |
|------|------|
| `get(key: K) -> V` | 读取数据，执行 L1 → L2 → 数据源的穿透查询 |
| `set(key: K, value: V) -> None` | 将 value 同时写入 L1 和 L2 两级缓存 |
| `delete(key: K) -> bool` | 删除指定 key，返回是否删除成功 |
| `invalidate(key: K) -> None` | 失效指定 key（等同于 delete） |
| `clear() -> None` | 清空所有缓存并重置统计 |
| `has_in_l1(key: K) -> bool` | 检查 key 是否存在于 L1 |
| `has_in_l2(key: K) -> bool` | 检查 key 是否存在于 L2 |

**属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `l1_capacity` | `int` | L1 缓存容量 |
| `l2_capacity` | `int` | L2 缓存容量 |
| `l1_size` | `int` | L1 当前条目数 |
| `l2_size` | `int` | L2 当前条目数 |
| `stats` | `CacheStats` | 缓存统计信息 |

### LRUCache[K, V]

单级 LRU 缓存实现，使用 `OrderedDict` 维护访问顺序。

**构造参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `capacity` | `int` | 缓存容量，必须为正整数 |

### CacheStats

不可变数据类，封装缓存统计信息：

| 字段 | 类型 | 说明 |
|------|------|------|
| `l1_hits` | `int` | L1 命中次数 |
| `l2_hits` | `int` | L2 命中次数 |
| `l1_misses` | `int` | L1 未命中次数 |
| `l2_misses` | `int` | L2 未命中次数 |
| `data_source_loads` | `int` | 数据源加载次数 |
| `evictions_l1` | `int` | L1 淘汰次数 |
| `evictions_l2` | `int` | L2 淘汰次数 |

### DataSource[K, V]

数据源协议（Protocol），定义了缓存未命中时的数据加载接口：

```python
class DataSource(Protocol[K, V]):
    def load(self, key: K) -> V: ...
```

## 数据流

### 读穿透回填（Read-Through with Backfill）

```
get(key)
    │
    ├─→ 查询 L1 缓存
    │    ├─ 命中 → 直接返回值（更新 LRU 顺序）
    │    └─ 未命中 → 继续
    │
    ├─→ 查询 L2 缓存
    │    ├─ 命中 → 回填到 L1 → 返回值
    │    └─ 未命中 → 继续
    │
    └─→ 调用数据源 load(key)
         ├─ 成功 → 先回填 L2 → 再回填 L1 → 返回值
         └─ 失败 → 抛出 DataSourceError，不写入任何缓存
```

### 写直接写入（Write-Through）

```
set(key, value)
    │
    ├─→ 将 value 写入 L2 缓存（更新或新增）
    └─→ 将 value 写入 L1 缓存（更新或新增）
```

### 失效传播（Invalidation）

```
invalidate(key) / delete(key)
    │
    ├─→ 从 L1 缓存删除 key
    └─→ 从 L2 缓存删除 key
```

**设计说明**：`set()` 采用写透（Write-Through）策略，同时更新两级缓存，确保后续直接读取命中。当需要强制从数据源重新加载时，使用 `invalidate()` 或 `delete()` 执行失效操作。

### 独立容量淘汰

```
L1 缓存（容量小）        L2 缓存（容量大）
┌───────────────┐      ┌───────────────┐
│ OrderedDict   │      │ OrderedDict   │
│ LRU 淘汰      │      │ LRU 淘汰      │
│ 独立计数      │      │ 独立计数      │
└───────────────┘      └───────────────┘
        ↑                      ↑
        │ 互不影响             │ 互不影响
        └──────────────────────┘
```

- L1 满时只淘汰 L1 中的 LRU 条目，不影响 L2
- L2 满时只淘汰 L2 中的 LRU 条目，不影响 L1
- L1 中被淘汰的数据仍然可能存在于 L2 中，后续读取可从 L2 回填

## 使用示例

### 基本使用

```python
from solocoder_py.multilevel_cache import MultiLevelCache

class DatabaseSource:
    def __init__(self):
        self.db = {"user:1": "Alice", "user:2": "Bob"}

    def load(self, key: str) -> str:
        print(f"Loading {key} from database...")
        return self.db[key]

cache = MultiLevelCache[str, str](
    l1_capacity=10,
    l2_capacity=100,
    data_source=DatabaseSource(),
)

# 第一次读取：穿透到数据源
print(cache.get("user:1"))  # Loading user:1 from database... → Alice

# 第二次读取：L1 命中
print(cache.get("user:1"))  # Alice（无数据库查询）

# 写入更新：直接写入两级缓存，立即生效
cache.set("user:1", "Alicia")

# 读取新值：L1 直接命中，不穿透数据源
print(cache.get("user:1"))  # Alicia（无数据库查询）

# 若需强制从数据源重新加载，使用 invalidate 而非 set
cache.invalidate("user:1")
print(cache.get("user:1"))  # Loading user:1 from database... → Alicia
```

### 统计信息

```python
stats = cache.stats
print(f"L1 命中率: {stats.l1_hits / max(1, stats.l1_hits + stats.l1_misses):.2%}")
print(f"L2 命中率: {stats.l2_hits / max(1, stats.l2_hits + stats.l2_misses):.2%}")
print(f"数据源加载次数: {stats.data_source_loads}")
print(f"L1 淘汰次数: {stats.evictions_l1}")
print(f"L2 淘汰次数: {stats.evictions_l2}")
```

### 无数据源模式

```python
# 仅作为两级缓存使用，需手动填充
cache = MultiLevelCache[str, int](l1_capacity=5, l2_capacity=20)

try:
    cache.get("key")  # 抛出 DataSourceError: No data source configured
except DataSourceError:
    pass
```

## 异常类型

- `MultiLevelCacheError`：模块基异常
- `CacheLevelNotFoundError`：缓存层级未找到
- `DataSourceError`：数据源操作失败
- `InvalidCapacityError`：无效的容量配置
