# Circuit Breaker 熔断器模块

本模块实现了一个基于内存数据结构的熔断器，支持失败率熔断、慢调用熔断与半开探测自动恢复机制。

## 模块功能

- **三态状态机**：关闭（CLOSED）、打开（OPEN）、半开（HALF_OPEN）三种状态的自动转换
- **滑动窗口统计**：基于真正的滑动时间窗口记录调用结果与耗时，避免窗口边界统计偏差
- **失败率熔断**：窗口内请求数达到最小样本数且失败率超过阈值时，熔断器打开
- **慢调用熔断**：调用耗时超过慢调用阈值的比例超限，也会触发熔断
- **半开探测恢复**：冷却时间结束后进入半开状态，有限次探测请求全部成功则恢复关闭
- **可注入时钟**：时间来源可通过依赖注入替换，便于在测试中精确控制时间流逝
- **状态可观测**：支持查询当前状态、窗口统计数据、最近一次状态切换原因及时间

## 核心类职责

### CircuitState
熔断器状态枚举。

- `CLOSED`：关闭状态，正常放行所有请求，持续收集调用统计
- `OPEN`：打开状态，快速拒绝所有请求，避免下游系统过载
- `HALF_OPEN`：半开状态，仅允许有限次探测请求，用于判断下游是否恢复

### StateChangeReason
状态切换原因枚举。

- `INITIALIZED`：初始创建
- `FAILURE_RATE_THRESHOLD_EXCEEDED`：失败率超过阈值
- `SLOW_CALL_RATE_THRESHOLD_EXCEEDED`：慢调用比例超过阈值
- `COOLDOWN_COMPLETE`：打开状态冷却时间结束
- `HALF_OPEN_SUCCESS`：半开状态所有探测请求成功
- `HALF_OPEN_FAILURE`：半开状态出现探测失败或慢调用

### CircuitBreakerConfig
熔断器配置数据类，构造时自动校验参数合法性。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `window_seconds` | float | 滑动统计窗口时长（秒），必须 > 0 |
| `minimum_number_of_calls` | int | 触发熔断所需的最小样本请求数，必须 > 0 |
| `failure_rate_threshold` | float | 失败率阈值，取值 (0, 1] |
| `slow_call_duration_threshold` | float | 慢调用耗时阈值（秒），必须 > 0 |
| `slow_call_rate_threshold` | float | 慢调用比例阈值，取值 (0, 1] |
| `permitted_number_of_calls_in_half_open_state` | int | 半开状态允许的探测请求数，必须 > 0 |
| `wait_duration_in_open_state` | float | 打开状态的冷却时间（秒），必须 > 0 |
| `automatic_transition_from_open_to_half_open_enabled` | bool | 是否自动从 OPEN 切换到 HALF_OPEN，默认 True |

### WindowStats
滑动窗口统计快照（不可变数据类）。

- `total_count`：窗口内总请求数
- `success_count`：成功请求数
- `failure_count`：失败请求数
- `slow_count`：慢调用次数
- `failure_rate`：失败率（total_count > 0 时有效）
- `slow_call_rate`：慢调用比例（total_count > 0 时有效）
- `window_start` / `window_end`：统计窗口的起止时间戳

### StateChangeEvent
状态切换事件记录。

- `previous_state` / `current_state`：切换前后状态
- `reason`：切换原因
- `timestamp`：切换发生时间
- `stats`：切换时的窗口统计快照（可能为 None）

### CircuitBreaker
熔断器主类。使用 `threading.RLock` 保护内部状态，保证线程安全。

核心方法：

- `state` 属性：获取当前状态（会触发 OPEN → HALF_OPEN 的自动转换检查）
- `is_call_permitted() -> bool`：非消耗性检查当前是否允许通过请求
- `acquire()` 上下文管理器：包裹业务调用，自动记录结果与耗时；被拒绝时抛出 `CircuitBreakerOpenError`
- `get_window_stats() -> WindowStats`：获取当前滑动窗口的统计快照
- `last_state_change_event` 属性：获取最近一次状态切换事件

### 异常类

- `CircuitBreakerError`：熔断器模块基类异常
- `CircuitBreakerOpenError`：熔断器打开时尝试调用被拒绝
- `InvalidConfigError`：配置参数不合法

### Clock（从 ratelimiter 模块复用）
时间来源抽象接口。

- `SystemClock`：默认实现，使用系统单调时钟（`time.monotonic()`）
- `ManualClock`：手动时钟，用于测试，通过 `advance()` 推进或 `set()` 设置时间

## 状态机图

```
                  失败率/慢调用率超限
     ┌────────────────────────────────────┐
     │                                    ▼
  CLOSED ────► (收集统计) ─────────────► OPEN
     ▲                                    │
     │                                    │ 冷却时间结束
     │                                    ▼
     │                                HALF_OPEN
     │                                    │
     │           探测全部成功              │
     └────────────────────────────────────┘
                    探测失败/慢调用
```

详细状态转换规则：

1. **CLOSED → OPEN**：滑动窗口内请求数 ≥ `minimum_number_of_calls`，且（失败率 ≥ 阈值 或 慢调用率 ≥ 阈值）
2. **OPEN → HALF_OPEN**：在 OPEN 状态停留时间 ≥ `wait_duration_in_open_state`（自动转换）
3. **HALF_OPEN → OPEN**：任意一次探测请求失败或判定为慢调用
4. **HALF_OPEN → CLOSED**：已完成的探测请求数达到 `permitted_number_of_calls_in_half_open_state` 且全部成功

## 使用示例

### 基础使用

```python
from solocoder_py.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
)

config = CircuitBreakerConfig(
    window_seconds=60.0,
    minimum_number_of_calls=20,
    failure_rate_threshold=0.5,
    slow_call_duration_threshold=3.0,
    slow_call_rate_threshold=0.3,
    permitted_number_of_calls_in_half_open_state=3,
    wait_duration_in_open_state=30.0,
)

breaker = CircuitBreaker(config)

def call_downstream():
    try:
        with breaker.acquire():
            # 实际调用下游服务
            result = risky_operation()
            return result
    except CircuitBreakerOpenError:
        # 熔断器打开，返回降级结果
        return get_fallback()
    except Exception as e:
        # 业务异常会被熔断器记录为失败并重新抛出
        raise
```

### 测试中使用手动时钟

```python
from solocoder_py.circuit_breaker import ManualClock, CircuitBreaker

clock = ManualClock()
breaker = CircuitBreaker(config, clock=clock)

# 模拟调用失败
for _ in range(15):
    try:
        with breaker.acquire():
            clock.advance(0.1)
            raise RuntimeError("service down")
    except RuntimeError:
        pass

assert breaker.state.value == "OPEN"

# 推进冷却时间
clock.advance(30.0)
assert breaker.state.value == "HALF_OPEN"

# 半开探测成功
with breaker.acquire():
    clock.advance(0.1)
with breaker.acquire():
    clock.advance(0.1)
with breaker.acquire():
    clock.advance(0.1)

assert breaker.state.value == "CLOSED"
```

### 查看窗口统计与状态事件

```python
stats = breaker.get_window_stats()
print(f"Total: {stats.total_count}, Failure rate: {stats.failure_rate:.2%}")

event = breaker.last_state_change_event
if event:
    print(
        f"Last change: {event.previous_state.value} -> {event.current_state.value}, "
        f"reason: {event.reason.value}"
    )
```
