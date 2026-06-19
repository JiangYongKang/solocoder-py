# coord — 坐标参考系边界校验器

## 模块功能

`coord` 模块提供地理坐标（经纬度）的边界校验能力，包括：

1. **经纬度合法范围检查** — 校验坐标点是否落在 WGS 84 定义的合法范围内
2. **反子午线穿越检测** — 检测连续坐标点之间的连线是否穿越 ±180° 经线
3. **极点奇异性处理** — 识别极点及极近点，避免将极点附近的经度变化误判为异常

## 核心类的职责

### `Coordinate`

不可变数据类，表示一个经纬度坐标点。构造时自动拒绝 `NaN` 和 `Inf` 值。提供 `is_polar` 和 `is_near_polar` 属性用于极点判断。

### `BoundingBox`

不可变数据类，表示一个矩形经纬度边界框。构造时校验 `min_lat <= max_lat`。提供 `contains()` 方法判断坐标点是否在边界内。

### `CoordValidator`

核心校验器，提供以下功能：

- `validate_coordinate()` — 校验单个坐标点的经纬度是否在合法范围内
- `validate_coordinates()` — 校验一组坐标点，返回所有非法坐标的索引和原因
- `validate_against_bounds()` / `validate_list_against_bounds()` — 校验坐标是否在自定义矩形边界内
- `check_antimeridian_crossing()` — 检测两个连续坐标点是否穿越反子午线
- `check_antimeridian_crossings()` — 检测整条航线的所有航段
- `check_polar_singularity()` — 检查坐标的极点奇异性
- `validate_with_polar_awareness()` — 结合范围校验和极点感知的综合校验

### 辅助数据类

- `ValidationResult` — 校验结果，包含 `valid` 标志和 `invalid_coordinates` 列表
- `InvalidCoordinate` — 描述一个非法坐标，包含索引、经纬度值和原因
- `AntimeridianCrossing` — 描述一次反子午线穿越，包含穿越方向和跨越点
- `PolarCheckResult` — 描述极点奇异性检查结果
- `CrossingDirection` — 枚举：`EASTWARD`（东向穿越）、`WESTWARD`（西向穿越）

## 经纬度合法范围的定义

| 维度   | 最小值   | 最大值  |
|--------|----------|---------|
| 纬度   | -90.0    | 90.0    |
| 经度   | -180.0   | 180.0   |

- 边界值视为合法：纬度 90.0、经度 -180.0 等均通过校验
- 超出范围的值（如纬度 90.001、经度 180.001）判定为非法
- `NaN` 和 `Inf` 在 `Coordinate` 构造时直接抛出 `NonFiniteCoordinateError`

## 反子午线穿越的判断依据

反子午线（Antimeridian）是经度 ±180° 的分界线。当两个连续坐标点的经度之差绝对值 **大于 180°** 时，判定为穿越了反子午线。

- **经度差恰好等于 180°** — 不判定为穿越（边界条件）
- **东向穿越（EASTWARD）** — 从西半球经正 180° 向东进入东半球，例如 (170°, -170°)
- **西向穿越（WESTWARD）** — 从东半球经负 180° 向西进入西半球，例如 (-170°, 170°)
- 穿越点通过线性插值计算：沿大圆航线在 ±180° 经度处的纬度

## 极点奇异性的概念与处理方式

在南北极点（纬度 ±90°），所有经度值代表同一个物理点，因此经度的定义存在奇异性。极点附近（如纬度 89.999°）的经度变化在实际地理意义上非常小，不应视为异常。

校验器的处理方式：

1. **极点识别** — 纬度绝对值与 90° 之差小于 1e-9 的坐标标记为 `is_polar=True`
2. **极近点识别** — 纬度与极点的距离小于可配置阈值（默认 0.001°）的坐标标记为 `is_near_polar=True`
3. **极点经度不报异常** — 极点坐标上的任意经度值均不触发警告
4. **越界极近点警告** — 纬度略超极点（如 90.001）会产生明确的 "exceeds" 警告
5. **极近点提醒** — 纬度接近但未达到极点时产生 "near the pole" 提醒

## 使用示例

### 基本范围校验

```python
from solocoder_py.coord import CoordValidator, Coordinate

validator = CoordValidator()

# 校验单个坐标
coord = Coordinate(latitude=45.0, longitude=90.0)
result = validator.validate_coordinate(coord)
print(result.valid)  # True

# 校验非法坐标
bad_coord = Coordinate(latitude=91.0, longitude=0.0)
result = validator.validate_coordinate(bad_coord)
print(result.valid)  # False
print(result.invalid_coordinates[0].reason)  # latitude 91.0 out of range [-90.0, 90.0]
```

### 批量坐标校验

```python
coords = [
    Coordinate(latitude=0.0, longitude=0.0),
    Coordinate(latitude=91.0, longitude=0.0),   # 非法
    Coordinate(latitude=0.0, longitude=181.0),   # 非法
]
result = validator.validate_coordinates(coords)
print(result.valid)  # False
for inv in result.invalid_coordinates:
    print(f"索引 {inv.index}: {inv.reason}")
```

### 反子午线穿越检测

```python
from solocoder_py.coord import CrossingDirection

start = Coordinate(latitude=0.0, longitude=170.0)
end = Coordinate(latitude=0.0, longitude=-170.0)
crossing = validator.check_antimeridian_crossing(start, end)

print(crossing.crosses)      # True
print(crossing.direction)    # CrossingDirection.EASTWARD
print(crossing.crossing_point)  # Coordinate(latitude=0.0, longitude=180.0)
```

### 极点奇异性检查

```python
pole = Coordinate(latitude=90.0, longitude=45.0)
polar = validator.check_polar_singularity(pole)
print(polar.is_polar)   # True
print(polar.latitude_warning)  # None — 极点经度不报异常

near_pole = Coordinate(latitude=89.999, longitude=0.0)
polar = validator.check_polar_singularity(near_pole)
print(polar.is_near_polar)  # True
print(polar.latitude_warning)  # "latitude 89.999 is near the pole; ..."
```

### 自定义边界校验

```python
from solocoder_py.coord import BoundingBox

bounds = BoundingBox(min_lat=20.0, max_lat=50.0, min_lon=100.0, max_lon=130.0)
coord = Coordinate(latitude=55.0, longitude=110.0)
result = validator.validate_against_bounds(coord, bounds)
print(result.valid)  # False — 纬度超出自定义边界
```
