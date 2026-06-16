# graph_cycle 有向图环检测器

## 模块功能

`graph_cycle` 模块提供了基于 DFS 三色标记法的有向图环检测功能。它能够：

- 检测有向图中是否存在环
- 找出图中的所有环并返回完整的环路径
- 对检测到的环进行去重（同一旋转视为同一个环）
- 单独报告自环节点
- 支持从指定节点出发检测可达的环

## 核心类职责

### `DirectedGraph`
有向图数据结构，使用邻接表表示图。

- `add_node(node)`: 添加节点
- `add_edge(from_node, to_node)`: 添加有向边
- `has_node(node)`: 检查节点是否存在
- `get_nodes()`: 获取所有节点列表
- `get_neighbors(node)`: 获取节点的所有邻居
- `node_count`: 节点数
- `edge_count`: 边数

### `CycleDetector`
环检测器，封装了 DFS 三色标记法的核心逻辑。

- `detect_cycles()`: 检测图中的所有环，返回去重后的环列表
- `detect_cycles_from_node(start_node)`: 从指定节点出发，检测所有可达的环
- `has_cycle()`: 判断图中是否存在任意环
- `get_cycle_nodes()`: 获取所有参与环的节点集合
- `set_graph(graph)`: 更换检测的图

### `Cycle`
表示一个环的数据类。

- `nodes`: 环的节点列表，按遍历顺序排列
- `is_self_loop()`: 判断是否为自环
- `canonical_key()`: 获取环的规范化表示（用于去重比较）

### `NodeColor`
节点颜色枚举，用于 DFS 三色标记：

- `WHITE`: 未访问
- `GRAY`: 正在当前递归栈中访问
- `BLACK`: 已完成访问

## DFS 三色标记法原理

### 基本思想

三色标记法是对标准 DFS 的增强，通过为每个节点分配三种状态之一来追踪遍历进度：

1. **白色 (WHITE)**: 节点尚未被访问
2. **灰色 (GRAY)**: 节点正在被访问，即位于当前 DFS 递归栈中
3. **黑色 (BLACK)**: 节点及其所有后代均已访问完成

### 环检测流程

1. 初始化所有节点为白色
2. 遍历图中每个白色节点，启动 DFS：
   - 将当前节点标记为灰色，压入递归栈
   - 遍历当前节点的所有邻居：
     - 若邻居为白色：对该邻居递归执行 DFS
     - 若邻居为灰色：**发现环！** 邻居在当前递归栈中，说明从邻居到当前节点形成了一个环
     - 若邻居为黑色：跳过，该子树已处理完毕
   - 当前节点的所有邻居处理完毕后，将其标记为黑色，弹出递归栈

### 环路径提取

当遇到灰色邻居时，说明该邻居位于当前 DFS 递归栈中。环路径即为递归栈中从该灰色邻居位置到栈顶（当前节点）的子序列。

例如：递归栈为 `[A, B, C, D]`，处理 D 的邻居时发现 B 为灰色，则环路径为 `[B, C, D]`，对应环 `B → C → D → B`。

### 环去重

同一个环可能因遍历起点不同而被多次检测到。例如 `A→B→C→A` 和 `B→C→A→B` 实际是同一个环。

去重方法：将环的节点序列旋转至字典序最小的节点作为起点，形成规范化表示。两个环若规范化表示相同，则视为同一个环。

## 使用示例

### 基本用法

```python
from solocoder_py.graph_cycle import CycleDetector, DirectedGraph

# 构建有向图
graph = DirectedGraph()
graph.add_edge("A", "B")
graph.add_edge("B", "C")
graph.add_edge("C", "A")  # 形成环 A→B→C→A
graph.add_edge("C", "D")
graph.add_edge("D", "E")

# 检测环
detector = CycleDetector(graph)
cycles = detector.detect_cycles()

for cycle in cycles:
    print(f"检测到环: {cycle.nodes}")
    print(f"是否为自环: {cycle.is_self_loop()}")

# 判断是否有环
if detector.has_cycle():
    print("图中存在环")

# 获取所有在环中的节点
print(f"参与环的节点: {detector.get_cycle_nodes()}")
```

### 检测自环

```python
graph = DirectedGraph()
graph.add_edge("S", "S")  # 自环
detector = CycleDetector(graph)
cycles = detector.detect_cycles()
# cycles 包含 Cycle(nodes=["S"])
```

### 从指定节点检测

```python
graph = DirectedGraph()
graph.add_edge("A", "B")
graph.add_edge("B", "C")
graph.add_edge("C", "B")
graph.add_edge("X", "Y")  # 独立分支，无环

detector = CycleDetector(graph)
# 只检测从 A 可达的环
cycles_from_a = detector.detect_cycles_from_node("A")
# 检测到 [B, C] 这个环
```

### 异常处理

```python
from solocoder_py.graph_cycle import NodeNotFoundError

detector = CycleDetector()
try:
    detector.detect_cycles_from_node("不存在的节点")
except NodeNotFoundError as e:
    print(f"错误: {e}")
```
