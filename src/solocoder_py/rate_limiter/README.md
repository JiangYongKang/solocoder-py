# Rate Limiter 模块

API 客户端限流器，基于令牌桶算法实现，支持响应头限额状态透传和突发容量配置。

## 模块功能

本模块提供了一个完整的 API 客户端限流解决方案，主要功能包括：

1. **令牌桶限流**：基于经典令牌桶算法，以固定速率补充令牌，支持配置桶容量和令牌补充速率
2. **响应头同步**：解析上游 API 返回的 `X-RateLimit-*` 响应头，根据服务端实际限额状态同步本地令牌桶
3. **突发请求支持**：通过配置突发容量（burst size），允许空闲后短时间内发出超出平均速率的突发请求
4. **线程安全**：所有公共操作均内置锁保护，可安全用于多线程环境
5. **灵活同步策略**：提供 MIN（取最小值）、SERVER（服务端优先）、LOCAL（本地优先）三种同步策略

## 核心类职责

### TokenBucketConfig
令牌桶配置类，定义限流参数：
- `refill_rate`：令牌每秒补充速率（float）
- `capacity`：桶的最大容量，即突发容量（int）
- `initial_tokens`：初始令牌数，默认为桶容量（Optional[int]）

### TokenBucket
令牌桶核心算法实现：
- 懒加载补充令牌：仅在访问令牌时计算补充量
- 提供 `try_acquire()` 非阻塞获取和 `acquire()` 阻塞等待两种模式
- 支持 `sync_with_server()` 根据服务端状态同步令牌数
- 支持 `set_tokens()` 直接设置令牌数
- 所有操作线程安全

### RateLimiter
API 客户端限流器主类，封装令牌桶并提供响应头同步功能：
- 管理 `TokenBucket` 实例
- 解析并存储服务端返回的限流响应头
- 按配置的同步策略更新本地令牌桶状态
- 可运行时切换同步策略

### RateLimitHeaders
限流响应头数据模型，解析标准 HTTP 限流头：
- `X-RateLimit-Remaining`：服务端剩余配额
- `X-RateLimit-Limit`：服务端总限额
- `X-RateLimit-Reset`：限额重置时间戳（Unix 时间）
- `Retry-After`：需等待的秒数

### SyncStrategy
同步策略枚举：
- `MIN`：取本地令牌数与服务端剩余量的较小值（默认，最保守）
- `SERVER`：完全以服务端返回值为准
- `LOCAL`：忽略服务端响应头，仅使用本地令牌桶

## 令牌桶 vs 漏桶算法

| 特性 | 令牌桶 (Token Bucket) | 漏桶 (Leaky Bucket) |
|------|----------------------|---------------------|
| 突发请求 | 支持，桶满后可一次性消费 | 不支持，以固定速率流出 |
| 空闲后行为 | 令牌积累至桶容量 | 桶保持空 |
| 平均速率控制 | 间接保证（长期平均等于 refill_rate） | 严格保证（恒定流出速率） |
| 适用场景 | API 调用、允许短时突发的场景 | 流量整形、需严格平滑输出的场景 |
| 配置复杂度 | 需配置容量和速率 | 仅需配置速率（容量可选） |

本模块选择令牌桶算法，因为 API 客户端通常需要容忍一定程度的突发请求。

## 响应头透传的作用

### 为什么需要响应头同步？

本地令牌桶仅基于时间估计令牌消耗，但存在以下问题：
1. 多个客户端共享同一 API Key 时，本地估计与服务端实际偏差大
2. 网络重试、重试风暴可能导致本地状态落后
3. 服务端可能动态调整限流策略

### 同步机制

每次 API 调用后，调用 `update_from_response_headers()` 将服务端返回的限流状态同步到本地：

- **X-RateLimit-Remaining**：服务端剩余请求数。若低于本地令牌数，说明有其他客户端也在消耗配额，需下调本地值
- **X-RateLimit-Reset**：服务端限额重置时间。若此时间已过，说明服务端已重置配额，本地桶应恢复满
- **Retry-After**：被限流时服务端建议的等待时间

## 突发容量与平均速率的配置关系

### 配置原则

- `capacity`（突发容量） >= `refill_rate`（平均速率）
- 容量决定了"空闲后一次性最多能发多少请求"
- 速率决定了"长期平均每秒最多能发多少请求"

### 典型配置示例

| 场景 | refill_rate | capacity | 效果 |
|------|-------------|----------|------|
| 严格匀速，不允许突发 | 10/s | 10 | 空闲后每秒最多 10 个，无额外突发 |
| 允许 3 倍突发 | 10/s | 30 | 空闲后前 3 秒可发 30 个，之后平均 10/s |
| 高突发批量处理 | 5/s | 200 | 空闲后一次性发 200 个，然后每 0.2 秒补充 1 个 |

### 计算公式

突发 N 个请求后，恢复到满桶所需时间：
```
recovery_time = (capacity - N) / refill_rate
```

## 使用示例

### 基础使用

```python
from solocoder_py.rate_limiter import RateLimiter, TokenBucketConfig

# 配置：每秒 5 个请求，最多突发 20 个
config = TokenBucketConfig(refill_rate=5.0, capacity=20)
limiter = RateLimiter(config=config)

# 调用前获取令牌
result = limiter.try_acquire()
if result.acquired:
    # 执行 API 调用
    response = requests.get("https://api.example.com/data")
    # 调用后同步服务端限流状态
    limiter.update_from_response_headers(dict(response.headers))
else:
    print(f"限流中，需等待 {result.retry_after:.2f}s")
```

### 阻塞等待模式

```python
# 最多等待 2 秒获取令牌
try:
    result = limiter.acquire(tokens=1, timeout=2.0)
    # 执行调用
except WaitTimeoutError:
    print("等待超时")
except TokenExhaustedError:
    print("令牌耗尽")
```

### 配置响应头同步策略

```python
from solocoder_py.rate_limiter import SyncStrategy

# 切换为服务端优先策略
limiter.sync_strategy = SyncStrategy.SERVER

# 或者在初始化时指定
limiter = RateLimiter(
    config=config,
    sync_strategy=SyncStrategy.SERVER,
)
```

### 手动同步响应头

```python
headers = {
    "X-RateLimit-Remaining": "42",
    "X-RateLimit-Limit": "100",
    "X-RateLimit-Reset": "1718409600.0",
}
limiter.update_from_response_headers(headers)

# 或直接构造对象
from solocoder_py.rate_limiter import RateLimitHeaders
headers_obj = RateLimitHeaders(remaining=42, limit=100, reset=1718409600.0)
limiter.update_from_headers_object(headers_obj)
```

### 单元测试中使用手动时钟

```python
from solocoder_py.ratelimiter import ManualClock

clock = ManualClock(start_time=0.0)
config = TokenBucketConfig(refill_rate=10.0, capacity=50)
limiter = RateLimiter(config=config, clock=clock)

# 消耗所有令牌
for _ in range(50):
    limiter.try_acquire()

assert limiter.available_tokens == 0

# 推进时间 3 秒
clock.advance(3.0)
assert limiter.available_tokens == 30
```
