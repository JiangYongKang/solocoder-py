# Counter 模块 - 多维计数器聚合域

本模块实现了一个基于内存数据结构的**多维层级计数器聚合系统**，支持树形维度结构下的计数增量、层级聚合查询、分布式合并上报和维度路径校验。

## 模块功能

- **层级维度展开**：每次计数增量携带完整的维度路径，系统自动将增量同时记录到该路径的每一层级节点上。
- **按层级聚合查询**：可查询任意层级的聚合计数，支持子节点列表查询。
- **合并上报**：支持将多个相同维度结构的计数器实例进行合并，适用于分布式场景下的中心汇总。
- **维度路径校验**：添加计数时严格校验维度路径是否符合预定义的层级结构，拒绝跳层或深度不符的路径。
- **线程安全**：所有操作均支持并发调用，内部使用可重入锁保证数据一致性。
- **状态序列化**：支持获取和恢复计数器完整状态，便于持久化和跨进程传输。

## 核心类职责

### MultiDimCounter

多维计数器核心类，负责计数的增量更新、聚合查询、合并和路径校验。

| 方法 | 描述 |
|------|------|
| `increment(path, delta=1)` | 对指定完整维度路径增加计数，自动向上级联展开 |
| `decrement(path, delta=1)` | 对指定完整维度路径减少计数，自动向上级联展开 |
| `query(path)` | 查询指定维度路径的聚合值，不存在则返回 0 |
| `query_children(path="")` | 查询指定路径下直接子节点的计数字典 |
| `merge(other)` | 将另一个相同结构的计数器合并到当前实例 |
| `total()` | 返回所有顶级维度的计数总和 |
| `get_state()` | 获取计数器状态快照（深拷贝） |
| `from_state(state)` | 从状态快照恢复计数器实例（类方法） |
| `all_paths()` | 返回所有存在计数的维度路径列表 |

### DimensionSchema

维度模式定义类，描述计数器的层级结构。

| 属性/方法 | 描述 |
|-----------|------|
| `levels` | 层级名称列表，按从顶层到底层的顺序排列 |
| `max_depth` | 最大层级深度（即 `levels` 的长度） |
| `validate_path(path_parts)` | 校验路径段列表是否符合模式 |
| `is_full_path(path_parts)` | 判断路径是否为完整路径（达到最大深度） |
| `level_name(depth)` | 获取指定深度的层级名称 |

### CounterState

计数器状态数据类，用于状态序列化和恢复。

| 属性 | 描述 |
|------|------|
| `schema` | 维度模式 |
| `counts` | 维度路径元组到计数值的映射字典 |
| `total()` | 所有顶级维度的计数总和 |

## 层级维度展开模型

计数器使用树形层级维度结构。以三级维度"数据中心 → 主机 → 服务"为例：

```
                          总计 (total)
                              │
           ┌──────────────────┴──────────────────┐
        dc-east (9)                          dc-west (20)
           │                                     │
     ┌─────┴─────┐                         host-01 (20)
  host-01 (5)  host-02 (4)                       │
     │             │                         service-b (20)
  ┌──┴──┐       service-a (4)
  │     │
svc-a svc-b
 (3)   (2)
```

**展开规则**：当对完整路径 `dc-east/host-01/api-service` 增加 5 时，计数会同时加到该路径的所有祖先节点上：

- `dc-east/host-01/api-service` (叶子节点) → +5
- `dc-east/host-01` (主机层) → +5
- `dc-east` (数据中心层) → +5

这意味着每一层节点的计数值都等于其所有子节点的计数之和，查询任意层级都可以直接获得该层的聚合值。

**路径格式**：使用 `/` 作为层级分隔符，例如 `dc-east/host-01/api-service`。

## 合并上报机制

合并操作用于分布式场景下的计数汇总。多个节点各自独立计数，最终在中心节点合并得到全局统计。

```
节点 A (dc-east/host-01/svc: 3)
节点 B (dc-east/host-01/svc: 5)
    │         │
    └───┬─────┘
        │
        ▼
合并结果 (dc-east/host-01/svc: 8)
```

**合并规则**：
1. 两个计数器必须具有**完全相同**的维度模式（层级名称和数量一致），否则抛出 `DimensionStructureMismatchError`
2. 对于相同的维度路径，计数值**相加**
3. 只存在于一个计数器中的路径，直接保留其计数值
4. 合并操作修改当前实例，不影响被合并的实例

合并操作满足以下数学性质：
- **交换律**：`A.merge(B)` 和 `B.merge(A)` 最终值相同（但各自修改的对象不同）
- **结合律**：连续合并多个计数器的结果与顺序无关

## 维度路径校验规则

### 增量操作（increment / decrement）

增量操作必须使用**完整维度路径**，即路径深度必须等于模式的最大深度。

| 情况 | 结果 |
|------|------|
| 路径深度 = max_depth | 允许 |
| 路径深度 < max_depth（跳层/部分路径） | 拒绝，抛出 `DimensionPathError` |
| 路径深度 > max_depth | 拒绝，抛出 `DimensionPathError` |
| 空路径或空段 | 拒绝，抛出 `DimensionPathError` |
| 非字符串路径 | 拒绝，抛出 `DimensionPathError` |

**为什么增量必须使用完整路径？**
因为跳层路径（如只给 `dc-east/api-service` 而跳过 host 层）具有歧义——系统无法确定新增的计数应该归入哪个主机。只有完整路径才能唯一确定计数在维度树中的位置，并正确向上聚合。

### 查询操作（query / query_children）

查询操作较为宽松，可以查询任意层级（1 ~ max_depth）的路径。

| 情况 | 结果 |
|------|------|
| 路径深度在 1 ~ max_depth 之间 | 正常查询，不存在则返回 0 |
| 路径深度 > max_depth | 返回 0（视为无效路径） |
| 路径存在但无数据 | 返回 0 |

## 线程安全

所有公共方法均为线程安全：
- 内部使用 `threading.RLock` 可重入锁
- 写入操作（`increment`、`decrement`、`merge`）在锁保护下执行
- 读取操作（`query`、`total`、`get_state` 等）也在锁保护下执行，保证读取一致性
- `merge` 操作会同时获取 self 和 other 的锁

## 使用示例

### 基本使用

```python
from solocoder_py.counter import MultiDimCounter

# 创建三级维度计数器：数据中心 -> 主机 -> 服务
counter = MultiDimCounter(levels=["datacenter", "host", "service"])

# 增加计数（必须使用完整路径）
counter.increment("dc-east/host-01/api-service", 5)
counter.increment("dc-east/host-01/web-service", 3)
counter.increment("dc-east/host-02/api-service", 4)
counter.increment("dc-west/host-01/api-service", 10)

# 查询具体服务的计数
print(counter.query("dc-east/host-01/api-service"))  # 5

# 查询主机级聚合
print(counter.query("dc-east/host-01"))  # 8 (5 + 3)

# 查询数据中心级聚合
print(counter.query("dc-east"))  # 12 (5 + 3 + 4)

# 查询全部总计
print(counter.total())  # 22 (12 + 10)
```

### 查询子节点

```python
# 查询所有数据中心
children = counter.query_children()
# {"dc-east": 12, "dc-west": 10}

# 查询 dc-east 下的所有主机
hosts = counter.query_children("dc-east")
# {"host-01": 8, "host-02": 4}
```

### 合并上报

```python
from solocoder_py.counter import MultiDimCounter

# 模拟两个分布式节点
node_a = MultiDimCounter(levels=["dc", "host", "service"])
node_b = MultiDimCounter(levels=["dc", "host", "service"])

node_a.increment("dc-east/host-01/svc", 10)
node_b.increment("dc-east/host-01/svc", 15)
node_b.increment("dc-west/host-02/svc", 20)

# 在中心节点合并
central = MultiDimCounter(levels=["dc", "host", "service"])
central.merge(node_a)
central.merge(node_b)

print(central.query("dc-east/host-01/svc"))  # 25 (10 + 15)
print(central.total())  # 45 (25 + 20)
```

### 状态序列化

```python
from solocoder_py.counter import MultiDimCounter

counter = MultiDimCounter(levels=["a", "b"])
counter.increment("x/y", 42)

# 保存状态
state = counter.get_state()

# 恢复状态
restored = MultiDimCounter.from_state(state)
print(restored.query("x/y"))  # 42
```

### 路径校验

```python
from solocoder_py.counter import MultiDimCounter, DimensionPathError

counter = MultiDimCounter(levels=["dc", "host", "service"])

# 完整路径 - 允许
counter.increment("dc-east/host-01/svc")

# 跳层路径 - 拒绝
try:
    counter.increment("dc-east/svc")  # 缺少 host 层
except DimensionPathError as e:
    print(f"拒绝: {e}")

# 顶级路径 - 拒绝（增量必须完整路径）
try:
    counter.increment("dc-east")
except DimensionPathError as e:
    print(f"拒绝: {e}")

# 查询可以使用任意层级
print(counter.query("dc-east"))  # 0（无数据时返回零）
```

### 单层级维度

```python
from solocoder_py.counter import MultiDimCounter

# 单层级计数器（无下级）
counter = MultiDimCounter(levels=["region"])
counter.increment("us-east", 100)
counter.increment("us-west", 200)

print(counter.query("us-east"))  # 100
print(counter.total())  # 300
```

### 负数与钳位传播策略

计数器的计数值不会低于零。当负增量（或减量操作）导致某叶子节点的计数值变为负数时，该节点的值会被**钳位为 0**。

#### 钳位传播机制

钳位操作采用**叶子优先、实际变化量传播**的策略，确保所有祖先节点的聚合值始终等于其子节点计数值之和：

1. 先根据叶子节点的旧值和 delta 计算新值：`new_leaf = max(old_leaf + delta, 0)`
2. 计算本次操作的**实际净变化量**：`actual_delta = new_leaf - old_leaf`
3. 将 `actual_delta`（而非原始 delta）同步累加到该叶子路径上的所有祖先节点

这保证了当父节点有多个叶子子节点时，对某个叶子的超额减量不会影响其他叶子的贡献，父节点及更上层祖先始终等于所有子节点之和。

```python
from solocoder_py.counter import MultiDimCounter

counter = MultiDimCounter(levels=["dc", "host", "service"])
counter.increment("dc-east/host-01/svc-a", 10)
counter.increment("dc-east/host-01/svc-b", 5)

# 对 svc-a 做超额减量，触发钳位
counter.decrement("dc-east/host-01/svc-a", 12)
# svc-a 被钳位为 0，实际减少量为 10（而非 12）
print(counter.query("dc-east/host-01/svc-a"))  # 0
print(counter.query("dc-east/host-01/svc-b"))  # 5
# host-01 聚合值 = 0 + 5 = 5（祖先节点使用实际变化量 -10 而非原始 -12）
print(counter.query("dc-east/host-01"))        # 5
print(counter.query("dc-east"))                # 5
print(counter.total())                         # 5
```

#### 常规减量（未触发钳位）

```python
counter = MultiDimCounter(levels=["a", "b"])
counter.increment("x/y", 5)

# 正常减少（未触及零边界），实际变化量等于 delta
counter.decrement("x/y", 2)
print(counter.query("x/y"))  # 3
print(counter.query("x"))    # 3
```
