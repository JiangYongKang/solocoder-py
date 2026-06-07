# Token Bucket 令牌桶限流器模块

本模块实现了一个基于内存数据结构的令牌桶限流器，支持单桶和多主体两种使用模式。

## 模块功能

- **令牌桶限流**：基于经典令牌桶算法，按恒定速率补充令牌，支持突发流量
- **多令牌消耗**：单次请求可消耗多个令牌，适用于不同权重的请求
- **多主体隔离**：按主体 ID 维护独立令牌桶，不同主体之间互不影响
- **可注入时钟**：时间来源可通过依赖注入替换，便于测试控制时间流逝
- **并发安全**：分层锁设计保证多线程操作时不会超发令牌或出现负数
- **状态查询**：支持查询任意主体当前剩余令牌数
- **精度保证**：内部使用整数微令牌存储，杜绝浮点误差累积问题

## 核心类职责

### Clock（从 ratelimiter 模块复用）

时间来源抽象接口，定义 `now()` 方法返回当前时间戳。

- `SystemClock`：默认实现，使用系统单调时钟（`time.monotonic()`）
- `ManualClock`：手动时钟，用于测试，可通过 `advance()` 推进时间或 `set()` 设置时间

### TokenBucketConfig

令牌桶不可变配置类。构造时自动校验参数合法性。

- `capacity: int`：桶的容量上限，即最多可容纳的令牌数（必须为正整数）
- `refill_rate_per_second: float`：每秒补充的令牌数（必须非负）
- `capacity_scaled: int`：容量对应的微令牌数（容量 × 1,000,000，内部精度使用）
- `refill_rate_scaled_per_second: float`：每秒补充的微令牌数

### TokenBucketState

令牌桶可变状态类。

- `current_tokens_scaled: int`：当前桶内微令牌数（整数存储，避免浮点误差）
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
2. 补充微令牌数 = round(经过时间 × 每秒补充微令牌速率)
3. 当前微令牌数 = min(当前微令牌数 + 补充微令牌数, 容量微令牌上限)
4. 更新上次补充时间为当前时间

规则约束：

- 桶内令牌数不会超过容量上限（突发容量即等于容量）
- 若时间未前进（差值 ≤ 0），则不补充令牌
- 对外接口返回浮点数，内部全用整数运算

## 精度保证

本模块使用 **整数微令牌（micro-token）** 存储方案消除浮点误差：

- **缩放因子**：1 令牌 = 1,000,000 微令牌，精度高于微秒级时间分辨率
- **内部存储**：`current_tokens_scaled`、`capacity_scaled` 均为 `int` 类型，所有比较、加减运算都是整数运算
- **补充计算**：`elapsed * rate_scaled_per_second` 结果用 `round()` 四舍五入取整后才参与累加，消除单次浮点乘法的残差
- **边界安全**：整数比较不存在 2.9999999 >= 3 返回 False 的问题，边界判断精确可靠
- **对外转换**：`get_available_tokens()` 仅在返回时将微令牌整数除以 1,000,000 转为 float，不参与内部状态流转

即使经过极长时间的持续补充与消耗，整数存储也不会累积误差，保证限流判断始终精确。

## 并发安全约定

本模块采用 **分层细粒度锁** 设计，兼顾正确性与并发性能：

### TokenBucket（单桶）

- 每个 `TokenBucket` 实例持有一把 `threading.Lock`（`_lock`）
- 所有读写桶状态的操作（`try_acquire`、`acquire`、`can_acquire`、`get_available_tokens`）均在该锁的临界区内完成
- 单次调用内的 **补充令牌 → 判断 → 扣减** 是原子操作，多线程并发调用同一桶不会超发、不会出现负数

### MultiSubjectTokenBucketLimiter（多主体）

- `_struct_lock`：结构锁，保护 `_buckets` 字典和 `_subject_locks` 字典的并发读写
- `_subject_locks[subject_id]`：每主体独立锁，每个主体 ID 对应一把 `threading.Lock`
- **关键原子性保证**：对任意主体的一次完整操作（获取/创建桶 → 桶操作）全程在该主体锁的临界区内完成，不存在"取桶后释放锁再扣减"的跨步窗口
- 不同主体的操作并行执行，互不阻塞；同一主体的操作串行化，保证状态一致性

锁的获取顺序（避免死锁）：
1. 先拿主体锁（通过 `_get_subject_lock`，内部拿 `_struct_lock` 取锁后立即释放）
2. 在主体锁内，拿 `_struct_lock` 取/创建桶后立即释放
3. 在主体锁内，调用桶方法（桶内部再拿自己的 `_lock`）

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
