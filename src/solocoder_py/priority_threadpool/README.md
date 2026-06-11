# Priority ThreadPool 优先级线程池模块

本模块实现了一个基于内存数据结构的优先级线程池，使用虚拟时间模拟任务调度，
不依赖真实操作系统线程。支持多优先级队列调度、任务老化提权、优雅关闭排空
和并发度控制。

## 模块功能

- **多优先级队列调度**：线程池维护高、中、低三级优先级队列，工作线程从高优先级队列优先取任务执行，高优先级队列为空时才依次向低优先级队列获取任务
- **任务老化提权**：低优先级队列中的任务如果等待时间超过阈值，自动提升到更高优先级队列，防止低优先级任务在持续有高优先级任务提交时被永久饿死
- **优雅关闭排空**：线程池关闭时不中断正在执行的任务，等待所有已提交任务（包括各优先级队列中等待的任务）全部执行完毕后线程池才彻底关闭。关闭期间不再接受新任务提交
- **并发度控制**：线程池创建时指定最大并发数（工作线程数量），同时执行的任务数不超过该并发数，超出部分的提交任务在队列中排队等待
- **可注入时钟**：时间来源可通过依赖注入替换，便于在测试中精确控制时间流逝
- **统计与可观测**：支持查询线程池当前状态、各优先级队列长度、已提交/完成/失败任务计数

## 核心类职责

### Priority
任务优先级枚举。数值越小优先级越高。

- `HIGH = 0`：高优先级
- `MEDIUM = 1`：中优先级（默认）
- `LOW = 2`：低优先级

### TaskStatus
任务执行状态枚举。

- `PENDING`：等待执行
- `RUNNING`：正在执行
- `SUCCESS`：执行成功
- `FAILED`：执行过程中抛出业务异常
- `CANCELLED`：任务被取消
- `REJECTED`：线程池已关闭，任务被拒绝

### ThreadPoolState
线程池状态枚举。

- `RUNNING`：运行中，可接受新任务
- `SHUTTING_DOWN`：关闭中，不再接受新任务，正在执行和等待的任务继续处理
- `TERMINATED`：已终止，所有任务已完成

### ThreadPoolConfig
线程池配置数据类，构造时自动校验参数合法性。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `max_concurrency` | int | 最大并发执行数，必须 > 0 |
| `aging_threshold` | float | 老化提权阈值（秒），任务等待时间超过该值则提升一级优先级，默认 10.0，必须 >= 0 |
| `aging_check_interval` | float | 老化检查间隔（秒），默认 1.0，必须 > 0 |

### TaskResult
任务执行结果数据类。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `task_id` | str | 任务唯一标识 |
| `status` | TaskStatus | 任务最终状态 |
| `priority` | Priority | 任务当前优先级（可能已被老化提权提升） |
| `result` | Any | 任务返回值（成功时有效） |
| `exception` | Optional[BaseException] | 任务执行异常（失败时有效） |
| `submitted_at` | float | 提交时间戳 |
| `started_at` | Optional[float] | 开始执行时间戳 |
| `completed_at` | Optional[float] | 完成时间戳 |
| `original_priority` | Priority | 提交时的原始优先级 |
| `priority_boost_count` | int | 老化提权次数 |

### ThreadPoolStats
线程池运行时统计快照（不可变数据类）。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `state` | ThreadPoolState | 当前状态 |
| `max_concurrency` | int | 最大并发数 |
| `current_concurrency` | int | 当前正在执行的任务数 |
| `high_queue_size` | int | 高优先级队列长度 |
| `medium_queue_size` | int | 中优先级队列长度 |
| `low_queue_size` | int | 低优先级队列长度 |
| `total_submitted` | int | 累计提交任务数 |
| `total_completed` | int | 累计成功完成任务数 |
| `total_failed` | int | 累计失败任务数 |

### PriorityThreadPool
优先级线程池主类。使用虚拟时间模拟，不依赖真实操作系统线程。

核心方法：

- `__init__(config: ThreadPoolConfig, clock: Optional[Clock] = None)`：构造线程池
- `submit(func, *args, priority=Priority.MEDIUM, task_id=None, duration=0.0, **kwargs) -> str`：提交任务，返回 task_id。任务仅入队，需通过 `tick()` / `advance_time()` / `run_until_complete()` 显式调度执行
- `tick()`：推进一个执行周期（检查老化、启动任务、完成到期任务）
- `advance_time(seconds: float)`：推进指定秒数的虚拟时间，期间执行所有到期任务
- `run_until_complete()`：运行直到所有已提交任务完成
- `shutdown(wait: bool = True)`：优雅关闭线程池。`wait=True` 时阻塞直到所有任务完成；`wait=False` 时仅触发关闭流程，需后续调度
- `wait_for_task(task_id: str, timeout: Optional[float] = None) -> TaskResult`：等待指定任务完成
- `get_task_result(task_id: str) -> TaskResult`：获取任务结果，任务未完成时抛出 `TaskNotFoundError`
- `get_stats() -> ThreadPoolStats`：获取线程池统计快照

### 异常类

- `PriorityThreadPoolError`：模块基类异常
- `InvalidConfigError`：配置参数校验失败
- `ThreadPoolShutdownError`：线程池已关闭时提交新任务
- `TaskNotFoundError`：查询不存在的 task_id

### Clock
时间来源抽象接口（本模块自带独立实现）。

- `Clock`：抽象基类，定义 `now()` 方法返回当前时间戳
- `SystemClock`：默认实现，使用系统单调时钟（`time.monotonic()`）
- `ManualClock`：手动时钟，用于测试，通过 `advance()` 推进或 `set()` 设置时间

## 优先级调度与老化提权策略

### 三级优先级队列

线程池内部维护三个独立的 FIFO 队列，分别对应 HIGH、MEDIUM、LOW 三个优先级。

调度时严格按照优先级从高到低取任务：

```
取任务时的检查顺序：
  HIGH 队列  →  非空则取队首
     ↓ 空
  MEDIUM 队列 →  非空则取队首
     ↓ 空
  LOW 队列   →  非空则取队首
     ↓ 空
  无任务可取
```

同一优先级队列内按提交时间（FIFO）顺序执行。

### 老化提权（Aging）

为防止低优先级任务被永久饿死，实现了老化提权机制：

1. 每个任务记录 `submitted_at` 提交时间戳
2. 每隔 `aging_check_interval` 秒检查一次各队列
3. 对于 LOW 队列：如果 `now - task.submitted_at >= aging_threshold`，将其提升到 MEDIUM 队列
4. 对于 MEDIUM 队列：如果 `now - task.submitted_at >= aging_threshold`，将其提升到 HIGH 队列
5. 每次提升 `priority_boost_count` 加 1，最多提升至 HIGH

**提权时的队列插入策略**：被提升的任务按原始 `submitted_at` 时间插入到目标队列的正确位置，确保先提交的任务优先执行。

```
示例：aging_threshold = 5s

t=0  提交 LOW_task_A  (LOW)
t=2  提交 HIGH_task_X (HIGH) → 立即执行，duration=10s
t=5  LOW_task_A 等待了 5s → 提升到 MEDIUM
t=10 HIGH_task_X 完成
     MEDIUM 队列中有 LOW_task_A，先执行
     此时即使有新提交的 MEDIUM_task_B (t=9 提交)，
     LOW_task_A (t=0 提交) 因其更早的 submitted_at 仍优先执行
```

### 虚拟时间调度

由于不使用真实操作系统线程，任务调度通过虚拟时间推进触发：

1. 任务提交时仅入队，不立即执行
2. 每个任务可通过 `duration` 参数指定模拟执行时长（默认 0 秒）
3. 调用 `advance_time(seconds)` 或 `tick()` 时：
   - 检查并应用老化提权
   - 按优先级从队列取任务启动，不超过 `max_concurrency`
   - 任务启动时计算 `completes_at = now + duration`
   - 对于所有 `completes_at <= now` 的运行中任务，执行函数并标记完成
   - 释放的并发槽位用于启动更多等待任务

### 优雅关闭流程

```
调用 shutdown(wait=True)
    │
    ▼
状态: RUNNING → SHUTTING_DOWN
    │
    ▼
拒绝新的 submit()（抛出 ThreadPoolShutdownError）
    │
    ▼
继续执行：
  · 当前运行中的任务
  · 各优先级队列中等待的任务
  · 老化提权机制继续生效
    │
    ▼
所有任务执行完毕
    │
    ▼
状态: SHUTTING_DOWN → TERMINATED
```

## 使用示例

### 基础使用：提交和调度任务

```python
from solocoder_py.priority_threadpool import (
    PriorityThreadPool,
    ThreadPoolConfig,
    Priority,
    TaskStatus,
)

pool = PriorityThreadPool(ThreadPoolConfig(max_concurrency=2))

execution_order = []

def task(name: str):
    execution_order.append(name)
    return f"{name}_result"

# 提交不同优先级的任务
low_id = pool.submit(task, "low_1", priority=Priority.LOW)
high_id = pool.submit(task, "high_1", priority=Priority.HIGH)
med_id = pool.submit(task, "med_1", priority=Priority.MEDIUM)

# 运行直到所有任务完成
pool.run_until_complete()

# 检查执行顺序：高优先级先执行
assert execution_order == ["high_1", "med_1", "low_1"]

# 获取任务结果
result = pool.get_task_result(high_id)
assert result.status == TaskStatus.SUCCESS
assert result.result == "high_1_result"

# 关闭线程池
pool.shutdown()
```

### 使用手动时钟控制时间（测试场景）

```python
from solocoder_py.priority_threadpool import (
    PriorityThreadPool,
    ThreadPoolConfig,
    Priority,
    ManualClock,
)

clock = ManualClock()
pool = PriorityThreadPool(
    ThreadPoolConfig(max_concurrency=1, aging_threshold=5.0),
    clock=clock,
)

# 提交一个占用很久的高优先级任务
pool.submit(lambda: None, priority=Priority.HIGH, task_id="blocker", duration=100.0)

# 提交一个低优先级任务
low_id = pool.submit(lambda: None, priority=Priority.LOW, task_id="low_task")

# 推进时间 10 秒，触发老化提权
clock.advance(10.0)
pool.tick()

# 检查低优先级任务已被提升
result = pool.get_task_result(low_id)
assert result.priority_boost_count >= 1  # 已从 LOW 提升到 MEDIUM
```

### 并发度控制

```python
from solocoder_py.priority_threadpool import (
    PriorityThreadPool,
    ThreadPoolConfig,
)

pool = PriorityThreadPool(ThreadPoolConfig(max_concurrency=2))

for i in range(5):
    pool.submit(lambda: None, task_id=f"task_{i}", duration=1.0)

stats = pool.get_stats()
# 提交后未调度，所以队列中有 5 个任务
assert stats.high_queue_size + stats.medium_queue_size + stats.low_queue_size == 5

# 推进时间
pool.advance_time(0.5)
stats = pool.get_stats()
# 并发度为 2，所以有 2 个任务正在运行，3 个在队列中
assert stats.current_concurrency == 2
```

### 优雅关闭

```python
from solocoder_py.priority_threadpool import (
    PriorityThreadPool,
    ThreadPoolConfig,
    ThreadPoolState,
    ThreadPoolShutdownError,
)

pool = PriorityThreadPool(ThreadPoolConfig(max_concurrency=2))

pool.submit(lambda: None, task_id="task_1")
pool.submit(lambda: None, task_id="task_2")

# 触发优雅关闭（不等待）
pool.shutdown(wait=False)

stats = pool.get_stats()
assert stats.state == ThreadPoolState.SHUTTING_DOWN

# 关闭后提交新任务会被拒绝
try:
    pool.submit(lambda: None, task_id="task_3")
except ThreadPoolShutdownError:
    print("任务已被正确拒绝")

# 运行直到完成（此时才会真正执行所有任务）
pool.run_until_complete()

stats = pool.get_stats()
assert stats.state == ThreadPoolState.TERMINATED
assert stats.total_completed == 2
```

### 观测统计信息

```python
from solocoder_py.priority_threadpool import PriorityThreadPool, ThreadPoolConfig

pool = PriorityThreadPool(ThreadPoolConfig(max_concurrency=3))

for i in range(10):
    pool.submit(lambda: None)

stats = pool.get_stats()
print(
    f"状态: {stats.state.value}, "
    f"并发: {stats.current_concurrency}/{stats.max_concurrency}, "
    f"队列: HIGH={stats.high_queue_size} MEDIUM={stats.medium_queue_size} LOW={stats.low_queue_size}, "
    f"提交: {stats.total_submitted}, 完成: {stats.total_completed}, 失败: {stats.total_failed}"
)
```
