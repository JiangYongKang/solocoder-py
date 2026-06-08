# Bulkhead 舱壁隔离执行器模块

本模块实现了一个基于内存数据结构的舱壁隔离（Bulkhead Isolation）执行器，
通过资源组维度的并发限制与队列管理，实现任务执行的资源隔离与故障隔离。

## 模块功能

- **多资源组管理**：支持创建多个命名的资源组，每个资源组拥有独立的并发上限、满额策略与队列配置
- **按组限并发**：每个资源组的并发执行槽位独立计数，互不干扰
- **超额快速失败**：资源组满额时支持两种策略
  - `REJECT`：直接拒绝新任务，立即返回失败结果，携带任务标识和资源组信息
  - `QUEUE`：在组内队列中排队等待，超时后仍未获得槽位则失败
- **故障隔离**：单个资源组内任务频繁失败不影响其他资源组的任务执行；任务执行异常时会正确释放并发槽位
- **统计与可观测**：支持查询每个资源组的当前并发数、最大并发数、等待队列长度、累计成功/失败次数以及满额策略配置
- **线程安全**：所有状态变更均受锁保护，可在多线程环境中安全使用
- **可注入时钟**：时间来源可通过依赖注入替换，便于在测试中精确控制时间流逝
- **上下文管理器接口**：除了 `submit()` 提交任务函数外，还提供 `acquire()` 上下文管理器，可用于包裹任意代码块

## 核心类职责

### FullStrategy
资源组满额时的处理策略枚举。

- `REJECT`：直接拒绝新任务，立即返回 `REJECTED` 状态
- `QUEUE`：将任务放入等待队列，按 FIFO 顺序等待可用槽位；可配置队列超时和最大队列长度

### TaskStatus
任务执行状态枚举。

- `PENDING`：等待执行
- `RUNNING`：正在执行
- `SUCCESS`：执行成功
- `FAILED`：执行过程中抛出业务异常
- `REJECTED`：因资源组满额被直接拒绝
- `QUEUE_TIMEOUT`：排队等待超时，未获得执行槽位

### GroupConfig
资源组配置数据类，构造时自动校验参数合法性。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `name` | str | 资源组名称，非空 |
| `max_concurrency` | int | 最大并发执行数，必须 > 0 |
| `full_strategy` | FullStrategy | 满额策略，默认 `QUEUE` |
| `queue_timeout` | float | 排队超时时间（秒），`QUEUE` 策略下有效，默认 0（无限等待） |
| `max_queue_size` | int | 最大等待队列长度，0 表示无限制，默认 0 |

### GroupStats
资源组运行时统计快照（不可变数据类）。

- `name`：资源组名称
- `max_concurrency`：最大并发数
- `current_concurrency`：当前占用的并发槽位数
- `queue_size`：当前等待队列长度
- `success_count`：累计成功执行的任务数
- `failure_count`：累计执行失败的任务数
- `full_strategy`：当前满额策略
- `queue_timeout`：当前排队超时配置
- `max_queue_size`：当前最大队列长度配置

### TaskResult
任务执行结果数据类。

- `task_id`：任务唯一标识
- `group_name`：所属资源组名称
- `status`：任务最终状态（`TaskStatus`）
- `result`：任务返回值（成功时有效）
- `exception`：任务执行或提交时抛出的异常（失败/拒绝/超时时有效）
- `execution_time`：任务实际执行耗时（秒）
- `queue_wait_time`：任务在队列中的等待时间（秒）

### BulkheadExecutor
舱壁执行器主类。使用 `threading.RLock` 保护资源组字典，每个资源组内部使用 `threading.Condition` 协调并发与排队。

核心方法：

- `create_group(config: GroupConfig)`：创建新的资源组，名称重复时抛出 `GroupAlreadyExistsError`
- `remove_group(group_name: str)`：移除指定资源组
- `has_group(group_name: str) -> bool`：检查资源组是否存在
- `update_group_config(config: GroupConfig)`：动态更新已有资源组的配置
- `get_group_stats(group_name: str) -> GroupStats`：获取单个资源组的统计快照
- `get_all_group_stats() -> Dict[str, GroupStats]`：获取所有资源组的统计快照
- `submit(group_name, func, *args, task_id=None, **kwargs) -> TaskResult`：提交任务函数到指定资源组执行，同步返回 `TaskResult`
- `acquire(group_name, task_id=None)`：上下文管理器，手动获取并发槽位包裹代码块；被拒绝时抛出 `BulkheadFullError`，排队超时时抛出 `BulkheadQueueTimeoutError`

### 异常类

- `BulkheadError`：舱壁模块基类异常
- `BulkheadFullError`：资源组满额被直接拒绝，携带 `task_id` 和 `group_name`
- `BulkheadQueueTimeoutError`：排队等待超时，携带 `task_id` 和 `group_name`
- `GroupNotFoundError`：操作不存在的资源组
- `GroupAlreadyExistsError`：创建重名资源组
- `InvalidConfigError`：`GroupConfig` 参数校验失败

### Clock
时间来源抽象接口（本模块自带独立实现）。

- `Clock`：抽象基类，定义 `now()` 方法返回当前时间戳
- `SystemClock`：默认实现，使用系统单调时钟（`time.monotonic()`）
- `ManualClock`：手动时钟，用于测试，通过 `advance()` 推进或 `set()` 设置时间

## 舱壁隔离原理

舱壁模式（Bulkhead Pattern）的灵感来源于船舶的水密隔舱设计——即使船体某一部分进水，
也不会蔓延至其他隔舱，从而保证整体不会沉没。在软件系统中，舱壁模式通过为不同的
服务或任务类型划分独立的资源池（线程池、连接池、并发槽位等），避免某个局部的
故障或过载消耗掉全部系统资源，造成级联故障（Cascading Failure）。

本模块的隔离实现：

```
┌─────────────────────────────────────────────────────┐
│                  BulkheadExecutor                    │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │  Group: "A"  │  │  Group: "B"  │  │ Group: "C" │ │
│  │  max=2       │  │  max=5       │  │ max=1      │ │
│  │  [slots: 2]  │  │  [slots: 5]  │  │ [slots: 1] │ │
│  │  queue: []   │  │  queue: [...]│  │ queue: []  │ │
│  └──────────────┘  └──────────────┘  └────────────┘ │
└─────────────────────────────────────────────────────┘
```

每个资源组维护：
1. **并发槽位计数器**：`current_concurrency`，不超过 `max_concurrency`
2. **等待队列**：`deque`，按 FIFO 顺序存放等待中的任务包装器
3. **条件变量**：`threading.Condition`，用于协调"槽位释放 → 唤醒排队任务"的通知
4. **统计计数器**：`success_count`、`failure_count`

提交流程：

```
submit(task)
    │
    ▼
current_concurrency < max ?
    │
    ├─ 是 → 占用槽位，执行任务 → 成功/失败 → 释放槽位 → 通知队列
    │
    └─ 否 ──► full_strategy == REJECT ?
                    │
                    ├─ 是 → 返回 REJECTED (BulkheadFullError)
                    │
                    └─ 否 → 检查队列容量
                                │
                                ├─ 队列已满 → 返回 REJECTED
                                │
                                └─ 入队 → 等待条件变量通知
                                              │
                                     ┌────────┴────────┐
                                     │                 │
                              超时到期           被唤醒且有槽位
                                     │                 │
                                     ▼                 ▼
                            QUEUE_TIMEOUT          出队执行
```

## 故障隔离策略

1. **槽位始终释放**：无论任务是正常返回，还是在执行中抛出任何异常，
   `finally` 块都会确保释放已占用的并发槽位，并通过条件变量通知等待队列。
   这避免了因任务异常导致的槽位泄漏。

2. **失败不跨组传播**：每个资源组的 `success_count` / `failure_count` 独立统计，
   某个资源组的任务连续失败不会影响其他资源组的并发调度。

3. **异常处理策略**：`submit()` 仅捕获 `Exception` 子类并将其封装为
   `TaskResult(status=FAILED)` 正常返回，以便调用方统一处理业务异常。
   对于更底层的异常（如 `SystemExit`、`KeyboardInterrupt`），不会被捕获封装，
   而是原样向上抛出，但并发槽位依然会通过 `finally` 块被正确释放。
   `acquire()` 上下文管理器不捕获任何异常，全部交由调用方处理，
   只保证 `finally` 中释放槽位。

4. **可配置降级策略**：每个资源组可独立配置 `REJECT` 或 `QUEUE` 策略，
   为关键业务组和非关键业务组设置不同的服务等级。

## 使用示例

### 基础使用：submit() 提交任务

```python
from solocoder_py.bulkhead import (
    BulkheadExecutor,
    FullStrategy,
    GroupConfig,
    TaskStatus,
)

executor = BulkheadExecutor()

# 创建两个独立的资源组
executor.create_group(GroupConfig(
    name="critical",
    max_concurrency=10,
    full_strategy=FullStrategy.QUEUE,
    queue_timeout=5.0,
))

executor.create_group(GroupConfig(
    name="background",
    max_concurrency=2,
    full_strategy=FullStrategy.REJECT,
))

def process_order(order_id: int) -> dict:
    # 业务逻辑
    return {"order_id": order_id, "status": "ok"}

# 提交任务
result = executor.submit("critical", process_order, 12345)

if result.status == TaskStatus.SUCCESS:
    print(f"处理成功: {result.result}")
elif result.status == TaskStatus.REJECTED:
    print(f"任务被拒绝: {result.exception}")
elif result.status == TaskStatus.QUEUE_TIMEOUT:
    print(f"排队超时: {result.exception}")
elif result.status == TaskStatus.FAILED:
    print(f"执行失败: {result.exception}")
```

### 使用 acquire() 上下文管理器

```python
from solocoder_py.bulkhead import (
    BulkheadExecutor,
    BulkheadFullError,
    GroupConfig,
)

executor = BulkheadExecutor()
executor.create_group(GroupConfig(name="db_ops", max_concurrency=5))

try:
    with executor.acquire("db_ops"):
        # 这里的代码受舱壁保护，最多 5 个并发
        cursor = db.query("SELECT * FROM ...")
        rows = cursor.fetchall()
except BulkheadFullError as e:
    print(f"数据库操作被限流: task_id={e.task_id}, group={e.group_name}")
    # 返回降级结果
```

### 运行时观测

```python
# 查询单个资源组
stats = executor.get_group_stats("critical")
print(
    f"[{stats.name}] "
    f"并发 {stats.current_concurrency}/{stats.max_concurrency}, "
    f"队列 {stats.queue_size}, "
    f"成功 {stats.success_count}, 失败 {stats.failure_count}, "
    f"策略 {stats.full_strategy.value}"
)

# 批量查询所有资源组
for name, s in executor.get_all_group_stats().items():
    print(f"{name}: {s.current_concurrency}/{s.max_concurrency}")
```

### 测试中使用手动时钟

```python
from solocoder_py.bulkhead import (
    BulkheadExecutor,
    FullStrategy,
    GroupConfig,
    ManualClock,
    TaskStatus,
)

clock = ManualClock()
executor = BulkheadExecutor(clock=clock)
executor.create_group(GroupConfig(
    name="test",
    max_concurrency=1,
    full_strategy=FullStrategy.QUEUE,
    queue_timeout=10.0,
))

# 第一个任务占用槽位
import threading
barrier = threading.Barrier(2)

def blocking_task():
    barrier.wait()
    return "done"

t = threading.Thread(target=lambda: executor.submit("test", blocking_task))
t.start()
barrier.wait()

# 此时并发已满，第二个任务入队
result_holder = []
def submit_waiting():
    result_holder.append(executor.submit("test", lambda: "second"))

t2 = threading.Thread(target=submit_waiting)
t2.start()
time.sleep(0.01)

# 推进时钟超过超时时间，排队任务应超时失败
clock.advance(15.0)
t2.join()

assert result_holder[0].status == TaskStatus.QUEUE_TIMEOUT
```

### 动态切换满额策略

```python
from solocoder_py.bulkhead import FullStrategy, GroupConfig

# 运行时将 background 组从 REJECT 切换为 QUEUE
executor.update_group_config(GroupConfig(
    name="background",
    max_concurrency=2,
    full_strategy=FullStrategy.QUEUE,
    queue_timeout=30.0,
    max_queue_size=100,
))
```
