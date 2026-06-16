# Dijkstra 最短路径算法

## 模块功能

本模块提供基于内存数据结构的 Dijkstra 最短路径算法实现，适用于带非负权重的有向图，核心功能包括：

- **加权有向图存储**：以邻接表形式高效存储带权重的有向图结构，支持节点与边的动态增删
- **单源最短路径计算**：从指定源节点出发，计算到达所有其他可达节点的最短距离
- **目标提前终止**：当指定目标节点时，算法在目标节点被确定最短路径后立即终止，避免不必要的全图计算
- **前驱链路径重建**：维护每个节点的前驱指针，可按目标节点反向追踪重建完整路径序列
- **可达性判断**：明确区分节点不可达与路径距离为零的情况，对不可达节点抛出专用异常

## 核心类职责

### `WeightedDigraph`
加权有向图容器，以邻接表 `Dict[str, Dict[str, float]]` 存储图结构，其中外层字典键为源节点，内层字典键为目标节点，值为边权重。

主要方法：

| 方法 | 说明 |
|------|------|
| `add_node(node)` | 添加节点，空标识将被拒绝 |
| `add_edge(from_node, to_node, weight)` | 添加带权有向边，自动创建端点节点，负权重被拒绝 |
| `remove_node(node)` | 删除节点及其所有关联的出边和入边 |
| `remove_edge(from_node, to_node)` | 删除指定有向边 |
| `has_node(node)` | 判断节点是否存在 |
| `has_edge(from_node, to_node)` | 判断边是否存在 |
| `get_neighbors(node)` | 获取指定节点的所有邻居节点及对应边权重 |
| `get_nodes()` | 获取所有节点（按字典序排序） |
| `get_edges()` | 获取所有边的列表 |
| `get_edge_weight(from_node, to_node)` | 获取指定边的权重 |

属性：

| 属性 | 说明 |
|------|------|
| `node_count` | 图中节点总数 |
| `edge_count` | 图中边的总数 |

### `Dijkstra`
Dijkstra 算法执行器，封装最短路径计算逻辑。可传入已有 `WeightedDigraph` 实例，也可通过自身方法构建图。

主要方法：

| 方法 | 说明 |
|------|------|
| `add_node(node)` | 向图中添加节点 |
| `add_edge(from_node, to_node, weight)` | 向图中添加带权边 |
| `shortest_paths(source, target=None)` | 计算从源节点出发的最短路径，可选指定目标提前终止 |
| `shortest_path(source, target)` | 便捷方法：直接返回到达指定目标的 (距离, 路径) 元组 |

### `ShortestPathResult`
算法执行结果封装，包含距离映射、前驱映射、访问序列等完整状态信息。

主要方法：

| 方法 | 说明 |
|------|------|
| `get_distance(node)` | 获取指定节点的最短距离，节点不存在时抛 `NodeNotFoundError` |
| `get_path(target)` | 重建从源节点到目标节点的路径序列，不可达时抛 `UnreachableNodeError` |
| `is_reachable(node)` | 判断节点是否从源节点可达 |

属性：

| 属性 | 说明 |
|------|------|
| `source` | 源节点标识 |
| `distances` | 各节点最短距离字典，不可达节点值为 `float("inf")` |
| `predecessors` | 各节点前驱节点字典，源节点前驱为 `None` |
| `visited` | 算法按顺序访问的节点列表 |
| `target` | 指定的目标节点（若有） |
| `terminated_early` | 是否因目标节点提前终止 |

### `Edge`
边的简单数据类，用于 `get_edges()` 返回结果，字段：`from_node`、`to_node`、`weight`。

### 异常类

| 异常 | 触发场景 |
|------|----------|
| `DijkstraError` | 模块基类异常 |
| `NodeNotFoundError` | 访问或操作不存在的节点 |
| `NegativeWeightError` | 尝试添加负权重边 |
| `UnreachableNodeError` | 尝试获取不可达节点的路径 |

## Dijkstra 算法原理

Dijkstra 算法用于求解带非负权重有向图的单源最短路径问题，其核心思想是 **贪心策略 + 优先队列**。

### 算法步骤

1. **初始化**：将源节点距离设为 0，其余所有节点距离设为无穷大（`inf`）；所有节点前驱设为 `None`。
2. **优先队列**：使用最小堆（`heapq`）作为优先队列，存储 `(当前距离, 节点)` 二元组，初始时将 `(0, source)` 入堆。
3. **迭代松弛**：
   - 从优先队列中弹出距离最小的节点 `u`
   - 若 `u` 已被访问过则跳过
   - 标记 `u` 为已访问
   - **提前终止检查**：若指定了目标节点且 `u` 就是目标，立即返回结果
   - 遍历 `u` 的所有邻居 `v`，尝试"松弛"边 `u → v`：
     - 若 `dist[u] + weight(u, v) < dist[v]`，则更新 `dist[v]` 并记录 `predecessor[v] = u`
     - 将更新后的 `(dist[v], v)` 推入优先队列
4. **终止**：当优先队列为空或触发提前终止时，算法结束。

### 关键性质

- **非负权重保证**：由于所有权重非负，一旦节点被从优先队列弹出（标记为已访问），其最短距离即已确定，后续不会再被更新。这是贪心正确性的基础。
- **重复入队处理**：同一节点可能以不同距离多次入队，算法通过 `visited_set` 跳过已确定最短距离的旧条目。
- **时间复杂度**：使用二叉堆时为 `O((V + E) log V)`，其中 `V` 为节点数，`E` 为边数。

## 前驱链路径重建机制

路径重建通过 **前驱指针反向追踪** 实现：

1. **前驱记录**：算法在松弛操作中，每当发现更短路径 `dist[u] + w(u,v) < dist[v]` 时，将 `predecessors[v] = u`，记录"到达 `v` 的最短路径中，`v` 的上一个节点是 `u`"。
2. **反向追踪**：重建路径时，从目标节点开始，反复沿 `predecessors` 指针回溯，直到遇到 `None`（即到达源节点）。
3. **路径反转**：由于回溯得到的是目标到源的逆序序列，最后将列表反转即得到源到目标的正序路径。

### 示例：路径重建过程

假设图结构为 `A →(4) B →(5) D →(2) E`，且最短路径为 `A → B → D → E`：

```
predecessors = {
    "A": None,   # 源节点无前驱
    "B": "A",
    "D": "B",
    "E": "D",
    ...
}

重建 "E" 的路径：
  current = "E"  → path = ["E"]
  current = "D"  → path = ["E", "D"]
  current = "B"  → path = ["E", "D", "B"]
  current = "A"  → path = ["E", "D", "B", "A"]
  current = None → 停止

反转后得到: ["A", "B", "D", "E"]
```

### 不可达节点处理

- 不可达节点在 `distances` 中保持初始值 `float("inf")`
- 不可达节点在 `predecessors` 中保持初始值 `None`
- 调用 `get_path()` 时通过检查距离是否为无穷来判断是否可达，不可达则抛出 `UnreachableNodeError` 而非返回空列表或错误路径
- 可通过 `is_reachable()` 方法预先判断节点可达性

## 使用示例

### 基础示例：计算所有最短路径

```python
from solocoder_py.dijkstra import Dijkstra

dj = Dijkstra()
dj.add_edge("A", "B", 4.0)
dj.add_edge("A", "C", 2.0)
dj.add_edge("B", "C", 1.0)
dj.add_edge("B", "D", 5.0)
dj.add_edge("C", "D", 8.0)
dj.add_edge("C", "E", 10.0)
dj.add_edge("D", "E", 2.0)

result = dj.shortest_paths("A")

print(f"到 D 的距离: {result.get_distance('D')}")       # 9.0
print(f"到 D 的路径: {result.get_path('D')}")           # ['A', 'B', 'D']
print(f"到 E 的距离: {result.get_distance('E')}")       # 11.0
print(f"到 E 的路径: {result.get_path('E')}")           # ['A', 'B', 'D', 'E']
print(f"访问过的节点: {result.visited}")                 # 按 Dijkstra 顺序
```

### 使用目标提前终止优化

```python
from solocoder_py.dijkstra import Dijkstra, UnreachableNodeError

dj = Dijkstra()
# ... 构建大图 ...

# 只关心到 D 的最短路径，到达 D 后立即停止
result = dj.shortest_paths("A", target="D")

assert result.terminated_early is True
assert result.target == "D"
print(f"仅计算了 {len(result.visited)} 个节点即找到 D")
print(f"最短距离: {result.get_distance('D')}")
```

### 便捷方法：直接获取单条路径

```python
from solocoder_py.dijkstra import Dijkstra, UnreachableNodeError

dj = Dijkstra()
dj.add_edge("S", "A", 7)
dj.add_edge("S", "B", 2)
dj.add_edge("A", "T", 1)
dj.add_edge("B", "T", 5)

distance, path = dj.shortest_path("S", "T")
print(f"最短距离: {distance}")  # 8.0  (S → A → T)
print(f"路径: {path}")          # ['S', 'A', 'T']
```

### 处理不可达节点

```python
from solocoder_py.dijkstra import Dijkstra, UnreachableNodeError

dj = Dijkstra()
dj.add_edge("A", "B", 1.0)
dj.add_node("C")  # C 是孤立节点

result = dj.shortest_paths("A")

print(result.is_reachable("A"))  # True
print(result.is_reachable("B"))  # True
print(result.is_reachable("C"))  # False
print(result.get_distance("C"))  # inf

try:
    path = result.get_path("C")
except UnreachableNodeError as e:
    print(f"正确处理不可达: {e}")
```

### 处理异常情况

```python
from solocoder_py.dijkstra import (
    Dijkstra,
    NegativeWeightError,
    NodeNotFoundError,
)

dj = Dijkstra()
dj.add_edge("A", "B", 1.0)

# 负权重边被拒绝
try:
    dj.add_edge("B", "C", -5.0)
except NegativeWeightError as e:
    print(f"拒绝负权边: {e}")

# 不存在的源节点
try:
    dj.shortest_paths("Z")
except NodeNotFoundError as e:
    print(f"节点不存在: {e}")
```

### 直接使用图容器

```python
from solocoder_py.dijkstra import WeightedDigraph, Dijkstra

graph = WeightedDigraph()
graph.add_edge("X", "Y", 3.0)
graph.add_edge("Y", "Z", 4.0)
graph.add_edge("X", "Z", 10.0)

print(f"节点数: {graph.node_count}")   # 3
print(f"边数: {graph.edge_count}")      # 3
print(f"所有节点: {graph.get_nodes()}") # ['X', 'Y', 'Z']

# 将已有图传入算法
dj = Dijkstra(graph)
dist, path = dj.shortest_path("X", "Z")
print(f"X→Z 最短距离: {dist}")  # 7.0
print(f"路径: {path}")          # ['X', 'Y', 'Z']
```
