# Kahn 拓扑排序算法

## 模块功能

本模块提供基于内存数据结构的 Kahn 拓扑排序算法实现，适用于有向无环图（DAG）的拓扑排序、环检测以及所有合法拓扑序列的枚举。核心功能包括：

- **有向图存储**：以邻接表形式高效存储有向图结构，支持节点与边的动态增删，维护每个节点的入度信息
- **Kahn 拓扑排序**：基于 BFS 的 Kahn 算法生成一个合法的拓扑序列
- **环检测**：在拓扑排序过程中检测有向图是否存在环，并提取环上涉及的所有节点
- **全拓扑序列枚举**：通过回溯算法以惰性生成器方式逐个产出合法拓扑排序，避免指数级内存占用

## 核心类职责

### `Digraph`
有向图容器，以邻接表 `Dict[str, Set[str]]` 存储图结构，同时维护 `Dict[str, int]` 的入度映射，支持 O(1) 入度查询。

主要方法：

| 方法 | 说明 |
|------|------|
| `add_node(node)` | 添加节点，空标识将被拒绝 |
| `add_edge(from_node, to_node)` | 添加有向边，自动创建端点节点，重复边无副作用 |
| `remove_node(node)` | 删除节点及其所有关联的出边和入边，同步更新入度 |
| `remove_edge(from_node, to_node)` | 删除指定有向边，同步更新目标节点入度 |
| `has_node(node)` | 判断节点是否存在 |
| `has_edge(from_node, to_node)` | 判断边是否存在 |
| `get_in_degree(node)` | 获取指定节点的入度 |
| `get_neighbors(node)` | 获取指定节点的所有后继节点（迭代器，不保证顺序） |
| `get_nodes()` | 获取所有节点（迭代器，不保证顺序） |
| `get_edges()` | 获取所有边的列表（按字典序稳定输出） |

属性：

| 属性 | 说明 |
|------|------|
| `node_count` | 图中节点总数 |
| `edge_count` | 图中边的总数 |

### `KahnTopologicalSort`
Kahn 算法执行器，封装拓扑排序、环检测与全枚举逻辑。可传入已有 `Digraph` 实例，也可通过自身方法构建图。

主要方法：

| 方法 | 说明 |
|------|------|
| `add_node(node)` | 向图中添加节点 |
| `add_edge(from_node, to_node)` | 向图中添加有向边 |
| `sort()` | 执行 Kahn 算法，返回 `TopologicalSortResult` |
| `detect_cycle()` | 检测图中的环，返回环上节点列表（无环则为空列表） |
| `enumerate_all_topological_orders()` | 惰性生成器，逐个产出合法拓扑序列，有环时立即抛出 `CycleDetectedError` |

### `TopologicalSortResult`
拓扑排序结果封装。

字段：

| 字段 | 说明 |
|------|------|
| `order` | 拓扑序列列表（有环时为部分序列） |
| `has_cycle` | 图中是否存在环 |
| `cycle_nodes` | 环上涉及的节点列表（无环则为空） |
| `is_valid` | 属性，等价于 `not has_cycle` |

### `Edge`
边的简单数据类，字段：`from_node`、`to_node`。

### 异常类

| 异常 | 触发场景 |
|------|----------|
| `KahnError` | 模块基类异常 |
| `NodeNotFoundError` | 访问或操作不存在的节点 |
| `CycleDetectedError` | 在有环图上尝试枚举拓扑序列，携带 `cycle_nodes` 属性 |

## Kahn 算法原理

Kahn 算法用于求解有向无环图（DAG）的拓扑排序问题，其核心思想是 **BFS + 入度计数**。

### 算法步骤

1. **入度初始化**：计算图中每个节点的入度。
2. **零入度入队**：将所有入度为 0 的节点加入队列（这些节点没有任何前置依赖）。
3. **迭代出队**：
   - 从队列中弹出一个节点 `u`，将其加入拓扑序列
   - 遍历 `u` 的所有后继节点 `v`，将 `v` 的入度减 1（表示 `u` 这个前置依赖已完成）
   - 若 `v` 的入度变为 0，将 `v` 加入队列
4. **终止判断**：当队列为空时，若拓扑序列包含所有节点，则排序成功；若序列长度小于总节点数，说明图中存在环。

### 环检测机制

Kahn 算法天然支持环检测，其原理为：

- 在有环子图中，每个节点至少有一条来自环上其他节点的入边，因此环上所有节点的入度永远不会降为 0
- 当算法结束时，未被加入拓扑序列的节点恰好就是环上（或可从环到达的）节点
- 实现中将拓扑排序过程中未被访问到的节点收集为 `cycle_nodes` 返回

### 全拓扑序列枚举

当图中存在多个入度为 0 的节点时，Kahn 算法的出队顺序不唯一，对应多个合法拓扑序列。枚举算法使用 **回溯（Backtracking） + 惰性生成器**：

1. 维护当前已选序列、剩余入度计数、已访问节点集合
2. 每一步从所有当前入度为 0 且未访问的节点中任选一个加入序列
3. 将该节点后继的入度减 1，递归进入下一层
4. 递归返回后恢复后继入度，回溯选择下一个候选节点
5. 当序列长度等于总节点数时 `yield` 该合法拓扑排序，然后继续

该算法使用 Python 生成器（`Iterator[List[str]]`）逐个产出结果，避免一次性将所有序列存入内存。即使对于 10 个离散节点（10! = 3,628,800 种排列），内存占用也始终保持在 O(V) 的递归栈级别，不会产生指数级爆炸。共享状态 + 回溯恢复的策略进一步避免了每层递归的数据结构复制开销。

## 使用示例

### 基础拓扑排序

```python
from solocoder_py.kahn import KahnTopologicalSort

kahn = KahnTopologicalSort()
kahn.add_edge("A", "B")
kahn.add_edge("A", "C")
kahn.add_edge("B", "D")
kahn.add_edge("C", "D")

result = kahn.sort()
print(result.is_valid)        # True
print(result.order)           # e.g. ['A', 'B', 'C', 'D']
```

### 环检测

```python
from solocoder_py.kahn import KahnTopologicalSort

kahn = KahnTopologicalSort()
kahn.add_edge("A", "B")
kahn.add_edge("B", "C")
kahn.add_edge("C", "A")

result = kahn.sort()
print(result.has_cycle)       # True
print(result.cycle_nodes)     # ['A', 'B', 'C']

# 便捷方法
cycle_nodes = kahn.detect_cycle()
print(cycle_nodes)            # ['A', 'B', 'C']
```

### 枚举所有合法拓扑序列（惰性生成器）

```python
from solocoder_py.kahn import KahnTopologicalSort, CycleDetectedError

kahn = KahnTopologicalSort()
kahn.add_edge("A", "B")
kahn.add_edge("A", "C")
kahn.add_edge("B", "D")
kahn.add_edge("C", "D")

# enumerate_all_topological_orders 返回迭代器，逐个产出结果
gen = kahn.enumerate_all_topological_orders()
print(type(gen))              # <class 'generator'>

# 可逐个迭代，节省内存
for i, order in enumerate(gen):
    print(f"第 {i+1} 种拓扑序: {order}")
# 第 1 种拓扑序: ['A', 'B', 'C', 'D']
# 第 2 种拓扑序: ['A', 'C', 'B', 'D']

# 如需一次性收集可用 list(gen)，但注意大数量时的内存
all_orders = list(kahn.enumerate_all_topological_orders())
print(len(all_orders))        # 2

# 有环图上枚举会在调用时立即抛异常（不等到迭代）
cyclic = KahnTopologicalSort()
cyclic.add_edge("X", "Y")
cyclic.add_edge("Y", "X")
try:
    cyclic.enumerate_all_topological_orders()
except CycleDetectedError as e:
    print("有环，节点:", e.cycle_nodes)   # 有环，节点: ['X', 'Y']
```

### 直接使用图容器

```python
from solocoder_py.kahn import Digraph, KahnTopologicalSort

graph = Digraph()
graph.add_edge("X", "Y")
graph.add_edge("Y", "Z")
graph.add_node("W")

print(graph.node_count)               # 3
print(graph.edge_count)                # 2
print(graph.get_in_degree("Y"))        # 1
print(list(graph.get_neighbors("X")))  # ['Y']  顺序不保证
print(set(graph.get_nodes()))          # {'W', 'X', 'Y', 'Z'}

# get_edges() 保持按字典序稳定输出，便于测试与调试
for edge in graph.get_edges():
    print(f"{edge.from_node} -> {edge.to_node}")
# X -> Y
# Y -> Z

kahn = KahnTopologicalSort(graph)
result = kahn.sort()
# result.order 是合法拓扑序，但具体顺序依赖入队顺序
print(set(result.order))               # {'W', 'X', 'Y', 'Z'}
```
