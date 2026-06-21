# Futures / Promise 组合子库

一个纯内存实现的 Promise/Future 异步组合子库，使用内部回调队列管理异步任务的链式调用与聚合，不依赖异步事件循环。

## 模块功能

- **链式调用**：支持 `then` / `compose` / `catch` 链式调用，构建异步操作流水线
- **异常处理**：`catch` 方法捕获链中任一环节的异常，支持异常恢复后继续链式调用
- **聚合组合子**：提供 `all`、`allSettled`、`race` 等静态方法，聚合多个 Future
- **超时控制**：`with_timeout` 方法为 Future 增加超时限制
- **同步回调机制**：基于内部回调队列的同步完成机制，无需 asyncio 等事件循环
- **线程安全**：核心操作使用锁保护，支持多线程环境

## 核心类职责

### Future

Future/Promise 主类，表示一个尚未完成的计算。核心职责：

- 维护 Future 的状态（PENDING / FULFILLED / REJECTED）
- 存储成功值或失败原因
- 管理链式回调队列，在完成时依次触发注册的回调
- 提供链式调用方法 `then` / `compose` / `catch`
- 提供静态工厂方法 `resolve` / `reject`
- 提供静态聚合方法 `all` / `allSettled` / `race`
- 提供超时方法 `with_timeout`

### FutureState

Future 状态枚举，定义了三种状态：

- `PENDING`：待完成，初始状态
- `FULFILLED`：已成功完成
- `REJECTED`：已失败

### SettledResult

`allSettled` 聚合的结果数据类，包含：

- `status`：状态字符串，`"fulfilled"` 或 `"rejected"`
- `value`：成功时的值（仅 fulfilled 时有意义）
- `reason`：失败时的异常（仅 rejected 时有意义）

## Future/Promise 链式调用语义

Future 采用类似 JavaScript Promise 的链式调用模型：

1. 每个 Future 有三种状态：PENDING（待完成）、FULFILLED（成功）、REJECTED（失败）
2. Future 一旦 settle（完成或失败），状态不可改变
3. `then` 和 `catch` 方法返回新的 Future，形成链式调用
4. 回调函数在 Future settle 时同步执行
5. 如果在 Future 已 settle 后注册回调，回调会立即执行

### 状态流转图

```
        resolve(value)
PENDING ──────────────────► FULFILLED
   │                           │
   │ reject(exception)         │ then/catch
   └────────────────► REJECTED │
                        │      │
                        └──────┘
                        catch
```

## then / compose / catch 的区别与使用场景

### then

**签名**：`then(on_fulfilled) -> Future`

在 Future 成功完成时执行回调，将结果传入回调函数，返回新的 Future。

- 回调返回普通值：新 Future 以该值成功完成
- 回调抛出异常：新 Future 以该异常失败
- 回调返回 Future：自动展平嵌套的 Future（与 compose 行为一致）

**使用场景**：
- 转换异步操作的结果
- 在成功后执行下一步操作
- 构建值转换流水线

```python
Future.resolve(1) \
    .then(lambda x: x + 1) \
    .then(lambda x: x * 2)
# 结果: 4
```

### compose

**签名**：`compose(on_fulfilled) -> Future`

与 `then` 类似，但回调函数必须返回一个 Future，自动展平嵌套的 Future。

- 回调必须返回 Future，否则新 Future 以 TypeError 失败
- 返回的 Future 完成后，外层 Future 才完成

**使用场景**：
- 串联多个返回 Future 的异步操作
- 避免 Future 嵌套（Future of Future）
- 扁平化异步调用链

```python
Future.resolve("user_id") \
    .compose(lambda uid: fetch_user(uid)) \
    .compose(lambda user: fetch_orders(user.id))
```

### catch

**签名**：`catch(on_rejected) -> Future`

在 Future 失败时执行回调，捕获异常并可以恢复。

- 回调返回普通值：新 Future 以该值成功完成（异常恢复）
- 回调抛出异常：新 Future 以新异常失败
- 回调返回 Future：自动展平

**使用场景**：
- 捕获并处理异常
- 异常恢复（提供默认值或降级方案）
- 错误日志记录

```python
Future.reject(RuntimeError("fail")) \
    .catch(lambda e: "recovered") \
    .then(lambda v: v.upper())
# 结果: "RECOVERED"
```

### 对比总结

| 方法 | 触发时机 | 回调参数 | 回调返回 | 用途 |
|------|----------|----------|----------|------|
| `then` | 成功时 | 成功值 | 任意值 / Future | 值转换、下一步操作 |
| `compose` | 成功时 | 成功值 | 必须是 Future | 串联异步操作、展平嵌套 |
| `catch` | 失败时 | 异常 | 任意值 / Future | 异常处理、错误恢复 |

## 组合子的行为

### all

**签名**：`Future.all(futures: List[Future]) -> Future`

等待所有子 Future 全部成功完成，以结果列表完成。

- 所有子 Future 都成功：聚合 Future 以结果列表成功，顺序与输入一致
- 任一子 Future 失败：聚合 Future 立即以第一个失败的异常失败
- 空列表：立即以空列表成功完成

```python
Future.all([
    Future.resolve(1),
    Future.resolve(2),
    Future.resolve(3),
])
# 结果: [1, 2, 3]
```

### allSettled

**签名**：`Future.allSettled(futures: List[Future]) -> Future`

等待所有子 Future 全部完成（无论成功或失败），以状态列表完成。

- 每个条目是 `SettledResult` 对象，包含 `status`、`value`/`reason`
- 总是成功完成（不会失败），即使所有子 Future 都失败
- 顺序与输入一致

```python
results = Future.allSettled([
    Future.resolve(1),
    Future.reject(RuntimeError("oops")),
    Future.resolve(3),
]).value

# results[0].status == "fulfilled", results[0].value == 1
# results[1].status == "rejected", results[1].reason == RuntimeError("oops")
# results[2].status == "fulfilled", results[2].value == 3
```

### race

**签名**：`Future.race(futures: List[Future]) -> Future`

竞速模式，当任意一个子 Future 完成（成功或失败）时立即以该结果完成。

- 第一个完成的子 Future 的结果决定聚合 Future 的结果
- 其余子 Future 的结果被忽略
- 空列表：抛出 `ValueError`

```python
Future.race([fast_future, slow_future])
# 结果: fast_future 的结果
```

### with_timeout

**签名**：`with_timeout(timeout: float) -> Future`

为 Future 添加超时限制。

- 如果在超时时间内原 Future 完成：新 Future 以相同结果完成
- 如果超时：新 Future 以 `TimeoutError` 失败
- 超时后原 Future 才完成：结果被忽略
- 非正数的超时时间抛出 `ValueError`

```python
slow_future.with_timeout(5.0)
# 5秒内完成则返回结果，否则超时失败
```

## 同步回调完成机制

本库采用**同步回调式完成机制**，不依赖异步事件循环（如 asyncio）。

### 工作原理

1. 每个 Future 内部维护一个回调链列表（`_next_futures`）
2. 当调用 `then` / `compose` / `catch` 时，创建新的 Future 和对应的链节（`_ChainLink`）
3. 当 Future 被 fulfill 或 reject 时，同步遍历所有链节，依次触发回调
4. 回调的执行结果决定下游 Future 的状态

### 关键特性

- **同步执行**：回调在 Future settle 时立即同步执行，不排队到事件循环
- **立即执行**：如果 Future 已经 settle，注册回调时立即执行
- **顺序保证**：同一 Future 上注册的多个回调按注册顺序执行
- **线程安全**：核心状态转换使用锁保护，支持多线程环境

### 与异步事件循环的区别

| 特性 | 本库（同步回调） | asyncio（异步事件循环） |
|------|-----------------|------------------------|
| 执行时机 | settle 时立即执行 | 下一轮事件循环 |
| 阻塞 | 会阻塞当前线程 | 不会阻塞（协程切换） |
| 依赖 | 无外部依赖 | 需要事件循环 |
| 适用场景 | 内存中状态管理、回调链 | I/O 密集型异步操作 |

## 使用示例

### 基本链式调用

```python
from solocoder_py.futures import Future

# 创建已完成的 Future
f = Future.resolve(42)

# 链式转换
result = f.then(lambda x: x + 1) \
          .then(lambda x: x * 2)

print(result.value)  # 86
```

### 异常处理与恢复

```python
from solocoder_py.futures import Future

f = Future.reject(ValueError("invalid input"))

result = f.catch(lambda e: f"Error: {e}") \
          .then(lambda msg: msg.upper())

print(result.value)  # "ERROR: INVALID INPUT"
```

### compose 展平嵌套

```python
from solocoder_py.futures import Future

def fetch_user(user_id):
    return Future.resolve({"id": user_id, "name": "Alice"})

def fetch_orders(user):
    return Future.resolve([f"order-{user['id']}-1", f"order-{user['id']}-2"])

result = Future.resolve(123) \
    .compose(fetch_user) \
    .compose(fetch_orders)

print(result.value)  # ["order-123-1", "order-123-2"]
```

### all 聚合

```python
from solocoder_py.futures import Future

f1 = Future.resolve("a")
f2 = Future.resolve("b")
f3 = Future.resolve("c")

combined = Future.all([f1, f2, f3])
print(combined.value)  # ["a", "b", "c"]
```

### allSettled 聚合

```python
from solocoder_py.futures import Future

f1 = Future.resolve(1)
f2 = Future.reject(RuntimeError("failed"))
f3 = Future.resolve(3)

results = Future.allSettled([f1, f2, f3]).value

for i, r in enumerate(results):
    if r.status == "fulfilled":
        print(f"[{i}] success: {r.value}")
    else:
        print(f"[{i}] failed: {r.reason}")
```

### race 竞速

```python
from solocoder_py.futures import Future
import threading
import time

def delayed_value(value, delay):
    f = Future()
    def complete():
        time.sleep(delay)
        f._fulfill(value)
    threading.Thread(target=complete, daemon=True).start()
    return f

fast = delayed_value("fast", 0.1)
slow = delayed_value("slow", 1.0)

winner = Future.race([fast, slow])
# 等待 fast 完成后，winner 立即完成
```

### with_timeout 超时

```python
from solocoder_py.futures import Future, TimeoutError
import threading
import time

def slow_operation():
    f = Future()
    def complete():
        time.sleep(5)
        f._fulfill("done")
    threading.Thread(target=complete, daemon=True).start()
    return f

result = slow_operation().with_timeout(1.0)

# 等待超时
import time
time.sleep(1.5)

print(result.state)  # REJECTED
print(isinstance(result.reason, TimeoutError))  # True
```

### 手动创建和完成 Future

```python
from solocoder_py.futures import Future, FutureState

# 创建待完成的 Future
f = Future()
assert f.state == FutureState.PENDING

# 注册回调
results = []
f.then(lambda v: results.append(v))

# 完成 Future
f._fulfill(42)

print(results)  # [42]
print(f.value)  # 42
```

## API 参考

### Future 方法

| 方法 | 说明 |
|------|------|
| `then(on_fulfilled)` | 注册成功回调，返回新 Future |
| `compose(on_fulfilled)` | 注册成功回调（返回 Future），自动展平 |
| `catch(on_rejected)` | 注册失败回调，返回新 Future |
| `with_timeout(timeout)` | 添加超时限制 |
| `_fulfill(value)` | 以成功值完成 Future（内部方法） |
| `_reject(reason)` | 以异常失败 Future（内部方法） |
| `is_settled` | 属性，判断是否已完成 |
| `state` | 属性，当前状态 |
| `value` | 属性，成功值（未完成或失败时抛异常） |
| `reason` | 属性，失败原因（未完成时抛异常） |

### Future 静态方法

| 方法 | 说明 |
|------|------|
| `Future.resolve(value)` | 创建已成功完成的 Future |
| `Future.reject(reason)` | 创建已失败的 Future |
| `Future.all(futures)` | 等待所有成功，返回结果列表 |
| `Future.allSettled(futures)` | 等待所有完成，返回状态列表 |
| `Future.race(futures)` | 竞速，第一个完成的获胜 |

## 异常类

| 异常 | 说明 |
|------|------|
| `FutureError` | 所有 Future 异常的基类 |
| `FutureNotReadyError` | 访问未完成 Future 的结果时抛出 |
| `FutureAlreadySettledError` | 重复 settle 时抛出 |
| `TimeoutError` | 超时时抛出，包含 `timeout` 属性 |
