# 分位数估算 (Quantile Estimation) 域模块

本模块提供了基于 T-Digest 近似算法的流式分位数估算功能，支持窗口时间衰减、多线程并发安全访问等特性。适用于大规模数据流场景下，在有限内存空间内高效估算 P50、P95、P99 等多级分位数。

## 模块功能

- **流式近似分位数估算**：基于 T-Digest 算法，无需存储全部原始数据即可高效估算分位数值，内存占用可控
- **多级分位数查询**：支持单次查询获取 P50、P90、P95、P99、P999 等多级分位数近似值，精度在可接受误差范围内
- **窗口衰减机制**：支持基于时间窗口的数据筛选和指数衰减权重，近期数据对分位数估计影响更大，历史数据按半衰期逐步降低权重
- **并发安全访问**：使用可重入锁保护共享状态，支持多线程同时插入数据和查询分位数
- **内存数据结构**：完全基于内存数据结构实现，无需外部依赖，方便嵌入各类应用场景

## 核心类

### QuantileEstimator

分位数估算器的主入口类，封装了 T-Digest 算法、窗口衰减和并发安全机制。

| 方法 / 属性 | 说明 |
|------------|------|
| `insert(value, weight=1.0)` | 插入单个数值，支持自定义权重 |
| `insert_many(values, weights=None)` | 批量插入多个数值 |
| `quantile(q, window_seconds=None)` | 查询指定分位数（0 ≤ q ≤ 1），可指定时间窗口 |
| `quantiles(quantiles, window_seconds=None)` | 批量查询多个分位数 |
| `p50(window_seconds=None)` | 查询 P50（中位数） |
| `p95(window_seconds=None)` | 查询 P95 |
| `p99(window_seconds=None)` | 查询 P99 |
| `common_quantiles(window_seconds=None)` | 查询 P50/P90/P95/P99/P999 并返回字典 |
| `is_empty` | 估算器是否为空 |
| `insert_count` | 累计插入次数 |
| `total_weight` | 当前总权重 |
| `delta` | T-Digest 压缩参数 |
| `window_config` | 窗口配置（如有） |

构造参数：

- `delta`：T-Digest 压缩因子，控制质心数量与估算精度的权衡，默认 100，越大精度越高但内存消耗越大
- `window_config`：可选的 `WindowConfig`，用于指定默认时间窗口和半衰期
- `clock`：可选的 `Clock` 实例，用于获取当前时间，便于测试时使用 `MockClock`

### TDigest

T-Digest 算法的核心实现类，负责质心合并、压缩和分位数计算。

| 方法 | 说明 |
|------|------|
| `add(value, weight, timestamp)` | 添加单个数据点 |
| `add_centroid(centroid)` | 添加质心 |
| `quantile(q)` | 计算单个分位数 |
| `quantiles(qs)` | 批量计算分位数 |
| `trim(current_time, window_seconds, half_life_seconds)` | 按时间窗口修剪并应用衰减 |
| `merge(other)` | 合并另一个 TDigest |

### Centroid

质心数据结构，表示一组相近数据点的聚合：

- `mean`：质心均值
- `weight`：质心权重（聚合的数据点数量或总权重）
- `timestamp`：质心中最新数据点的时间戳

### QuantileResult

分位数查询结果：

- `quantile`：分位数值（如 0.5, 0.95）
- `value`：估算得到的分位值

### WindowConfig

窗口衰减配置：

- `window_seconds`：时间窗口大小（秒），只保留该时间范围内的数据
- `half_life_seconds`：可选的半衰期（秒），用于指数衰减权重

### Clock 体系

- `Clock`：抽象时钟接口，定义 `now()` 方法
- `SystemClock`：系统时钟，使用 `time.time()`
- `MockClock`：可手动控制的模拟时钟，便于单元测试

## T-Digest 近似分位数算法原理

T-Digest 是一种用于近似估算分位数的概率数据结构，由 Ted Dunning 提出。其核心思想是将数据分布表示为一组加权质心（Centroid），通过对质心进行智能合并，在保证分位数估算精度的同时大幅压缩内存占用。

### 核心机制

1. **质心聚合**：每个质心代表一组数值相近的数据点，记录其均值、权重和时间戳。当新数据到达时，不会存储原始值，而是尝试合并到现有质心中
2. **尺度函数（Scale Function）**：使用 arcsin 变换的尺度函数 k(q) = δ · (arcsin(2q-1) + π/2) / (2π)，该函数在分布的尾部（靠近 0 和 1）保持更高的分辨率，从而在极端分位数（P99、P999）处获得更好的精度
3. **合并规则**：当两个相邻质心的 k 值差乘以总权重再除以 δ 大于其合并权重时，可以安全合并，否则保留独立质心。这保证了质心在整个分布上的合理分布
4. **分位数计算**：按均值排序质心后，通过累计权重确定目标分位数所在的质心区间，再使用线性插值在相邻质心之间估算精确值

### 精度与内存权衡

- 参数 `delta` 控制质心的最大数量上限（约为 O(δ)）
- 较大的 δ 意味着更多质心、更高精度，但内存占用和计算时间也相应增加
- 默认 δ=100 通常能在 P50 处获得 <1% 相对误差，在 P95/P99 处获得 <5% 相对误差

## 窗口衰减策略

### 硬时间窗口

`window_seconds` 参数指定仅保留最近 N 秒内插入的数据，超出该时间窗口的质心会被完全剔除。这适用于需要严格限定统计范围的场景。

### 指数衰减（半衰期）

`half_life_seconds` 参数启用指数衰减权重：对于年龄为 t 的数据点，其权重乘以 e^(-λt)，其中 λ = ln(2) / half_life。这意味着：

- 数据经过一个半衰期后，权重衰减为原来的 50%
- 经过两个半衰期后，权重为 25%，以此类推
- 衰减是渐进平滑的，不会出现硬窗口带来的"断崖"效应

两种策略可以组合使用：先用硬窗口过滤掉过旧数据，再对窗口内的数据按半衰期进行软衰减。

## 异常类

| 异常类 | 说明 | 触发场景 |
|--------|------|----------|
| `QuantileError` | 分位数操作基类异常 | — |
| `EmptyDigestError` | 对空数据集执行查询操作 | 空估算器或空时间窗口调用 quantile |
| `InvalidQuantileError` | 分位数值非法 | q < 0 或 q > 1 |
| `InvalidValueError` | 插入值非法 | NaN、Inf、非正权重等 |
| `InvalidWindowError` | 窗口参数非法 | window_seconds ≤ 0 |

## 使用示例

### 基础使用

```python
from solocoder_py.quantile import QuantileEstimator

# 创建估算器
est = QuantileEstimator(delta=100.0)

# 插入数据流（模拟延迟监控数据）
import random
for _ in range(10000):
    latency_ms = random.gauss(100, 30)
    est.insert(latency_ms)

# 查询常用分位数
stats = est.common_quantiles()
print(f"P50: {stats['p50']:.2f}ms")
print(f"P95: {stats['p95']:.2f}ms")
print(f"P99: {stats['p99']:.2f}ms")

# 单次查询任意分位数
p999 = est.quantile(0.999)
print(f"P99.9: {p999:.2f}ms")

# 批量查询多个分位数
results = est.quantiles([0.1, 0.5, 0.9, 0.99])
for r in results:
    print(f"P{int(r.quantile * 100)}: {r.value:.2f}ms")
```

### 带权重插入

```python
from solocoder_py.quantile import QuantileEstimator

est = QuantileEstimator()

# 某些数据点具有更高权重（例如聚合数据）
est.insert(50.0, weight=10.0)   # 相当于插入 10 个 50.0
est.insert(100.0, weight=1.0)

print(est.p50())  # 结果更接近 50.0
```

### 时间窗口衰减

```python
from solocoder_py.quantile import QuantileEstimator, WindowConfig, MockClock

# 使用模拟时钟便于测试
clock = MockClock(initial_time=1000.0)

# 配置默认窗口：最近 60 秒，半衰期 30 秒
config = WindowConfig(window_seconds=60.0, half_life_seconds=30.0)
est = QuantileEstimator(delta=100.0, window_config=config, clock=clock)

# 早期数据（会被衰减或排除）
for _ in range(100):
    est.insert(10.0)

# 时间前进 30 秒（一个半衰期）
clock.advance(30.0)

# 近期数据
for _ in range(100):
    est.insert(100.0)

# 查询：结果偏向近期的 100.0
print(est.p50())  # ~70 左右（早期数据权重衰减为 50%）

# 也可以在查询时覆盖窗口设置
p50_full = est.quantile(0.5, window_seconds=300.0)  # 更大的窗口
```

### 多线程并发访问

```python
import threading
from solocoder_py.quantile import QuantileEstimator

est = QuantileEstimator(delta=200.0)

# 多线程写入
def writer(start, count):
    for i in range(start, start + count):
        est.insert(float(i))

threads = [threading.Thread(target=writer, args=(i * 1000, 1000)) for i in range(8)]
for t in threads:
    t.start()

# 同时可以安全地进行查询
def reader():
    for _ in range(100):
        try:
            _ = est.p95()
        except Exception:
            pass

reader_thread = threading.Thread(target=reader)
reader_thread.start()

for t in threads:
    t.join()
reader_thread.join()

print(f"Total inserts: {est.insert_count}")  # 8000
```

### 单元测试中使用 MockClock

```python
from solocoder_py.quantile import QuantileEstimator, MockClock, WindowConfig
import pytest

def test_window_decay():
    clock = MockClock(initial_time=0.0)
    config = WindowConfig(window_seconds=60.0, half_life_seconds=30.0)
    est = QuantileEstimator(window_config=config, clock=clock)

    est.insert(10.0)
    clock.advance(120.0)  # 前进超过窗口
    est.insert(100.0)

    # 旧数据已在窗口外，仅保留新数据
    assert est.p50() == pytest.approx(100.0, abs=1.0)
```
