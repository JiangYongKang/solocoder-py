# Point-in-Polygon (PIP) 判定引擎

## 模块功能
---------

本模块实现了基于射线法的点在多边形内判定引擎，支持使用经纬度或平面坐标点作为输入。提供以下为核心功能：

- **射线法判定**：从给定点向右方发射水平射线，通过统计射线与多边形边的交点数量来判断点是否在多边形内部

- **边界情况处理**：正确处理顶点相交、水平边共线、点在边上等边界情况

- **坐标校验**：对输入坐标进行合法性校验，拒绝 NaN、Inf 等非法值

## 核心类职责
-------

### Point

表示二维坐标点，支持平面坐标或经纬度点均可使用。

- `x: float - x 坐标（或经度）

- `y: float - y 坐标（或纬度）

### Polygon

表示多边形，由有序顶点序列定义，首尾相连形成闭合环。

- `vertices: List[Point] - 多边形顶点列表

- `vertex_count: int - 顶点数量

- `from_tuples(vertices)` - 从元组列表构造多边形

### RayCastingEngine

射线法判定引擎，是本模块的核心类。

- `contains(polygon, point) -> PointLocation

  判断点相对于多边形的位置

- `is_inside(polygon, point) -> bool`

  判断点是否在多边形内部（含边界）

- `is_outside(polygon, point) -> bool`

  判断点是否在多边形外部

- `is_on_boundary(polygon, point) -> bool

  判断点是否在多边形边界上

- `contains_many(polygon, points) -> List[PointLocation]

  批量判定多个点

### PointLocation (Enum

判定结果枚举：

- `INSIDE` - 点在多边形内部

- `OUTSIDE` - 点在多边形外部

- `ON_BOUNDARY` - 点在多边形边界上

## 射线法判定原理
---------------

### 基本思想

从待判定点 P 向右方发射一条水平射线，统计射线与多边形各边的交点数量：

- 交点数为奇数 → 点在多边形**内部**

- 交点数为偶数 → 点在多边形**外部**

```
    │
    │   ┌───────┐
    │   │       │
 P ─┼───►       │
    │   │       │
    │   └───────┘
    │

  射线与多边形交于 1 次（奇数）→ 点在内部
```

### 射线与边相交的各种情况

#### 1. 正常相交（边跨越射线）

```
    \       /
     \     /
  -------*-------  ← 射线
       / \
      /   \
```

边的两个端点分别在射线两侧，计为一次相交。

#### 2. 不相交（边在射线同侧）

```
      / \
     /   \
  -------*-------  ← 射线

  边整体在射线上方，不计相交
```

边的两个端点都在射线的同一侧，不计数。

#### 3. 射线经过顶点（两侧边异侧）

```
       /
      /
  ---*---  ← 射线
      \
       \
```

当射线恰好经过顶点，且该顶点的两条邻边分别在射线两侧，计为一次相交。

#### 4. 射线经过顶点（两侧边同侧）

```
      / \
     /   \
  ---*-----  ← 射线
```

当射线恰好经过顶点，且该顶点的两条邻边都在射线的同一侧，不计为相交。

#### 5. 射线与水平边共线

```
  ───────────  ← 射线与水平边重合
```

射线与多边形的一条水平边共线时，忽略该边，只考虑其端点与其他边的关系。

## 顶点和共线边边界情况处理规则
-----------------------------

### 顶点处理规则

当射线恰好经过多边形顶点时，采用"异侧计数原则：

1. 找到该顶点的前后相邻顶点

2. 如果两个相邻顶点分别在射线的两侧，则计为一次相交

3. 如果两个相邻顶点都在射线的同一侧，则不计为相交

### 共线边处理规则

1. 当射线与多边形的一条水平边共线时，不将该边计入交点统计

2. 对于共线水平边的端点，按照顶点处理规则进行判断

### 点在边上的判定

点在多边形某条边上时（点到线段的距离为零且投影在线段范围内，直接判定为 `ON_BOUNDARY`。

### 退化多边形处理

对于连续三个顶点共线的退化情况，判定引擎仍能正确工作，因为：

- 点在边上的检测会正确识别共线情况

- 射线法对共线边的处理不影响最终奇偶性判定

## 使用示例
---------

### 基本使用

```python
from solocoder_py.pip import Point, Polygon, RayCastingEngine, PointLocation

engine = RayCastingEngine()

square = Polygon.from_tuples([
    (0, 0),
    (10, 0),
    (10, 10),
    (0, 10),
])

point_inside = Point(5, 5)
point_outside = Point(15, 5)

result1 = engine.contains(square, point_inside)
assert result1 == PointLocation.INSIDE

result2 = engine.contains(square, point_outside)
assert result2 == PointLocation.OUTSIDE

assert engine.is_inside(square, point_inside) is True
assert engine.is_outside(square, point_outside) is True
```

### 判定边界点

```python
point_on_edge = Point(5, 0)
result = engine.contains(square, point_on_edge)
assert result == PointLocation.ON_BOUNDARY
assert engine.is_on_boundary(square, point_on_edge) is True
```

### 批量判定

```python
points = [Point(i, i) for i in range(15)]
results = engine.contains_many(square, points)
```

### 经纬度坐标

```python
beijing = Point(116.4074, 39.9042)
shanghai = Point(121.4737, 31.2304)

china_polygon = Polygon.from_tuples([
    (73.5, 53.5),
    (135.0, 53.5),
    (135.0, 18.0),
    (73.5, 18.0),
])

assert engine.is_inside(china_polygon, beijing) is True
```

### 异常处理

```python
from solocoder_py.pip import EmptyPolygonError, InsufficientVerticesError

try:
    Polygon.from_tuples([(0, 0), (1, 1)])
except InsufficientVerticesError:
    print("多边形顶点不足3个")
```
