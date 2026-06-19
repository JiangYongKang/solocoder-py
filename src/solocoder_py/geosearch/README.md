# 地理位置邻近搜索模块

本模块提供基于内存的地理位置邻近搜索实现，支持经纬度坐标的邻近点搜索，采用包围盒预过滤 + Haversine 精确距离计算的两级搜索策略。

## 模块功能

- **包围盒预过滤**：基于经纬度构建搜索区域的矩形包围盒，利用纬度/经度弧长的近似特性快速排除明显超出范围的候选点，减少后续精确计算的开销
- **Haversine 精确距离计算**：对包围盒过滤后的候选点，使用 Haversine 公式计算球面上两点间的大圆距离，确保距离计算的准确性
- **结果排序**：按计算出的精确距离升序排序候选点
- **返回数量限制**：支持指定返回最近的 N 个点
- **坐标校验**：完整的经纬度坐标合法性校验，包括数值范围、类型、NaN/Inf 等边界情况
- **跨反子午线支持**：正确处理包围盒跨越 ±180° 经线的场景
- **极地附近处理**：正确处理南北极附近纬度范围受限的场景

## 核心类职责

### GeoSearchEngine

地理位置搜索的核心引擎类，负责维护候选点集合并执行搜索操作。

| 方法 / 属性 | 说明 |
|------------|------|
| `__init__(candidates=None)` | 构造函数，可选地接受初始候选点列表 |
| `add_candidate(point)` | 添加单个候选点 |
| `add_candidates(points)` | 批量添加候选点 |
| `clear_candidates()` | 清空所有候选点 |
| `search(center, radius_km, limit=None)` | 执行邻近搜索，返回 `GeoSearchResponse` |
| `candidate_count` | 当前候选点总数（属性） |

`search` 方法参数：

- `center`：搜索中心点（`GeoPoint`）
- `radius_km`：搜索半径（公里），必须 >= 0
- `limit`：返回结果数量限制（可选），必须 >= 0，为 `None` 时返回所有匹配结果

### GeoPoint

表示一个经纬度坐标点，使用 `frozen=True` 确保不可变性。

- `latitude`：纬度，范围 [-90, 90]
- `longitude`：经度，范围 [-180, 180]

### BoundingBox

表示经纬度包围盒。

- `min_lat`：最小纬度
- `max_lat`：最大纬度
- `min_lng`：最小经度
- `max_lng`：最大经度

### GeoSearchResult

单个搜索结果。

- `point`：候选点坐标（`GeoPoint`）
- `distance_km`：到中心点的精确距离（公里）

### GeoSearchResponse

搜索响应。

- `results`：搜索结果列表（`list[GeoSearchResult]`），按距离升序排列
- `total_count`：最终返回的结果数量
- `filtered_count`：经过包围盒预过滤后的候选点数量

## 包围盒预过滤策略

### 近似公式

包围盒预过滤利用地球表面经纬度的弧长近似特性：

**纬度偏移量计算**：
```
纬度偏移量（度） = 搜索半径（公里） / 111.32
```
纬度每度对应的弧长近似为常数，约 111.32 公里。

**经度偏移量计算**：
```
经度偏移量（度） = 搜索半径（公里） / (111.32 × cos(中心纬度))
```
经度每度对应的弧长随纬度变化，在赤道处约为 111.32 公里，在极地附近趋近于 0。

### 包围盒构建

1. 计算纬度偏移量，得到 `[min_lat, max_lat]`
2. 计算经度偏移量，得到 `[min_lng, max_lng]`
3. 对纬度范围进行边界夹紧，确保在 [-90, 90] 范围内
4. 当中心靠近极地时，调整纬度范围以保持合理的搜索区域

### 极地附近处理

当中心点靠近南北极（纬度接近 ±90°）时，纬度范围可能超出 [-90, 90] 边界。此时：
- 将超出的边界夹紧到 ±90°
- 向相反方向扩展，保持搜索范围的对称性

### 跨反子午线处理

当经度范围超出 [-180, 180] 边界时，包围盒会跨越反子午线（±180° 经线）。此时 `min_lng > max_lng`，在判断点是否在包围盒内时使用 OR 逻辑：
```
lng_ok = (lng >= min_lng) OR (lng <= max_lng)
```

### 过滤效率

包围盒预过滤可以快速排除大部分明显超出范围的候选点，将后续需要执行 Haversine 计算的点数量减少到原来的一小部分。对于均匀分布的点集，过滤效率约为：
```
过滤后点数 ≈ 总点数 × (π × r²) / (4 × r²) = 总点数 × π/4 ≈ 总点数 × 78.5%
```
实际效率取决于点的分布情况和搜索半径。

## Haversine 距离计算原理

Haversine 公式用于计算球面上两点之间的大圆距离（即最短距离）。

### 公式推导

对于球面上的两点 P1(φ1, λ1) 和 P2(φ2, λ2)：
- φ 为纬度（弧度）
- λ 为经度（弧度）
- R 为地球半径（取平均值 6371 公里）

计算步骤：

1. 计算经纬度差：
   ```
   Δφ = φ2 - φ1
   Δλ = λ2 - λ1
   ```

2. 计算 Haversine 函数值：
   ```
   a = sin²(Δφ/2) + cos(φ1) × cos(φ2) × sin²(Δλ/2)
   ```

3. 计算中心角：
   ```
   c = 2 × atan2(√a, √(1-a))
   ```

4. 计算距离：
   ```
   d = R × c
   ```

### 实现特点

- 使用 `math.radians()` 将角度转换为弧度
- 使用 `math.atan2()` 确保在所有象限都能正确计算角度
- 地球半径采用平均半径 6371 公里
- 距离计算精度约为 ±0.5%（由于地球并非完美球体）

## 返回数量限制策略

1. 对所有通过距离校验的候选点按距离升序排序
2. 如果指定了 `limit` 参数：
   - 当过滤后的候选点数量 > `limit`，只返回前 `limit` 个最近的点
   - 当过滤后的候选点数量 ≤ `limit`，返回所有找到的点
3. `limit = 0` 时返回空结果列表
4. `limit = None` 时返回所有匹配的点

## 异常类

| 异常类 | 说明 | 触发场景 |
|--------|------|----------|
| `GeoSearchError` | 地理位置搜索操作的基类异常 | — |
| `InvalidLatitudeError` | 纬度无效时抛出 | 纬度超出 [-90, 90]、NaN、Inf、非数值类型 |
| `InvalidLongitudeError` | 经度无效时抛出 | 经度超出 [-180, 180]、NaN、Inf、非数值类型 |
| `InvalidRadiusError` | 搜索半径或返回限制无效时抛出 | 搜索半径 < 0、返回限制 < 0 |
| `InvalidCoordinateError` | 坐标无效的通用异常 | 预留 |

## 使用示例

### 基本搜索

```python
from solocoder_py.geosearch import GeoPoint, GeoSearchEngine

# 创建候选点列表
candidates = [
    GeoPoint(latitude=39.9042, longitude=116.4074),  # 北京
    GeoPoint(latitude=31.2304, longitude=121.4737),  # 上海
    GeoPoint(latitude=22.5431, longitude=114.0579),  # 深圳
    GeoPoint(latitude=30.5728, longitude=114.3055),  # 武汉
]

# 初始化搜索引擎
engine = GeoSearchEngine(candidates=candidates)

# 以北京为中心，搜索半径 1000 公里内的点
center = GeoPoint(latitude=39.9042, longitude=116.4074)
response = engine.search(center, radius_km=1000.0)

print(f"包围盒过滤后候选点数: {response.filtered_count}")
print(f"最终匹配点数: {response.total_count}")
for result in response.results:
    print(f"  ({result.point.latitude:.4f}, {result.point.longitude:.4f}) "
          f"距离: {result.distance_km:.2f} 公里")
```

### 限制返回数量

```python
# 只返回最近的 3 个点
response = engine.search(center, radius_km=2000.0, limit=3)
print(f"返回前 {response.total_count} 个最近点:")
for result in response.results:
    print(f"  距离: {result.distance_km:.2f} 公里")
```

### 增量添加候选点

```python
engine = GeoSearchEngine()
engine.add_candidate(GeoPoint(39.9042, 116.4074))
engine.add_candidates([
    GeoPoint(31.2304, 121.4737),
    GeoPoint(22.5431, 114.0579),
])
print(f"当前候选点数: {engine.candidate_count}")

engine.clear_candidates()
print(f"清空后候选点数: {engine.candidate_count}")
```

### 跨反子午线搜索

```python
# 在斐济附近搜索（靠近反子午线）
center = GeoPoint(latitude=-18.1248, longitude=178.4501)  # 斐济苏瓦

# 候选点分布在反子午线两侧
candidates = [
    GeoPoint(-18.1248, 179.0),    # 苏瓦以东
    GeoPoint(-18.1248, -179.0),   # 苏瓦以西（跨越反子午线）
    GeoPoint(-18.1248, 177.0),    # 苏瓦以西（正常经度）
]

engine = GeoSearchEngine(candidates=candidates)
response = engine.search(center, radius_km=200.0)

print(f"跨反子午线搜索结果: {response.total_count} 个点")
for result in response.results:
    print(f"  经度: {result.point.longitude:.1f}, 距离: {result.distance_km:.2f} 公里")
```

### 极地附近搜索

```python
# 在北极附近搜索
center = GeoPoint(latitude=89.0, longitude=0.0)

candidates = [
    GeoPoint(89.5, 0.0),      # 靠近北极点
    GeoPoint(89.0, 90.0),     # 同一纬度，不同经度
    GeoPoint(89.0, -90.0),    # 同一纬度，不同经度
    GeoPoint(89.0, 180.0),    # 反子午线
]

engine = GeoSearchEngine(candidates=candidates)
response = engine.search(center, radius_km=100.0)

print(f"极地附近搜索结果: {response.total_count} 个点")
```

### 异常处理

```python
from solocoder_py.geosearch import (
    InvalidLatitudeError,
    InvalidLongitudeError,
    InvalidRadiusError,
)

try:
    engine.search(GeoPoint(91.0, 0.0), radius_km=10.0)
except InvalidLatitudeError as e:
    print(f"纬度错误: {e}")

try:
    engine.search(GeoPoint(0.0, 181.0), radius_km=10.0)
except InvalidLongitudeError as e:
    print(f"经度错误: {e}")

try:
    engine.search(center, radius_km=-5.0)
except InvalidRadiusError as e:
    print(f"半径错误: {e}")
```

## 性能特点

- **时间复杂度**：O(N) 其中 N 为候选点总数。包围盒过滤为 O(N)，Haversine 计算为 O(M) 其中 M 为过滤后的点数（M ≤ N），排序为 O(M log M)
- **空间复杂度**：O(N) 用于存储候选点
- **预过滤效率**：对于均匀分布的点集，包围盒过滤通常可以排除约 20% 的候选点，显著减少 Haversine 计算量
- **适用场景**：中小规模的内存数据集（万级到十万级点），对于更大规模数据集建议使用 R-tree 或 GeoHash 等空间索引

## 精度说明

- Haversine 公式假设地球为完美球体，实际距离计算存在约 ±0.5% 的误差
- 对于需要更高精度的场景，应使用 Vincenty 公式或考虑地球椭球模型
- 包围盒预过滤是近似的，可能包含实际距离略大于搜索半径的点（尤其是在包围盒的角落处），这些点会在后续的 Haversine 精确计算中被过滤掉
