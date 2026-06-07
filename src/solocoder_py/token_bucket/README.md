# Token Bucket 令牌桶限流器模块

本模块实现了一个基于内存数据结构的令牌桶限流器，支持单桶和多主体两种使用模式。

## 模块功能

- **令牌桶限流**：基于经典令牌桶算法，按恒定速率补充令牌，支持突发流量
- **多令牌消耗**：单次请求可消耗多个令牌，适用于不同权重的请求
- **多主体隔离**：按主体 ID 维护独立令牌桶，不同主体之间互不影响
- **可注入时钟**：时间来源可通过依赖注入替换，便于测试控制时间流逝
- **并发安全**：内置线程锁，多个线程同时操作时不会超发令牌或出现负数
- **状态查询**：支持查询任意主体当前剩余令牌数

## 核心类职责

### Clock（从 ratelimiter 模块复用）

时间来源抽象接口，定义 `now()` 方法返回当前时间戳。

- `SystemClock`：默认实现，使用系统单调时钟（`time.monotonic()`）
- `ManualClock`：手动时钟，用于测试，可通过 `advance()` 推进时间或 `set()` 设置时间

### TokenBucketConfig

令牌桶不可变配置类。构造时自动校验参数合法性。

- `capacity: int`：桶的容量上限，即最多可容纳的令牌数（必须为正整数）
- `refill_rate_per_second: float`：每秒补充的令牌数（必须非负）

### TokenBucketState

令牌桶可变状态类。

- `current_tokens: float`：当前桶内令牌数
- `last_refill_time: float`：上次补充令牌的时间戳

### TokenBucket

单实例令牌桶限流器。每次请求令牌前先按经过时间补充令牌，再判断是否允许通过。

**核心方法：**

- `try_acquire(tokens: int = 1) -> bool`：尝试消耗指定数量的令牌，成功返回 True，令牌不足返回 False
- `acquire(tokens: int = 1) -> None`：消耗指定数量的令牌，令牌不足时抛出 `NotEnoughTokensError`
- `can_acquire(tokens: int = 1) -> bool`：非消耗性检查，仅判断当前令牌是否足够，不修改状态
- `get_available_tokens() -> float`：获取当前桶内剩余令牌数（会触发令牌补充）

**属性：**

- `capacity: int`：桶容量上限
- `refill_rate_per_second: float`：令牌补充速率

### MultiSubjectTokenBucketLimiter

多主体令牌桶限流器。内部维护主体 ID 到 `TokenBucket` 的映射，按需自动创建桶。

**核心方法：**

- `try_acquire(subject_id: str, tokens: int = 1) -> bool`：指定主体尝试获取令牌
- `acquire(subject_id: str, tokens: int = 1) -> None`：指定主体获取令牌，不足时抛异常
- `can_acquire(subject_id: str, tokens: int = 1) -> bool`：非消耗性检查指定主体
- `get_available_tokens(subject_id: str) -> float`：查询指定主体剩余令牌
- `has_subject(subject_id: str) -> bool`：判断指定主体是否已有桶
- `list_subjects() -> list[str]`：列出所有已有桶的主体 ID

### 异常类

- `TokenBucketError`：基类异常
- `InvalidBucketConfigError`：桶配置不合法（容量非正、补充速率为负等）
- `NotEnoughTokensError`：令牌不足，携带 `requested`（请求数）和 `available`（可用数）字段

## 令牌补充规则

令牌补充采用"惰性计算"策略，仅在需要时（调用任意方法时）才计算应补充的令牌数：

1. 获取当前时间，计算与上次补充时间的差值（秒）
2. 补充令牌数 = 经过时间 × 每秒补充速率
3. 当前令牌数 = min(当前令牌数 + 补充令牌数, 容量上限)
4. 更新上次补充时间为当前时间

规则约束：

- 桶内令牌数不会超过容量上限（突发容量即等于容量）
- 若时间未前进（差值 ≤ 0），则不补充令牌
- 令牌数为浮点数，支持亚秒级精确补充

## 使用示例

### 基础使用（单桶）

```python
from solocoder_py.token_bucket import TokenBucket

# 容量 10，每秒补充 2 个令牌
bucket = TokenBucket(capacity=10, refill_rate_per_second=2.0)

# 消耗 1 个令牌
if bucket.try_acquire():
    print("请求通过")
else:
    print("限流")

# 消耗多个令牌（权重请求）
if bucket.try_acquire(3):
    print("高权重请求通过")
```

### 多主体限流

```python
from solocoder_py.token_bucket import MultiSubjectTokenBucketLimiter

# 每个主体默认容量 100，每秒补充 10 个
limiter = MultiSubjectTokenBucketLimiter(
    capacity=100,
    refill_rate_per_second=10.0,
)

# 不同主体完全隔离
limiter.try_acquire("user_1")  # True
limiter.try_acquire("user_2")  # True

# 查询剩余令牌
remaining = limiter.get_available_tokens("user_1")
print(f"user_1 剩余令牌: {remaining}")
```

### 异常处理

```python
from solocoder_py.token_bucket import (
    TokenBucket,
    NotEnoughTokensError,
    InvalidBucketConfigError,
)

try:
    bucket = TokenBucket(capacity=10, refill_rate_per_second=2.0)
    bucket.acquire(5)
    bucket.acquire(20)  # 令牌不足
except NotEnoughTokensError as e:
    print(f"请求被限流: 需要 {e.requested}，可用 {e.available}")
except InvalidBucketConfigError as e:
    print(f"配置错误: {e}")
```

### 测试中使用手动时钟

```python
from solocoder_py.token_bucket import TokenBucket, ManualClock

clock = ManualClock(start_time=0.0)
bucket = TokenBucket(capacity=10, refill_rate_per_second=2.0, clock=clock)

# 初始满桶，消耗所有令牌
assert bucket.try_acquire(10) is True
assert bucket.try_acquire() is False

# 推进时间 1 秒，应补充 2 个令牌
clock.advance(1.0)
assert bucket.get_available_tokens() == 2.0
assert bucket.try_acquire() is True

# 推进时间 100 秒，令牌不会超过容量
clock.advance(100.0)
assert bucket.get_available_tokens() == 10.0
```
