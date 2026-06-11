# Future 组合器域模块

## 模块功能

本模块实现了基于内存数据结构的 Future 组合器，用于模拟异步任务的执行与结果组合。支持以下核心能力：

1. **Future 抽象**：表示尚未完成的异步计算结果，支持三种状态（PENDING / COMPLETED / FAILED），通过回调或阻塞等待获取最终结果。
2. **all 组合器**：等待所有 Future 全部成功完成，按输入顺序聚合结果；任一 Future 失败则立即失败，携带第一个遇到的异常。
3. **any 组合器**：等待任意一个 Future 成功完成，返回最快成功的那个结果；所有 Future 全部失败时才失败，聚合所有异常信息。
4. **race 组合器**：等待任意一个 Future 最先完成（无论成功还是失败），忽略其余 Future 的后续结果。
5. **超时熔断**：为任意 Future 设置超时时间，超时未完成则自动以 `FutureTimeoutError` 完成，不再等待原始结果。

## 核心类职责

### models.py

| 类名 | 职责 |
|------|------|
| `FutureState` | Future 状态枚举，包含 `PENDING`（未完成）、`COMPLETED`（已完成有结果）、`FAILED`（已完成有异常）三种状态 |

### exceptions.py

| 类名 | 职责 |
|------|------|
| `FutureError` | 模块异常基类 |
| `FutureNotReadyError` | 访问尚未完成的 Future 的结果时抛出 |
| `FutureAlreadyCompletedError` | 对已完成的 Future 重复设置结果时抛出 |
| `FutureTimeoutError` | Future 超时未完成时抛出 |
| `AllCombinatorError` | all 组合器中任一 Future 失败时抛出，携带第一个异常（`first_error` 属性） |
| `AnyCombinatorError` | any 组合器中所有 Future 均失败时抛出，聚合所有异常（`errors` 属性） |

### future.py

| 类名 | 职责 |
|------|------|
| `Future` | 核心异步计算抽象，线程安全。支持 `set_result` / `set_error` 设置结果、`add_callback` 注册回调、`wait` / `get` 阻塞等待、以及 `completed` / `failed` / `from_callable` 静态工厂方法 |

### combinators.py

| 函数名 | 职责 |
|--------|------|
| `all_combinator` | 接收一组 Future，返回新 Future；全部成功时结果按输入顺序排列，任一失败则立即失败 |
| `any_combinator` | 接收一组 Future，返回新 Future；首个成功即完成，全部失败时聚合所有异常 |
| `race_combinator` | 接收一组 Future，返回新 Future；最先完成（无论成功或失败）即作为结果 |

### timeout.py

| 函数名 | 职责 |
|--------|------|
| `with_timeout` | 为 Future 添加超时熔断，超时未完成则以 `FutureTimeoutError` 完成；原 Future 已完成则直接透传 |

## 组合器行为规则差异

| 特性 | all | any | race |
|------|-----|-----|------|
| 完成条件 | **所有** Future 都成功完成 | **任意一个** Future 成功完成 | **任意一个** Future 最先完成（不论成败） |
| 成功结果 | 按输入顺序的结果列表 | 最快成功的单个结果 | 最先完成的单个结果 |
| 失败条件 | 任一 Future 失败 | 所有 Future 都失败 | 第一个完成的是失败 |
| 失败信息 | 第一个遇到的异常（`AllCombinatorError.first_error`） | 所有异常列表（`AnyCombinatorError.errors`） | 最先完成的那个异常 |
| 空列表行为 | 返回已完成 Future，结果为 `[]` | 返回已失败 Future，`AnyCombinatorError(errors=[])` | 抛出 `ValueError` |

### 行为对比示例

```
假设 3 个 Future：f1 成功(v1)、f2 失败(e2)、f3 成功(v3)

all_combinator([f1, f2, f3])  →  AllCombinatorError(first_error=e2)  # f2 失败，整体立即失败

假设 3 个 Future：f1 失败(e1)、f2 成功(v2)、f3 失败(e3)

any_combinator([f1, f2, f3])  →  v2  # f2 成功，整体成功
any_combinator([f1, f3])       →  AnyCombinatorError(errors=[e1, e3])  # 全部失败

假设 3 个 Future：f1 最先完成（失败 e1）、f2 较晚成功、f3 最晚

race_combinator([f1, f2, f3])  →  e1  # 最先完成的是 f1（失败），整体以失败完成
```

## 使用示例

### 创建和完成 Future

```python
from solocoder_py.future_combinator import Future, FutureState

# 创建未完成的 Future
f = Future()
assert f.state == FutureState.PENDING

# 设置成功结果
f.set_result(42)
assert f.state == FutureState.COMPLETED
assert f.result == 42

# 创建已完成的 Future
done = Future.completed("hello")
assert done.result == "hello"

# 创建已失败的 Future
failed = Future.failed(ValueError("oops"))
```

### 回调注册

```python
from solocoder_py.future_combinator import Future

f = Future()
results = []

f.add_callback(lambda fut: results.append(fut.result))
f.set_result(99)
# results == [99]

# 已完成的 Future 注册回调会立即触发
f2 = Future.completed(10)
f2.add_callback(lambda fut: results.append(fut.result))
# results == [99, 10]
```

### 阻塞等待

```python
from solocoder_py.future_combinator import Future

f = Future()

# 非阻塞等待，返回是否完成
f.wait(timeout=0.1)  # False

# 阻塞获取结果，超时抛出 FutureTimeoutError
try:
    f.get(timeout=1.0)
except FutureTimeoutError:
    print("timed out")
```

### 从可调用对象创建

```python
import time
from solocoder_py.future_combinator import Future

def slow_computation():
    time.sleep(0.1)
    return 42

f = Future.from_callable(slow_computation)
result = f.get(timeout=2.0)  # 42
```

### all 组合器

```python
from solocoder_py.future_combinator import Future, all_combinator, AllCombinatorError

# 全部成功
f1 = Future()
f2 = Future()
combined = all_combinator([f1, f2])

f1.set_result(1)
f2.set_result(2)
assert combined.result == [1, 2]

# 任一失败
f3 = Future()
f4 = Future()
combined2 = all_combinator([f3, f4])

f4.set_error(RuntimeError("boom"))
# combined2 以 AllCombinatorError 完成

# 空列表
combined3 = all_combinator([])
assert combined3.result == []
```

### any 组合器

```python
from solocoder_py.future_combinator import Future, any_combinator, AnyCombinatorError

# 首个成功
f1 = Future()
f2 = Future()
combined = any_combinator([f1, f2])

f1.set_result("winner")
assert combined.result == "winner"

# 全部失败
f3 = Future.failed(ValueError("e1"))
f4 = Future.failed(RuntimeError("e2"))
combined2 = any_combinator([f3, f4])
# combined2 以 AnyCombinatorError 完成，errors 包含两个异常
```

### race 组合器

```python
import time
from solocoder_py.future_combinator import Future, race_combinator

# 最先完成（不论成败）即作为结果
f1 = Future.from_callable(lambda: time.sleep(0.2) or "slow")
f2 = Future.from_callable(lambda: time.sleep(0.05) or "fast")
combined = race_combinator([f1, f2])
assert combined.get(timeout=1.0) == "fast"

# 最先完成的是失败
f3 = Future.from_callable(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
f4 = Future()
combined2 = race_combinator([f3, f4])
# combined2 以 RuntimeError 完成
```

### 超时熔断

```python
from solocoder_py.future_combinator import Future, with_timeout, FutureTimeoutError

# 超时触发
f = Future()
timed = with_timeout(f, timeout=0.1)
# 0.1 秒后 timed 以 FutureTimeoutError 完成

# 在超时前完成
f2 = Future()
timed2 = with_timeout(f2, timeout=2.0)
f2.set_result("done")
assert timed2.result == "done"

# 与组合器配合使用
from solocoder_py.future_combinator import all_combinator

f3 = Future()
f4 = Future()
combined = all_combinator([f3, f4])
timed3 = with_timeout(combined, timeout=0.5)
f3.set_result(1)
# f4 未完成，0.5 秒后 timed3 以 FutureTimeoutError 完成
```

## 运行测试

```bash
pytest tests/future_combinator/ -v
```
