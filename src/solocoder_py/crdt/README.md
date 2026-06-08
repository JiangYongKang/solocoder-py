# CRDT 模块

本模块实现了两类无冲突复制数据类型 (Conflict-free Replicated Data Type, CRDT)：
**PN 计数器 (Positive-Negative Counter)** 和 **OR-Set (Observed-Remove Set)**。
两者均为状态复制型 (State-based) CRDT，支持分布式环境下的最终一致性。

## 模块功能

- **PNCounter**: 支持递增和递减操作的计数器，保证在任意网络延迟和消息乱序下收敛到正确的计数值。
- **ORSet**: 支持添加和删除操作的集合，采用 add-wins 语义处理并发操作，保证并发添加的元素不会被意外删除。

## 核心类职责

### PNCounter

PN 计数器通过两个独立的 G-Counter（只增计数器）分别记录正数增量和负数增量。

| 方法 | 描述 |
|------|------|
| `increment(delta=1)` | 本地副本递增 `delta`（默认为 1），`delta` 必须非负 |
| `decrement(delta=1)` | 本地副本递减 `delta`（默认为 1），`delta` 必须非负 |
| `value()` | 返回当前计数器值，保证非负（最小值为 0） |
| `get_state()` | 获取当前副本的完整状态（正/负计数映射的深拷贝） |
| `from_state(state, replica_id=None)` | 从状态快照恢复 PNCounter 实例的工厂方法 |
| `merge(other)` | 合并另一个副本的状态到当前副本 |
| `diff(other)` | 计算当前副本相对于另一个副本的差异（见下方 diff 语义） |
| `is_ge(other)` | 判断当前副本在状态偏序上是否大于等于另一个副本 |

内部状态包含两个字典：
- `_positive: dict[str, int]` — 各副本的正增量映射
- `_negative: dict[str, int]` — 各副本的负增量映射

最终值 = `sum(_positive.values()) - sum(_negative.values())`，并与 0 取最大值。

### ORSet

观察移除集合通过为每个添加操作分配唯一标签 (unique tag) 来追踪元素的存在性，使用墓碑 (tombstone) 机制传播删除操作。

| 方法 | 描述 |
|------|------|
| `add(element)` | 添加元素到集合，生成新的唯一标签 |
| `add_all(elements)` | 批量添加多个元素 |
| `remove(element)` | 移除元素（将当前活跃标签移入墓碑集合） |
| `contains(element)` | 判断元素是否存在于集合中 |
| `value()` | 返回当前集合中的所有元素（不重复） |
| `clear()` | 清空集合中的所有元素 |
| `get_state()` | 获取当前副本的完整状态（元素→标签/墓碑映射的深拷贝） |
| `from_state(state, replica_id=None)` | 从状态快照恢复 ORSet 实例的工厂方法 |
| `merge(other)` | 合并另一个副本的状态到当前副本 |
| `diff(other)` | 计算当前副本相对于另一个副本的差异（见下方 diff 语义） |
| `is_ge(other)` | 判断当前副本在状态偏序上是否大于等于另一个副本 |

内部状态：
- `_elements: dict[Any, ORSetElement]` — 元素到 `ORSetElement` 的映射
  - `ORSetElement.tags`: 所有曾添加该元素的标签集合
  - `ORSetElement.tombstones`: 已被删除的标签集合（墓碑）

元素存在当且仅当 `alive_tags = tags - tombstones` 非空。
内部表示与 `get_state()` 导出的 `ORSetState` 使用相同的数据类型 `ORSetElement`，保证接口一致性。

## 合并规则

### PNCounter 合并

合并操作满足**交换律**、**结合律**和**幂等律**：

- 对 `_positive` 字典中的每个副本 ID，取两个副本中对应值的**最大值**
- 对 `_negative` 字典中的每个副本 ID，取两个副本中对应值的**最大值**

由于正、负计数各自单调递增，取最大值保证了合并操作的正确性和收敛性。

```
merge(A, B).positive[rid] = max(A.positive[rid], B.positive[rid])
merge(A, B).negative[rid] = max(A.negative[rid], B.negative[rid])
```

### ORSet 合并

合并操作同样满足**交换律**、**结合律**和**幂等律**：

- 对每个元素，取两个副本中该元素标签集合的**并集**
- 对每个元素，取两个副本中该元素墓碑集合的**并集**

这确保了 add-wins 语义：如果一个副本添加了元素（产生新标签），而另一个副本并发地删除了该元素（仅将它已知的旧标签加入墓碑），合并后新标签不在墓碑中，元素被保留。删除操作通过墓碑传播到所有副本。

```
merge(A, B).elements[e].tags       = A.elements[e].tags       ∪ B.elements[e].tags
merge(A, B).elements[e].tombstones = A.elements[e].tombstones ∪ B.elements[e].tombstones
alive_tags(e) = tags(e) - tombstones(e)
```

## 状态序列化与恢复

两个 CRDT 类均提供 `get_state()` 与 `from_state()` 配对的序列化能力，
用于持久化、网络传输或测试场景下创建副本快照。

- `get_state()` 返回不可变的深拷贝快照（`PNCounterState` 或 `ORSetState`）
- `from_state(state, replica_id=None)` 是类方法，从状态快照构造一个独立的新实例，
  对新实例的修改不会影响原实例

调用方无需访问对象内部私有属性即可完成状态复制。

## diff 语义

`a.diff(b)` 计算的是**副本 a 相对于副本 b 的单向差异**，即：a 有哪些变化是 b 还没观察到的。
返回结果包含以下字段：

### PNCounterDiff

| 字段 | 含义 |
|------|------|
| `added_positive` | a 中有、b 中无的正增量副本及其值 |
| `added_negative` | a 中有、b 中无的负增量副本及其值 |
| `increased_positive` | a 和 b 共有、但 a 值更大的正增量副本，格式 `(old_val, new_val)` |
| `increased_negative` | a 和 b 共有、但 a 值更大的负增量副本，格式 `(old_val, new_val)` |

### ORSetDiff

| 字段 | 含义 |
|------|------|
| `added` | a 中存在、b 中不存在的元素及其活跃标签 |
| `removed` | a 中不存在、b 中存在的元素及其活跃标签 |
| `updated` | a 和 b 均存在但活跃标签集合不同的元素，格式 `(old_tags, new_tags)` |

## 并发安全

所有实例方法均为线程安全：
- 每个对象内部持有一把 `threading.RLock` 可重入锁
- 本地更新（`increment`、`decrement`、`add`、`remove`、`clear`）在锁保护下执行
- `merge`、`diff`、`is_ge` 等涉及两个副本的方法会**同时获取 self 和 other 的锁**，
  保证两个状态快照在同一原子区间内获取，避免中间状态不一致
- `get_state()` 返回深拷贝，外部修改不会影响对象内部状态
- `from_state()` 创建独立实例，与原对象无共享可变状态

> **注意**：在极端情况下，若两个线程分别以相反顺序在两个相同对象上调用 `merge`/`diff`/`is_ge`，
> 由于使用 `RLock` 以及 Python GIL 的存在，不会发生经典死锁，但仍建议在应用层保持调用顺序一致。

## 使用示例

### PNCounter 示例

```python
from solocoder_py.crdt import PNCounter

# 创建两个副本，模拟两个节点
node_a = PNCounter(replica_id="node-a")
node_b = PNCounter(replica_id="node-b")

# 各节点本地操作
node_a.increment(10)
node_b.increment(5)
node_a.decrement(3)
node_b.decrement(1)

# 查看本地值
print(node_a.value())  # 7
print(node_b.value())  # 4

# 合并状态
node_a.merge(node_b)
node_b.merge(node_a)

# 合并后两节点收敛到相同值
print(node_a.value())  # 11 = (10+5) - (3+1)
print(node_b.value())  # 11
```

### 从状态快照恢复

```python
from solocoder_py.crdt import PNCounter, ORSet

# 创建并操作计数器
counter = PNCounter(replica_id="node-a")
counter.increment(10)
counter.decrement(3)

# 序列化状态
state = counter.get_state()

# 从状态恢复一个新实例（可用于持久化或跨进程传输）
restored = PNCounter.from_state(state, replica_id="node-a-restored")
assert restored.value() == counter.value()

# 恢复后的实例与原实例相互独立
counter.increment(1)
assert restored.value() == 7
assert counter.value() == 8

# ORSet 用法相同
s = ORSet(replica_id="r1")
s.add("hello")
s.add("world")
snapshot = s.get_state()
restored_set = ORSet.from_state(snapshot, replica_id="r1-clone")
```

### ORSet 示例

```python
from solocoder_py.crdt import ORSet

# 创建两个副本
replica1 = ORSet(replica_id="r1")
replica2 = ORSet(replica_id="r2")

# 各自添加元素
replica1.add("apple")
replica1.add("banana")
replica2.add("cherry")

# 合并
replica1.merge(replica2)
print(replica1.value())  # {"apple", "banana", "cherry"}

# 演示 add-wins 语义
replica3 = ORSet(replica_id="r3")
replica3.merge(replica1)       # replica3 同步状态
replica3.remove("apple")       # replica3 删除 apple
replica1.add("apple")          # replica1 并发地重新添加 apple
replica1.merge(replica3)
print(replica1.value())        # {"apple", "banana", "cherry"} — add wins!
```

### 查询状态与差值

```python
from solocoder_py.crdt import PNCounter

c1 = PNCounter(replica_id="a")
c2 = PNCounter(replica_id="a")
c1.increment(5)

# 查询完整状态
state = c1.get_state()
print(state.positive)  # {"a": 5}
print(state.negative)  # {}
print(state.value())   # 5

# 计算差异：c1 相对于 c2 有哪些变化
diff = c1.diff(c2)
print(diff.added_positive)  # {"a": 5}
```
