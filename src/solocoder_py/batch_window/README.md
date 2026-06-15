# Batch Window Processor (批窗口处理器)

## 模块功能

批窗口处理器是一个基于事件时间的流数据窗口聚合模块，使用内存数据结构模拟数据源。核心功能包括：

1. **水位线(Watermark)推进机制**：基于已到达事件的时间戳维护水位线，按固定延迟滞后于当前已见的最大事件时间
2. **迟到事件归窗策略**：根据可配置的允许迟到时间上限决定迟到事件的归属
3. **精确一次(Exactly-Once)输出语义**：每个窗口的最终结果只输出一次，区分中间更新输出和最终输出

## 核心类职责

### Event
事件数据模型，表示流数据中的单个事件。
- `timestamp`: 事件发生时间（事件时间）
- `value`: 事件携带的数值数据（可选）
- `key`: 事件的键标识（可选）

### Window
窗口定义，表示一个左闭右开的时间区间 `[start, end)`。
- `start`: 窗口起始时间（包含）
- `end`: 窗口结束时间（不包含）
- `size`: 窗口大小
- `contains(timestamp)`: 判断时间戳是否属于该窗口

### WindowState
窗口状态，维护窗口内的聚合数据和生命周期标记。
- `window`: 对应的窗口定义
- `count/sum_value/min_value/max_value`: 聚合指标
- `is_fired`: 水位线是否已越过窗口结束时间（窗口已触发）
- `is_closed`: 窗口是否已完全关闭（不再接受任何事件）
- `final_output_emitted`: 最终结果是否已输出

### AggregationResult
聚合结果输出。
- `window`: 对应的窗口
- `agg_type`: 聚合类型
- `value`: 聚合结果值
- `output_type`: 输出类型（INTERMEDIATE 中间更新 / FINAL 最终输出）
- `is_late_update`: 是否为迟到事件触发的更新
- `is_final` / `is_intermediate`: 便捷属性判断输出类型

### WatermarkGenerator
水位线生成器，负责维护和推进水位线。
- `delay_seconds`: 水位线延迟量（可配置）
- `max_event_time`: 已观察到的最大事件时间
- `observe_event(timestamp)`: 观察事件时间戳，推进水位线
- `get_watermark()`: 获取当前水位线
- `advance_watermark(new_watermark)`: 手动推进水位线
- `is_window_triggerable(window_end)`: 判断窗口是否可触发计算
- `is_window_expired(window_end, allowed_lateness)`: 判断窗口是否已过期

### MemoryEventSource
内存事件源，模拟流式数据源。
- `add_event(event)` / `add_events(events)`: 添加事件
- `has_next()`: 是否有下一个事件
- `next()`: 获取并消费下一个事件
- `peek()`: 查看下一个事件但不消费
- `reset()`: 重置消费位置
- `clear()`: 清空所有事件

### BatchWindowProcessor
批窗口处理器主类，整合所有功能。
- `window_size_seconds`: 窗口大小（秒）
- `agg_type`: 聚合类型（COUNT/SUM/AVG/MIN/MAX）
- `allowed_lateness_seconds`: 允许迟到时间上限
- `watermark_delay_seconds`: 水位线延迟量（默认 5 秒）
- `on_event(event)`: 处理单个事件，返回触发的聚合结果
- `advance_watermark(new_watermark)`: 手动推进水位线
- `process_source(source)`: 处理整个事件源
- `get_watermark()`: 获取当前水位线
- `get_window_state(window_start)`: 获取窗口状态
- `get_final_output_count()`: 已输出最终结果的窗口数
- `get_final_output_windows()`: 已输出最终结果的窗口列表
- `reset()`: 重置处理器状态

## 水位线工作原理

水位线(Watermark)是流处理中衡量事件时间进度的机制：

```
最大事件时间 = max(所有已到达事件的时间戳)
水位线 = 最大事件时间 - 水位线延迟量
```

**核心规则**：
1. 水位线只向前推进，永不回退（防御性处理乱序事件）
2. 当水位线 >= 窗口结束时间时，该窗口被触发进行计算
3. 水位线延迟量决定了系统对乱序事件的容忍程度，延迟越大，等待乱序事件的时间越长

**示例**（延迟 5 秒）：
- 事件时间 10 到达 → 水位线 = 5
- 事件时间 15 到达 → 水位线 = 10（触发 [0,10) 窗口）
- 事件时间 20 到达 → 水位线 = 15

## 迟到事件的三种处理路径

### 路径1：归窗更新（Late Event Accepted with Update）

**条件**：窗口已触发（水位线越过窗口结束时间），但窗口尚未关闭（水位线 < 窗口结束时间 + 允许迟到时间）

**处理**：
- 事件被纳入原窗口
- 触发一次 INTERMEDIATE 类型的中间更新输出（标记 `is_late_update=True`）
- 下游看到的是更新后的结果值

### 路径2：丢弃（Late Event Dropped）

**条件**：窗口已关闭（水位线 >= 窗口结束时间 + 允许迟到时间）

**处理**：
- 事件被直接丢弃
- 抛出 `LateEventDroppedError` 异常
- `dropped_late_count` 计数器递增

### 路径3：拒绝（Window Already Closed）

**条件**：窗口状态已标记为 `is_closed=True`（窗口已被清理）

**处理**：
- 事件被拒绝
- 抛出 `WindowAlreadyClosedError` 异常
- `rejected_closed_count` 计数器递增

**三种路径的判断流程**：
```
事件到达
  ↓
更新水位线
  ↓
计算事件所属窗口
  ↓
窗口已关闭? → 是 → [路径3] 拒绝 (WindowAlreadyClosedError)
  ↓ 否
水位线 >= 窗口结束时间 + 允许迟到时间? → 是 → [路径2] 丢弃 (LateEventDroppedError)
  ↓ 否
水位线 >= 窗口结束时间? → 是 → [路径1] 归窗并输出中间更新
  ↓ 否
正常纳入窗口（窗口尚未触发）
```

## 精确一次语义保证机制

精确一次(Exactly-Once)语义确保每个窗口的最终结果只输出一次：

### 机制1：双重状态标记
每个窗口维护两个独立标记：
- `is_fired`: 水位线已越过窗口结束时间（已触发计算）
- `final_output_emitted`: 最终结果已输出

### 机制2：输出类型区分
- `OutputType.INTERMEDIATE`: 中间更新输出（窗口触发后、关闭前的迟到事件更新）
- `OutputType.FINAL`: 最终输出（窗口关闭时输出，之后不再接受任何事件）

### 机制3：已输出窗口集合
`_emitted_final_windows` 集合记录所有已输出最终结果的窗口起始时间，防止重复输出。

### 机制4：窗口关闭清理
当水位线越过 `窗口结束时间 + 允许迟到时间` 时：
1. 如果窗口有数据且尚未输出最终结果 → 输出 FINAL 结果
2. 标记窗口为 `is_closed=True`
3. 从活动窗口字典中删除该窗口

### 保证效果
- 每个窗口最多输出一条 FINAL 类型的结果
- 中间更新（INTERMEDIATE）可以有 0 或多条，但 FINAL 只有 1 条
- 最终输出之后，窗口完全关闭，任何该窗口的后续事件都被丢弃或拒绝

## 使用示例

### 示例1：基本窗口计数（无迟到容忍）

```python
from solocoder_py.batch_window import (
    BatchWindowProcessor,
    Event,
    AggregationType,
    OutputType,
)

proc = BatchWindowProcessor(
    window_size_seconds=10.0,
    agg_type=AggregationType.COUNT,
    allowed_lateness_seconds=0.0,
    watermark_delay_seconds=5.0,
)

proc.on_event(Event(timestamp=1.0))
proc.on_event(Event(timestamp=5.0))
proc.on_event(Event(timestamp=8.0))

results = proc.advance_watermark(10.0)
for r in results:
    if r.is_final:
        print(f"窗口 [{r.window.start}, {r.window.end}) 最终计数: {r.value}")
        # 输出: 窗口 [0.0, 10.0) 最终计数: 3
```

### 示例2：带迟到容忍的求和聚合

```python
from solocoder_py.batch_window import (
    BatchWindowProcessor,
    Event,
    AggregationType,
)

proc = BatchWindowProcessor(
    window_size_seconds=10.0,
    agg_type=AggregationType.SUM,
    allowed_lateness_seconds=5.0,
    watermark_delay_seconds=0.0,
)

proc.on_event(Event(timestamp=5.0, value=10.0))

# 窗口触发，输出中间结果
results = proc.advance_watermark(10.0)
# 收到迟到事件，输出更新后的中间结果
proc.on_event(Event(timestamp=3.0, value=20.0))
proc.on_event(Event(timestamp=7.0, value=15.0))

# 窗口关闭，输出最终结果
results = proc.advance_watermark(15.0)
final = [r for r in results if r.is_final][0]
print(f"最终求和结果: {final.value}")
# 输出: 最终求和结果: 45.0
```

### 示例3：使用内存事件源批量处理

```python
from solocoder_py.batch_window import (
    BatchWindowProcessor,
    Event,
    MemoryEventSource,
    AggregationType,
)

source = MemoryEventSource()
source.add_events([
    Event(timestamp=1.0, value=10),
    Event(timestamp=5.0, value=20),
    Event(timestamp=12.0, value=30),
    Event(timestamp=15.0, value=40),
    Event(timestamp=25.0, value=50),
])

proc = BatchWindowProcessor(
    window_size_seconds=10.0,
    agg_type=AggregationType.SUM,
    allowed_lateness_seconds=0.0,
    watermark_delay_seconds=0.0,
)

results = proc.process_source(source)
for r in results:
    if r.is_final:
        print(f"[{r.window.start}, {r.window.end}): sum={r.value}")
# 输出:
# [0.0, 10.0): sum=30.0
# [10.0, 20.0): sum=70.0
# [20.0, 30.0): sum=50.0
```

### 示例4：处理迟到事件统计

```python
from solocoder_py.batch_window import (
    BatchWindowProcessor,
    Event,
    LateEventDroppedError,
)

proc = BatchWindowProcessor(
    window_size_seconds=10.0,
    allowed_lateness_seconds=0.0,
    watermark_delay_seconds=0.0,
)

proc.on_event(Event(timestamp=100.0))

for ts in [5.0, 15.0, 25.0]:
    try:
        proc.on_event(Event(timestamp=ts))
    except LateEventDroppedError as e:
        print(f"丢弃事件: ts={e.event_timestamp}, "
              f"窗口结束={e.window_end}, "
              f"允许迟到={e.allowed_lateness}")

print(f"总共丢弃 {proc.dropped_late_count} 个迟到事件")
```
