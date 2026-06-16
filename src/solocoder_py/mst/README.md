# Kruskal 最小生成树算法

## 模块功能

本模块提供基于内存数据结构的 Kruskal 最小生成树（Minimum Spanning Tree, MST）算法实现，适用于无向加权图，核心功能包括：

- **无向加权图存储**：以邻接表形式高效存储无向加权图，支持节点与边的动态增删，支持同一对节点间存在多条边（多重图）
- **Kruskal 最小生成树计算**：对连通无向加权图计算总权重最小的生成树，总边数为 V-1（V 为节点数）
- **并查集数据结构**：提供按秩合并与路径压缩优化的并查集（Union-Find / Disjoint Set Union），作为可复用的独立组件
- **最小生成森林**：对非连通图，输出最小生成森林（Minimum Spanning Forest），每个连通分量独立生成一棵最小生成树
- **连通性追踪**：每条生成树边明确标识其所属的连通分量，支持按分量查询边和节点集合

## 核心类职责

### `UnionFind[T]`

并查集（不相交集合）数据结构，支持按秩合并和路径压缩两种优化，使查找和合并操作的均摊时间复杂度接近常数。

主要方法：

| 方法 | 说明 |
|------|------|
| `__init__(elements=None)` | 构造并查集，可可选传入初始元素列表 |
| `add(element)` | 添加一个元素，返回是否成功添加（已存在返回 False） |
| `find(element)` | 查找元素的根节点，执行路径压缩 |
| `union(a, b)` | 合并两个元素所在的集合，返回是否实际执行了合并 |
| `connected(a, b)` | 判断两个元素是否属于同一集合 |
| `has(element)` | 判断元素是否存在于并查集中 |
| `roots()` | 返回所有根节点的列表 |
| `get_components()` | 返回所有连通分量的列表 |

属性：

| 属性 | 说明 |
|------|------|
| `count` | 当前连通分量的数量 |

### `Edge[T]`

无向边的数据类，表示无向加权边，自动处理无向性（u-v 相等性和哈希与边方向无关）。

字段：

| 字段 | 说明 |
|------|------|
| `u` | 边的一个端点 |
| `v` | 边的另一个端点 |
| `weight` | 边的权重 |

主要方法和属性：

| 方法/属性 | 说明 |
|-----------|------|
| `endpoints` | 返回边的两个端点（u, v） |
| `contains(node)` | 判断节点是否是边的端点 |
| `other(node)` | 返回边的另一个端点 |
| `__eq__` | 无向边相等比较（与方向无关） |
| `__hash__` | 无向边哈希（与方向无关） |

### `ForestEdge[T]`

生成森林中的边，封装了原始边和所属分量的 ID。

属性：

| 属性 | 说明 |
|------|------|
| `edge` | 原始边对象 |
| `u` | 边的一个端点（快捷访问） |
| `v` | 边的另一个端点（快捷访问） |
| `weight` | 边的权重（快捷访问） |
| `component_id` | 边所属连通分量的 ID |

### `MSTResult[T]`

Kruskal 算法执行结果封装，包含生成森林的所有边和连通分量信息。

属性：

| 属性 | 说明 |
|------|------|
| `forest_edges` | 生成森林中所有边的列表（`ForestEdge` 对象列表） |
| `components` | 所有连通分量的列表（每个分量是节点集合） |
| `total_weight` | 生成森林的总权重 |
| `edge_count` | 生成森林的边总数 |
| `component_count` | 连通分量的数量 |
| `is_spanning_tree` | 是否是生成树（即图是否连通，只有一个分量） |

主要方法：

| 方法 | 说明 |
|------|------|
| `get_component(component_id)` | 获取指定 ID 的连通分量（节点集合） |
| `get_edges_by_component(component_id)` | 获取指定分量的所有生成树边 |

### `UndirectedWeightedGraph[T]`

无向加权图容器，支持多重图（同一对节点间可有多条边），以邻接表 + 边列表存储。

主要方法：

| 方法 | 说明 |
|------|------|
| `add_node(node)` | 添加节点，None 被拒绝 |
| `add_edge(u, v, weight)` | 添加无向加权边，自动创建端点节点，自环边被拒绝 |
| `remove_node(node)` | 删除节点及其所有关联边 |
| `remove_edge(u, v, weight=None)` | 删除指定边，可指定权重删除特定边 |
| `has_node(node)` | 判断节点是否存在 |
| `has_edge(u, v)` | 判断两点之间是否存在至少一条边 |
| `get_neighbors(node)` | 获取节点的所有邻居及最小权重 |
| `get_nodes()` | 获取所有节点列表 |
| `get_edges()` | 获取所有边的列表 |
| `get_edges_between(u, v)` | 获取两点之间的所有边 |

属性：

| 属性 | 说明 |
|------|------|
| `node_count` | 图中节点总数 |
| `edge_count` | 图中边的总数（含多重边） |

### `Kruskal[T]`

Kruskal 算法执行器，封装最小生成树/森林计算逻辑。可传入已有 `UndirectedWeightedGraph` 实例，也可通过自身方法构建图。

主要方法：

| 方法 | 说明 |
|------|------|
| `add_node(node)` | 向图中添加节点 |
| `add_edge(u, v, weight)` | 向图中添加无向加权边 |
| `compute_mst()` | 计算最小生成树/森林，返回 `MSTResult` |

属性：

| 属性 | 说明 |
|------|------|
| `graph` | 内部的图对象 |

### 异常类

| 异常 | 触发场景 |
|------|----------|
| `KruskalError` | 模块基类异常 |
| `NodeNotFoundError` | 访问或操作不存在的节点 |
| `EdgeNotFoundError` | 删除不存在的边 |

## Kruskal 算法原理

Kruskal 算法用于求解无向加权图的最小生成树问题，其核心思想是 **贪心策略 + 并查集**。

### 算法步骤

1. **边排序**：将图中所有边按权重从小到大升序排序。
2. **初始化并查集**：每个节点初始时各自为一个独立的连通分量。
3. **依次选边**：按权重从小到大遍历每条边：
   - 使用并查集判断边的两个端点是否属于不同连通分量
   - 若属于不同分量，则将该边加入生成树，并通过并查集合并两个分量
   - 若属于同一分量（加入会形成环），则跳过该边
4. **终止条件**：
   - 对于连通图，当生成树恰好包含 V-1 条边时可提前终止（V 为节点数）
   - 对于非连通图，遍历完所有边后得到最小生成森林

### 关键性质

- **贪心选择性质**：每次选择权重最小且不形成环的边，最终得到全局最优解
- **时间复杂度**：主要由排序决定，为 `O(E log E)`，其中 `E` 为边数。并查集操作的均摊复杂度接近 `O(1)`
- **空间复杂度**：`O(V + E)`，存储图和并查集

### 最小生成森林

对于非连通图，Kruskal 算法自然地为每个连通分量独立计算一棵最小生成树，构成最小生成森林。森林的总边数为 V-C（V 为节点总数，C 为连通分量数）。

## 并查集优化机制

并查集支持两种经典优化，使操作均摊复杂度接近常数：

### 路径压缩（Path Compression）

在 `find` 操作中，将查找路径上的所有节点直接连接到根节点，使后续查找更快。

```
find 前:
    A (根)
   / \
  B   C
 /
D

find(D) 后 (路径压缩):
    A (根)
   / | \
  B  C  D
```

路径压缩后，D 直接指向根 A，下次查找 D 时只需一步。

### 按秩合并（Union by Rank）

在 `union` 操作中，将秩（树的高度近似值）较小的树合并到秩较大的树下，保持树的平衡，避免树退化成链表。

```
合并前:
    A (rank=2)        C (rank=1)
   / \               |
  B   D              E

按秩合并 (将矮树合并到高树):
    A (rank=2)
   / | \
  B  D  C
          \
           E
```

当两棵树秩相同时，合并后根节点的秩加 1。

### 复杂度分析

- 仅路径压缩：均摊复杂度约为 `O(log n)`
- 仅按秩合并：最坏情况 `O(log n)`
- 两者结合：均摊复杂度接近 `O(1)`（精确为反阿克曼函数的反函数，增长极慢，对于实际应用中可视为常数）

## 使用示例

### 基础示例：连通图最小生成树

```python
from solocoder_py.mst import Kruskal

kruskal = Kruskal()
kruskal.add_edge("A", "B", 4.0)
kruskal.add_edge("A", "C", 2.0)
kruskal.add_edge("B", "C", 1.0)
kruskal.add_edge("B", "D", 5.0)
kruskal.add_edge("C", "D", 8.0)
kruskal.add_edge("C", "E", 10.0)
kruskal.add_edge("D", "E", 2.0)

result = kruskal.compute_mst()

print(f"是否生成树: {result.is_spanning_tree}")  # True
print(f"总权重: {result.total_weight}")          # 10.0
print(f"边数: {result.edge_count}")              # 4 (5个节点，V-1=4)
print(f"分量数: {result.component_count}")        # 1

for fe in result.forest_edges:
    print(f"  {fe.u}-{fe.v}: {fe.weight}")
```

### 非连通图最小生成森林

```python
from solocoder_py.mst import Kruskal, UndirectedWeightedGraph

graph = UndirectedWeightedGraph()
graph.add_edge("A", "B", 1.0)
graph.add_edge("B", "C", 2.0)
graph.add_edge("D", "E", 3.0)
graph.add_edge("E", "F", 4.0)
graph.add_node("G")  # 孤立节点

kruskal = Kruskal(graph)
result = kruskal.compute_mst()

print(f"是否生成树: {result.is_spanning_tree}")  # False
print(f"总权重: {result.total_weight}")          # 10.0
print(f"边数: {result.edge_count}")              # 4 (7-3=4)
print(f"分量数: {result.component_count}")        # 3

for cid in range(result.component_count):
    comp = result.get_component(cid)
    edges = result.get_edges_by_component(cid)
    print(f"分量 {cid}: {len(comp)} 个节点, {len(edges)} 条边")
    print(f"  节点: {comp}")
```

### 使用并查集

```python
from solocoder_py.mst import UnionFind

uf = UnionFind(["a", "b", "c", "d", "e"])

print(uf.count)  # 5

uf.union("a", "b")
uf.union("c", "d")
uf.union("b", "c")

print(uf.count)  # 2
print(uf.connected("a", "d"))  # True
print(uf.connected("a", "e"))  # False

print(uf.find("d"))  # 路径压缩后的根节点
```

### 处理多重图（多条边在同一对节点之间）

```python
from solocoder_py.mst import Kruskal

kruskal = Kruskal()
kruskal.add_edge("A", "B", 5.0)
kruskal.add_edge("A", "B", 3.0)  # 同一对节点间的另一条边
kruskal.add_edge("A", "B", 7.0)
kruskal.add_edge("B", "C", 2.0)
kruskal.add_edge("A", "C", 4.0)

result = kruskal.compute_mst()

print(f"总权重: {result.total_weight}")  # 5.0 (B-C:2 + A-B:3)
```

### 负权重边

Kruskal 算法可以正确处理负权重边（与 Dijkstra 不同）

```python
from solocoder_py.mst import Kruskal

kruskal = Kruskal()
kruskal.add_edge("A", "B", -2.0)
kruskal.add_edge("A", "C", 1.0)
kruskal.add_edge("B", "C", 3.0)
kruskal.add_edge("B", "D", -1.0)
kruskal.add_edge("C", "D", 2.0)

result = kruskal.compute_mst()
print(f"总权重: {result.total_weight}")  # -2.0
```

### 直接使用图容器

```python
from solocoder_py.mst import UndirectedWeightedGraph, Kruskal

graph = UndirectedWeightedGraph()
graph.add_edge("X", "Y", 3.0)
graph.add_edge("Y", "Z", 4.0)
graph.add_edge("X", "Z", 10.0)

print(f"节点数: {graph.node_count}")   # 3
print(f"边数: {graph.edge_count}")      # 3
print(f"所有节点: {graph.get_nodes()}") # ['X', 'Y', 'Z']

# 将已有图传入算法
kruskal = Kruskal(graph)
result = kruskal.compute_mst()
print(f"MST 总权重: {result.total_weight}")  # 7.0
```

### 处理异常情况

```python
from solocoder_py.mst import (
    Kruskal,
    KruskalError,
    NodeNotFoundError,
    EdgeNotFoundError,
)

graph = Kruskal()
graph.add_edge("A", "B", 1.0)

# 自环边被拒绝
try:
    graph.add_edge("A", "A", 1.0)
except KruskalError as e:
    print(f"自环边被拒绝: {e}")

# 不存在的节点
try:
    graph.graph.get_neighbors("Z")
except NodeNotFoundError as e:
    print(f"节点不存在: {e}")

# 删除不存在的边
try:
    graph.graph.remove_edge("A", "C")
except EdgeNotFoundError as e:
    print(f"边不存在: {e}")
```
