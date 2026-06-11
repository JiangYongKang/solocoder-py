# Work Stealing Queue 工作窃取队列模块

基于内存数据结构实现的工作窃取队列域模块，提供并发安全的双端队列与工作线程池，支持本地 LIFO 操作与跨队列 FIFO 窃取。

## 模块功能

1. **本地 LIFO 操作**：每个工作线程拥有自己的本地任务队列，本地线程向自己的队列推入任务和弹出任务时使用后进先出策略（即最近推入的任务最先被本地线程取出），以提高缓存局部性。

2. **跨队列前端窃取**：当某个工作线程的本地队列为空时，它可以随机从其他工作线程的本地队列中窃取任务。窃取发生在被窃取队列的前端（即最早入队的任务被窃取走），使用先进先出（FIFO）策略，避免与本地线程的 LIFO 操作冲突。

3. **并发安全**：多个工作线程可能同时对同一个队列执行本地操作和窃取操作，队列的内部数据结构在并发场景下不会出现数据破坏或不一致。本地 LIFO 操作和远端窃取 FIFO 操作可以同时发生在不同端，在多数情况下互不阻塞。

4. **工作线程池**：管理一组工作线程，自动调度任务执行与窃取逻辑，对外提供简洁的任务提交接口。

## 核心类职责

### `Task`（任务模型）
代表队列中的单个任务。

**核心属性**：
- `id`：任务唯一标识
- `body`：任务体，支持任意类型
- `owner_worker_id`：所属工作线程 ID
- `status`：任务状态（`PENDING` / `RUNNING` / `COMPLETED` / `STOLEN`）
- `stolen_by`：被哪个线程窃取
- `created_at`：创建时间
- `completed_at`：完成时间

**核心方法**：
- `mark_running()`：标记为运行中
- `mark_stolen(thief_worker_id)`：标记为已被窃取
- `mark_completed()`：标记为已完成

### `WorkStealingDeque`（工作窃取双端队列）
并发安全的双端队列，是工作窃取算法的核心数据结构。

**设计思想**：
- 队列的底端（bottom / right end）供本地线程使用，采用 LIFO 策略
- 队列的顶端（top / left end）供窃取线程使用，采用 FIFO 策略
- 使用双锁设计：`_bottom_lock` 保护底端操作，`_steal_lock` 保护窃取操作
- 当队列元素 > 1 时，两端操作可并发执行，互不阻塞
- 当队列元素 == 1 时，需要协调两端操作，按 `bottom -> steal` 顺序加锁避免死锁

**核心方法**：
- `push_bottom(item)`：向底端推入元素（本地 LIFO 入队）
- `pop_bottom()`：从底端弹出元素（本地 LIFO 出队），空队列返回 `None`
- `steal()`：从顶端窃取元素（FIFO 出队），空队列返回 `None`
- `is_empty()`：判断队列是否为空
- `size()`：获取队列当前元素数量
- `max_capacity`：最大容量属性

### `WorkerPool`（工作线程池）
管理多个工作线程及其本地队列，自动执行任务并处理窃取逻辑。

**核心特性**：
- 任务提交支持指定工作线程或轮询分配
- 工作线程优先消费本地队列（LIFO）
- 本地队列为空时随机从其他线程窃取任务（FIFO）
- 统计信息追踪：已提交数、已完成数、被窃取数

**核心方法**：
- `submit(body, worker_id=None)`：提交任务，可指定目标线程
- `start(task_handler)`：启动所有工作线程
- `stop()`：停止所有工作线程
- `get_queue_size(worker_id)`：获取指定线程队列大小
- `get_total_queued()`：获取总队列长度
- `is_running`：是否运行中
- `submitted_count` / `completed_count` / `stolen_count`：统计属性

### 异常类
- `WorkStealingQueueError`：工作窃取队列异常基类
- `QueueFullError`：队列已满异常
- `QueueEmptyError`：队列为空异常
- `InvalidWorkerError`：无效工作线程异常

## LIFO / FIFO 双端操作策略

```
                     ┌─────────────────────────────────────────────┐
   顶端 (top)     │   任务 A │ 任务 B │ 任务 C │ 任务 D │     底端 (bottom)
   FIFO 窃取端     └─────────────────────────────────────────────┘
         ▲                                                          ▲
         │                                                          │
         │  steal()  从顶端窃取（最早入队）              push_bottom()  向底端推入
         │  FIFO 策略                                       LIFO 策略
         │                                                          │
    窃取线程                                                     本地线程
    (其他 worker)                                               (所有者 worker)
                                                                ▲
                                                                │
                                                          pop_bottom()
                                                          从底端弹出
                                                          （最近入队）
```

**策略说明**：

1. **本地 LIFO（底端）**：任务从底端推入，也从底端弹出。最新推入的任务最先被本地线程取出，提高缓存局部性（最近处理的任务数据可能仍在缓存中）。

2. **窃取 FIFO（顶端）**：窃取从顶端进行，窃取最早入队的任务。这样窃取操作与本地弹出操作分别在队列两端，减少冲突。

3. **并发设计**：
   - 多数情况下（队列元素 > 1），底端的 push/pop 与顶端的 steal 可并发执行，互不阻塞
   - 只有当队列仅剩一个元素时，两端操作需要协调，通过按固定顺序加锁避免死锁

## 使用示例

```python
import time
from solocoder_py.work_stealing_queue import (
    WorkStealingDeque,
    WorkerPool,
    Task,
    QueueFullError,
)

# 1. 基础双端队列基本操作
dq = WorkStealingDeque(max_capacity=100)

# 本地 LIFO 推入弹出
dq.push_bottom("task-1")
dq.push_bottom("task-2")
dq.push_bottom("task-3")

print(dq.pop_bottom())  # "task-3"  (LIFO: 最后推入的最先弹出
print(dq.pop_bottom())  # "task-2"

# 窃取 FIFO 操作
dq.push_bottom("task-4")
print(dq.steal())  # "task-1"  (FIFO: 最早入队的被窃取走)

# 2. 工作线程池
def process_task(task: Task):
    print(f"Processing {task.body} (owner={task.owner_worker_id}")
    time.sleep(0.01)

pool = WorkerPool(num_workers=4, max_queue_capacity=200)

# 提交任务到指定线程
for i in range(20):
    pool.submit(f"job-{i}", worker_id=0)  # 全部提交给 worker-0

# 启动线程池
pool.start(process_task)

# 等待任务完成
time.sleep(1.0)

# 查看统计
print(f"已提交: {pool.submitted_count}")
print(f"已完成: {pool.completed_count}")
print(f"被窃取: {pool.stolen_count}")

pool.stop()

# 3. 满容量队列
small_dq = WorkStealingDeque(max_capacity=2)
small_dq.push_bottom(1)
small_dq.push_bottom(2)

try:
    small_dq.push_bottom(3)
except QueueFullError:
    print("队列已满，无法推入")
```
