# Anomaly 异常检测器模块

本模块实现了基于移动平均和标准差带的实时数据流异常检测与告警功能。使用内存数据结构模拟实时数据流，支持滑动窗口基线计算、异常判定、多级告警触发规则以及状态查询。

## 模块功能

1. **移动平均基线计算**：维护一个可配置大小的滑动窗口，存储最近 N 个正常数据点。每收到一个新数据点，窗口向前推进（最旧数据点被移出），重新计算移动平均值作为基线。窗口未满时使用已有数据点计算均值。

2. **标准差带异常判定**：基于滑动窗口内数据计算标准差，以移动平均值为中心、K 倍标准差为宽度构建正常带。新数据点如果在正常带之外则判定为异常。被判定为异常的离群点不会加入滑动窗口，避免污染正常基线。

3. **多级告警触发规则**：
   - **连续异常阈值**：连续 M 个点被判定为异常时触发告警
   - **告警冷却期**：一次告警触发后，在冷却时间窗口内即使再次满足条件也不重复告警
   - **最大异常点比例**：滑动窗口内异常点占比超过阈值时触发告警

4. **状态查询与重置**：可查询当前滑动窗口的移动平均值、标准差、最近 N 个数据点、最近的异常点列表；支持手动重置基线（清空滑动窗口重新积累数据）。

## 核心类与职责

### `AnomalyConfig`（[models.py](models.py)）

检测器配置对象，所有参数在构造时校验：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `window_size` | `int` | 100 | 滑动窗口大小 N，必须 >= 1 |
| `k_sigma` | `float` | 2.0 | 标准差倍数 K，必须 >= 0 |
| `consecutive_threshold` | `int` | 3 | 连续异常点告警阈值 M，必须 >= 1 |
| `cooldown_seconds` | `float` | 60.0 | 告警冷却期（秒），必须 >= 0 |
| `max_anomaly_ratio` | `float` | 0.3 | 滑动窗口内最大异常点比例，范围 [0, 1] |
| `anomaly_history_limit` | `int` | 1000 | 异常点历史记录最大保留数量 |

### `AnomalyPoint`（[models.py](models.py)）

单个数据点的检测结果：

| 字段 | 类型 | 说明 |
|------|------|------|
| `value` | `float` | 数据点数值 |
| `timestamp` | `float` | 数据点时间戳 |
| `is_anomaly` | `bool` | 是否为异常点 |
| `deviation` | `float` | 与当前均值的偏差绝对值；窗口为空时为 0.0（首个点作为基线起点，相对于自身无偏离） |

### `AlertEvent`（[models.py](models.py)）

告警事件：

| 字段 | 类型 | 说明 |
|------|------|------|
| `reason` | `str` | 告警触发原因（可包含多个原因，以分号分隔） |
| `triggered_at` | `float` | 告警触发时间戳 |
| `anomaly_points` | `list[AnomalyPoint]` | 与本次告警直接相关的最近连续异常点列表；长度等于触发告警时的 `consecutive_anomalies` 计数，而非 `recent_point_flags` 队列总长度；不包含历史上已被正常点打断的无关异常点 |
| `window_mean` | `float` | 触发告警时的窗口均值 |
| `window_std` | `float` | 触发告警时的窗口标准差 |

### `DetectorState`（[models.py](models.py)）

检测器内部状态快照：

| 字段 | 类型 | 说明 |
|------|------|------|
| `window` | `list[float]` | 当前滑动窗口内的正常数据点 |
| `anomaly_history` | `list[AnomalyPoint]` | 异常点历史记录 |
| `consecutive_anomalies` | `int` | 当前连续异常点计数 |
| `last_alert_time` | `Optional[float]` | 上次告警时间（None 表示从未告警） |
| `total_points_seen` | `int` | 累计处理的数据点总数 |
| `total_anomalies_seen` | `int` | 累计检测到的异常点总数 |

### `AnomalyDetector`（[detector.py](detector.py)）

异常检测器核心类，提供以下主要方法：

| 方法 | 说明 |
|------|------|
| `add_point(value: float) -> tuple[AnomalyPoint, Optional[AlertEvent]]` | 添加一个新数据点，返回检测结果和可能的告警事件 |
| `get_mean() -> float` | 获取当前滑动窗口的移动平均值（空窗口返回 0.0） |
| `get_std() -> float` | 获取当前滑动窗口的标准差（空窗口或单点返回 0.0） |
| `get_window() -> list[float]` | 获取当前滑动窗口内所有数据点的副本 |
| `get_window_size() -> int` | 获取当前滑动窗口内数据点数量 |
| `get_recent_anomalies(limit: Optional[int] = None) -> list[AnomalyPoint]` | 获取最近的异常点（可限制数量） |
| `get_anomaly_ratio() -> float` | 获取总体异常点比例 |
| `get_recent_anomaly_ratio() -> float` | 获取最近窗口内的异常点比例 |
| `reset() -> None` | 重置检测器，清空所有状态 |
| `update_config(config: AnomalyConfig) -> None` | 动态更新检测器配置 |

### 辅助函数（[detector.py](detector.py)）

| 函数 | 说明 |
|------|------|
| `_mean(values: list[float]) -> float` | 计算算术平均值（空列表返回 0.0） |
| `_std(values: list[float]) -> float` | 计算样本标准差（n < 2 时返回 0.0，使用 n-1 作为分母） |

### 异常类（[exceptions.py](exceptions.py)）

| 类 | 说明 |
|----|------|
| `AnomalyError` | 异常检测器模块的基础异常 |
| `AnomalyConfigError` | 配置参数校验失败异常 |

### 时钟接口（[models.py](models.py)，继承自 [seat/clock.py](../seat/clock.py)）

| 类 | 说明 |
|----|------|
| `Clock` | 抽象时钟接口，定义 `now()` 方法 |
| `SystemClock` | 基于系统 `time.monotonic()` 的默认时钟实现 |
| `ManualClock` | 手动控制时间的时钟实现（用于测试，通过 `advance()` 推进时间） |

## 移动平均与标准差带的数学公式

### 移动平均值

对于滑动窗口内的 N 个数据点 $x_1, x_2, \ldots, x_n$（$n \le N$，N 为窗口大小），移动平均值为：

$$
\mu = \frac{1}{n} \sum_{i=1}^{n} x_i
$$

当窗口为空（$n = 0$）时，均值定义为 0。

### 样本标准差

使用样本标准差（无偏估计，分母为 $n-1$）：

$$
\sigma = \sqrt{\frac{1}{n-1} \sum_{i=1}^{n} (x_i - \mu)^2}
$$

当窗口数据点少于 2 个（$n < 2$）时，标准差定义为 0。

### 正常带

以均值为中心、K 倍标准差为宽度的正常区间：

$$
[\mu - K \cdot \sigma,\ \mu + K \cdot \sigma]
$$

新数据点 $x$ 若满足以下任一条件则判定为异常：

$$
x > \mu + K \cdot \sigma \quad \text{或} \quad x < \mu - K \cdot \sigma
$$

**特殊情况**：当标准差 $\sigma = 0$ 时（窗口内所有数据点完全相同），正常带退化为单点 $\mu$，此时任何与均值不相等的点均判定为异常。

## 异常判定规则

### 判定前置条件

1. **空窗口**：窗口中无数据点时，新点直接加入窗口，不判定异常
2. **窗口只有 1 个点且窗口大小 > 1**：此时无法计算有意义的样本标准差（n-1 分母为 0，标准差为 0），不进行异常判定，新点直接加入窗口以积累数据
3. **窗口有 2 个或更多数据点**：正常进行异常判定。即使只有 2 个不同值的数据点（如 [10.0, 20.0]），样本标准差也可以正常计算，K 倍标准差带的异常判定逻辑完全可用
4. **窗口大小为 1**：极端窗口大小，按正常规则判定（标准差为 0 时任何不同值均异常）

### 异常点处理

- 被判定为**异常**的点：计入异常历史、连续异常计数 +1，**不加入滑动窗口**（避免污染基线）
- 被判定为**正常**的点：加入滑动窗口，连续异常计数归零

### Deviation 计算规则

每个 `AnomalyPoint` 的 `deviation` 字段表示数据点与当前基线均值的偏离绝对值：

- **窗口不为空时**：`deviation = |value - μ|`，即数据点与当前滑动窗口移动平均值的绝对偏差
- **窗口为空时（首个数据点）**：`deviation = 0.0`，表示该点作为基线起点，相对于自身无偏离

该字段始终为 `float` 类型，不会为 `None`。

### 告警异常列表语义

告警事件中的 `anomaly_points` 列表仅包含与本次告警直接相关的异常点：

- 列表长度以触发告警时的 `consecutive_anomalies`（当前连续异常点计数）为准，而非 `recent_point_flags` 队列的总长度
- 仅包含最近的连续异常点，不包含历史上已被正常点打断的无关异常点
- 保证告警语义清晰，便于定位本次告警的根本原因

## 告警触发规则

告警触发需要同时满足以下条件：

1. **当前点是异常点**
2. **冷却期已过**：距上次告警时间超过 `cooldown_seconds`（或从未告警过）

满足上述条件后，以下任一规则触发即产生告警：

### 规则一：连续异常阈值

当前连续异常点数量 >= `consecutive_threshold`

```
reason: "consecutive anomalies (X) >= threshold (M)"
```

### 规则二：异常点比例超限

最近窗口内（最多 window_size 个点）的异常点比例 >= `max_anomaly_ratio`

```
reason: "anomaly ratio (X.XXX) >= threshold (R)"
```

两个规则可同时触发，此时 `reason` 字段包含两个原因，以分号 `; ` 分隔。

## 滑动窗口与冷却期机制

### 滑动窗口

- 使用 `collections.deque` 实现固定大小的先进先出（FIFO）队列
- 窗口最大长度为 `window_size`，新的正常数据点从右侧加入
- 当窗口已满时，新点加入会自动从左侧弹出最旧的数据点
- 异常点永远不会加入窗口，保证基线不受污染

### 冷却期

- 每次告警触发后记录 `last_alert_time`
- 后续异常点到达时，若距 `last_alert_time` 不足 `cooldown_seconds`，则跳过告警检查
- 冷却期结束后首次满足条件的异常点会重新触发告警
- `reset()` 会清空 `last_alert_time`，相当于重置冷却期

## 使用示例

### 基本异常检测

```python
from solocoder_py.anomaly import AnomalyConfig, AnomalyDetector

# 使用默认配置
detector = AnomalyDetector()

# 或者自定义配置
config = AnomalyConfig(
    window_size=20,       # 滑动窗口保存最近 20 个正常点
    k_sigma=3.0,          # 3 倍标准差带
    consecutive_threshold=3,   # 连续 3 个异常触发告警
    cooldown_seconds=60.0,     # 60 秒冷却期
    max_anomaly_ratio=0.2,     # 异常比例超过 20% 告警
)
detector = AnomalyDetector(config=config)

# 模拟数据流
normal_values = [10.0, 10.1, 9.9, 10.2, 9.8, 10.0, 10.1, 9.9]
for v in normal_values:
    point, alert = detector.add_point(v)
    assert point.is_anomaly is False
    assert alert is None

# 注入异常值
point, alert = detector.add_point(1000.0)
print(f"Value={point.value}, is_anomaly={point.is_anomaly}")
# Value=1000.0, is_anomaly=True

# 异常点未污染基线
print(f"Mean={detector.get_mean():.2f}, Std={detector.get_std():.4f}")
# Mean≈10.00, Std≈0.13
```

### 连续异常触发告警

```python
from solocoder_py.anomaly import AnomalyConfig, AnomalyDetector
from solocoder_py.seat.clock import ManualClock

# 使用手动时钟便于测试
clock = ManualClock(start_time=1_718_150_400.0)
config = AnomalyConfig(
    window_size=10,
    k_sigma=2.0,
    consecutive_threshold=3,
    cooldown_seconds=60.0,
)
detector = AnomalyDetector(config=config, clock=clock)

# 先填充正常数据建立基线
for _ in range(10):
    detector.add_point(50.0)

# 连续注入异常点
alerts = []
for i in range(5):
    clock.advance(1.0)  # 每个点间隔 1 秒
    point, alert = detector.add_point(500.0 + i)
    if alert is not None:
        alerts.append(alert)

print(f"告警次数: {len(alerts)}")  # 告警次数: 1
print(f"原因: {alerts[0].reason}")
# 原因: "consecutive anomalies (3) >= threshold (3)"
print(f"连续异常计数: {detector.state.consecutive_anomalies}")  # 5
```

### 告警冷却期

```python
# 接上例
# 继续在冷却期内注入异常点，不会重复告警
for _ in range(10):
    clock.advance(1.0)
    _, alert = detector.add_point(999.0)
    assert alert is None  # 冷却期内无告警

# 等待冷却期结束
clock.advance(120.0)  # 推进 120 秒
detector.state.consecutive_anomalies = 0  # 重置连续计数

# 冷却期后再次连续异常，重新触发告警
for i in range(3):
    clock.advance(1.0)
    _, alert = detector.add_point(888.0 + i)

print(f"重新触发告警: {alert is not None}")  # True
```

### 状态查询与重置

```python
from solocoder_py.anomaly import AnomalyDetector

detector = AnomalyDetector()
for v in [1.0, 2.0, 3.0, 4.0, 5.0]:
    detector.add_point(v)

print(f"窗口数据: {detector.get_window()}")          # [1.0, 2.0, 3.0, 4.0, 5.0]
print(f"窗口大小: {detector.get_window_size()}")      # 5
print(f"移动均值: {detector.get_mean():.2f}")          # 3.00
print(f"标准差: {detector.get_std():.4f}")             # 1.5811
print(f"异常历史: {detector.get_recent_anomalies()}")  # []
print(f"总体异常率: {detector.get_anomaly_ratio()}")   # 0.0

# 重置检测器
detector.reset()
print(f"重置后窗口大小: {detector.get_window_size()}")  # 0
print(f"重置后均值: {detector.get_mean()}")             # 0.0
```

### 标准差为零的情况

```python
from solocoder_py.anomaly import AnomalyConfig, AnomalyDetector

config = AnomalyConfig(window_size=5, k_sigma=2.0, consecutive_threshold=1)
detector = AnomalyDetector(config=config)

# 全部相同数据，标准差为 0
for _ in range(5):
    point, _ = detector.add_point(42.0)
    assert point.is_anomaly is False

print(f"标准差: {detector.get_std()}")  # 0.0

# 相同的值仍然正常
point, _ = detector.add_point(42.0)
assert point.is_anomaly is False

# 任何不同的值均判定为异常
point, alert = detector.add_point(43.0)
assert point.is_anomaly is True
assert alert is not None  # consecutive_threshold=1，单点即告警
```

### K=0 的极端灵敏度

```python
from solocoder_py.anomaly import AnomalyConfig, AnomalyDetector

config = AnomalyConfig(
    window_size=5,
    k_sigma=0.0,           # K=0，正常带宽度为 0
    consecutive_threshold=1,
)
detector = AnomalyDetector(config=config)

for _ in range(5):
    detector.add_point(10.0)

# 极小偏差即判定为异常
point, _ = detector.add_point(10.0001)
assert point.is_anomaly is True

point, _ = detector.add_point(9.9999)
assert point.is_anomaly is True

# 完全相同才正常
point, _ = detector.add_point(10.0)
assert point.is_anomaly is False
```

### 窗口有 2 个数据点时的异常判定

窗口有 2 个不同值的数据点时，样本标准差可以正常计算，异常判定逻辑完全可用：

```python
from solocoder_py.anomaly import AnomalyConfig, AnomalyDetector
from solocoder_py.seat.clock import ManualClock

clock = ManualClock()
config = AnomalyConfig(
    window_size=10,
    k_sigma=2.0,
    consecutive_threshold=1,
)
detector = AnomalyDetector(config=config, clock=clock)

# 填充 2 个不同值的数据点建立基线
detector.add_point(10.0)
detector.add_point(20.0)

assert detector.get_window_size() == 2
assert detector.get_mean() == 15.0
assert detector.get_std() > 0  # 样本标准差可正常计算

# 第三个严重偏离的点会被正确标记为异常
point, alert = detector.add_point(1000.0)
assert point.is_anomaly is True
assert alert is not None

# 异常点未污染基线
assert detector.get_window_size() == 2
assert detector.get_mean() == 15.0
```

### 空窗口 Deviation 计算规则

首个数据点的 deviation 为 0.0，不会丢失偏离信息：

```python
from solocoder_py.anomaly import AnomalyConfig, AnomalyDetector

config = AnomalyConfig(window_size=10)
detector = AnomalyDetector(config=config)

# 首个数据点，deviation 为 0.0
point1, _ = detector.add_point(42.0)
assert point1.deviation == 0.0
assert point1.is_anomaly is False

# 第二个点的 deviation 相对于首个点计算
point2, _ = detector.add_point(52.0)
assert point2.deviation == 10.0  # |52.0 - 42.0| = 10.0

# 重置后，新的首个点 deviation 仍为 0.0
detector.reset()
point3, _ = detector.add_point(100.0)
assert point3.deviation == 0.0
```

## 运行测试

```bash
pytest tests/anomaly/ -v
```
