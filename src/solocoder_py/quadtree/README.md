# Quadtree 四叉树空间索引模块

## 模块功能

本模块提供了一个基于内存的四叉树（Quadtree）空间索引实现，用于高效管理和查询二维空间中的点和矩形区域对象。四叉树通过递归地将二维空间分割为四个象限，使得范围查询只需检查相关的子区域，从而大幅提升查询效率。

主要功能：

- **点插入**：支持插入二维点对象，点由 x, y 坐标唯一标识
- **矩形区域插入**：支持插入矩形区域对象，由最小角坐标和宽高定义
- **范围查询**：给定查询矩形，返回所有与该矩形相交或包含的空间对象
- **自动分裂**：当节点内对象数量超过容量阈值时，节点自动分裂为四个子节点
- **最大深度约束**：限制四叉树的最大分裂深度，防止高密度数据下的无限递归

## 核心类的职责

### `Point` - 点对象

表示二维空间中的一个点。

- **属性**：
  - `x: float` - 点的 x 坐标
  - `y: float` - 点的 y 坐标
  - `data: Any` - 可选的附加数据

### `Rectangle` - 矩形区域对象

表示二维空间中的一个轴对齐矩形。

- **属性**：
  - `x: float` - 矩形左下角（最小角）的 x 坐标
  - `y: float` - 矩形左下角（最小角）的 y 坐标
  - `width: float` - 矩形的宽度
  - `height: float` - 矩形的高度
  - `data: Any` - 可选的附加数据

- **关键方法**：
  - `contains_point(point: Point) -> bool` - 判断点是否在矩形内（包含边界）
  - `intersects(other: Rectangle) -> bool` - 判断两个矩形是否相交
  - `contains(other: Rectangle) -> bool` - 判断矩形是否完全包含另一个矩形

### `Quadtree` - 四叉树主类

四叉树的对外接口类，提供插入、查询等操作。

- **构造参数**：
  - `boundary: Rectangle` - 四叉树的空间边界范围
  - `max_capacity: int` - 每个节点的最大对象容量，默认 4
  - `max_depth: int` - 树的最大深度，默认 10

- **属性**：
  - `boundary: Rectangle` - 四叉树的边界
  - `max_capacity: int` - 节点最大容量
  - `max_depth: int` - 最大深度
  - `point_count: int` - 当前点对象总数
  - `rectangle_count: int` - 当前矩形对象总数
  - `total_count: int` - 当前对象总数

- **关键方法**：
  - `insert(obj) -> None` - 插入点或矩形对象
  - `insert_point(point: Point) -> None` - 插入点对象
  - `insert_rectangle(rect: Rectangle) -> None` - 插入矩形对象
  - `query(range_rect: Rectangle) -> List` - 范围查询，返回相交的所有对象
  - `get_all() -> List` - 获取所有对象
  - `clear() -> None` - 清空四叉树

### `_QuadNode` - 四叉树内部节点

四叉树的内部节点实现，负责节点分裂、对象分配和递归查询。

- **属性**：
  - `boundary: Rectangle` - 节点的空间边界
  - `depth: int` - 当前节点深度（根节点深度为 0）
  - `points: List[Point]` - 节点中的点对象列表
  - `rectangles: List[Rectangle]` - 节点中的矩形对象列表
  - `northwest, northeast, southwest, southeast: Optional[_QuadNode]` - 四个子节点

- **关键方法**：
  - `insert_point(point: Point) -> None` - 插入点
  - `insert_rectangle(rect: Rectangle) -> None` - 插入矩形
  - `query(range_rect: Rectangle, results: List) -> None` - 递归查询
  - `_subdivide() -> None` - 分裂为四个子节点

## 分裂策略与象限编号规则

### 分裂触发条件

当节点中的对象总数（点数 + 矩形数）超过 `max_capacity` 阈值，并且当前节点深度小于 `max_depth` 时，节点会自动分裂为四个子节点。

### 象限划分

节点分裂时，以当前节点的中心点为界，将空间划分为四个象限：

```
         +-----------------+-----------------+
         |                 |                 |
         |   Northwest     |   Northeast     |
         |   (NW)          |   (NE)          |
         |                 |                 |
         +------- mid_y ---+------- mid_y ---+
         |                 |                 |
         |   Southwest     |   Southeast     |
         |   (SW)          |   (SE)          |
         |                 |                 |
         +-----------------+-----------------+
       min_x             mid_x             max_x
```

- **Northwest (NW) 西北象限**：x < mid_x, y >= mid_y
- **Northeast (NE) 东北象限**：x >= mid_x, y >= mid_y
- **Southwest (SW) 西南象限**：x < mid_x, y < mid_y
- **Southeast (SE) 东南象限**：x >= mid_x, y < mid_y

### 对象分配规则

**点对象**：根据点的坐标分配到对应的子象限中。
- 位于象限边界上的点（如 x == mid_x 或 y == mid_y）分配到右侧或上侧的象限。

**矩形对象**：
- 如果矩形完全包含在某个子象限内，则分配到该子节点
- 如果矩形跨越多个象限（即不能完全放入任何一个子象限），则保留在当前父节点中，不向下分配

## 范围查询的递归遍历逻辑

范围查询采用深度优先的递归遍历策略：

1. **节点相交检查**：从根节点开始，首先检查查询矩形与当前节点的边界是否相交。如果不相交，直接返回，跳过该子树。

2. **收集当前节点对象**：
   - 对每个点对象，检查是否在查询矩形内
   - 对每个矩形对象，检查是否与查询矩形相交

3. **递归遍历子节点**：如果当前节点有子节点，递归地对四个子节点执行查询。

4. **结果合并**：将所有匹配的对象收集到结果列表中返回。

### 查询优化

通过只遍历与查询矩形相交的子树，四叉树将查询复杂度从 O(n)（暴力遍历）降低到 O(log n) 平均情况。

## 最大深度约束

### 作用

最大深度约束限制了四叉树可以分裂的层数，防止在极高密度数据或数据分布极不均匀的情况下出现无限递归，避免内存耗尽和性能下降。

### 生效机制

- 当节点深度达到 `max_depth` 时，即使对象数量超过容量阈值，也不再分裂
- 所有新插入的对象都保留在该节点中
- 查询时会遍历该节点中的所有对象

### 选择建议

- 数据分布均匀：可设置较大的最大深度
- 数据分布不均或可能出现聚集：设置合理的最大深度防止过度分裂
- 默认值 10 适用于大多数场景

## 异常类型

- `QuadtreeError` - 四叉树异常基类
- `OutOfBoundsError` - 对象超出四叉树边界
- `DuplicatePointError` - 重复插入相同坐标的点
- `InvalidCapacityError` - 无效的容量参数
- `InvalidDepthError` - 无效的深度参数
- `InvalidRectangleError` - 无效的矩形（负宽/高）

## 使用示例

### 基本使用

```python
from solocoder_py.quadtree import Point, Quadtree, Rectangle

# 创建四叉树，边界为 (0, 0) 到 (200, 200)
boundary = Rectangle(x=0, y=0, width=200, height=200)
qt = Quadtree(boundary, max_capacity=4, max_depth=10)

# 插入点
qt.insert(Point(x=50, y=50, data="point1"))
qt.insert(Point(x=150, y=150, data="point2"))

# 插入矩形
qt.insert(Rectangle(x=20, y=20, width=40, height=40, data="rect1"))
qt.insert(Rectangle(x=100, y=100, width=60, height=60, data="big_rect"))

# 范围查询
query_rect = Rectangle(x=0, y=0, width=100, height=100)
results = qt.query(query_rect)

for obj in results:
    print(f"Found: {obj.data}")

# 获取所有对象
all_objects = qt.get_all()
print(f"Total objects: {len(all_objects)}")

# 清空四叉树
qt.clear()
```

### 处理异常

```python
from solocoder_py.quadtree import (
    DuplicatePointError,
    OutOfBoundsError,
    Point,
    Quadtree,
    Rectangle,
)

boundary = Rectangle(x=0, y=0, width=100, height=100)
qt = Quadtree(boundary)

# 插入越界点
try:
    qt.insert(Point(x=200, y=200))
except OutOfBoundsError as e:
    print(f"Out of bounds: {e}")

# 插入重复点
qt.insert(Point(x=50, y=50, data="first"))
try:
    qt.insert(Point(x=50, y=50, data="second"))
except DuplicatePointError as e:
    print(f"Duplicate point: {e}")
```
