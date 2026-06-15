# Event Counter 模块 - 多粒度时间窗口事件计数器

本模块实现了一个基于内存数据结构的**多粒度时间窗口事件计数系统**，支持分钟、小时、天三种粒度的窗口计数、自动上卷聚合、窗口过期清理和读时智能合并查询。

## 模块功能

- **多粒度时间窗口计数**：支持按分钟、小时、天三种粒度创建计数窗口，事件发生时自动归入对应粒度的窗口并递增计数。
- **多粒度自动上卷**：写入事件时同步更新所有粒度级别的窗口计数，保证同一事件在所有粒度层级上的一致可见。
- **窗口自动过期清理**：每种粒度的窗口可配置保留时长，系统定期或按条件清理超出保留期的窗口数据，释放内存。清理粒度精确到窗口边界，不会在窗口中间截断导致计数丢失。
- **读时合并查询**：当查询的时间范围内不存在对应粒度的预聚合窗口时，系统在读时用更细粒度或相邻粒度的窗口数据临时合并出查询结果，保证查询不因过期而返回空值。
- **线程安全**：所有操作均支持并发调用，内部使用可重入锁保证数据一致性。

## 核心类职责

### EventCounter

事件计数器核心类，负责事件写入、多粒度上卷、窗口清理和查询合并。

| 方法 | 描述 |
|------|------|
| `record(event: Event)` | 记录单个事件，同步更新所有粒度窗口 |
| `record_many(events: list[Event])` | 批量记录多个事件 |
| `query(start, end, granularity)` | 查询指定时间范围内按指定粒度聚合的计数结果列表 |
| `query_single(timestamp, granularity)` | 查询单个时间点所在窗口的计数 |
| `get_count(timestamp, granularity)` | 获取单个时间点所在窗口的计数值（快捷方法） |
| `cleanup(reference_time=None)` | 手动触发窗口过期清理，返回各粒度清理的窗口数量 |
| `count_windows(granularity)` | 获取指定粒度当前存储的窗口数量 |
| `clear(granularity=None)` | 清除指定粒度或所有粒度的窗口数据 |

### Granularity (枚举)

时间窗口粒度枚举。

| 枚举值 | 说明 |
|--------|------|
| `Granularity.MINUTE` | 分钟级窗口（60秒） |
| `Granularity.HOUR` | 小时级窗口（3600秒） |
| `Granularity.DAY` | 天级窗口（86400秒） |

### Event

事件数据类，描述一次事件发生。

| 属性 | 类型 | 描述 |
|------|------|------|
| `timestamp` | datetime | 事件发生时间，支持时区感知或朴素时间（自动转为 UTC） |
| `count` | int | 本次事件的计数增量，默认为 1，必须为正数 |

### TimeWindow

时间窗口数据类，描述一个特定粒度的时间窗口。

| 属性/方法 | 描述 |
|-----------|------|
| `granularity` | 窗口的粒度 |
| `start` | 窗口起始时间（包含边界） |
| `end` | 窗口结束时间（排除边界） |
| `contains(timestamp)` | 判断时间戳是否在窗口内 |
| `key` | 窗口唯一标识键（用于存储） |
| `next_window()` | 获取下一个同粒度窗口 |
| `previous_window()` | 获取上一个同粒度窗口 |
| `to_coarser(coarser_granularity)` | 获取当前窗口所属的更粗粒度窗口 |
| `from_timestamp(timestamp, granularity)` | 从时间戳和粒度构造窗口（类方法） |

### CountResult

查询结果数据类。

| 属性 | 类型 | 描述 |
|------|------|------|
| `window` | TimeWindow | 对应的时间窗口 |
| `count` | int | 窗口内的计数值 |
| `is_estimated` | bool | 结果是否为估算值（从粗粒度向下拆分得到） |
| `source_granularity` | Granularity \| None | 实际数据来源的粒度；None 表示无数据 |

### GranularityConfig

粒度配置数据类。

| 属性 | 类型 | 描述 |
|------|------|------|
| `retention` | timedelta | 该粒度窗口的保留时长 |
| `default(granularity)` | GranularityConfig | 获取指定粒度的默认配置（类方法） |

默认保留时长：
- 分钟窗口：2 小时
- 小时窗口：7 天
- 天级窗口：90 天

## 多粒度上卷的工作机制

当一个事件被写入时，系统会同时更新该事件在**所有三个粒度**下对应的窗口计数，确保数据在所有层级的一致性。

```
事件时间: 2024-01-15 12:34:56 UTC

        ┌─────────────────────────────────────────────────┐
        │                    事件 +1                      │
        └─────────────┬──────────────┬───────────────────┘
                      │              │
                      ▼              ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│   分钟窗口 12:34:00      │  │   小时窗口 12:00:00      │
│   +1                     │  │   +1                     │
└──────────────────────────┘  └──────────────────────────┘
                      │
                      ▼
        ┌──────────────────────────┐
        │   天级窗口 2024-01-15     │
        │   +1                     │
        └──────────────────────────┘
```

### 一致性保证

由于所有粒度窗口在写入时同步更新，因此：
- 任意小时窗口的计数值 = 该小时内所有分钟窗口计数值之和
- 任意天级窗口的计数值 = 该天内所有小时窗口计数值之和

这为后续读时合并提供了数据基础。

## 窗口过期清理策略

### 清理触发时机

1. **自动清理**：每次写入事件（`record` 或 `record_many`）后自动触发
2. **手动清理**：调用 `cleanup()` 方法显式触发

### 清理粒度边界

清理操作以**完整窗口**为单位进行，不会在窗口中间截断：

```
保留期: 分钟窗口保留 2 小时
当前时间: 2024-01-15 12:30:00 UTC

   已过期（将被清理）           保留范围内
◄───────────────────────┤├───────────────────────────────►
  ... 10:29 | 10:30 | ... | 10:31 | ... | 12:29 | 12:30
          完整窗口边界       ↑
                    cutoff = 12:30 - 2h = 10:30
                    所有 start < 10:30 的分钟窗口都将被删除
```

具体规则：
- 计算截止时间 `cutoff = reference_time - retention`
- 找到 `cutoff` 所在的窗口边界
- 删除所有 `start < cutoff_window_start` 的窗口

这样保证即使一个窗口只过期了一部分，只要窗口起始时间在截止时间之前，整个窗口都会被完整删除，不会出现部分计数的情况。

## 读时合并规则

当查询某个粒度的窗口时，如果该窗口数据不存在（可能已过期或从未写入），系统会按照以下优先级尝试从其他粒度合并结果：

### 优先级 1：从更细粒度向上聚合（精确）

如果目标粒度没有直接数据，但存在更细粒度的窗口数据，系统会将所有落在目标窗口内的细粒度窗口计数值求和，得到精确结果。

```
查询: 小时窗口 12:00:00（无直接数据）

存在的分钟窗口:
  12:10:00 = 5
  12:20:00 = 3
  12:30:00 = 7

合并结果: 5 + 3 + 7 = 15  (is_estimated=False, source=MINUTE)
```

此结果是**精确值**，`is_estimated` 标记为 `False`。

### 优先级 2：从更粗粒度向下拆分（估算）

如果目标粒度和更细粒度都没有数据，但存在更粗粒度的窗口数据，系统会将粗粒度计数值平均拆分到细粒度窗口。

```
查询: 分钟窗口 12:34:00（无直接数据，分钟级已过期）
粗粒度数据存在: 小时窗口 12:00:00 = 60

拆分: 60 / 60分钟 = 1  (is_estimated=True, source=HOUR)
```

此结果是**估算值**，`is_estimated` 标记为 `True`，`source_granularity` 标记为实际使用的粗粒度。

### 优先级 3：返回零值

如果所有粒度都没有相关数据，返回计数值 0。

### 查询结果回退链

```
查询目标粒度窗口
    │
    ├─ 存在直接数据 ──► 返回精确值 (source=目标粒度)
    │
    └─ 无直接数据
         │
         ├─ 存在更细粒度数据 ──► 聚合返回精确值 (source=细粒度)
         │
         └─ 无细粒度数据
              │
              ├─ 存在更粗粒度数据 ──► 拆分返回估算值 (source=粗粒度, estimated=True)
              │
              └─ 无任何数据 ──► 返回 0 (source=None)
```

## 使用示例

### 基本使用

```python
from datetime import datetime, timedelta, timezone
from solocoder_py.event_counter import EventCounter, Event, Granularity

# 创建计数器（使用默认保留策略）
counter = EventCounter()

# 记录事件
ts = datetime(2024, 1, 15, 12, 34, 56, tzinfo=timezone.utc)
counter.record(Event(timestamp=ts))
counter.record(Event(timestamp=ts, count=3))  # 一次记录多个计数

# 查询单个窗口
print(counter.get_count(ts, Granularity.MINUTE))  # 4
print(counter.get_count(ts, Granularity.HOUR))    # 4
print(counter.get_count(ts, Granularity.DAY))     # 4
```

### 时间范围查询

```python
from datetime import datetime, timedelta, timezone
from solocoder_py.event_counter import EventCounter, Event, Granularity

counter = EventCounter()
base = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

# 记录 5 分钟的事件
for minute in range(5):
    ts = base + timedelta(minutes=minute)
    counter.record(Event(timestamp=ts, count=2))

# 查询分钟级结果
results = counter.query(
    start=base,
    end=base + timedelta(minutes=5),
    granularity=Granularity.MINUTE,
)
for r in results:
    print(f"{r.window.start} -> count={r.count}")
# 输出 5 个分钟窗口，每个 count=2

# 查询小时级结果（自动聚合）
hourly = counter.query(
    start=base,
    end=base + timedelta(hours=1),
    granularity=Granularity.HOUR,
)
print(hourly[0].count)  # 10 (5分钟 × 2 = 10)
```

### 自定义保留策略

```python
from datetime import timedelta
from solocoder_py.event_counter import EventCounter, Granularity
from solocoder_py.event_counter.models import GranularityConfig

# 自定义各粒度的保留时长
configs = {
    Granularity.MINUTE: GranularityConfig(retention=timedelta(hours=1)),
    Granularity.HOUR: GranularityConfig(retention=timedelta(days=3)),
    Granularity.DAY: GranularityConfig(retention=timedelta(days=30)),
}
counter = EventCounter(granularity_configs=configs)
```

### 手动触发清理

```python
from datetime import datetime, timezone
from solocoder_py.event_counter import EventCounter

counter = EventCounter()

# 指定参考时间进行清理
reference = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
removed = counter.cleanup(reference_time=reference)
print(f"清理了 {removed[Granularity.MINUTE]} 个分钟窗口")
print(f"清理了 {removed[Granularity.HOUR]} 个小时窗口")
print(f"清理了 {removed[Granularity.DAY]} 个天级窗口")
```

### 读时合并场景

```python
from datetime import datetime, timedelta, timezone
from solocoder_py.event_counter import EventCounter, Event, Granularity

counter = EventCounter()
hour_start = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

# 写入分钟级数据
for minute in range(5):
    ts = hour_start + timedelta(minutes=minute)
    counter.record(Event(timestamp=ts, count=2))

# 清除小时级窗口，模拟过期
counter.clear(Granularity.HOUR)

# 查询小时级 - 系统自动从分钟级聚合
result = counter.query_single(hour_start, Granularity.HOUR)
print(result.count)           # 10
print(result.is_estimated)    # False
print(result.source_granularity)  # Granularity.MINUTE

# 再清除分钟级窗口
counter.clear(Granularity.MINUTE)

# 先写入小时级数据
counter.record(Event(timestamp=hour_start, count=60))
counter.clear(Granularity.MINUTE)
counter.clear(Granularity.DAY)

# 查询分钟级 - 从小时级估算
minute_ts = hour_start + timedelta(minutes=30)
result = counter.query_single(minute_ts, Granularity.MINUTE)
print(result.count)           # 1 (60 / 60分钟)
print(result.is_estimated)    # True
print(result.source_granularity)  # Granularity.HOUR
```

### 批量写入

```python
from datetime import datetime, timedelta, timezone
from solocoder_py.event_counter import EventCounter, Event

counter = EventCounter()
base = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

events = [
    Event(timestamp=base + timedelta(seconds=i), count=i + 1)
    for i in range(100)
]
counter.record_many(events)
```

### 自定义时钟（用于测试）

```python
from datetime import datetime, timezone
from solocoder_py.event_counter import EventCounter, Event

# 使用固定时钟，便于测试
fixed_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
counter = EventCounter(clock=lambda: fixed_time)
```

## 线程安全

所有公共方法均为线程安全：
- 内部使用 `threading.RLock` 可重入锁
- 写入操作（`record`、`record_many`、`cleanup`、`clear`）在锁保护下执行
- 读取操作（`query`、`query_single`、`get_count`、`count_windows`）也在锁保护下执行，保证读取一致性

## 异常类型

| 异常类 | 描述 |
|--------|------|
| `EventCounterError` | 事件计数器模块的基础异常 |
| `InvalidGranularityError` | 无效的粒度参数 |
| `InvalidTimeRangeError` | 无效的时间范围（如 start >= end） |
| `WindowExpiredError` | 窗口已过期（保留供未来使用） |
