# Geohash - 地理哈希编解码器

## 模块功能

`geohash` 模块提供了 Geohash 地理编码算法的完整实现。Geohash 是一种将经纬度坐标编码为字符串的地理哈希系统，通过将地球表面划分为网格来实现位置的近似表示。该模块支持以下特性：

- **可配置精度编码解码**：支持 1-12 位字符精度，精度越高表示的地理范围越小
- **包围盒计算**：从 Geohash 字符串直接推导所覆盖的地理矩形区域边界
- **邻胞枚举**：计算指定 Geohash 周围八个方向的相邻 Geohash
- **边界处理**：正确处理南北极点、经度 ±180 度反子午线等边界情况

## 核心类的职责

### 主要数据类

| 类名 | 职责 |
|------|------|
| `GeohashBoundingBox` | 表示 Geohash 覆盖的地理矩形区域，包含 min_lon、max_lon、min_lat、max_lat 四个边界值，以及中心点坐标和误差范围的计算属性 |
| `GeohashNeighbors` | 表示八个方向的邻胞 Geohash，提供 to_dict()、to_list() 等便捷方法 |
| `GeohashCodec` | 编解码器类，封装指定精度的编码/解码/包围盒/邻胞操作 |

### 便捷函数

| 函数名 | 功能 |
|--------|------|
| `encode(lat, lon, precision)` | 将经纬度编码为指定精度的 Geohash 字符串 |
| `decode(geohash)` | 将 Geohash 字符串解码为中心点坐标及误差范围 |
| `decode_bbox(geohash)` | 计算 Geohash 的包围盒边界 |
| `get_neighbors(geohash)` | 获取 Geohash 的八个邻胞 |

## Geohash 编码算法原理

Geohash 采用**经纬度交替二分逼近**的算法将二维坐标编码为一维字符串：

### 编码过程

1. **初始化范围**：纬度范围 [-90, 90]，经度范围 [-180, 180]
2. **交替二分**：
   - 从经度开始，交替对经度和纬度范围进行二分
   - 对于每个坐标值，判断其落在二分点的左侧（0）还是右侧（1）
   - 根据判断结果缩小对应坐标的范围
3. **位组合**：将每次二分产生的二进制位按顺序组合
4. **Base32 编码**：每 5 位二进制位映射为一个 Base32 字符（使用 `0123456789bcdefghjkmnpqrstuvwxyz` 字符表，去掉易混淆的 `a`, `i`, `l`, `o`）
5. **精度控制**：重复上述过程直到达到指定的字符数

### 解码过程

1. **Base32 解码**：将每个字符转换为 5 位二进制
2. **位分离**：按顺序分离出经度位和纬度位（偶数位为经度，奇数位为纬度）
3. **范围还原**：根据二进制位逐步还原经纬度的范围区间
4. **结果计算**：返回范围中心点作为坐标估计值，范围半长作为误差

## 精度与地理范围对应关系表

| 精度（字符数） | 纬度误差 ± | 经度误差 ± | 典型用途 |
|---------------|-----------|-----------|----------|
| 1 | ±2250 km | ±2500 km | 大洲、国家级别 |
| 2 | ±625 km | ±1250 km | 大型区域、省份 |
| 3 | ±78 km | ±78 km | 城市级别 |
| 4 | ±19.5 km | ±39 km | 区县级别 |
| 5 | ±2.4 km | ±2.4 km | 社区、街区 |
| 6 | ±0.61 km | ±1.2 km | 街道级别 |
| 7 | ±76 m | ±76 m | 大型建筑物 |
| 8 | ±9.5 m | ±19 m | 精确位置 |
| 9 | ±2.4 m | ±2.4 m | 房间级精度 |
| 10 | ±0.30 m | ±0.59 m | 人体级精度 |
| 11 | ±74 mm | ±74 mm | 亚分米级 |
| 12 | ±9.3 mm | ±19 mm | 厘米级精度 |

> **注意**：在实际应用中，由于浮点数精度限制，超过 8-9 位的精度在大多数场景下意义不大。

### 偶数精度与奇数精度的差异

由于 Geohash 采用经度优先的交替编码方式，且经度范围（360°）是纬度范围（180°）的两倍，因此偶数位和奇数位精度的包围盒形状有明显差异：

- **奇数精度**（1, 3, 5, 7, 9, 11）：经度位比纬度位多 1 位，但由于经度范围是纬度的两倍，最终经度和纬度方向的误差近似相等，包围盒近似正方形
- **偶数精度**（2, 4, 6, 8, 10, 12）：经度位和纬度位数量相同，但由于经度范围是纬度的两倍，经度方向的误差是纬度的两倍，包围盒呈现"宽 = 2 × 高"的矩形

## 邻胞枚举算法要点

### 基本原理

Geohash 字符串具有空间连续性，相邻的地理位置通常具有相似的 Geohash 前缀。邻胞枚举通过查找 Base32 字符映射表来计算相邻的 Geohash。

### 算法步骤

1. **奇偶性判断**：根据 Geohash 长度的奇偶性选择对应的邻接表
2. **字符查找**：对于最后一个字符，在邻接表中查找对应方向的字符
3. **边界处理**：
   - 如果最后一个字符位于边界（需要进位），则递归处理前缀部分
   - 如果前缀也需要进位且已达顶层，南北方向返回 None（极点边界），东西方向自动跨越反子午线
4. **对角线邻胞**：先计算南北方向邻胞，再在此基础上计算东西方向邻胞

### 特殊边界处理

| 边界类型 | 处理方式 |
|---------|---------|
| **北极点**（纬度 90°） | 向北的邻胞不存在，返回 None |
| **南极点**（纬度 -90°） | 向南的邻胞不存在，返回 None |
| **反子午线**（经度 ±180°） | 东西方向自动跨越，从 +180° 邻接 -180° |

## 包围盒计算方法

### 直接从二进制交织编码推导

包围盒计算无需完整解码出坐标，而是直接通过二进制位逐步缩小经纬度范围：

1. 初始化纬度范围 [-90, 90]，经度范围 [-180, 180]
2. 对于 Geohash 的每个字符，解码为 5 位二进制
3. 从高位到低位处理每一位：
   - 偶数位（从 0 开始）：更新经度范围，0 表示左半区，1 表示右半区
   - 奇数位：更新纬度范围，0 表示下半区，1 表示上半区
4. 最终得到的经纬度范围即为包围盒的四个边界

### 优化点

- 直接操作二进制位，无需额外的解码步骤
- 每一步只需要维护两个区间的四个边界值
- 时间复杂度 O(n)，n 为 Geohash 字符串长度

## 使用示例

### 基本编码解码

```python
from solocoder_py.geohash import encode, decode, decode_bbox, get_neighbors

# 编码：北京天安门坐标，精度 8 位
geohash = encode(39.9087, 116.3975, precision=8)
print(geohash)  # "wx4g09nj"

# 解码：返回中心点和误差
lat, lon, lat_err, lon_err = decode(geohash)
print(f"中心点: ({lat:.6f}, {lon:.6f})")
print(f"误差范围: 纬度±{lat_err:.6f}°, 经度±{lon_err:.6f}°")

# 计算包围盒
bbox = decode_bbox(geohash)
print(f"经度范围: [{bbox.min_lon:.6f}, {bbox.max_lon:.6f}]")
print(f"纬度范围: [{bbox.min_lat:.6f}, {bbox.max_lat:.6f}]")

# 获取邻胞
neighbors = get_neighbors(geohash)
print(f"北邻: {neighbors.north}")
print(f"南邻: {neighbors.south}")
print(f"东邻: {neighbors.east}")
print(f"西邻: {neighbors.west}")
```

### 编解码器类使用

```python
from solocoder_py.geohash import GeohashCodec

# 创建指定精度的编解码器
codec = GeohashCodec(precision=6)

# 编码多个坐标
locations = [
    (31.2304, 121.4737),  # 上海
    (22.5431, 114.0579),  # 深圳
    (30.5728, 104.0668),  # 成都
]

for lat, lon in locations:
    gh = codec.encode(lat, lon)
    print(f"({lat}, {lon}) -> {gh}")
```

### 包围盒邻接验证

```python
from solocoder_py.geohash import decode_bbox, get_neighbors

geohash = "9q9hx5"
bbox = decode_bbox(geohash)
neighbors = get_neighbors(geohash)

for neighbor_gh in neighbors:
    if neighbor_gh:
        neighbor_bbox = decode_bbox(neighbor_gh)
        is_adjacent = bbox.is_adjacent(neighbor_bbox)
        print(f"{neighbor_gh} 与原 Geohash 相邻: {is_adjacent}")
```

### 反子午线跨越测试

```python
from solocoder_py.geohash import encode, get_neighbors, decode_bbox

# 斐济附近（接近 180° 经线）
geohash = encode(-16.0, 179.9, precision=6)
print(f"原 Geohash: {geohash}")

neighbors = get_neighbors(geohash)
print(f"东邻（应跨越到 -180° 附近）: {neighbors.east}")

if neighbors.east:
    east_bbox = decode_bbox(neighbors.east)
    print(f"东邻经度范围: [{east_bbox.min_lon:.2f}, {east_bbox.max_lon:.2f}]")
```

## 异常处理

| 异常类 | 触发场景 |
|--------|----------|
| `InvalidLatitudeError` | 纬度超出 [-90, 90] 范围 |
| `InvalidLongitudeError` | 经度超出 [-180, 180] 范围 |
| `InvalidPrecisionError` | 精度不在 [1, 12] 范围内 |
| `InvalidGeohashCharacterError` | Geohash 字符串包含非法字符 |
| `EmptyGeohashError` | Geohash 字符串为空 |
| `GeohashError` | 所有异常的基类 |

```python
from solocoder_py.geohash import encode, InvalidLatitudeError

try:
    encode(100.0, 0.0)  # 纬度超出范围
except InvalidLatitudeError as e:
    print(f"编码失败: {e}")
```
