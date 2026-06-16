# 强连通分量（SCC）算法域

## 模块功能

本模块提供一个基于内存数据结构的强连通分量（Strongly Connected Components, SCC）检测与分析工具，支持：

- **有向图存储与管理**：使用邻接表存储有向图，支持节点和边的动态添加
- **SCC 检测**：基于 Tarjan 算法在线性时间 O(V+E) 内找出图中所有强连通分量
- **缩点图构建**：将每个 SCC 收缩为超节点，构建有向无环的缩点图（Condensation Graph）
- **拓扑编号保证**：SCC 编号满足缩点图的拓扑排序，边总是从小号分量指向大号分量
- **高效查询**：支持查询节点所属 SCC、SCC 包含的节点列表、缩点图的边信息等

## 核心类职责

### `DirectedGraph`
有向图数据结构，使用邻接表存储。

| 属性/方法 | 说明 |
|-----------|------|
| `add_node(node)` | 添加节点 |
| `add_edge(from_node, to_node)` | 添加有向边 |
| `add_edges(edges)` | 批量添加边 |
| `get_neighbors(node)` | 获取节点的出邻接点集合 |
| `has_node(node)` | 判断节点是否存在 |
| `has_edge(from, to)` | 判断边是否存在 |
| `nodes` | 返回所有节点列表（已排序） |
| `edges` | 返回所有边列表（已排序） |
| `num_nodes` | 节点数量 |
| `num_edges` | 边数量 |
| `is_empty()` | 图是否为空 |
| `get_transpose()` | 返回转置图（所有边反向） |

### `TarjanSCC`
Tarjan 算法实现类，用于检测强连通分量和构建缩点图。

| 方法 | 说明 |
|------|------|
| `__init__(graph)` | 构造函数，接收有向图 |
| `find_sccs()` | 执行 SCC 检测，返回 `SCCResult` |
| `build_condensation(scc_result=None)` | 构建缩点图，返回 `CondensationGraph` |

### `SCCResult`
SCC 检测结果封装类。

| 属性/方法 | 说明 |
|-----------|------|
| `node_to_component` | 节点到分量 ID 的映射字典 |
| `component_to_nodes` | 分量 ID 到节点列表的映射字典 |
| `components` | 所有分量的列表，每个分量是节点列表 |
| `get_component_id(node)` | 查询节点所属的 SCC 编号 |
| `get_component_nodes(component_id)` | 查询 SCC 包含的节点列表 |
| `__len__()` | 返回 SCC 总数 |

### `CondensationGraph`
缩点图数据结构，每个超节点代表一个 SCC。

| 属性/方法 | 说明 |
|-----------|------|
| `num_components` | 超节点总数 |
| `adjacency` | 超节点的邻接表（使用 set 自动去重） |
| `node_to_component` | 原图节点到分量 ID 的映射 |
| `component_to_nodes` | 分量 ID 到原图节点列表的映射 |
| `get_outgoing_edges(component_id)` | 获取超节点的出边集合 |
| `get_incoming_edges(component_id)` | 获取超节点的入边集合 |
| `is_dag()` | 判断缩点图是否为有向无环图（DAG） |
| `topological_order()` | 返回缩点图的拓扑排序 |
| `has_edge(from, to)` | 判断是否存在超边 |
| `get_edges()` | 返回所有超边列表 |

### 异常类

| 异常 | 触发场景 |
|------|----------|
| `SCCError` | 模块基类异常 |
| `NodeNotFoundError` | 查询不存在的节点或分量 ID |
| `EmptyGraphError` | 对空图执行缩点图构建 |

## Tarjan 算法原理

Tarjan 算法是 Robert Tarjan 在 1972 年提出的线性时间 SCC 检测算法，基于深度优先搜索（DFS）实现。

### 核心概念

- **发现时间戳（disc）**：记录节点首次被 DFS 访问的时间点
- **低链路值（low）**：记录从该节点出发，通过一条 DFS 树边加上至多一条后向边（指向栈中祖先的边）能到达的最早发现的节点的发现时间
- **辅助栈**：保存当前 DFS 遍历路径上的节点

### 算法步骤

1. 对图中每个未访问节点启动 DFS
2. 在 DFS 过程中：
   - 为节点分配递增的发现时间戳 `disc`
   - 初始化 `low` 值为自身的发现时间
   - 将节点压入辅助栈
3. 对每个邻接点递归 DFS 后：
   - 如果邻接点未访问过，递归后更新 `low[u] = min(low[u], low[v])`
   - 如果邻接点已访问且仍在栈中（说明是后向边），更新 `low[u] = min(low[u], disc[v])`
4. 当节点 DFS 返回时，若 `low[u] == disc[u]`，说明 `u` 是一个 SCC 的根节点
   - 从栈中弹出节点直到 `u` 被弹出，这些节点构成一个 SCC

### 拓扑编号保证

Tarjan 算法中，SCC 的发现顺序是逆拓扑序（先发现的 SCC 没有指向后发现的 SCC 的边）。因此，我们将分量顺序反转后分配编号，即可保证：**缩点图中的边总是从小号分量指向大号分量**。

## 缩点图构建机制

### 构建流程

1. 运行 Tarjan 算法得到所有 SCC 及其编号
2. 遍历原图的每条边 `(u, v)`：
   - 找到 `u` 所属的分量 `cid_u`
   - 找到 `v` 所属的分量 `cid_v`
   - 如果 `cid_u != cid_v`，在缩点图中添加超边 `(cid_u, cid_v)`
3. 使用 `Set` 存储邻接表，自动对平行超边去重

### 性质保证

- **DAG 保证**：缩点图必然是有向无环图。如果缩点图中存在环，那么环上的所有 SCC 实际上应该属于同一个更大的 SCC，与 SCC 的极大性矛盾。
- **边去重**：邻接表使用 `Set` 存储，同一对分量之间的多条平行边会自动合并为一条超边。
- **拓扑编号**：由于 SCC 编号已按拓扑序分配，缩点图中的边总是 `(小ID, 大ID)`。

## 时间复杂度分析

| 操作 | 时间复杂度 | 说明 |
|------|-----------|------|
| SCC 检测 | O(V + E) | 每个节点和边各访问一次 |
| 缩点图构建 | O(V + E) | 遍历所有节点和边一次 |
| 查询节点所属 SCC | O(1) | 字典查找 |
| 查询 SCC 包含节点 | O(k) | k 为分量大小 |
| DAG 判定 | O(C + E') | C 为分量数，E' 为超边数 |

## 使用示例

### 基础示例：多 SCC 图分析

```python
from solocoder_py.scc import DirectedGraph, TarjanSCC

# 构建有向图
g = DirectedGraph()
g.add_edges([
    (0, 1), (1, 2), (2, 0),  # SCC 0: {0, 1, 2}
    (2, 3),
    (3, 4), (4, 5), (5, 3),  # SCC 1: {3, 4, 5}
    (5, 6),
    (6, 7), (7, 8), (8, 6),  # SCC 2: {6, 7, 8}
])

# 检测 SCC
solver = TarjanSCC(g)
result = solver.find_sccs()

print(f"共 {len(result)} 个强连通分量")
for cid in range(len(result)):
    nodes = result.get_component_nodes(cid)
    print(f"分量 {cid}: {nodes}")

# 查询节点所属分量
print(f"节点 0 属于分量 {result.get_component_id(0)}")
print(f"节点 5 属于分量 {result.get_component_id(5)}")

# 构建缩点图
cond = solver.build_condensation(result)
print(f"缩点图是 DAG: {cond.is_dag()}")
print(f"缩点图边: {cond.get_edges()}")

# 验证拓扑编号
for from_cid, to_cid in cond.get_edges():
    assert from_cid < to_cid  # 边总是从小号指向大号
```

### 强连通图示例

```python
from solocoder_py.scc import DirectedGraph, TarjanSCC

g = DirectedGraph()
g.add_edges([
    (0, 1), (1, 2), (2, 0),
    (0, 3), (3, 0),
])

solver = TarjanSCC(g)
result = solver.find_sccs()
assert len(result) == 1  # 整个图是一个 SCC
assert set(result.get_component_nodes(0)) == {0, 1, 2, 3}

cond = solver.build_condensation(result)
assert cond.num_components == 1
assert len(cond.get_edges()) == 0  # 单个节点没有边
```

### 离散图示例

```python
from solocoder_py.scc import DirectedGraph, TarjanSCC

g = DirectedGraph()
for i in range(5):
    g.add_node(i)  # 5 个孤立节点，无边

solver = TarjanSCC(g)
result = solver.find_sccs()
assert len(result) == 5  # 每个节点自成一个 SCC

for i in range(5):
    nodes = result.get_component_nodes(i)
    assert len(nodes) == 1
```

### 包含自环的图

```python
from solocoder_py.scc import DirectedGraph, TarjanSCC

g = DirectedGraph()
g.add_edges([
    (0, 0),              # 自环
    (0, 1), (1, 0),      # SCC: {0, 1}
    (2, 2),              # 自环
    (2, 3), (3, 2),      # SCC: {2, 3}
])

solver = TarjanSCC(g)
result = solver.find_sccs()
assert len(result) == 2

c0 = result.get_component_id(0)
assert result.get_component_id(1) == c0

c1 = result.get_component_id(2)
assert result.get_component_id(3) == c1

assert c0 < c1  # 边 (1,2) 保证 c0 -> c1
```

### 平行边去重

```python
from solocoder_py.scc import DirectedGraph, TarjanSCC

g = DirectedGraph()
g.add_edges([
    (0, 1), (1, 0),      # SCC 0
    (0, 2), (0, 2),      # 重复边
    (1, 2), (1, 2),      # 重复边
    (2, 3), (3, 2),      # SCC 1
    (2, 4),
    (4, 5), (5, 4),      # SCC 2
    (3, 4), (3, 4),      # 重复边
])

solver = TarjanSCC(g)
result = solver.find_sccs()
cond = solver.build_condensation(result)

edges = cond.get_edges()
assert len(edges) == len(set(edges))  # 无重复边
```

### 异常处理

```python
from solocoder_py.scc import (
    DirectedGraph, TarjanSCC,
    NodeNotFoundError, EmptyGraphError
)

# 空图
g = DirectedGraph()
solver = TarjanSCC(g)
result = solver.find_sccs()
assert len(result) == 0  # 空结果

try:
    solver.build_condensation()  # 空图不能构建缩点图
except EmptyGraphError as e:
    print(f"错误: {e}")

# 非空图查询不存在的节点
g2 = DirectedGraph()
g2.add_edge(0, 1)
solver2 = TarjanSCC(g2)
result2 = solver2.find_sccs()

try:
    result2.get_component_id(999)
except NodeNotFoundError as e:
    print(f"错误: {e}")
```
