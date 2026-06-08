# Vector Clock (向量时钟)

本模块实现了基于内存数据结构的向量时钟，用于分布式系统中捕获事件之间的因果偏序关系。

## 模块功能

- **本地事件递增**：节点本地每发生一个事件，对应该节点的计数值自动加 1
- **因果偏序判定**：给定两个向量时钟，可以判定"前者发生在后者之前"、"后者发生在前者之前"、"两者并发"或"两者相等"四种关系
- **并发关系识别**：当两个向量时钟互不为对方的前驱时（且不相等），判定为并发关系
- **时钟合并**：两个向量时钟合并时，每个节点取两者对应计数值的最大值，产生新的向量时钟
- **时钟查询与比较**：支持查询指定节点的计数值、比较两个时钟的先后关系、判断两个时钟是否相等

## 核心类职责

### `VectorClock`
向量时钟的主类，维护节点 ID 到计数值的映射。

**节点 ID 校验规则**：节点 ID 必须为非空字符串。在构造函数 `__init__` 和 `tick` 方法中均会校验，传入空字符串将抛出 `ValueError: node_id must not be empty`。

主要方法：
- `tick(node_id)`：节点本地事件递增，对应节点计数值 +1
- `get(node_id)`：查询指定节点的当前计数值（不存在则返回 0）
- `nodes()`：获取所有已知节点 ID 的集合（仅包含计数值大于 0 的节点）
- `to_dict()`：返回向量时钟内部数据的字典副本（仅包含计数值大于 0 的节点）
- `copy()`：返回向量时钟的独立副本
- `happens_before(other)`：判断当前时钟是否发生在另一个时钟之前
- `happens_after(other)`：判断当前时钟是否发生在另一个时钟之后
- `is_concurrent_with(other)`：判断当前时钟与另一个时钟是否为并发关系
- `compare(other)`：返回两个时钟的关系枚举值（`ClockRelation.BEFORE` / `AFTER` / `CONCURRENT` / `EQUAL`）
- `merge(other)`：合并两个向量时钟，每个节点取最大值，返回新的 `VectorClock` 实例

### `ClockRelation` (Enum)
时钟比较结果的枚举类型：
- `BEFORE`：前者发生在后者之前
- `AFTER`：后者发生在前者之前
- `CONCURRENT`：两者并发
- `EQUAL`：两者相等

## 向量时钟偏序判定规则

### 隐含零值约定

向量时钟在比较时采用**隐含零值**语义：对于未在时钟中显式出现的节点，其计数值隐含为 0。因此：
- `VectorClock({"a": 1})` 与 `VectorClock({"a": 1, "b": 0})` 被视为相等
- 构造时传入的零计数值节点会被归一化（不存储在内部数据结构中），`nodes()` 和 `to_dict()` 仅返回计数值大于 0 的节点
- 该约定保证了 `__eq__` 与 `__hash__` 的一致性，相等的时钟在 `set` 和 `dict` 中可正确去重

### 偏序定义

对于两个向量时钟 VC(A) 和 VC(B)：

1. **VC(A) ≤ VC(B)**（A 不晚于 B）：当且仅当对于所有节点 i，VC(A)[i] ≤ VC(B)[i]
2. **VC(A) < VC(B)**（A 发生在 B 之前，严格偏序）：当且仅当 VC(A) ≤ VC(B) 且 VC(A) ≠ VC(B)
   - 即：所有节点的计数值 A 都不超过 B，且至少有一个节点 A 严格小于 B
3. **并发关系**：当且仅当 VC(A) ≮ VC(B) 且 VC(B) ≮ VC(A) 且 VC(A) ≠ VC(B)
   - 即：存在节点 i 使得 VC(A)[i] > VC(B)[i]，同时存在节点 j 使得 VC(A)[j] < VC(B)[j]
4. **相等**：当且仅当对于所有节点 i，VC(A)[i] == VC(B)[i]
   - 在隐含零值约定下，`{"a": 1}` 与 `{"a": 1, "b": 0}` 视为相等

### 并集处理原则

比较或合并两个具有不同节点集合的向量时钟时，对两个时钟的节点取并集，未在某时钟中出现的节点计数值按 0 处理。这保证了不同节点集的时钟也能正确比较。

## 使用示例

### 基本操作

```python
from solocoder_py.vector_clock import VectorClock, ClockRelation

vc = VectorClock()
vc.tick("node-a")
vc.tick("node-a")
vc.tick("node-b")

print(vc.get("node-a"))  # 2
print(vc.get("node-b"))  # 1
print(vc.get("node-c"))  # 0（未知节点默认返回 0）
print(vc.nodes())        # {"node-a", "node-b"}
```

### 因果关系判定

```python
# A 发生在 B 之前
a = VectorClock({"a": 1, "b": 0})
b = VectorClock({"a": 2, "b": 1})
print(a.happens_before(b))  # True
print(b.happens_after(a))   # True

# 并发关系
x = VectorClock({"a": 2, "b": 1})
y = VectorClock({"a": 1, "b": 2})
print(x.is_concurrent_with(y))  # True

# 使用 compare 统一判定
relation = x.compare(y)
if relation == ClockRelation.BEFORE:
    print("x happens before y")
elif relation == ClockRelation.AFTER:
    print("x happens after y")
elif relation == ClockRelation.CONCURRENT:
    print("x and y are concurrent")
elif relation == ClockRelation.EQUAL:
    print("x and y are equal")
```

### 时钟合并（模拟接收消息）

```python
local = VectorClock({"a": 3, "b": 1})
received = VectorClock({"a": 1, "b": 2, "c": 4})

merged = local.merge(received)
print(merged.to_dict())  # {"a": 3, "b": 2, "c": 4}

# 本地事件继续递增
merged.tick("a")
print(merged.get("a"))   # 4
```

### 分布式场景模拟

```python
base = VectorClock({"A": 1})

# 节点 A 继续执行本地事件
branch_a = base.copy()
branch_a.tick("A")
branch_a.tick("A")

# 节点 B 独立执行本地事件（与 branch_a 并发）
branch_b = base.copy()
branch_b.tick("B")

print(branch_a.is_concurrent_with(branch_b))  # True

# 节点 B 接收到节点 A 的消息后合并时钟
reconciled = branch_a.merge(branch_b)
print(reconciled.to_dict())  # {"A": 3, "B": 1}
print(branch_a.happens_before(reconciled))  # True
print(branch_b.happens_before(reconciled))  # True
```
