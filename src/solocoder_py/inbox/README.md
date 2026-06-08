# Inbox 模块

消费侧收件箱去重域，用于保证消息接收端在面对重复投递、乱序到达时能够正确识别并过滤重复消息。使用内存数据结构（`OrderedDict`）模拟消息接收记录，适合单机场景下的消费端去重。

## 功能概述

- **消息 ID 滑动窗口去重**：根据消息唯一 ID 判断是否重复，窗口按已接收消息数量或时间跨度自动滑动，窗口外的旧 ID 不再参与去重比对
- **乱序到达处理**：不依赖消息到达顺序，在窗口范围内即使后发送的消息先到达，也能正确识别重复
- **TTL 过期清理**：去重记录超过 TTL 后自动失效，清理后的 ID 再次到达时视为新消息。支持惰性过期（访问时检查）和主动定时清理两种方式
- **灵活窗口配置**：窗口大小（最大记录数 / 最大时间跨度）和 TTL 均可独立配置，支持混合模式
- **统计查询**：支持查询当前窗口内的去重记录数量、累计接收数、累计重复数和去重命中率
- **并发安全**：使用 `threading.RLock` 保证多线程场景下同一条消息不会被判断为非重复多次消费

## 核心类职责

### Clock / SystemClock / ManualClock

时钟抽象，与 `idempotency`、`ratelimiter` 等模块保持一致的接口：

- `Clock`：抽象基类，定义 `now() -> float` 方法，返回单调递增的秒级时间戳
- `SystemClock`：生产环境默认实现，基于 `time.monotonic()`
- `ManualClock`：测试专用实现，支持 `advance(seconds)` 手动推进时间，无需 `sleep()` 等待真实时间流逝

### DedupWindowMode

枚举类型，定义去重窗口的滑动模式：

- `COUNT`：仅按消息数量滑动窗口，达到 `max_count` 后淘汰最早的记录
- `TIME`：仅按时间跨度滑动窗口，记录超过 `max_time_seconds` 后被淘汰
- `HYBRID`：混合模式，同时启用数量和时间两种淘汰策略，任一条件满足即淘汰

### InboxMessageRecord

数据类，封装单条消息的去重记录：

- `message_id`：消息唯一标识，业务方传入
- `received_at`：消息被去重器接收的时间戳（float 秒）

关键方法：
- `is_expired(ttl_seconds, clock)`：基于 TTL 和可注入时钟判断是否过期
- `age_seconds(clock)`：计算记录已存在的秒数
- `snapshot()`：返回字段完全相同的独立副本，避免外部修改影响内部状态

### DedupResult

去重检查结果封装：

- `is_duplicate`：是否为重复消息
- `record`：对应的消息记录快照（首次接收时为新创建的记录，重复时为已存在的记录）
- `should_process`：便捷属性，等价于 `not is_duplicate`

### DedupStats

统计信息数据类：

- `window_size`：当前窗口内的有效记录数
- `total_received`：累计接收的消息数（含重复）
- `total_duplicates`：累计判定为重复的消息数
- `hit_rate`：去重命中率 = `total_duplicates / total_received`，范围 [0.0, 1.0]

### InboxDedupStore

去重存储核心类，使用 `OrderedDict` 维护消息记录，保证插入有序的同时支持 O(1) 查找。

#### 可配置参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_count` | `Optional[int]` | `None` | 窗口最大记录数，超过后淘汰最早记录 |
| `max_time_seconds` | `Optional[float]` | `None` | 窗口最大时间跨度（秒），超过后淘汰超时记录 |
| `ttl_seconds` | `float` | `3600.0` | 单条记录的 TTL（秒），过期后记录失效 |
| `cleanup_interval_seconds` | `Optional[float]` | `None` | 主动清理间隔（秒），设置后每次 `check_duplicate` 会检查是否触发清理 |
| `_clock` | `Clock` | `SystemClock()` | 注入的时钟实例，测试中替换为 `ManualClock` |

> **注意**：`max_count` 和 `max_time_seconds` 至少需要设置一个，否则抛出 `DedupWindowConfigError`。

#### 主要方法

| 方法 | 说明 |
|------|------|
| `check_duplicate(message_id)` | 核心去重检查，返回 `DedupResult`，内部自动滑动窗口和惰性过期检查 |
| `contains(message_id)` | 判断消息 ID 是否存在于当前有效窗口内 |
| `get_record(message_id)` | 查询消息记录快照，不存在或已过期返回 `None` |
| `window_count()` | 返回当前窗口内的有效记录数 |
| `get_stats()` | 返回去重统计信息 `DedupStats` |
| `cleanup_expired()` | 主动清理所有 TTL 过期的记录，返回清理数量 |
| `remove(message_id)` | 主动移除指定消息 ID |
| `clear()` | 清空所有记录和统计数据 |
| `list_records()` | 返回当前窗口内所有记录的快照列表 |

## 滑动窗口去重原理

### 数据结构

使用 `collections.OrderedDict` 存储 `message_id -> InboxMessageRecord` 映射：

- **有序性**：保持消息的接收顺序（插入顺序），便于实现 FIFO 风格的数量淘汰
- **O(1) 查找**：判断重复时通过字典直接查找，避免遍历
- **move_to_end**：重复访问时将记录移到末尾，保持"最近活跃"的顺序语义

### 窗口滑动策略

每次 `check_duplicate()` 调用时按以下顺序执行：

```
check_duplicate(msg_id)
    │
    ├─ 1. maybe_trigger_cleanup()  // 若配置了 cleanup_interval，触发主动 TTL 清理
    │
    ├─ 2. slide_window()
    │      ├─ evict_by_time()     // 按 max_time_seconds 淘汰超时记录
    │      └─ evict_by_count()    // 按 max_count 淘汰超额记录
    │
    ├─ 3. 查找 msg_id 是否存在
    │      │
    │      ├─ 不存在 → 创建新记录，加入 OrderedDict 末尾，total_received++
    │      │
    │      └─ 存在
    │             ├─ 已过期 TTL → 删除旧记录，创建新记录（视为新消息）
    │             └─ 有效 → 判定为重复，total_received++，total_duplicates++
    │
    └─ 4. 再次 slide_window()     // 新记录加入后可能触发数量/时间淘汰
```

### 乱序到达的处理

去重逻辑完全基于 `message_id`，不依赖任何发送顺序或序列号：

- 消息 A（id=1）和消息 B（id=2）按发送顺序 1→2 到达：正常记录，均判定为新消息
- 消息 B（id=2）先于消息 A（id=1）到达：由于去重仅检查 id 是否存在于窗口内，两条消息均判定为新消息，去重结果与到达顺序无关
- 消息 A（id=1）之后再次到达 id=1：无论中间穿插了多少其他消息，只要 id=1 仍在窗口内且未过期，即判定为重复

### 过期清理的两种方式

1. **惰性过期（默认开启）**：每次 `check_duplicate` / `contains` / `get_record` 访问时，对被访问的单条记录检查 TTL。对整体性能影响最小，但未被访问的过期记录会继续占用内存。

2. **主动定时清理**：配置 `cleanup_interval_seconds` 后，每次 `check_duplicate` 会检查距上次清理是否超过间隔，若是则遍历所有记录清理 TTL 过期项。也可手动调用 `cleanup_expired()` 立即清理。

TTL 过期与窗口滑动的区别：
- 窗口滑动 (`max_count` / `max_time_seconds`) 控制"去重比对范围"，被滑出窗口的记录即使未到 TTL 也不再参与去重
- TTL 控制"记录的有效寿命"，即使记录在窗口大小范围内，超过 TTL 也会被清理

## 并发安全

所有公共方法均通过 `threading.RLock` 保护，保证：

- 多线程同时 `check_duplicate` 同一 `message_id` 时，只有一个线程会获得 `is_duplicate=False` 的结果
- 查询类方法与修改类方法之间不存在竞态条件
- `RLock`（可重入锁）允许内部方法嵌套调用时不发生死锁

## 快速使用

### 基础去重（按数量窗口）

```python
from solocoder_py.inbox import InboxDedupStore

store = InboxDedupStore(
    max_count=1000,        # 最多保留最近 1000 条消息 ID
    ttl_seconds=3600.0,    # 每条记录 1 小时后过期
)

result = store.check_duplicate("msg-001")
assert result.should_process is True   # 首次接收，应处理

result2 = store.check_duplicate("msg-001")
assert result2.is_duplicate is True    # 重复消息，跳过
```

### 按时间窗口

```python
from solocoder_py.inbox import InboxDedupStore, ManualClock

clock = ManualClock(start_time=0.0)
store = InboxDedupStore(
    max_time_seconds=60.0,   # 仅保留最近 60 秒内的消息
    ttl_seconds=300.0,
    _clock=clock,
)

store.check_duplicate("msg-old")
clock.advance(61.0)  # 推进时间超过窗口

result = store.check_duplicate("msg-old")
assert result.should_process is True   # 已滑出时间窗口，视为新消息
```

### 混合模式 + 主动清理

```python
from solocoder_py.inbox import InboxDedupStore

store = InboxDedupStore(
    max_count=500,
    max_time_seconds=120.0,
    ttl_seconds=60.0,
    cleanup_interval_seconds=10.0,  # 每 10 秒自动触发一次全局清理
)

# 业务处理循环
while True:
    msg = receive_message()
    result = store.check_duplicate(msg.id)
    if result.should_process:
        process_message(msg)
```

### 查询统计

```python
stats = store.get_stats()
print(f"窗口内记录数: {stats.window_size}")
print(f"累计接收: {stats.total_received}")
print(f"累计重复: {stats.total_duplicates}")
print(f"命中率: {stats.hit_rate:.2%}")
```
