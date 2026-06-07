# Retry 重试模块

本模块实现了一个基于内存数据结构的指数退避重试策略引擎，支持可配置的退避规则、可重试异常分类、执行轨迹追踪以及可注入时钟。

## 模块功能

- **指数退避重试**：根据配置的初始延迟和退避倍数，自动计算每次重试的等待时间，并支持最大延迟封顶
- **抖动（Jitter）**：可选启用随机抖动，使重试等待时间在合理范围内变化，避免惊群效应
- **可重试异常分类**：基于异常类型或错误码判断异常是否可重试，不可重试异常立即终止
- **尝试轨迹记录**：完整记录每次尝试的序号、执行时间、结果、错误原因及下一次计划时间
- **可注入时钟**：时间来源可通过依赖注入替换，便于测试中控制时间流逝
- **同步执行器**：包装可能失败的函数，按照策略执行直到成功、不可重试失败或达到最大尝试次数

## 核心类职责

### Clock（抽象基类）
时间来源抽象接口，定义 `now()` 方法返回当前时间戳，以及 `sleep(seconds)` 方法等待指定时长。

- `SystemClock`：默认实现，使用系统单调时钟（`time.monotonic()`）和 `time.sleep()`
- `ManualClock`：手动时钟，用于测试。可通过 `advance()` 推进时间或 `set()` 设置时间；`sleep()` 会直接推进虚拟时间并记录历史，不产生真实等待

### RetryStrategy
重试策略配置数据类，构造时自动校验参数合法性。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `initial_delay` | `float` | `1.0` | 第一次重试的等待时间（秒），必须为正 |
| `backoff_multiplier` | `float` | `2.0` | 退避倍数，每次重试等待时间乘以该值，必须 ≥ 1.0 |
| `max_delay` | `float` | `60.0` | 最大等待时间（秒），超过则封顶；必须 ≥ `initial_delay` |
| `max_attempts` | `int` | `3` | 最大尝试次数，必须 ≥ 1 |
| `enable_jitter` | `bool` | `False` | 是否启用抖动 |
| `jitter_ratio` | `float` | `0.2` | 抖动比例（0 到 1 之间） |

主要方法：
- `calculate_delay(attempt_number, rng=None) -> float`：计算执行第 `attempt_number` 次尝试**之前**需要等待的时间（秒）。`attempt_number` 从 **1** 开始计数，第 1 次尝试前无需等待，返回 `0.0`；若 `attempt_number < 1` 会抛出 `ValueError`。
- `should_attempt(attempt_number) -> bool`：判断该尝试序号是否在允许范围内。

### RetryPolicy（抽象基类）
可重试异常分类策略接口，定义 `is_retryable(exception) -> bool` 方法。

- `RetryAllPolicy`：默认策略，所有异常均视为可重试
- `RetryNonePolicy`：所有异常均视为不可重试
- `ExceptionTypePolicy`：基于异常类型的白名单/黑名单策略，支持子类匹配
- `ErrorCodePolicy`：基于异常属性（如错误码）的白名单/黑名单策略。当配置了 `retryable_codes`（白名单模式）时，缺失代码属性或代码为 `None` 的异常会被视为**不可重试**；仅配置 `non_retryable_codes`（仅黑名单模式）时，缺失代码属性或代码为 `None` 的异常仍视为可重试。
- `CompositePolicy`：组合多个策略，所有策略均允许时才视为可重试

### AttemptRecord
单次尝试的记录数据类：

| 字段 | 类型 | 说明 |
|------|------|------|
| `attempt_number` | `int` | 尝试序号（从 1 开始） |
| `executed_at` | `float` | 执行时间戳（由 Clock 提供） |
| `result` | `str` | 结果：`success` / `failure` / `non_retryable_failure` |
| `error` | `Exception \| None` | 失败时的异常对象，成功时为 None |
| `next_scheduled_at` | `float \| None` | 下一次计划执行时间；若为最后一次尝试则为 None |

### RetryEngine
重试引擎主入口。维护内部尝试轨迹列表，按照策略和分类规则执行目标函数。

主要方法：
- `execute(func, *args, **kwargs) -> Any`：执行函数，成功返回结果；不可重试失败抛出 `NonRetryableError`；超过最大尝试次数抛出 `MaxAttemptsExceededError`。**不会自动清空历史轨迹**，多次调用 `execute()` 会累加历史；上一次运行以 `SUCCESS` 或 `NON_RETRYABLE_FAILURE` 结束时，新运行内部的 `attempt_number` 从 1 重新开始；上一次运行在 `FAILURE` 状态中断时（如进程崩溃），后续 `execute()` 会从下一次尝试继续推进。如需从干净状态开始，显式调用 `reset()`。
- `attempts`：获取尝试轨迹列表（快照），包含所有历史运行的记录
- `attempt_count`：当前尝试次数（即轨迹总长度）
- `last_attempt`：最近一次尝试记录
- `reset()`：清空尝试轨迹，重置为干净状态

## 退避时间计算规则

### attempt_number 约定

`calculate_delay(attempt_number)` 的参数 `attempt_number` 从 **1** 开始计数，对应重试序列中的第几次尝试：

| `attempt_number` | 含义 | 返回值 |
|-----------------|------|--------|
| 1 | 第 1 次尝试（首次执行） | `0.0`（无需等待） |
| 2 | 第 2 次尝试（第 1 次重试） | `initial_delay` |
| 3 | 第 3 次尝试（第 2 次重试） | `initial_delay × backoff_multiplier` |
| 4 | 第 4 次尝试（第 3 次重试） | `initial_delay × backoff_multiplier²` |
| … | … | … |

如果 `attempt_number < 1`，方法会抛出 `ValueError`。

### 基础退避公式

设：
- `D₀` = `initial_delay`（初始延迟）
- `m` = `backoff_multiplier`（退避倍数）
- `M` = `max_delay`（最大延迟）
- `k` = `attempt_number - 1`（已发生的失败次数）

则第 `attempt_number` 次尝试**之前**的**基础等待时间**为：

```
delay = min(D₀ × m^(k-1), M)    （当 attempt_number ≥ 2）
delay = 0.0                       （当 attempt_number = 1）
```

即：
- `attempt_number = 1` → 首次执行，不等待
- `attempt_number = n` → 在执行第 n 次尝试前，需要等待 `min(D₀ × m^(n-2), M)` 秒

### 示例（D₀=1, m=2, M=60）

| attempt_number | 含义 | 等待时间 |
|----------------|------|----------|
| 1 | 首次执行 | 0 |
| 2 | 第 1 次重试 | 1 |
| 3 | 第 2 次重试 | 2 |
| 4 | 第 3 次重试 | 4 |
| 5 | 第 4 次重试 | 8 |
| ... | ... | ... |
| 8 | 第 7 次重试 | 60（封顶） |

### 启用抖动

启用抖动时，实际等待时间在基础值的 ±`jitter_ratio` 范围内随机变化：

```
jitter_range = delayₙ × jitter_ratio
lower_bound = delayₙ - jitter_range
upper_bound = delayₙ + jitter_range
actual_delay = uniform(lower_bound, upper_bound)
```

例如 `delayₙ=2.0, jitter_ratio=0.2`，实际延迟在 [1.6, 2.4] 内均匀分布。

## 使用示例

### 基础使用

```python
from solocoder_py.retry import RetryEngine, RetryStrategy

strategy = RetryStrategy(
    initial_delay=1.0,
    backoff_multiplier=2.0,
    max_delay=30.0,
    max_attempts=5,
)
engine = RetryEngine(strategy=strategy)

def flaky_api_call():
    # 可能失败的操作
    ...

try:
    result = engine.execute(flaky_api_call)
    print(f"成功，共尝试 {engine.attempt_count} 次")
except Exception as e:
    print(f"失败：{e}")
```

### 基于异常类型的分类

```python
from solocoder_py.retry import ExceptionTypePolicy, RetryEngine

class FatalError(Exception):
    pass

class TransientError(Exception):
    pass

policy = ExceptionTypePolicy(
    non_retryable_exceptions=[FatalError],
)
engine = RetryEngine(policy=policy)
```

### 基于错误码的分类

```python
from solocoder_py.retry import ErrorCodePolicy, RetryEngine

class ApiError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)

policy = ErrorCodePolicy(
    retryable_codes=["TIMEOUT", "RATE_LIMITED", "INTERNAL_ERROR"],
    non_retryable_codes=["BAD_REQUEST", "UNAUTHORIZED"],
)
engine = RetryEngine(policy=policy)
```

### 组合多个策略

```python
from solocoder_py.retry import (
    CompositePolicy,
    ErrorCodePolicy,
    ExceptionTypePolicy,
    RetryEngine,
)

policy = CompositePolicy([
    ExceptionTypePolicy(retryable_exceptions=[ApiError]),
    ErrorCodePolicy(non_retryable_codes=["FATAL"]),
])
engine = RetryEngine(policy=policy)
```

### 测试中使用手动时钟

```python
from solocoder_py.retry import ManualClock, RetryEngine, RetryStrategy

clock = ManualClock()
strategy = RetryStrategy(initial_delay=1.0, backoff_multiplier=2.0, max_attempts=4)
engine = RetryEngine(strategy=strategy, clock=clock)

# 执行一个需要多次重试的函数
result = engine.execute(flaky_function)

# 检查睡眠历史（每次重试等待的时长，无真实等待）
print(clock.sleep_history)  # 例如 [1.0, 2.0, 4.0]

# 检查完整尝试轨迹
for record in engine.attempts:
    print(f"尝试 {record.attempt_number}: {record.result}")
```

### 查询尝试轨迹

```python
for record in engine.attempts:
    if record.result == "success":
        print(f"第 {record.attempt_number} 次尝试成功")
    elif record.result == "failure":
        print(f"第 {record.attempt_number} 次失败: {record.error}, 下次计划: {record.next_scheduled_at}")
    else:
        print(f"第 {record.attempt_number} 次不可重试失败: {record.error}")
```
