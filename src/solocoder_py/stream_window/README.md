# Stream Window Aggregation Module

流式时间窗口聚合域功能模块，使用内存数据结构模拟数据源，支持滚动窗口、滑动窗口、水位线推进和迟到事件处理。

## 功能概览

- **滚动窗口聚合 (Tumbling Window)**：按固定时间长度切分窗口，窗口边界不重叠，每个事件归入唯一窗口
- **滑动窗口聚合 (Sliding Window)**：窗口长度和滑动步长均可配置，一个事件可同时属于多个重叠窗口
- **水位线机制 (Watermark)**：基于已到达事件的时间戳向前推进，支持可配置的延迟阈值
- **迟到事件处理 (Late Event)**：窗口已计算输出后仍可接受迟到事件，支持可配置的容忍迟到上限
- **多种聚合类型**：支持 COUNT、SUM、AVG、MIN、MAX 五种聚合方式
- **内存事件源**：使用内存数据结构模拟的事件流数据源

## 核心类职责

### 数据模型 (models.py)

| 类名 | 职责 |
|------|------|
| `Event` | 事件数据类，包含时间戳、值和可选键，时间戳必须非负 |
| `Window` | 窗口数据类，定义窗口的起始和结束时间，左闭右开区间 `[start, end)` |
| `WindowState` | 窗口状态类，维护窗口内的聚合状态（计数、求和、最小、最大值） |
| `AggregationResult` | 聚合结果数据类，包含窗口、聚合类型、结果值和是否为重计算标记 |
| `AggregationType` | 聚合类型枚举：COUNT、SUM、AVG、MIN、MAX |

### 异常类

| 类名 | 说明 |
|------|------|
| `StreamWindowError` | 模块基异常 |
| `InvalidWindowConfigError` | 窗口配置错误 |
| `LateEventDroppedError` | 迟到事件被丢弃错误 |

### 水位线生成器 (watermark.py)

`WatermarkGenerator` 负责水位线的推进：

- 基于已观察到的最大事件时间推进水位线
- 水位线 = 最大事件时间 - 延迟阈值
- 水位线只能前进，不能后退
- 提供 `is_window_expired()` 方法判断窗口是否过期

### 滚动窗口聚合器 (tumbling_window.py)

`TumblingWindowAggregator` 实现滚动窗口聚合：

- 窗口大小固定，窗口之间不重叠
- 每个事件只属于一个窗口
- 窗口起始时间对齐到 0 点，即窗口起始为窗口大小的整数倍
- 水位线到达窗口结束时间时触发窗口计算输出

### 滑动窗口聚合器 (sliding_window.py)

`SlidingWindowAggregator` 实现滑动窗口聚合：

- 窗口大小和滑动步长均可配置
- 一个事件可属于多个重叠窗口
- 每个窗口独立维护聚合状态
- 水位线到达各窗口结束时间时分别触发输出

### 内存事件源 (source.py)

`MemoryEventSource` 提供内存中的事件流模拟：

- 支持添加单个或批量事件
- 支持迭代器协议
- 支持 `peek()` 查看下一个事件而不消费
- 支持 `reset()` 重置到起始位置

## 滚动窗口与滑动窗口的区别

| 特性 | 滚动窗口 (Tumbling) | 滑动窗口 (Sliding) |
|------|---------------------|---------------------|
| 窗口重叠 | 不重叠 | 可重叠 |
| 事件归属 | 每个事件只属于一个窗口 | 每个事件可属于多个窗口 |
| 配置参数 | 窗口大小 | 窗口大小 + 滑动步长 |
| 窗口数量 | 时间跨度 / 窗口大小 | 时间跨度 / 滑动步长 |
| 适用场景 | 周期性统计，每分钟计数等 | 平滑移动统计，最近 N 分钟等 |

### 滚动窗口示例

窗口大小 10 秒：

```
[0-10) [10-20) [20-30) ...
```

事件 t=5 属于 [0-10) 窗口。

### 滑动窗口示例

窗口大小 10 秒，滑动步长 5 秒：

```
[0-10) [5-15) [10-20) [15-25) ...
```

事件 t=7 同时属于 [0-10) 和 [5-15) 两个窗口。

## 水位线与迟到事件处理规则

### 水位线 (Watermark)

水位线是一个时间标记，表示"该时间之前的所有事件应该都已到达"。

- **推进方式**：水位线基于已到达事件的最大时间戳推进
- **延迟阈值**：`watermark_delay_seconds` 控制水位线滞后于最大事件时间的量
- **单调性**：水位线只能向前推进，不能后退
- **触发条件**：当水位线 >= 窗口结束时间时，触发该窗口的计算输出

### 迟到事件 (Late Event)

迟到事件是指在窗口已经触发计算输出后才到达的事件。

- **容忍迟到**：`allowed_lateness_seconds` 控制窗口触发后继续保留多长时间
- **处理规则**：
  - 事件到达时，若水位线 < 窗口结束时间：正常加入窗口
  - 事件到达时，若窗口结束时间 <= 水位线 < 窗口结束时间 + 容忍迟到：事件被接受，触发窗口重计算，输出标记为 `is_late_recompute=True`
  - 事件到达时，若水位线 >= 窗口结束时间 + 容忍迟到：事件被丢弃，`dropped_late_count` 加一
- **窗口清理**：水位线 >= 窗口结束时间 + 容忍迟到时，窗口状态被清理

### 生命周期图示

```
事件时间 →
  |
  |   窗口 [0, 10)
  |   ┌───────────────────────────┐
  │   │ 正常事件   │ 迟到事件     │ 事件被丢弃
  │   │ 加入窗口   │ 触发重计算   │
  │   └────────────┴──────────────┴───────────→
  │   0           10             15
  │               ↑              ↑
  │          水位线到达      水位线到达
  │          窗口结束      窗口+容忍迟到
  │          → 触发输出    → 清理窗口
  ↓
水位线推进方向
```

## 使用示例

### 滚动窗口计数

```python
from solocoder_py.stream_window import (
    TumblingWindowAggregator,
    AggregationType,
    Event,
)

agg = TumblingWindowAggregator(
    window_size_seconds=10.0,
    agg_type=AggregationType.COUNT,
)

agg.on_event(Event(timestamp=1.0))
agg.on_event(Event(timestamp=5.0))
agg.on_event(Event(timestamp=12.0))

results = agg.advance_watermark(20.0)
for r in results:
    print(f"Window [{r.window.start}, {r.window.end}): {r.value}")
# 输出:
# Window [0.0, 10.0): 2
# Window [10.0, 20.0): 1
```

### 滑动窗口求和

```python
from solocoder_py.stream_window import (
    SlidingWindowAggregator,
    AggregationType,
    Event,
)

agg = SlidingWindowAggregator(
    window_size_seconds=10.0,
    slide_seconds=5.0,
    agg_type=AggregationType.SUM,
)

agg.on_event(Event(timestamp=7.0, value=10.0))
agg.on_event(Event(timestamp=8.0, value=20.0))

results = agg.advance_watermark(15.0)
for r in results:
    print(f"Window [{r.window.start}, {r.window.end}): sum={r.value}")
```

### 水位线延迟与容忍迟到

```python
from solocoder_py.stream_window import (
    TumblingWindowAggregator,
    AggregationType,
    Event,
)

agg = TumblingWindowAggregator(
    window_size_seconds=10.0,
    agg_type=AggregationType.COUNT,
    watermark_delay_seconds=2.0,  # 水位线滞后2秒
    allowed_lateness_seconds=3.0,  # 容忍迟到3秒
)

agg.on_event(Event(timestamp=5.0))
# 当前水位线 = 5 - 2 = 3.0，窗口未触发

agg.on_event(Event(timestamp=15.0))
# 当前水位线 = 15 - 2 = 13.0
# 窗口 [0,10) 已触发 (13.0 >= 10.0)
# 但尚未清理 (13.0 < 10.0 + 3.0 = 13.0? 等于，所以已过期)

# 迟到事件
results = agg.on_event(Event(timestamp=7.0))
# 如果在容忍范围内，会触发重计算
late_results = [r for r in results if r.is_late_recompute]
```

### 使用内存事件源

```python
from solocoder_py.stream_window import (
    MemoryEventSource,
    TumblingWindowAggregator,
    AggregationType,
    Event,
)

source = MemoryEventSource([
    Event(timestamp=1.0, value=10.0),
    Event(timestamp=5.0, value=20.0),
    Event(timestamp=12.0, value=30.0),
])

agg = TumblingWindowAggregator(
    window_size_seconds=10.0,
    agg_type=AggregationType.SUM,
)

all_results = []
for event in source:
    results = agg.on_event(event)
    all_results.extend(results)

# 推进水位线触发剩余窗口
all_results.extend(agg.advance_watermark(100.0))
```
