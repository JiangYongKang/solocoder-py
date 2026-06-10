# Sessionization 会话化域模块

## 模块功能

本模块实现了基于内存数据结构的会话化（Sessionization）域功能，支持以下核心能力：

1. **按空闲间隔切分会话**：连续事件之间的时间间隔不超过预设空闲阈值时属于同一会话，超过空闲阈值后当前会话关闭并开启新会话。
2. **会话合并**：当两个已完成会话在时间上存在重叠或间隔小于合并阈值时，将两者合并为单一会话，合并后的会话时间区间取最早开始和最晚结束。
3. **会话超时关闭**：会话持续无新事件超过指定超时时长后自动关闭并输出会话摘要信息（包含会话ID、开始时间、结束时间、事件计数等）。
4. **按主体分组独立维护**：不同主体（subject）的会话状态相互隔离互不干扰，同一主体的请求保证串行处理以避免并发创建多个重叠会话。

## 核心类职责

### clock.py

| 类名 | 职责 |
|------|------|
| `Clock` (ABC) | 时钟抽象接口，提供 `now()` 方法返回当前时间 |
| `SystemClock` | 基于系统时间的真实时钟实现 |
| `ManualClock` | 可手动推进的模拟时钟，用于测试超时等时间相关场景，支持 `advance_seconds()` 和 `set()` |

### exceptions.py

| 类名 | 职责 |
|------|------|
| `SessionizationError` | 会话化模块异常基类 |
| `SessionError` | 会话相关异常基类 |
| `SessionNotFoundError` | 指定会话不存在 |
| `InvalidEventError` | 事件非法（空事件、缺少时间等） |
| `InvalidSubjectError` | 主体ID非法（空值） |
| `InvalidThresholdError` | 阈值参数非法（负数或零） |

### models.py

| 类名/函数 | 职责 |
|-----------|------|
| `SessionEvent` | 会话事件数据模型：主体ID、事件时间、事件类型、事件载荷 |
| `Session` | 会话数据模型：会话ID、主体ID、开始时间、结束时间、事件计数、是否活跃、事件列表；提供 `duration` 属性、`add_event()`、`close()`、`copy()` 方法 |
| `make_session()` | 工厂函数，基于首个事件创建带唯一ID的新会话 |
| `merge_sessions()` | 合并两个会话，取最早开始和最晚结束时间，事件按时间排序 |

### sessionizer.py

| 类名 | 职责 |
|------|------|
| `Sessionizer` | 会话化管理器，线程安全，通过注入 `Clock` 支持可测试的时间驱动；维护各主体的活跃会话、已关闭会话、主体锁；提供事件添加、会话查询、会话合并、超时检测、回调注册等核心操作 |

## 异常层次

```
SessionizationError
├── SessionError
│   ├── SessionNotFoundError      # 会话不存在
│   ├── InvalidEventError         # 事件非法
│   ├── InvalidSubjectError       # 主体非法
│   └── InvalidThresholdError     # 阈值非法
```

所有异常均继承自 `SessionizationError`，调用方可通过捕获 `SessionizationError` 统一处理会话化相关错误。

## 会话切分规则

会话切分基于**空闲阈值**（`idle_threshold`，单位：秒）：

- 当新事件到达时，若主体当前没有活跃会话，创建新会话
- 若主体存在活跃会话，计算新事件与会话最后一个事件的时间间隔
  - 间隔 **≤ idle_threshold**：事件加入当前活跃会话，更新会话结束时间
  - 间隔 **> idle_threshold**：关闭当前活跃会话，创建新的活跃会话

### 边界处理

| 场景 | 行为 |
|------|------|
| 间隔恰好等于阈值 | 属于同一会话（`<=` 判定） |
| 间隔略大于阈值（如 1 秒） | 切分新会话 |
| 单个事件 | 自成一个会话，持续时间为 0 |
| 乱序事件（早于当前会话开始） | 若与当前会话开始时间的间隔 ≤ idle_threshold，加入当前会话并更新开始时间；否则创建新会话 |

## 会话合并规则

会话合并基于**合并阈值**（`merge_threshold`，单位：秒）：

调用 `merge_adjacent_sessions(subject_id)` 时：

1. 首先关闭当前活跃会话（若存在）
2. 将该主体所有已关闭会话按开始时间排序
3. 从前往后依次检查相邻会话：
   - 若后一个会话的开始时间与前一个会话的结束时间的间隔 **≤ merge_threshold**，则两者合并
   - 合并后的会话：开始时间取最早，结束时间取最晚，事件列表按时间排序
4. 重复此过程直到没有可合并的相邻会话

### 合并示例

假设 merge_threshold = 60 秒：

```
会话A: [10:00 - 10:05]
会话B: [10:06 - 10:10]   # 间隔 60 秒，恰好等于阈值 → 合并
会话C: [10:15 - 10:20]   # 间隔 300 秒，超过阈值 → 不合并

合并结果: [10:00 - 10:10], [10:15 - 10:20]
```

### 三方重叠合并

当存在三方重叠或链式合并时，算法会逐个合并，确保所有可合并的会话最终合并为一个：

```
会话A: [10:00 - 10:05]
会话B: [10:04 - 10:08]   # 与 A 重叠
会话C: [10:07 - 10:12]   # 与 B 重叠

合并结果: [10:00 - 10:12] （单次遍历链式合并）
```

## 会话超时机制

### 超时规则

基于**超时时长**（`timeout`，单位：秒）：

- 从会话的最后一个事件时间开始计算空闲时间
- 若空闲时间 **≥ timeout**，会话自动关闭
- 关闭时触发所有已注册的会话关闭回调

### 超时检测时机

超时检测在以下时机触发：

1. **事件添加时**：`add_event()` 方法在处理事件前先检测当前活跃会话是否超时
2. **查询会话时**：`get_active_session()`、`get_closed_sessions()`、`get_all_sessions()` 等查询方法在返回前检测超时
3. **批量检测**：`check_timeouts()` 方法遍历所有主体，检测并关闭所有超时的活跃会话，返回所有新关闭的会话

### 超时边界

| 场景 | 行为 |
|------|------|
| 空闲时间恰好等于 timeout | 会话关闭（`>=` 判定） |
| 空闲时间略小于 timeout | 会话保持活跃 |

## 主体隔离与并发安全

### 主体隔离

每个主体（subject）拥有独立的会话状态：

- 独立的活跃会话引用
- 独立的已关闭会话列表
- 独立的锁

不同主体的操作完全互不干扰。

### 并发安全

采用「全局锁 → 主体锁」的**统一锁顺序**架构，彻底避免死锁：

| 锁 | 保护范围 |
|----|----------|
| `_global_lock` (`threading.RLock`) | 主体会话字典、主体锁字典 |
| 每个主体独立的 `threading.RLock` | 单个主体的会话读写 |

**统一加锁顺序**：所有需要同时操作全局和主体数据的方法都严格按照**先获取 `_global_lock`，再获取对应主体锁**的顺序执行，绝不反向嵌套。

该策略保证：
1. **无死锁**：任意两个线程获取锁的顺序一致，不会出现循环等待
2. **串行处理**：同一主体的请求串行处理，避免并发创建多个重叠会话
3. **并发安全**：不同主体的操作可并行执行，提高吞吐量

## 会话关闭回调

通过 `add_session_closed_callback(callback)` 注册回调函数，当会话因以下原因关闭时触发：

- 空闲间隔超限导致的切分（旧会话关闭）
- 超时自动关闭
- 手动调用 `close_session()` 或 `force_close_all()`
- 合并操作导致的活跃会话关闭

回调函数接收一个 `Session` 对象（副本）作为参数，包含会话摘要信息：

- `session_id`：会话唯一标识
- `subject_id`：所属主体
- `start_time`：开始时间
- `end_time`：结束时间
- `event_count`：事件数量
- `is_active`：是否活跃（此时为 `False`）

## 封装保护

所有返回 `Session` 对象的公共方法均返回对象的深拷贝，调用方对返回值的任何修改不会影响管理器内部状态。

## 使用示例

### 基本使用

```python
from datetime import datetime
from solocoder_py.sessionization import Sessionizer, SessionEvent

sessionizer = Sessionizer(
    idle_threshold=300.0,   # 5 分钟空闲切分
    merge_threshold=0.0,    # 默认不合并
    timeout=1800.0,         # 30 分钟超时关闭
)

# 发送事件
event1 = SessionEvent(
    subject_id="user-001",
    event_time=datetime(2025, 1, 1, 12, 0, 0),
    event_type="page_view",
    payload={"page": "home"},
)
session = sessionizer.add_event(event1)
print(session.session_id, session.event_count)  # 新会话，1 个事件

event2 = SessionEvent(
    subject_id="user-001",
    event_time=datetime(2025, 1, 1, 12, 3, 0),
)
session = sessionizer.add_event(event2)
print(session.event_count)  # 仍为同一会话，2 个事件
```

### 会话切分

```python
sessionizer = Sessionizer(idle_threshold=60.0)  # 60 秒空闲切分

# 第一个会话
sessionizer.add_event(SessionEvent(
    subject_id="user-001",
    event_time=datetime(2025, 1, 1, 12, 0, 0),
))

# 超过 60 秒，切分新会话
sessionizer.add_event(SessionEvent(
    subject_id="user-001",
    event_time=datetime(2025, 1, 1, 12, 2, 0),
))

closed = sessionizer.get_closed_sessions("user-001")
active = sessionizer.get_active_session("user-001")
print(len(closed))   # 1 个已关闭会话
print(active is not None)  # 1 个活跃会话
```

### 会话合并

```python
sessionizer = Sessionizer(
    idle_threshold=60.0,
    merge_threshold=120.0,  # 间隔 ≤ 2 分钟的会话合并
)

times = [
    datetime(2025, 1, 1, 12, 0, 0),
    datetime(2025, 1, 1, 12, 1, 0),
    datetime(2025, 1, 1, 12, 2, 30),
    datetime(2025, 1, 1, 12, 4, 0),
]
for t in times:
    sessionizer.add_event(SessionEvent(subject_id="user-001", event_time=t))

# 合并前：3 个会话
all_sessions = sessionizer.get_all_sessions("user-001")
print(len(all_sessions))  # 3

# 合并后：1 个会话
merged = sessionizer.merge_adjacent_sessions("user-001")
print(len(merged))  # 1
print(merged[0].event_count)  # 4
```

### 会话超时与回调

```python
from solocoder_py.sessionization import ManualClock, Session, Sessionizer

clock = ManualClock(datetime(2025, 1, 1, 12, 0, 0))
sessionizer = Sessionizer(timeout=600.0, _clock=clock)  # 10 分钟超时

closed_sessions = []

def on_session_closed(s: Session) -> None:
    closed_sessions.append(s)
    print(f"会话 {s.session_id} 已关闭，共 {s.event_count} 个事件")

sessionizer.add_session_closed_callback(on_session_closed)

sessionizer.add_event(SessionEvent(
    subject_id="user-001",
    event_time=datetime(2025, 1, 1, 12, 0, 0),
))

# 推进时间超过超时阈值
clock.advance_seconds(700)

# 批量检测超时
newly_closed = sessionizer.check_timeouts()
print(len(newly_closed))  # 1
print(len(closed_sessions))  # 1，回调已触发
```

### 多主体隔离

```python
sessionizer = Sessionizer()

# 两个用户各有自己的会话，互不影响
sessionizer.add_event(SessionEvent(
    subject_id="user-A",
    event_time=datetime(2025, 1, 1, 12, 0, 0),
))
sessionizer.add_event(SessionEvent(
    subject_id="user-B",
    event_time=datetime(2025, 1, 1, 12, 0, 0),
))

session_a = sessionizer.get_active_session("user-A")
session_b = sessionizer.get_active_session("user-B")
print(session_a.session_id != session_b.session_id)  # True，不同会话
```

### 使用手动时钟测试

```python
from datetime import datetime
from solocoder_py.sessionization import ManualClock, Sessionizer

clock = ManualClock(datetime(2025, 1, 1, 12, 0, 0))
sessionizer = Sessionizer(
    idle_threshold=300.0,
    timeout=1800.0,
    _clock=clock,
)

# 添加事件
sessionizer.add_event(SessionEvent(
    subject_id="user-001",
    event_time=clock.now(),
))

# 推进时间
clock.advance_seconds(200)  # 200 秒，未超过空闲阈值

# 新事件加入同一会话
s = sessionizer.add_event(SessionEvent(
    subject_id="user-001",
    event_time=clock.now(),
))
print(s.event_count)  # 2

# 继续推进时间直到超时
clock.advance_seconds(2000)

# 查询时自动检测超时
active = sessionizer.get_active_session("user-001")
print(active is None)  # True，会话已超时关闭
```

## 运行测试

```bash
poetry run pytest tests/sessionization/ -q
```

测试覆盖以下场景：

- **正常流程**：会话创建、事件追加、会话切分、会话合并、超时关闭、主体隔离
- **边界条件**：空闲间隔恰好等于阈值、单个事件自成会话、超时边界时刻、合并阈值恰好等于间隔
- **异常分支**：事件乱序到达打乱现有会话、合并时三方重叠、空主体/空事件校验、阈值非法值
- **并发安全**：单主体多线程事件追加无重复会话、多主体并发隔离、并发读写无异常
- **封装保护**：返回对象均为独立副本，修改返回值不影响内部状态
