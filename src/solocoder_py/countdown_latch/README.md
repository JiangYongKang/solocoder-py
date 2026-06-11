# 倒计时栅栏（Countdown Latch）域模块

## 模块功能

本模块实现了基于内存数据结构的倒计时栅栏（Countdown Latch）同步原语，用于协调多个线程的执行，使一组线程能够等待计数归零时同时继续执行。支持以下核心能力：

1. **栅栏初始化与倒计数**：创建时指定计数初值 N，表示需要 N 方到达后栅栏才打开。每次调用 `count_down()` 将计数减一，当计数归零时栅栏打开，所有等待者被唤醒。
2. **多方到达等待汇合**：调用者可以通过 `wait()` 阻塞等待栅栏打开，支持多个调用者同时在栅栏上等待，栅栏打开时所有等待者同时唤醒继续执行。
3. **超时中止**：等待栅栏打开时支持指定超时时间，如果在超时时间内栅栏计数未归零，`wait()` 方法返回 `False` 表示超时失败，不会无限期阻塞。
4. **一次性触发语义**：栅栏计数归零后进入终态（OPENED），后续任何倒计数操作不影响状态（仍保持归零），任何新的等待调用应立即返回不再阻塞。栅栏不支持重置复用。
5. **可注入时钟**：通过 `Clock` 抽象接口支持注入自定义时钟，便于在测试中精确控制超时行为。
6. **状态查询与统计**：提供当前计数、栅栏状态、等待线程数等统计信息的查询接口。

## 核心类职责

### exceptions.py

| 类名 | 职责 |
|------|------|
| `CountdownLatchError` | 倒计时栅栏模块异常基类 |
| `InvalidCountError` | 无效计数异常，当初始化计数为负数时抛出 |
| `LatchTimeoutError` | 等待超时异常（预留，当前通过返回值标识超时） |

### models.py

| 类名 | 职责 |
|------|------|
| `LatchState` | 栅栏状态枚举，定义 `WAITING`（等待中）和 `OPENED`（已打开）两种状态 |
| `LatchStats` | 栅栏统计数据模型，包含初始计数、当前计数、当前状态、等待线程数 |
| `Clock` | 时钟抽象接口（ABC），定义 `now() -> float` 方法，返回单调递增的时间戳（秒） |
| `SystemClock` | 系统默认时钟实现，基于 `time.monotonic()` 返回真实单调时间 |
| `ManualClock` | 手动控制时钟，提供 `advance()`、`set()` 方法用于测试中精确推进时间 |

### countdown_latch.py

| 类名 | 职责 |
|------|------|
| `CountdownLatch` | 倒计时栅栏核心类，线程安全。可通过构造参数注入自定义 `Clock`；维护当前计数、状态、同步 Event 及等待线程统计，提供 `count_down()`、`wait()`、`get_stats()` 等接口 |

## 栅栏状态转换图

```
       初始化 count > 0
    ┌─────────────────────────┐
    │                         ▼
    │                   ┌───────────┐
    │                   │  WAITING  │
    │                   └───────────┘
    │                         │
    │                         │ count_down() 被调用 N 次
    │                         │ 使 current_count 减至 0
    │                         ▼
    │                   ┌───────────┐
    └──────────────────►│  OPENED   │  ←─── 初始化 count = 0
                        └───────────┘
                              ▲
                              │  终态，不可逆转
                              └────────────────────┐
                                                   │
                            任何 count_down() 都不改变状态
                            任何 wait() 都立即返回 True
```

### 状态说明

- **WAITING**：初始状态（count > 0 时），栅栏关闭，线程调用 `wait()` 会阻塞，直到计数归零。
- **OPENED**：终态，计数已归零，栅栏打开。所有等待中的线程被唤醒，后续调用 `wait()` 立即返回 `True`，调用 `count_down()` 不产生任何效果。

### 关键行为保证

1. **状态不可逆转**：一旦进入 OPENED 状态，永远不会回到 WAITING 状态。
2. **原子性计数**：`count_down()` 操作在锁保护下原子执行，确保并发安全。
3. **计数钳制**：当计数已为零时，继续 `count_down()` 不会使计数变为负数，始终保持为 0。
4. **全唤醒语义**：栅栏打开时，所有等待线程同时被唤醒，而非逐个唤醒。

## 使用示例

### 基本用法：等待多个任务完成

```python
import threading
from solocoder_py.countdown_latch import CountdownLatch

latch = CountdownLatch(count=3)
results = []
lock = threading.Lock()

def worker(task_id: int):
    global results
    # 模拟任务执行
    print(f"Task {task_id} started")
    import time
    time.sleep(0.1)
    with lock:
        results.append(task_id)
    # 任务完成，倒计数
    latch.count_down()
    print(f"Task {task_id} completed")

# 启动3个工作线程
threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
for t in threads:
    t.start()

# 主线程等待所有任务完成
print("Main thread waiting...")
latch.wait()
print(f"All tasks completed! Results: {results}")
```

### 多线程同时等待栅栏打开

```python
import threading
import time
from solocoder_py.countdown_latch import CountdownLatch

latch = CountdownLatch(count=1)
start_times = {}
end_times = {}
lock = threading.Lock()

def waiter(name: str):
    with lock:
        start_times[name] = time.monotonic()
    latch.wait()
    with lock:
        end_times[name] = time.monotonic()
    print(f"{name} resumed at {end_times[name]}")

# 启动5个等待线程
waiters = [threading.Thread(target=waiter, args=(f"Thread-{i}",)) for i in range(5)]
for t in waiters:
    t.start()

time.sleep(0.1)  # 确保所有线程都进入等待状态

# 倒计数一次，打开栅栏
print("Opening latch...")
latch.count_down()

for t in waiters:
    t.join()

# 验证所有线程几乎同时被唤醒
times = list(end_times.values())
max_diff = max(times) - min(times)
print(f"Max wakeup time difference: {max_diff:.6f}s")  # 应该非常小
```

### 带超时的等待

```python
import threading
from solocoder_py.countdown_latch import CountdownLatch

latch = CountdownLatch(count=5)

def slow_worker():
    import time
    for _ in range(5):
        time.sleep(0.3)
        latch.count_down()

t = threading.Thread(target=slow_worker)
t.start()

# 等待，但只愿意等1秒
print("Waiting with 1s timeout...")
result = latch.wait(timeout=1.0)
if result:
    print("Latch opened in time!")
else:
    print("Timeout! Latch not opened yet.")
    print(f"Current count: {latch.current_count}")

t.join()
print(f"Final count: {latch.current_count}")
```

### 一次性语义演示

```python
from solocoder_py.countdown_latch import CountdownLatch

latch = CountdownLatch(count=2)

# 倒计数两次，打开栅栏
latch.count_down()
latch.count_down()
print(f"Is open: {latch.is_open}")  # True
print(f"Current count: {latch.current_count}")  # 0

# 继续倒计数不影响状态
latch.count_down()
latch.count_down()
print(f"Current count after extra count_downs: {latch.current_count}")  # 0
print(f"Is open: {latch.is_open}")  # True

# 新的等待立即返回
import time
start = time.monotonic()
result = latch.wait()
elapsed = time.monotonic() - start
print(f"wait() returned {result} in {elapsed:.6f}s")  # 立即返回 True
```

### 注入 ManualClock 控制超时

```python
from solocoder_py.countdown_latch import CountdownLatch, ManualClock
import threading

clock = ManualClock()
latch = CountdownLatch(count=3, clock=clock)
wait_result = None

def waiter():
    global wait_result
    wait_result = latch.wait(timeout=5.0)

t = threading.Thread(target=waiter)
t.start()
import time
time.sleep(0.05)  # 确保线程进入等待

# 推进时间4.9秒，还没超时
clock.advance(4.9)
time.sleep(0.02)
print(f"After 4.9s, result: {wait_result}")  # None，仍在等待

# 再推进0.2秒，总时间5.1秒，超时触发
clock.advance(0.2)
t.join()
print(f"After 5.1s, result: {wait_result}")  # False，超时

# 如果在超时前打开栅栏
latch2 = CountdownLatch(count=1, clock=clock)
result2 = None

def waiter2():
    global result2
    result2 = latch2.wait(timeout=5.0)

t2 = threading.Thread(target=waiter2)
t2.start()
time.sleep(0.05)

clock.advance(3.0)
latch2.count_down()  # 打开栅栏
t2.join()
print(f"Result when opened in time: {result2}")  # True
```

### 查询统计信息

```python
from solocoder_py.countdown_latch import CountdownLatch
import threading
import time

latch = CountdownLatch(count=3)
start_event = threading.Event()

def waiter():
    start_event.wait()
    latch.wait()

# 启动3个等待线程
threads = [threading.Thread(target=waiter) for _ in range(3)]
for t in threads:
    t.start()

start_event.set()
time.sleep(0.05)

# 查询统计
stats = latch.get_stats()
print(f"Initial count: {stats.initial_count}")  # 3
print(f"Current count: {stats.current_count}")  # 3
print(f"State: {stats.state}")  # LatchState.WAITING
print(f"Waiting threads: {stats.waiting_threads}")  # 3

# 倒计数两次
latch.count_down()
latch.count_down()

stats = latch.get_stats()
print(f"Current count after 2 count_downs: {stats.current_count}")  # 1
print(f"State: {stats.state}")  # LatchState.WAITING

# 最后一次倒计数
latch.count_down()

stats = latch.get_stats()
print(f"Current count after 3 count_downs: {stats.current_count}")  # 0
print(f"State: {stats.state}")  # LatchState.OPENED
print(f"Waiting threads: {stats.waiting_threads}")  # 0

for t in threads:
    t.join()
```

### 边界情况：计数为1的栅栏

```python
from solocoder_py.countdown_latch import CountdownLatch
import threading
import time

latch = CountdownLatch(count=1)

# 多个线程同时等待
results = []
lock = threading.Lock()

def worker():
    latch.wait()
    with lock:
        results.append(time.monotonic())

threads = [threading.Thread(target=worker) for _ in range(10)]
for t in threads:
    t.start()

time.sleep(0.05)

# 一次倒计数打开栅栏
latch.count_down()

for t in threads:
    t.join()

print(f"All {len(results)} threads resumed")
print(f"Max time difference: {max(results) - min(results):.6f}s")
```

## 运行测试

```bash
pytest tests/countdown_latch/ -v
```
