# 公平资源池调度器域

## 模块功能

本模块实现了一个带优先级、老化机制和饥饿防护的公平资源池调度器，核心功能包括：

1. **带优先级的任务调度**：资源池拥有固定数量的并发槽位，调度器按任务优先级从高到低分配，同优先级按提交时间 FCFS 分配。
2. **优先级老化（Aging）**：低优先级任务在等待队列中停留超过老化间隔后，其有效优先级会自动提升，避免长期被高优先级任务压制。
3. **饥饿防护（Starvation Protection）**：任何任务等待超过最大等待时间后，立即被提升至最高优先级，确保其能尽快获得下一个可用槽位。
4. **并发槽位占用与释放**：任务开始执行时占用槽位，执行完成后释放；释放后调度器立即从等待队列中分配可用槽位。
5. **内存数据结构**：使用内存列表和字典模拟资源池与等待队列，无外部依赖。

## 核心类职责

### models.py

| 类名 | 职责 |
|------|------|
| `Priority` | 优先级枚举（LOWEST=0, LOW=1, NORMAL=2, HIGH=3, HIGHEST=4），提供 `clamp` 方法将整型值限制在合法范围 |
| `Task` | 任务实体，包含 ID、原始优先级、有效优先级、资源槽位需求量、提交/等待开始时间、运行状态、饥饿防护标记等 |
| `SchedulerError` | 调度器异常基类 |
| `InsufficientSlotsError` | 任务资源需求超过资源池总容量时抛出 |
| `TaskNotFoundError` | 尝试释放不存在或未运行的任务时抛出 |
| `TaskNotRunningError` | 任务在运行集合中但未标记为运行时抛出 |

### scheduler.py

| 类名 | 职责 |
|------|------|
| `FairResourcePoolScheduler` | 调度器聚合根，管理槽位计数、等待队列、运行中任务集合；对外提供 `submit`、`release`、`tick` 等接口 |

#### `FairResourcePoolScheduler` 构造参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `total_slots` | `int` | 必填 | 资源池总并发槽位数，必须为正 |
| `aging_interval` | `timedelta` | 30 秒 | 优先级老化检查间隔 |
| `aging_promotion_step` | `int` | 1 | 每次老化提升的优先级步数 |
| `aging_threshold` | `Priority` | `Priority.LOW` | 老化提升后的有效优先级必须高于此阈值才生效 |
| `max_wait_time` | `timedelta` | 2 分钟 | 触发饥饿防护的最大等待时间 |
| `clock` | `callable` | `datetime.now` | 可注入的时间源，便于测试 |

#### 核心公开方法

| 方法 | 返回值 | 说明 |
|------|--------|------|
| `submit(task)` | `Task \| None` | 提交任务；槽位足够则立即执行并返回该任务，否则入队并返回 `None` |
| `release(task_id)` | `List[Task]` | 释放任务占用的槽位，并尝试从等待队列调度，返回新启动的任务列表 |
| `tick()` | `List[Task]` | 触发一次老化与饥饿防护检查，并尝试调度可执行任务 |

#### 只读属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `total_slots` | `int` | 总槽位数 |
| `available_slots` | `int` | 当前可用槽位数 |
| `used_slots` | `int` | 已占用槽位数 |
| `waiting_count` | `int` | 等待队列长度 |
| `running_count` | `int` | 运行中任务数 |

## 调度策略流程图

```
                 ┌─────────────────────┐
                 │   任务提交 submit   │
                 └──────────┬──────────┘
                            │
                 ┌──────────▼──────────┐
                 │ 需求 > 总槽位 ?     │────是────► InsufficientSlotsError
                 └──────────┬──────────┘
                            │否
                 ┌──────────▼──────────┐
                 │ 可用槽位 >= 需求 ?   │
                 └──────────┬──────────┘
                      是    │    否
            ┌───────────────┴───────────────┐
            │                               │
 ┌──────────▼──────────┐        ┌──────────▼──────────┐
 │  占用槽位、标记运行  │        │  进入等待队列       │
 │  返回 Task          │        │  记录 wait_started_at│
 └─────────────────────┘        └──────────┬──────────┘
                                            │
                              ┌─────────────▼─────────────┐
                              │         tick() 周期       │
                              │  1) 遍历等待队列           │
                              │  2) 应用优先级老化         │
                              │  3) 应用饥饿防护           │
                              └─────────────┬─────────────┘
                                            │
                              ┌─────────────▼─────────────┐
                              │       release(task_id)    │
                              │  1) 释放占用槽位           │
                              └─────────────┬─────────────┘
                                            │
                              ┌─────────────▼─────────────┐
                              │    _schedule_from_queue   │
                              │                           │
                              │  饥饿防护任务? ──是──► 取等待最久的
                              │       │否                  │
                              │       ▼                   │
                              │  按 (有效优先级 DESC,      │
                              │     等待开始时间 ASC) 排序 │
                              │       │                   │
                              │       ▼                   │
                              │  取出队首任务              │
                              │  槽位够? ──否──► 结束      │
                              │       │是                  │
                              │       ▼                   │
                              │  出队并分配槽位            │
                              │  循环直至无法分配          │
                              └───────────────────────────┘
```

### 关键决策规则

1. **调度优先级**
   - 饥饿防护任务（`is_starvation_protected=True`）优先于所有普通任务，多个饥饿任务按 `wait_started_at` 升序（FCFS）。
   - 普通任务按 `effective_priority` 降序，再按 `wait_started_at` 升序。

2. **优先级老化**
   - 参考时间为 `last_promoted_at`（首次为 `wait_started_at`）。
   - 距离参考时间超过 `aging_interval` 则提升 `aging_promotion_step` 级。
   - 只有当新的有效优先级严格大于 `aging_threshold` 时才真正生效。
   - 饥饿防护任务不再参与老化。

3. **饥饿防护**
   - 等待时长（`now - wait_started_at`）超过 `max_wait_time` 即触发。
   - 触发后 `is_starvation_protected=True`，`effective_priority=Priority.HIGHEST`。

## 使用示例

### 基本提交与释放

```python
from solocoder_py.scheduler import (
    FairResourcePoolScheduler, Priority, Task
)

scheduler = FairResourcePoolScheduler(total_slots=4)

t1 = Task.create(resource_slots=2, priority=Priority.HIGH, name="high-1")
t2 = Task.create(resource_slots=2, priority=Priority.LOW,  name="low-1")
t3 = Task.create(resource_slots=2, priority=Priority.NORMAL, name="normal-1")

assert scheduler.submit(t1) is t1        # 立即运行
assert scheduler.submit(t2) is t2        # 立即运行，2+2=4 满
assert scheduler.submit(t3) is None      # 入队
assert scheduler.waiting_count == 1

started = scheduler.release(t1.id)       # 释放 2 个槽位
assert len(started) == 1
assert started[0].name == "normal-1"     # 普通优先级高于 low
assert scheduler.running_count == 2
```

### 优先级老化

```python
from datetime import timedelta
from solocoder_py.scheduler import FairResourcePoolScheduler, Priority, Task
from datetime import datetime

start = datetime(2025, 1, 1, 0, 0, 0)
clock = [start]
def fake_clock():
    return clock[0]

scheduler = FairResourcePoolScheduler(
    total_slots=1,
    aging_interval=timedelta(seconds=30),
    aging_promotion_step=2,
    aging_threshold=Priority.LOW,
    clock=fake_clock,
)

blocker = Task.create(resource_slots=1)
scheduler.submit(blocker)

low_task = Task.create(resource_slots=1, priority=Priority.LOWEST)
scheduler.submit(low_task)

clock[0] += timedelta(seconds=45)
scheduler.tick()

assert low_task.effective_priority > Priority.LOWEST  # 已老化提升
```

### 饥饿防护

```python
from datetime import timedelta, datetime
from solocoder_py.scheduler import FairResourcePoolScheduler, Priority, Task

start = datetime(2025, 1, 1, 0, 0, 0)
clock = [start]

scheduler = FairResourcePoolScheduler(
    total_slots=1,
    max_wait_time=timedelta(minutes=2),
    clock=lambda: clock[0],
)

blocker = Task.create(resource_slots=1)
scheduler.submit(blocker)

forgotten = Task.create(resource_slots=1, priority=Priority.LOWEST)
high_task = Task.create(resource_slots=1, priority=Priority.HIGHEST)
scheduler.submit(forgotten)
scheduler.submit(high_task)

clock[0] += timedelta(minutes=3)
scheduler.tick()

assert forgotten.is_starvation_protected is True
assert forgotten.effective_priority == Priority.HIGHEST

started = scheduler.release(blocker.id)
assert started[0].id == forgotten.id   # 饥饿防护优先于原生高优先级
```

### 超大任务拒绝

```python
from solocoder_py.scheduler import (
    FairResourcePoolScheduler, Task, InsufficientSlotsError
)

scheduler = FairResourcePoolScheduler(total_slots=5)
huge = Task.create(resource_slots=10)

try:
    scheduler.submit(huge)
except InsufficientSlotsError:
    print("任务需求超过资源池总容量，已拒绝")
```

## 运行测试

```bash
poetry run pytest tests/scheduler/ -v
```
