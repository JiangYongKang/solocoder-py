# Pathfinding - A* 网格寻路域

## 模块功能

`pathfinding` 模块提供了基于 A* 算法的二维网格寻路实现，使用内存数据结构模拟网格地图。支持可配置的地形权重代价、八方向移动（含对角线）、路径点简化压缩等功能。

### 核心特性

1. **A* 寻路算法**：在二维网格上实现标准 A* 算法，支持通过/不可通过两种格子类型
2. **可配置权重代价**：每个格子可设置独立的移动代价权重（默认 1.0），支持不同地形类型
3. **八方向移动**：支持上、下、左、右及四个对角线方向，对角线移动成本为直线移动的 √2 倍（1.414）
4. **路径简化压缩**：移除共线的冗余中间路径点，输出简化后的路径序列

## 核心类职责

### `GridMap`

网格地图数据结构，负责管理二维网格的格子状态。

主要方法：
- `set_wall(point) / set_passable(point, passable)`：设置格子的可通过性
- `set_weight(point, weight) / set_terrain(point, weight, passable)`：设置格子权重和地形
- `get_neighbors(point, allow_diagonal)`：获取相邻可达格子及其移动代价
- `is_passable(point) / in_bounds(point)`：查询格子属性
- `from_char_map(char_map, weight_map)`：从字符地图创建网格

### `AStarFinder`

A* 寻路算法核心类，接收 GridMap 并执行寻路计算。

主要方法：
- `find_path(start, goal) -> PathResult`：执行寻路，返回路径结果

属性：
- `allow_diagonal`：是否允许对角线移动
- `heuristic`：当前使用的启发式函数

### `PathResult`

寻路结果容器，包含：

- `path`：有序路径点序列（`List[Point]`）
- `cost`：路径总代价
- `simplified_path`：简化后的路径序列（需调用 `simplify_path_result` 后填充）
- `failure_reason`：寻路失败时的原因描述
- `found`：是否成功找到路径
- `length`：路径点数量

### `Point`

不可变的二维坐标点（frozen dataclass），支持加法运算和迭代解包。

### 启发式函数

模块提供四种启发式函数：

| 函数 | 适用场景 | 公式 |
|------|----------|------|
| `manhattan_distance` | 四方向移动 | \|Δx\| + \|Δy\| |
| `euclidean_distance` | 自由移动 | √(Δx² + Δy²) |
| `chebyshev_distance` | 八方向移动（无代价区分） | max(\|Δx\|, \|Δy\|) |
| `octile_distance` | 八方向移动（对角线代价 √2） | max(Δx, Δy) + (√2 - 1) × min(Δx, Δy) |

## A* 算法原理

### 基本原理

A* 是一种启发式搜索算法，用于在图（或网格）中寻找从起点到目标点的最短路径。它结合了 Dijkstra 算法的最短路径保证和贪心最佳优先搜索的效率。

核心评估函数：

```
f(n) = g(n) + h(n)
```

- **g(n)**：从起点到节点 n 的实际代价（已知）
- **h(n)**：从节点 n 到目标点的启发式估计代价
- **f(n)**：经过节点 n 的路径的估计总代价

### 算法流程

1. 将起点加入开放列表（Open Set），g(start) = 0
2. 从开放列表中取出 f(n) 最小的节点 n
3. 如果 n 是目标点，回溯构建路径并返回
4. 将 n 移入关闭列表（Closed Set）
5. 遍历 n 的所有邻居节点 m：
   - 如果 m 在关闭列表中，跳过
   - 计算新的 g 值：tentative_g = g(n) + cost(n, m)
   - 如果 tentative_g < g(m)，更新 g(m) 和父节点
   - 将 m 加入开放列表
6. 重复步骤 2-5，直到开放列表为空（无路径）或找到目标

### 启发式函数选择

启发式函数的选择直接影响 A* 算法的效率和正确性：

- **可采纳性（Admissibility）**：h(n) 永远不超过从 n 到目标的实际最短路径代价。可采纳的启发式保证 A* 找到最优路径
- **一致性（Consistency）**：h(n) ≤ cost(n, m) + h(m)。一致的启发式保证节点不会被重复扩展

本模块的默认选择策略：
- **四方向移动**：默认使用曼哈顿距离，因为它是四方向网格上可采纳且一致的启发式
- **八方向移动**：默认使用 Octile 距离，因为它精确反映了八方向移动的最优代价估计，优于曼哈顿距离和切比雪夫距离

### 代价计算

- 直线移动代价：`1.0 × 目标格子权重`
- 对角线移动代价：`1.414 × 目标格子权重`
- 防止穿墙：对角线移动时，两个相邻正方向格子必须均可通过

### 路径简化

A* 输出的原始路径包含每一步的格子坐标。简化算法移除共线的中间点：如果连续三个路径点在同一直线上（向量叉积为零），则中间点被移除。这大幅减少了路径点数量，同时保持路径的几何正确性。

## 使用示例

### 基本寻路

```python
from solocoder_py.pathfinding import GridMap, AStarFinder, Point

# 创建 10x10 开阔地图
grid = GridMap(width=10, height=10)

# 添加障碍物
grid.set_wall(Point(5, 2))
grid.set_wall(Point(5, 3))
grid.set_wall(Point(5, 4))
grid.set_wall(Point(5, 5))

# 创建寻路器（默认八方向移动）
finder = AStarFinder(grid)

# 寻找路径
result = finder.find_path(Point(0, 0), Point(9, 9))

if result.found:
    print(f"路径长度: {result.length}, 总代价: {result.cost:.2f}")
    for pt in result.path:
        print(f"  -> ({pt.x}, {pt.y})")
else:
    print(f"寻路失败: {result.failure_reason}")
```

### 带权重的地形

```python
from solocoder_py.pathfinding import GridMap, AStarFinder, Point

grid = GridMap(width=10, height=10)

# 设置沼泽地形（高代价）
for x in range(3, 7):
    for y in range(3, 7):
        grid.set_terrain(Point(x, y), weight=5.0)

# 设置道路（低代价）
for x in range(10):
    grid.set_terrain(Point(x, 0), weight=0.5)

finder = AStarFinder(grid)
result = finder.find_path(Point(0, 0), Point(9, 9))
```

### 从字符地图创建

```python
from solocoder_py.pathfinding import GridMap, AStarFinder, Point

char_map = [
    "..........",
    ".###......",
    "..........",
    "......###.",
    "..........",
]

# # 表示墙壁，~ 可映射为高代价地形
grid = GridMap.from_char_map(
    char_map,
    weight_map={"~": 5.0},  # ~ 字符映射为代价 5.0 的地形
)

finder = AStarFinder(grid)
result = finder.find_path(Point(0, 0), Point(9, 4))
```

### 四方向移动 + 曼哈顿启发式

```python
from solocoder_py.pathfinding import (
    GridMap, AStarFinder, Point, manhattan_distance
)

grid = GridMap(width=10, height=10)
finder = AStarFinder(
    grid,
    allow_diagonal=False,
    heuristic=manhattan_distance,
)
result = finder.find_path(Point(0, 0), Point(5, 5))
```

### 路径简化

```python
from solocoder_py.pathfinding import (
    GridMap, AStarFinder, Point, simplify_path_result
)

grid = GridMap(width=20, height=20)
finder = AStarFinder(grid)
result = finder.find_path(Point(0, 0), Point(19, 0))

# 简化路径
simplified = simplify_path_result(result)
print(f"原始路径点: {result.length}, 简化后: {len(simplified.simplified_path)}")
```

## 异常处理

| 异常类 | 触发场景 |
|--------|----------|
| `CoordinateOutOfBoundsError` | 起点或终点超出网格边界 |
| `StartNotPassableError` | 起点位于不可通过的格子上 |
| `GoalNotPassableError` | 终点位于不可通过的格子上 |
| `InvalidGridDimensionsError` | 网格宽度或高度为零或负数 |
| `PathfindingError` | 所有寻路异常的基类 |
