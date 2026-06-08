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
| `merge(other)` | 合并另一个副本的状态到当前副本 |
| `diff(other)` | 计算当前副本与另一个副本的差异 |
| `is_ge(other)` | 判断当前副本在状态偏序上是否大于等于另一个副本 |

内部状态包含两个字典：
- `_positive: dict[str, int]` — 各副本的正增量映射
- `_negative: dict[str, int]` — 各副本的负增量映射

最终值 = `sum(_positive.values()) - sum(_negative.values())`，并与 0 取最大值。

### ORSet

观察移除集合通过为每个添加操作分配唯一标签 (unique tag) 来追踪元素的存在性。

| 方法 | 描述 |
|------|------|
| `add(element)` | 添加元素到集合，生成新的唯一标签 |
| `add_all(elements)` | 批量添加多个元素 |
| `remove(element)` | 移除元素（仅移除当前已知的标签） |
| `contains(element)` | 判断元素是否存在于集合中 |
| `value()` | 返回当前集合中的所有元素（不重复） |
| `clear()` | 清空集合中的所有元素 |
| `get_state()` | 获取当前副本的完整状态（元素→(标签集合, 墓碑集合)映射的深拷贝） |
| `merge(other)` | 合并另一个副本的状态到当前副本 |
| `diff(other)` | 计算当前副本与另一个副本的差异 |
| `is_ge(other)` | 判断当前副本在状态偏序上是否大于等于另一个副本 |

内部状态：
- `_elements: dict[Any, tuple[set[str], set[str]]]` — 元素到 (标签集合, 墓碑集合) 的映射
  - `tags`: 所有曾添加该元素的标签集合
  - `tombstones`: 已被删除的标签集合（墓碑）

元素存在当且仅当 `alive_tags = tags - tombstones` 非空。

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

# 计算差异
diff = c1.diff(c2)
print(diff.added_positive)  # {"a": 5}
```
