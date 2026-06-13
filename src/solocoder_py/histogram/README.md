# Streaming Histogram 流式直方图模块

## 模块功能

本模块实现了基于内存数据结构的流式直方图（Streaming Histogram），用于高效统计数值分布统计与在线分位数估算。直方图在需要对海量数值数据做聚合统计的场景，如监控系统延迟分布、业务指标监控、性能基准测试延迟分布等。

核心特性：

- **可配置桶边界：支持自定义桶边界数组，灵活划分数值区间
- **在线分位数估算：基于累计计数与线性插值估算 P50、P90、P95、P99 等分位数
- **多实例合并：相同桶边界的直方图可合并，等价于将所有数据集中统计
- **流式增量统计查询：支持总计数、各桶计数、桶占比百分比等统计信息
- **重置清空重置：清空所有计数，复用直方图复用

## 核心类

### `StreamingHistogram`

流式直方图的核心类，负责数据结构，支持：

| 方法 | 说明 |
|------|------|
| `__init__(boundaries)` | 初始化直方图，接受桶边界数组
| `insert(value)` | 插入一个数值到直方图中
| `quantile(q)` | 估算单个分位数（0-100
| `quantiles(qs)` | 一次查询多个分位数
| `merge(other)` | 合并另一个相同桶边界的直方图
| `get_bucket_percentage(idx)` | 获取指定桶的计数占总体的百分比
| `reset()` | 重置清空所有计数

### 主要属性：

| 属性 | 类型 | 说明 |
|------|------|------|
| `boundaries` | `list[float]` | 桶边界数组（副本）
| `total_count` | `int` | 总插入次数
| `underflow_count` | `int` | 下溢桶计数（小于最小边界的值
| `overflow_count` | `int` | 上溢桶计数（大于等于最大边界的值
| `bucket_counts` | `list[int]` | 各正常桶的计数值列表

### 异常类

| 异常 | 说明 |
|--------|------|
| `HistogramError` | 直方图模块基础异常
| `InvalidBoundariesError` | 桶边界配置非法
| `IncompatibleBoundariesError` | 合并时桶边界不兼容
| `InvalidQuantileError` | 分位数参数超出范围
| `EmptyHistogramError` | 空直方图查询分位数

## 桶边界配置规则

桶边界是一个严格递增的数值序列，定义了直方图的区间划分方式。

### 区间规则

- 桶边界数组 B = [b₀, b₁, b₂, ..., bₙ] 定义了以下区间：

| 桶编号 | 区间 | 说明 |
|---------|------|------|
| 下溢桶 | (-∞, b₀) | 值小于最小边界 |
| 桶 0 | [b₀, b₁) | 左闭右开 |
| 桶 1 | [b₁, b₂) | 左闭右开 |
| ... | ... | ... |
| 桶 n-2 | [bₙ₋₂, bₙ₋₁) | 左闭右开 |
| 上溢桶 | [bₙ₋₁, +∞) | 值大于等于最大边界 |

- 正常桶总数为 `len(boundaries) - 1` 个
- 每个正常桶都是**左闭右开**区间
- 最后一个桶（上溢桶）包含最大边界值本身

### 合法性校验

初始化时会自动校验：

1. 边界数组长度必须 >= 2（否则无法形成至少一个桶）
2. 边界数组必须**严格递增**（不允许相等或递减
3. 允许包含负数、零和浮点数

合法示例：
```python
[0, 10, 50, 100, 500, 1000]
[-100, -50, 0, 50, 100]
[0.0, 0.5, 1.0, 2.5, 5.0]
```

非法示例：
```python
[]          # 长度不足
[0]         # 长度不足
[10, 50, 30, 100]   # 非递增
[0, 10, 10, 50]       # 有重复值
```

## 在线分位数估算算法

### 基本思想：基于各桶的累计计数，结合桶内做线性插值估算分位数近似值。

### 算法步骤：

1. 计算目标分位数 q 对应的总计数排名：

```
target_rank = q / 100.0 * total_count
```

2. 从左到右累加各桶计数，找到排名落入的桶：

- 若排名落入下溢桶，返回最小边界值
- 若排名落入某正常桶，在桶内做线性插值
- 若排名全部在所有桶之后，返回最大边界值

3. 桶内线性插值公式：

```
lower = 桶左边界
upper = 桶右边界
cumulative = 桶前累计计数
bucket_count = 当前桶计数

offset = target_rank - cumulative
result = lower + (upper - lower) * (offset / bucket_count)
```

### 特殊情况：

- 分位数为 0：直接返回最小边界值
- 分位数为 100：直接返回最大边界值
- 空直方图查询分位数：抛出 `EmptyHistogramError`

## 直方图合并策略

两个直方图可以合并的条件：

- 桶边界配置完全相同（边界值相同且顺序一致）
- 合并后各桶计数为两个实例对应桶计数的计数相加
- 合并不改变原直方图的副本，原直方图保持不变

合并结果等价于将两份数据全部插入同一直方图：

```python
merged = h1.merge(h2)
```

合并后的分位数估算结果应等于将两份数据全部插入同一直方图后的结果。

## 使用示例

### 基本使用

```python
from solocoder_py.histogram import StreamingHistogram

boundaries = [0, 10, 50, 100, 500, 1000]
hist = StreamingHistogram(boundaries)

for value in data_stream:
    hist.insert(value)

print(f"总计数: {hist.total_count}")
print(f"P50: {hist.quantile(50)}")
print(f"P90: {hist.quantile(90)}")
print(f"P99: {hist.quantile(99)}")
```

### 批量查询多个分位数

```python
quantiles = hist.quantiles([50, 90, 95, 99])
for q, val in zip([50, 90, 95, 99]):
    print(f"P{q}: {val}")
```

### 查询桶统计信息

```python
print(f"各桶计数: {hist.bucket_counts}")
print(f"桶0 占比: {hist.get_bucket_percentage(0):.2f}%")
print(f"下溢: {hist.underflow_count}")
print(f"上溢: {hist.overflow_count}")
```

### 合并直方图

```python
h1 = StreamingHistogram([0, 10, 50, 100])
h2 = StreamingHistogram([0, 10, 50, 100])

for v in batch1:
    h1.insert(v)
for v in batch2:
    h2.insert(v)

merged = h1.merge(h2)
print(f"合并后总计数: {merged.total_count}")
```

### 重置直方图

```python
hist.reset()
assert hist.total_count == 0
```

### 异常处理

```python
from solocoder_py.histogram import (
    StreamingHistogram,
    InvalidBoundariesError,
    IncompatibleBoundariesError,
    InvalidQuantileError,
    EmptyHistogramError,
)

try:
    hist = StreamingHistogram([0])
except InvalidBoundariesError as e:
    print(f"边界配置错误: {e}")

try:
    merged = h1.merge(h2)
except IncompatibleBoundariesError:
    print("桶边界不一致，无法合并")

try:
    hist.quantile(150)
except InvalidQuantileError:
    print("分位数范围错误")

try:
    empty_hist.quantile(50)
except EmptyHistogramError:
    print("空直方图无法估算")
```
