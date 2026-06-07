# 单飞（Single-Flight）请求合并器域模块

## 模块功能

本模块实现了基于内存数据结构的单飞（Single-Flight）请求合并器，用于在高并发场景下合并对同一个 key 的重复请求，避免重复计算，降低后端压力。支持以下核心能力：

1. **同 key 并发请求合并**：多个线程同时请求同一个 key 时，只允许第一个请求（领导者）真正执行计算函数，其余请求（等待者）阻塞等待并共享同一份执行结果。
2. **不同 key 并发隔离**：不同 key 的请求完全并行执行，互不阻塞，某个 key 的慢请求不会影响其他 key 的处理效率。
3. **结果共享与及时清理**：领导者请求完成后，所有等待者获得相同结果；该 key 的进行中记录立即从内部字典中移除，后续新的同 key 请求会重新触发计算。
4. **失败不缓存**：领导者请求执行失败时，所有等待者获得同一个异常对象；失败不会被长期缓存，下一次同 key 请求会重新执行计算函数。
5. **超时等待**：等待者可以配置等待超时时间，超时未得到结果会抛出 `WaitTimeoutError`。超时判断使用可注入的 `Clock` 抽象，便于测试中精确控制时间。
6. **调用统计**：合并器统计每个 key 的真实执行次数（executions）、共享命中次数（shared_hits）和失败次数（failures）。
7. **异常分层传播**：仅捕获并共享 `Exception` 级别的业务异常；`BaseException`（如 `KeyboardInterrupt`、`SystemExit`）会原样穿透，不会被当作业务失败传播给等待者。

## 核心类职责

### clock.py

| 类名 | 职责 |
|------|------|
| `Clock` | 时钟抽象接口（ABC），定义 `now() -> float` 方法，返回单调递增的时间戳（秒） |
| `SystemClock` | 系统默认时钟实现，基于 `time.monotonic()` 返回真实单调时间 |
| `ManualClock` | 手动控制时钟，提供 `advance()`、`set()` 方法用于测试中精确推进时间 |

### models.py

| 类名 | 职责 |
|------|------|
| `SingleFlightError` | 单飞模块异常基类 |
| `WaitTimeoutError` | 等待者超时异常，继承自 `SingleFlightError` |
| `CallCancelledError` | 领导者因系统级异常（`BaseException`）中止时，向等待者抛出的取消异常，继承自 `SingleFlightError` |
| `KeyStats` | 单个 key 的调用统计数据模型，包含真实执行次数、共享命中次数、失败次数 |
| `_Call` | 内部进行中请求条目，记录 key、结果、异常、完成标志、等待者数量及同步 Event |

### singleflight.py

| 类名 | 职责 |
|------|------|
| `SingleFlight` | 单飞请求合并器，线程安全。可通过构造参数注入自定义 `Clock`；维护进行中请求字典和统计字典，提供 `do()` 方法发起合并请求及各类统计查询接口 |

## 异常传播策略

为避免将系统级信号误判为业务失败，同时保证等待者不会永久挂死，本模块采用分层异常传播策略：

```
fn() 抛出异常
    │
    ├─ 是 Exception 子类（业务异常）
    │      ├─ 领导者：记录为 call.error，更新 failures 统计，原子 pop+set()
    │      └─ 等待者：收到同一个 Exception 对象
    │
    └─ 是 BaseException 但非 Exception（如 KeyboardInterrupt、SystemExit）
           ├─ 领导者：
           │      · 不创建/更新任何统计（不计入 executions/failures）
           │      · 设置 call.done=True，call.error=CallCancelledError(...)
           │      · 原子完成 pop + call.event.set()
           │      └─ 最终原样 re-raise 原始 BaseException（供领导者调用方感知）
           │
           └─ 等待者：
                  · 被 call.event.set() 唤醒（不会永久阻塞）
                  · 读取 call.error，收到 CallCancelledError
                  └─ 可通过 isinstance(e, SingleFlightError) 判断为框架级取消
```

### 设计理由

- `KeyboardInterrupt`、`SystemExit`、`GeneratorExit` 等 `BaseException` 属于进程级控制信号，不属于业务计算的"失败"，因此不计入任何业务统计。
- 原始 `BaseException` 不会直接共享给等待者——否则等待者会误判为业务失败而触发不必要的重试。等待者收到的是明确语义的 `CallCancelledError`（继承自 `SingleFlightError`），表示"本次合并调用因领导者被系统信号中止而被取消"。
- 领导者在 `BaseException` 分支与成功/业务失败分支一样，都会在同一把锁内完成 `_calls.pop()` + `call.event.set()`，保证：
  1. 等待者一定能被唤醒，不会永久挂死
  2. 后续新请求不会被"死条目"阻塞
  3. 等待者被唤醒时所有状态均已写入，无竞态窗口
- 领导者最终仍会原样 re-raise 原始 `BaseException`，保证进程级信号能被上层调用方正确感知（例如使得 `KeyboardInterrupt` 仍然可以终止程序）。

## 时钟注入

### 设计动机

项目中限流器、重试器等模块均采用可注入的 `Clock` 抽象来解耦真实时间，使得超时、窗口计算等逻辑在测试中可被精确控制。单飞模块遵循同一模式。

### 使用方式

```python
from solocoder_py.singleflight import SingleFlight, SystemClock, ManualClock

# 默认使用 SystemClock
sf_default = SingleFlight()
assert isinstance(sf_default.clock, SystemClock)

# 注入自定义时钟（测试场景）
clock = ManualClock()
sf_test = SingleFlight(clock=clock)
assert sf_test.clock is clock

# 手动推进时间
clock.advance(5.0)
assert clock.now() == 5.0
```

## 并发合并流程

```
Thread-A (Leader)                Thread-B (Waiter)            Thread-C (Waiter)
     |                                |                            |
     |  do("k", fn)                   |  do("k", fn)              |  do("k", fn)
     |  acquire lock                  |  acquire lock             |  acquire lock
     |  _calls["k"] = new Call        |  call.waiters++           |  call.waiters++
     |  is_leader=True                |  is_leader=False          |  is_leader=False
     |  release lock                  |  release lock             |  release lock
     |                                |                            |
     |  execute fn()                  |  call.event.wait()        |  call.event.wait()
     |    ...耗时计算...               |     ......阻塞......      |     ......阻塞......
     |                                |                            |
     |  ┌───────── WITHIN LOCK ────────────────────────────────────────┐
     |  │  store result/error in call                                    │
     |  │  update stats                                                  │
     |  │  self._calls.pop(key, None)   ← 原子移除                       │
     |  │  call.event.set()              ← 原子唤醒（与 pop 同一临界区）  │
     |  └───────────────────────────────────────────────────────────────┘
     |         event signal ───────────►│  wake up                  │  wake up
     |                                |  read result/error        |  read result/error
     |  return result/raise           |  return result/raise      |  return result/raise
     |                                |                            |
     ▼                                ▼                            ▼
```

### 流程说明

1. **竞争领导者**：多个线程同时调用 `do(key, fn)` 时，第一个获取锁并发现 `_calls` 中无该 key 的线程成为领导者，负责创建 `_Call` 条目。
2. **等待者登记**：后续到达的线程发现 `_Call` 已存在，将自身登记为等待者（`call.waiters++`）。
3. **领导者执行**：领导者释放锁后执行计算函数 `fn()`。
4. **原子完成**：领导者完成（成功或失败）后，在同一把锁内完成：写入结果/异常 → 更新统计 → 从 `_calls` 移除条目 → 调用 `call.event.set()` 唤醒所有等待者。这保证了等待者被唤醒时，所有状态均已就绪，不存在"事件已触发但数据未写入"的竞态窗口。
5. **等待者唤醒**：等待者被唤醒后进入锁内读取 `_Call` 中的结果或异常，返回给调用方。
6. **清理完毕**：领导者从 `_calls` 中移除条目后，新请求会重新触发计算，不会复用旧结果。

## 使用示例

### 基本用法：合并重复请求

```python
from solocoder_py.singleflight import SingleFlight

sf = SingleFlight()
call_count = 0

def expensive_computation() -> int:
    global call_count
    call_count += 1
    return 42

result = sf.do("user:123:profile", expensive_computation)
print(result)       # 42
print(call_count)   # 1
```

### 多线程并发合并

```python
import threading
from solocoder_py.singleflight import SingleFlight

sf = SingleFlight()
call_count = 0
barrier = threading.Barrier(5)
results = []

def worker():
    barrier.wait()
    def fn():
        global call_count
        call_count += 1
        import time
        time.sleep(0.05)
        return "result"
    results.append(sf.do("shared-key", fn))

threads = [threading.Thread(target=worker) for _ in range(5)]
for t in threads:
    t.start()
for t in threads:
    t.join()

print(call_count)   # 1，只执行了一次
print(len(results)) # 5，所有线程都拿到了结果
```

### 不同 key 并行执行

```python
import threading
import time
from solocoder_py.singleflight import SingleFlight

sf = SingleFlight()

def slow_fn(key):
    def inner():
        time.sleep(0.2)
        return key
    return inner

start = time.monotonic()
threads = []
for i in range(3):
    t = threading.Thread(target=lambda k: sf.do(f"key-{k}", slow_fn(k)), args=(i,))
    threads.append(t)
    t.start()
for t in threads:
    t.join()

elapsed = time.monotonic() - start
print(f"Total elapsed: {elapsed:.2f}s")  # 约 0.2s，三个 key 并行执行
```

### 等待者超时

```python
import threading
from solocoder_py.singleflight import SingleFlight, WaitTimeoutError

sf = SingleFlight()
slow_started = threading.Event()

def slow_leader():
    def fn():
        slow_started.set()
        import time
        time.sleep(2.0)
        return "done"
    return sf.do("slow-key", fn)

leader = threading.Thread(target=slow_leader)
leader.start()
slow_started.wait()

try:
    sf.do("slow-key", lambda: "x", timeout=0.1)
except WaitTimeoutError as e:
    print(f"Timed out: {e}")
```

### 异常共享与 BaseException 穿透

```python
import threading
from solocoder_py.singleflight import (
    SingleFlight,
    CallCancelledError,
    SingleFlightError,
)

sf = SingleFlight()

# --- 业务异常（Exception）会被共享给等待者 ---
class ServiceDown(Exception):
    pass

call_count = 0

def flaky_fn():
    global call_count
    call_count += 1
    if call_count <= 2:
        raise ServiceDown(f"attempt {call_count} failed")
    return f"success on attempt {call_count}"

try:
    sf.do("api", flaky_fn)
except ServiceDown as e:
    print(e)  # attempt 1 failed

try:
    sf.do("api", flaky_fn)
except ServiceDown as e:
    print(e)  # attempt 2 failed，失败不缓存，重新执行

result = sf.do("api", flaky_fn)
print(result)  # success on attempt 3

# --- 系统级信号（BaseException）：领导者穿透 + 等待者收到 CallCancelledError ---
class FatalSignal(BaseException):
    pass

leader_ready = threading.Event()
leader_exc: dict[str, BaseException] = {}
waiter_exc: dict[str, Exception] = {}

def leader_work():
    def fn():
        leader_ready.set()
        import time
        time.sleep(0.05)
        raise FatalSignal("interrupt")
    try:
        sf.do("cancel-demo", fn)
    except BaseException as e:
        leader_exc["leader"] = e

def waiter_work():
    try:
        sf.do("cancel-demo", lambda: "should-not-run")
    except Exception as e:
        waiter_exc["waiter"] = e

leader = threading.Thread(target=leader_work)
leader.start()
leader_ready.wait()

waiter = threading.Thread(target=waiter_work)
waiter.start()
leader.join()
waiter.join()

# 领导者原样收到 FatalSignal
assert isinstance(leader_exc["leader"], FatalSignal)

# 等待者不会挂死，收到 CallCancelledError（属于 SingleFlightError 体系）
assert isinstance(waiter_exc["waiter"], CallCancelledError)
assert isinstance(waiter_exc["waiter"], SingleFlightError)

# BaseException 路径不产生任何统计记录
assert sf.get_stats("cancel-demo") is None
```

### 注入 ManualClock 控制时间

```python
from solocoder_py.singleflight import SingleFlight, ManualClock

clock = ManualClock(start_time=0.0)
sf = SingleFlight(clock=clock)

assert sf.clock.now() == 0.0

clock.advance(10.0)
assert sf.clock.now() == 10.0

clock.set(100.0)
assert sf.clock.now() == 100.0
```

### 调用统计

```python
from solocoder_py.singleflight import SingleFlight

sf = SingleFlight()

sf.do("a", lambda: 1)
sf.do("a", lambda: 2)

stats = sf.get_stats("a")
if stats:
    print(f"Key: {stats.key}")
    print(f"  Executions: {stats.executions}")    # 2
    print(f"  Shared hits: {stats.shared_hits}")  # 0
    print(f"  Failures: {stats.failures}")        # 0

# 获取所有 key 的统计
all_stats = sf.get_all_stats()
for k, s in all_stats.items():
    print(f"{k}: executions={s.executions}, shared={s.shared_hits}, failures={s.failures}")

# 重置统计
sf.reset_stats()
```

### 查询进行中请求

```python
import threading
from solocoder_py.singleflight import SingleFlight

sf = SingleFlight()
ready = threading.Event()
proceed = threading.Event()

def slow_op():
    ready.set()
    proceed.wait()
    return "ok"

t = threading.Thread(target=lambda: sf.do("working", slow_op))
t.start()
ready.wait()

print(sf.in_flight_count("working"))  # 1
print(sf.in_flight_count())           # 1
print(sf.in_flight_count("other"))    # 0

proceed.set()
t.join()
print(sf.in_flight_count("working"))  # 0
```

## 运行测试

```bash
pytest tests/singleflight/ -v
```
