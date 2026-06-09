# 心跳看门狗监控模块

本模块实现了一个基于内存数据结构的心跳看门狗监控域，用于追踪被监控实体的存活状态，支持租约过期判定、状态翻转去抖以及失活回调通知。

## 模块功能

- **实体注册与心跳上报**：每个被监控实体具有唯一 ID，通过定期上报心跳来刷新自身租约时间
- **租约过期判定**：若实体在租约时间内未上报心跳，则判定为疑似失活；支持不同实体配置不同的租约时间
- **状态翻转去抖**：当实体状态在"活跃"与"失活"之间频繁切换时（如网络抖动导致心跳短暂延迟），引入去抖计数窗口，只有连续多次判定为失活才真正变更状态
- **失活回调通知**：当实体被最终判定为失活（经过去抖窗口后）时，触发注册的失活回调函数，通知上层业务处理
- **可注入时钟**：时间来源可通过依赖注入替换，便于在测试中精确控制时间流逝
- **线程安全**：所有核心状态操作均通过 `threading.RLock` 保护，支持多线程并发访问
- **回调安全隔离**：失活回调在锁外执行，单个回调的异常或耗时操作不会阻塞其他实体的心跳上报或状态判定

## 核心类职责

### EntityStatus
实体状态枚举。

- `ACTIVE`：活跃状态，实体正常上报心跳
- `INACTIVE`：失活状态，实体在租约时间内连续多次未上报心跳

### WatchdogConfig
看门狗全局默认配置数据类，构造时自动校验参数合法性。

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `default_lease_ttl` | float | 10.0 | 默认租约时长（秒），必须 > 0 |
| `default_debounce_count` | int | 3 | 默认去抖次数，必须 > 0 |

### EntityConfig
单个实体的注册配置数据类，构造时自动校验参数合法性。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `entity_id` | str | 实体唯一标识，不能为空 |
| `lease_ttl` | float | 该实体的租约时长（秒），必须 > 0 |
| `debounce_count` | int | 该实体的去抖次数，必须 > 0 |
| `on_inactive` | Optional[Callable[[str], None]] | 可选，实体最终失活时的回调函数 |

### MonitoredEntity
被监控实体的状态数据类。

核心字段：
- `entity_id`：实体唯一标识
- `lease_ttl`：该实体的租约时长（秒）
- `debounce_count`：该实体的去抖次数
- `status`：当前状态（EntityStatus）
- `last_heartbeat_at`：最后一次收到心跳的时间戳
- `inactive_streak`：连续失活判定计数，每次 `check_expired()` 发现租约过期 +1，收到心跳重置为 0
- `on_inactive`：可选，失活回调函数
- `status_changed_at`：最近一次状态变更的时间戳

核心方法：
- `record_heartbeat(now)`：记录心跳，更新 `last_heartbeat_at` 并重置 `inactive_streak`
- `is_lease_expired(now)`：判断当前时间是否已超过租约时间
- `mark_inactive_streak()`：连续失活计数 +1，返回当前值
- `should_debounce_to_inactive()`：判断连续失活计数是否已达到去抖阈值
- `transition_to_inactive(now)`：将状态切换为 INACTIVE
- `transition_to_active(now)`：将状态切换为 ACTIVE 并重置计数
- `clone()`：深拷贝

### HeartbeatWatchdog
心跳看门狗主类，负责实体注册、心跳管理、租约过期判定、去抖与失活回调。

核心方法：
- `register_entity(entity_id, lease_ttl=None, debounce_count=None, on_inactive=None)`：注册实体，可自定义租约 TTL、去抖次数和失活回调；未指定的参数使用全局默认值
- `register_entity_from_config(config)`：通过 `EntityConfig` 对象注册实体
- `unregister_entity(entity_id)`：注销实体
- `heartbeat(entity_id)`：实体上报心跳，更新租约时间；若实体处于 INACTIVE 状态，将其恢复为 ACTIVE
- `get_entity(entity_id)`：获取指定实体的快照副本
- `get_all_entities()` / `get_active_entities()` / `get_inactive_entities()`：按状态查询所有实体的快照副本
- `is_registered(entity_id)`：判断实体是否已注册
- `check_expired()`：检查并推进所有 ACTIVE 实体的失活状态机，返回本次由 ACTIVE 转为 INACTIVE 的实体 ID 列表；触发相应的失活回调
- `check_all()`：执行 `check_expired()` 后返回所有实体的当前状态字典

### Clock
时间来源抽象接口。

- `Clock`：抽象基类，定义 `now()` 方法
- `SystemClock`：默认实现，使用系统单调时钟 `time.monotonic()`
- `ManualClock`：手动时钟，测试专用，支持 `advance(seconds)` 推进或 `set(time)` 设置时间

## 租约过期与去抖机制

### 租约过期判定

每个实体拥有独立的租约时长 `lease_ttl`。当 `check_expired()` 被调用时，对于每个处于 ACTIVE 状态的实体：

1. 计算 `now - last_heartbeat_at`，若结果 `>= lease_ttl`，则认为本次检查中租约已过期
2. 租约过期仅使 `inactive_streak` 计数 +1，并不直接变更状态

### 去抖窗口

为避免因网络抖动等瞬时故障导致的状态频繁翻转，引入 `debounce_count` 去抖参数：

- 只有当 `inactive_streak >= debounce_count` 时，实体状态才会真正从 ACTIVE 转为 INACTIVE
- 只要在达到去抖阈值前收到一次心跳，`inactive_streak` 即被重置为 0，状态保持 ACTIVE
- 去抖计数是基于 `check_expired()` 调用次数的，而非时间；上层业务可根据检查频率调整 `debounce_count`

### 失活回调

当实体通过去抖窗口被最终判定为 INACTIVE 时：

1. 若该实体注册时提供了 `on_inactive` 回调函数，则以 `entity_id` 为参数调用该回调
2. 回调函数在**锁外**执行，不会阻塞其他实体的心跳上报或状态判定
3. 每个回调函数的执行完全独立，单个回调抛出的异常会被静默捕获，不会影响其他回调的执行
4. 每个实体从 ACTIVE 转为 INACTIVE 只会触发一次回调；若实体通过心跳恢复为 ACTIVE 后再次失活，会再次触发回调
5. 回调函数内部可以安全地调用看门狗的任意公共方法（`register_entity`、`unregister_entity`、`heartbeat` 等），不会导致字典迭代异常或死锁

### 锁策略与回调安全性

为保证高并发场景下的可用性与正确性，模块采用以下锁策略：

#### 状态判定阶段（持锁）

`check_expired()` 在持有 `threading.RLock` 的情况下完成：
1. 通过 `list(self._entities.values())` 对实体字典创建快照副本，避免在迭代过程中字典结构发生变化
2. 遍历快照，对每个实体执行租约过期检查、去抖计数推进以及状态变更
3. 收集所有需要触发的失活回调（不立即执行）

此阶段锁的持有时间仅与实体数量成正比，不涉及任何用户代码，保证了最短的临界区。

#### 回调通知阶段（无锁）

状态判定完成并释放锁后，依次执行所有待触发的失活回调：

- **无锁执行**：回调执行期间不持有任何锁，其他线程可自由调用 `heartbeat()`、`register_entity()` 等方法，正常活跃实体不会因某个回调执行耗时操作而被阻塞
- **异常隔离**：每个回调用独立的 `try/except Exception` 包裹，单个回调抛出异常不会中断后续回调的执行，也不会影响 `check_expired()` 的返回结果
- **重入安全**：回调内部可自由调用看门狗的任意公共方法（包括修改内部字典的操作）。由于回调在锁外执行，不会与状态判定阶段产生竞态，也不会导致 Python 的 "dictionary changed size during iteration" 异常
- **执行顺序**：回调按实体在本次状态判定中被标记为 INACTIVE 的顺序依次同步执行；若需异步执行，业务方应在回调内部自行投递到线程池或消息队列

```
check_expired() 调用流程
┌──────────────────────────────────────────────────────────┐
│  1. 获取锁                                                │
│  2. list(self._entities.values()) → 创建实体快照          │
│  3. 遍历快照：租约检查 → 去抖计数 → 状态变更 → 收集回调    │
│  4. 释放锁                                                │
├──────────────────────────────────────────────────────────┤
│  5. （无锁）依次执行回调，每个回调独立 try/except          │
│     - 回调可安全调用 register_entity / unregister_entity │
│     - 回调可安全调用 heartbeat                            │
│     - 单个回调异常不影响其他回调                          │
└──────────────────────────────────────────────────────────┘
```

### 状态机流转

```
  心跳上报
   ┌──────┐
   │      ▼
ACTIVE ──────────────────────────────────────► INACTIVE
  ▲                                              │
  │  连续 check_expired() 租约过期               │
  │  且 inactive_streak >= debounce_count        │
  │                                              │
  └──────────────── 心跳上报 ────────────────────┘
```

详细规则：
1. **ACTIVE → INACTIVE**：连续 `debounce_count` 次 `check_expired()` 均判定租约过期
2. **ACTIVE → ACTIVE（重置计数）**：收到心跳，`inactive_streak` 重置为 0
3. **INACTIVE → ACTIVE**：收到心跳，立即恢复为 ACTIVE，`inactive_streak` 重置为 0
4. INACTIVE 状态的实体不受 `check_expired()` 影响，也不会重复触发失活回调

## 使用示例

### 基础：注册与心跳上报

```python
from solocoder_py.watchdog import HeartbeatWatchdog, ManualClock

clock = ManualClock()
watchdog = HeartbeatWatchdog(clock=clock)

watchdog.register_entity("service-1", lease_ttl=10.0, debounce_count=3)
watchdog.register_entity("service-2", lease_ttl=5.0, debounce_count=2)

clock.advance(3.0)
watchdog.heartbeat("service-1")

clock.advance(3.0)
watchdog.heartbeat("service-2")
```

### 失活检测与回调

```python
from solocoder_py.watchdog import HeartbeatWatchdog, ManualClock, EntityStatus

clock = ManualClock()
watchdog = HeartbeatWatchdog(clock=clock)

inactive_services = []

def on_service_down(entity_id: str) -> None:
    inactive_services.append(entity_id)
    print(f"Service {entity_id} is down!")

watchdog.register_entity(
    "worker-1",
    lease_ttl=5.0,
    debounce_count=3,
    on_inactive=on_service_down,
)

clock.advance(6.0)
watchdog.check_expired()  # inactive_streak = 1
watchdog.check_expired()  # inactive_streak = 2
assert watchdog.get_entity("worker-1").status == EntityStatus.ACTIVE
assert inactive_services == []

watchdog.check_expired()  # inactive_streak = 3 >= debounce_count
assert watchdog.get_entity("worker-1").status == EntityStatus.INACTIVE
assert inactive_services == ["worker-1"]
```

### 去抖期间恢复

```python
from solocoder_py.watchdog import HeartbeatWatchdog, ManualClock, EntityStatus

clock = ManualClock()
watchdog = HeartbeatWatchdog(clock=clock)

watchdog.register_entity("db-1", lease_ttl=2.0, debounce_count=5)

clock.advance(3.0)
watchdog.check_expired()  # streak = 1
watchdog.check_expired()  # streak = 2
watchdog.check_expired()  # streak = 3

watchdog.heartbeat("db-1")  # streak 重置为 0
assert watchdog.get_entity("db-1").inactive_streak == 0
assert watchdog.get_entity("db-1").status == EntityStatus.ACTIVE
```

### 从失活中恢复

```python
from solocoder_py.watchdog import HeartbeatWatchdog, ManualClock, EntityStatus

clock = ManualClock()
watchdog = HeartbeatWatchdog(clock=clock)

watchdog.register_entity("node-1", lease_ttl=1.0, debounce_count=1)

clock.advance(2.0)
expired = watchdog.check_expired()
assert "node-1" in expired
assert watchdog.get_entity("node-1").status == EntityStatus.INACTIVE

watchdog.heartbeat("node-1")
assert watchdog.get_entity("node-1").status == EntityStatus.ACTIVE
```

### 使用 EntityConfig 批量注册

```python
from solocoder_py.watchdog import HeartbeatWatchdog, EntityConfig

watchdog = HeartbeatWatchdog()

configs = [
    EntityConfig(entity_id="api-1", lease_ttl=5.0, debounce_count=3),
    EntityConfig(entity_id="api-2", lease_ttl=5.0, debounce_count=3),
    EntityConfig(entity_id="cache-1", lease_ttl=2.0, debounce_count=2),
]

for cfg in configs:
    watchdog.register_entity_from_config(cfg)

active = watchdog.get_active_entities()
assert set(active.keys()) == {"api-1", "api-2", "cache-1"}
```
