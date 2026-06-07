# 单飞（Single-Flight）请求合并器域模块

## 模块功能

本模块实现了基于内存数据结构的单飞（Single-Flight）请求合并器，用于在高并发场景下合并对同一个 key 的重复请求，避免重复计算，降低后端压力。支持以下核心能力：

1. **同 key 并发请求合并**：多个线程同时请求同一个 key 时，只允许第一个请求（领导者）真正执行计算函数，其余请求（等待者）阻塞等待并共享同一份执行结果。
2. **不同 key 并发隔离**：不同 key 的请求完全并行执行，互不阻塞，某个 key 的慢请求不会影响其他 key 的处理效率。
3. **结果共享与及时清理**：领导者请求完成后，所有等待者获得相同结果；该 key 的进行中记录立即从内部字典中移除，后续新的同 key 请求会重新触发计算。
4. **失败不缓存**：领导者请求执行失败时，所有等待者获得同一个异常对象；失败不会被长期缓存，下一次同 key 请求会重新执行计算函数。
5. **超时等待**：等待者可以配置等待超时时间，超时未得到结果会抛出 `WaitTimeoutError`。
6. **调用统计**：合并器统计每个 key 的真实执行次数（executions）、共享命中次数（shared_hits）和失败次数（failures）。

## 核心类职责

### models.py

| 类名 | 职责 |
|------|------|
| `SingleFlightError` | 单飞模块异常基类 |
| `WaitTimeoutError` | 等待者超时异常，继承自 `SingleFlightError` |
| `KeyStats` | 单个 key 的调用统计数据模型，包含真实执行次数、共享命中次数、失败次数 |
| `_Call` | 内部进行中请求条目，记录 key、结果、异常、完成标志、等待者数量及同步 Event |

### singleflight.py

| 类名 | 职责 |
|------|------|
| `SingleFlight` | 单飞请求合并器，线程安全，维护进行中请求字典和统计字典，提供 `do()` 方法发起合并请求及各类统计查询接口 |

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
     |  store result/error in call    |                            |
     |  update stats                  |                            |
     |  remove _calls["k"]            |                            |
     |  call.event.set() ────────────►│  wake up                  │  wake up
     |                                |  read result/error        |  read result/error
     |  return result                 |  return result/raise      |  return result/raise
     |                                |                            |
     ▼                                ▼                            ▼
```

### 流程说明

1. **竞争领导者**：多个线程同时调用 `do(key, fn)` 时，第一个获取锁并发现 `_calls` 中无该 key 的线程成为领导者，负责创建 `_Call` 条目。
2. **等待者登记**：后续到达的线程发现 `_Call` 已存在，将自身登记为等待者（`call.waiters++`）。
3. **领导者执行**：领导者释放锁后执行计算函数 `fn()`，将结果或异常写入 `_Call`，更新统计数据，从 `_calls` 中移除条目，最后通过 Event 唤醒所有等待者。
4. **等待者唤醒**：等待者被唤醒后读取 `_Call` 中的结果或异常，返回给调用方。
5. **清理完毕**：领导者从 `_calls` 中移除条目后，新请求会重新触发计算，不会复用旧结果。

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

### 异常共享与失败重试

```python
from solocoder_py.singleflight import SingleFlight

sf = SingleFlight()

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
