# Stream Window Aggregation Module

流式时间窗口聚合域功能模块，使用内存数据结构模拟数据源，支持滚动窗口、滑动窗口、水位线推进和迟到事件处理。

## 功能概览

- **滚动窗口聚合 (Tumbling Window)**：按固定时间长度切分窗口，窗口边界不重叠，每个事件归入唯一窗口
- **滑动窗口聚合 (Sliding Window)**：窗口长度和滑动步长均可配置，一个事件可同时属于多个重叠窗口
- **水位线机制 (Watermark)**：基于已到达事件的时间戳向前推进，支持可配置的延迟阈值
- **迟到事件处理 (Late Event)**：窗口已计算输出后仍可接受迟到事件，支持可配置的容忍迟到上限
- **异常通知**：迟到事件超过容忍上限时抛出 `LateEventDroppedError` 异常，包含事件详情
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
| `StreamWindowError` | 模块基异常，所有模块异常的父类 |
| `InvalidWindowConfigError` | 窗口配置错误，如窗口大小非正、滑动步长大于窗口大小等 |
| `LateEventDroppedError` | 迟到事件被丢弃异常，包含事件时间戳、最早过期窗口结束时间、容忍迟到上限 |

`LateEventDroppedError` 属性：
- `event_timestamp: float` - 被丢弃事件的时间戳
- `window_end: float` - 该事件所属窗口的最早结束时间
- `allowed_lateness: float` - 配置的容忍迟到秒数

### 水位线生成器 (watermark.py)

`WatermarkGenerator` 负责水位线的推进：

- 基于已观察到的最大事件时间推进水位线
- 水位线 = 最大事件时间 - 延迟阈值
- 水位线只能前进，不能后退
- 提供 `is_window_expired(window_end, allowed_lateness)` 方法判断窗口是否过期
- 提供 `observe_event(timestamp)` 方法观察事件并自动推进水位线
- 提供 `advance_watermark(new_watermark)` 方法手动推进水位线

### 滚动窗口聚合器 (tumbling_window.py)

`TumblingWindowAggregator` 实现滚动窗口聚合：

- 窗口大小固定，窗口之间不重叠
- 每个事件只属于一个窗口
- 窗口起始时间对齐到 0 点，即窗口起始为窗口大小的整数倍
- 水位线到达窗口结束时间时触发窗口计算输出
- `dropped_late_count` 属性记录被丢弃的迟到事件总数（按事件计数）
- 事件被丢弃时抛出 `LateEventDroppedError` 异常

### 滑动窗口聚合器 (sliding_window.py)

`SlidingWindowAggregator` 实现滑动窗口聚合：

- 窗口大小和滑动步长均可配置
- 一个事件可属于多个重叠窗口
- 每个窗口独立维护聚合状态
- 水位线到达各窗口结束时间时分别触发输出
- `dropped_late_count` 属性记录被丢弃的迟到事件总数（按事件计数，与滚动窗口语义一致）
- 只有当事件所属的**所有**窗口都已过期时，该事件才被视为丢弃
- 如果事件所属的部分窗口已过期、部分窗口仍活跃，则只加入活跃窗口，不计入丢弃数
- 事件被丢弃时抛出 `LateEventDroppedError` 异常，`window_end` 为最早过期的窗口结束时间

### 内存事件源 (source.py)

`MemoryEventSource` 提供内存中的事件流模拟：

- 支持添加单个或批量事件
- 支持迭代器协议
- 支持 `peek()` 查看下一个事件而不消费
- 支持 `reset()` 重置到起始位置
- 支持 `total_events` 和 `remaining_events` 属性

## 滚动窗口与滑动窗口的区别

| 特性 | 滚动窗口 (Tumbling) | 滑动窗口 (Sliding) |
|------|---------------------|---------------------|
| 窗口重叠 | 不重叠 | 可重叠 |
| 事件归属 | 每个事件只属于一个窗口 | 每个事件可属于多个窗口 |
| 配置参数 | 窗口大小 | 窗口大小 + 滑动步长 |
| 窗口数量 | 时间跨度 / 窗口大小 | 时间跨度 / 滑动步长 |
| 适用场景 | 周期性统计，每分钟计数等 | 平滑移动统计，最近 N 分钟等 |
| dropped_late_count | 按事件计数 | 按事件计数（语义一致） |

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

### 水位线推进机制

水位线是一个时间标记，表示"该时间之前的所有事件应该都已到达"。

**推进方式**：
1. 每个事件到达时，首先通过 `WatermarkGenerator.observe_event(timestamp)` 观察其时间戳
2. 系统记录已观察到的最大事件时间戳 `max_event_time`
3. 当前水位线 = `max_event_time - watermark_delay_seconds`
4. 水位线具有单调性：即使后来到达的事件时间戳更早，水位线也不会后退
5. 也可以通过 `advance_watermark(new_watermark)` 手动推进水位线，但若新值小于当前水位线则无效

**水位线延迟 (watermark_delay_seconds)**：
- 控制水位线滞后于最大事件时间的时间量
- 用于应对预期内的乱序到达
- 例如设置为 2 秒，表示系统期望事件最多乱序 2 秒

**触发窗口计算**：
- 当水位线 >= 窗口结束时间（`window.end`）时，触发该窗口的计算输出
- 每个窗口只会触发一次正常计算（由 `WindowState.fired` 标记控制）

### 迟到事件判定规则

迟到事件是指在窗口已经触发计算输出后才到达的事件。

**判定条件**：

对于一个事件和它所属的窗口，设窗口结束时间为 `window_end`，当前水位线为 `watermark`：

1. **正常事件**：`watermark < window_end`
   - 事件正常加入窗口
   - 若窗口尚未触发则等待水位线推进
   - 不影响 `dropped_late_count`

2. **可接受的迟到事件**：`window_end <= watermark < window_end + allowed_lateness_seconds`
   - 事件仍被接受并加入窗口
   - 触发窗口重计算，输出结果标记 `is_late_recompute=True`
   - 不影响 `dropped_late_count`

3. **被丢弃的迟到事件**：`watermark >= window_end + allowed_lateness_seconds`
   - 事件被丢弃，不加入窗口
   - `dropped_late_count` 加 1（按事件计数，滑动窗口中即使属于多个窗口也只计一次）
   - 抛出 `LateEventDroppedError` 异常，包含事件详情
   - 对于滑动窗口，只有当事件所属的**所有**窗口都满足此条件时才算丢弃

**容忍迟到 (allowed_lateness_seconds)**：
- 控制窗口触发计算输出后，继续保留窗口状态多长时间
- 在这段时间内到达的迟到事件仍会被接受并触发重计算
- 水位线 >= `window_end + allowed_lateness_seconds` 时，窗口状态被清理

### 窗口生命周期

```
事件时间 →
  |
  |   窗口 [0, 10)，allowed_lateness=5
  |   ┌───────────────────────────┬──────────────────┐
  │   │ 正常事件   │ 迟到事件     │ 事件被丢弃       │
  │   │ 加入窗口   │ 触发重计算   │ → 抛异常         │
  │   └────────────┴──────────────┴──────────────────┴→
  │   0           10             15                 (时间)
  │               ↑              ↑
  │          水位线到达      水位线到达
  │          窗口结束      窗口+容忍迟到
  │          → 触发输出    → 清理窗口，迟到事件抛出异常
  ↓
水位线推进方向 (只前进，不后退)
```

### 滑动窗口中的部分过期场景

对于滑动窗口，一个事件可能同时属于多个窗口，存在部分窗口已过期、部分窗口仍活跃的情况：

```
事件 t=7，窗口大小 10，步长 5，所属窗口 [0,10) 和 [5,15)

watermark = 12

  [0, 10) → 已过期 (12 >= 10 + 0)
  [5, 15) → 仍活跃 (12 < 15)

结果：事件加入 [5,15) 窗口，不计数为丢弃，不抛出异常
```

只有当事件所属的**所有**窗口都已过期时，该事件才被视为丢弃并抛出异常。

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

### 滚动窗口：水位线与迟到事件完整示例

```python
from solocoder_py.stream_window import (
    TumblingWindowAggregator,
    AggregationType,
    Event,
    LateEventDroppedError,
)

# 创建滚动窗口聚合器：10秒窗口，水位线延迟2秒，容忍迟到3秒
agg = TumblingWindowAggregator(
    window_size_seconds=10.0,
    agg_type=AggregationType.COUNT,
    watermark_delay_seconds=2.0,
    allowed_lateness_seconds=3.0,
)

# 第一批事件到达
agg.on_event(Event(timestamp=3.0))  # 属于 [0,10)
agg.on_event(Event(timestamp=6.0))  # 属于 [0,10)
print(f"当前水位线: {agg.get_watermark()}")  # max=6, watermark=6-2=4.0

# 推进时间，触发窗口计算
agg.on_event(Event(timestamp=14.0))  # 属于 [10,20)
print(f"当前水位线: {agg.get_watermark()}")  # max=14, watermark=14-2=12.0
# watermark=12.0 >= 10.0，所以 [0,10) 窗口已触发但尚未清理（12.0 < 10+3=13.0）

# 可接受的迟到事件：触发重计算
results = agg.on_event(Event(timestamp=8.0))  # 属于 [0,10)，在容忍范围内
late_results = [r for r in results if r.is_late_recompute]
print(f"迟到重计算结果数: {len(late_results)}")  # 1
if late_results:
    print(f"重计算值: {late_results[0].value}")  # 3 (3, 6, 8 共3个事件)

# 推进水位线超过容忍上限
agg.advance_watermark(15.0)  # watermark=15.0 >= 10+3=13.0，窗口被清理
print(f"活跃窗口数: {agg.get_active_window_count()}")  # 1（只剩 [10,20)）

# 超过容忍上限的迟到事件：抛出异常
try:
    agg.on_event(Event(timestamp=5.0))
except LateEventDroppedError as e:
    print(f"事件被丢弃: timestamp={e.event_timestamp}, "
          f"window_end={e.window_end}, allowed_lateness={e.allowed_lateness}")
    print(f"被丢弃事件总数: {agg.dropped_late_count}")  # 1
```

### 滑动窗口：水位线与迟到事件完整示例

```python
from solocoder_py.stream_window import (
    SlidingWindowAggregator,
    AggregationType,
    Event,
    LateEventDroppedError,
)

# 创建滑动窗口聚合器：10秒窗口，5秒步长，容忍迟到3秒
agg = SlidingWindowAggregator(
    window_size_seconds=10.0,
    slide_seconds=5.0,
    agg_type=AggregationType.SUM,
    allowed_lateness_seconds=3.0,
)

# 事件 t=7 属于 [0,10) 和 [5,15) 两个窗口
agg.on_event(Event(timestamp=7.0, value=10.0))
print(f"活跃窗口数: {agg.get_active_window_count()}")  # 2

# 触发 [0,10) 窗口计算
results = agg.advance_watermark(10.0)
print(f"触发窗口数: {len(results)}")  # 1
print(f"窗口 [0,10) sum={results[0].value}")  # 10.0
print(f"[0,10) 已触发: {agg.get_window_state(0.0).fired}")  # True

# 迟到事件 t=3，属于 [0,10)（已触发但在容忍范围内）
# 注意 t=3 不属于 [5,15)（3 < 5）
results = agg.on_event(Event(timestamp=3.0, value=20.0))
late = [r for r in results if r.is_late_recompute]
print(f"重计算结果数: {len(late)}")  # 1
if late:
    print(f"窗口 [0,10) 重计算 sum={late[0].value}")  # 30.0

# 推进水位线，清理所有过期窗口
agg.advance_watermark(25.0)
print(f"活跃窗口数: {agg.get_active_window_count()}")  # 0

# 迟到事件同时属于多个已过期窗口：只计数一次，抛出异常
try:
    agg.on_event(Event(timestamp=7.0, value=5.0))  # 属于 [0,10) 和 [5,15)，都已过期
except LateEventDroppedError as e:
    print(f"事件被丢弃: timestamp={e.event_timestamp}")
    print(f"最早过期窗口结束时间: {e.window_end}")  # 10.0（两个窗口中较早结束的）
    print(f"被丢弃事件总数: {agg.dropped_late_count}")  # 1（按事件计数，不是按窗口）

# 部分窗口过期的情况：不视为丢弃
agg2 = SlidingWindowAggregator(
    window_size_seconds=10.0,
    slide_seconds=5.0,
    agg_type=AggregationType.COUNT,
    allowed_lateness_seconds=0.0,
    watermark_delay_seconds=100.0,  # 保持窗口不自动清理
)
agg2.on_event(Event(timestamp=12.0))  # 属于 [10,20) 和 [5,15)
agg2.advance_watermark(10.0)  # [0,10) 已过期

# t=7 属于 [0,10)（过期）和 [5,15)（活跃），只加入活跃窗口
results = agg2.on_event(Event(timestamp=7.0))
print(f"dropped_late_count: {agg2.dropped_late_count}")  # 0（未被丢弃）
print(f"[5,15) 计数: {agg2.get_window_state(5.0).count}")  # 2
```

### 水位线延迟配置示例

```python
from solocoder_py.stream_window import (
    TumblingWindowAggregator,
    AggregationType,
    Event,
)

# 水位线延迟 5 秒：表示系统预期事件最多乱序 5 秒
agg = TumblingWindowAggregator(
    window_size_seconds=10.0,
    agg_type=AggregationType.COUNT,
    watermark_delay_seconds=5.0,
)

agg.on_event(Event(timestamp=3.0))
print(f"水位线: {agg.get_watermark()}")  # 3 - 5 = -2.0 → 显示为 -1.0（初始值）

agg.on_event(Event(timestamp=12.0))
print(f"水位线: {agg.get_watermark()}")  # 12 - 5 = 7.0

agg.on_event(Event(timestamp=20.0))
print(f"水位线: {agg.get_watermark()}")  # 20 - 5 = 15.0
# watermark=15.0 >= 10.0，触发 [0,10) 窗口计算
```

### 使用内存事件源

```python
from solocoder_py.stream_window import (
    MemoryEventSource,
    TumblingWindowAggregator,
    AggregationType,
    Event,
    LateEventDroppedError,
)

# 创建事件源
source = MemoryEventSource([
    Event(timestamp=1.0, value=10.0),
    Event(timestamp=5.0, value=20.0),
    Event(timestamp=12.0, value=30.0),
])

# 也可以动态添加事件
source.add_event(Event(timestamp=15.0, value=40.0))

agg = TumblingWindowAggregator(
    window_size_seconds=10.0,
    agg_type=AggregationType.SUM,
    allowed_lateness_seconds=2.0,
)

all_results = []
for event in source:
    try:
        results = agg.on_event(event)
        all_results.extend(results)
    except LateEventDroppedError as e:
        print(f"跳过迟到事件: t={e.event_timestamp}")

# 推进水位线触发剩余窗口
all_results.extend(agg.advance_watermark(100.0))

for r in all_results:
    tag = " [迟到重算]" if r.is_late_recompute else ""
    print(f"[{r.window.start:.0f}, {r.window.end:.0f}): {r.agg_type.value}={r.value}{tag}")
```
