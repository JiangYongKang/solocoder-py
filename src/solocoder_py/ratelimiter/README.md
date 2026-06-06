# Rate Limiter 模块

本模块实现了一个基于内存数据结构的多级滑动窗口限流器，支持全局、租户、主体三级配额联动。

## 模块功能

- **滑动窗口限流**：基于真正的滑动时间窗口（而非固定窗口）统计请求次数，避免窗口边界突发问题
- **多级配额联动**：同时检查全局、租户、主体三级配额，任意一级超限即拒绝请求
- **配额约束验证**：下级配额之和不得超过上级配额，配置不合法时拒绝
- **可注入时钟**：时间来源可通过依赖注入替换，便于测试控制时间流逝

## 核心类职责

### Clock（抽象基类）
时间来源抽象接口，定义 `now()` 方法返回当前时间戳。

- `SystemClock`：默认实现，使用系统单调时钟（`time.monotonic()`）
- `ManualClock`：手动时钟，用于测试，可通过 `advance()` 推进时间或 `set()` 设置时间

### SlidingWindowRateLimiter
单实例滑动窗口限流器。维护一个请求时间戳的双端队列，每次请求前驱逐窗口外的过期时间戳，然后判断是否还有剩余配额。

- `try_acquire() -> bool`：尝试获取一个配额（消耗配额），成功返回 True，超限返回 False
- `can_acquire() -> bool`：非消耗性检查，仅判断当前是否有剩余配额，不修改计数
- `current_count() -> int`：获取当前窗口内的请求数量

### 数据模型
- `SubjectQuota`：主体配额配置（subject_id + max_requests）
- `TenantQuota`：租户配额配置（tenant_id + max_requests + subjects）
- `RateLimitConfig`：完整配置，包含全局配额、窗口时长、租户列表。构造时自动校验配额约束，包括：下级配额之和不超过上级配额、租户 ID 不重复、租户内主体 ID 不重复。

### MultiLevelRateLimiter
多级限流器主入口。同时维护全局、各租户、各主体的滑动窗口限流器。整个获取流程使用可重入锁保护，保证全局→租户→主体三级检查的原子性，以及失败回滚的正确性。

- `try_acquire(tenant_id, subject_id) -> None`：原子地获取配额，成功无返回，超限抛出 `QuotaExceededError`；失败时自动回滚已成功获取的上级配额
- `is_allowed(tenant_id, subject_id) -> bool`：非消耗性检查，仅判断当前是否允许通过，不消耗任何配额，不修改各级计数
- `get_global_count() / get_tenant_count() / get_subject_count()`：查询各级别当前计数

### 异常类
- `RateLimiterError`：基类异常
- `InvalidQuotaError`：配额配置不合法
- `QuotaExceededError`：请求超出配额，携带 `level`（global/tenant/subject）和 `key` 字段

## 多级配额联动模型

```
全局配额 (global_max_requests)
  ├── 租户 A (tenant_max)
  │     ├── 主体 1 (subject_max)
  │     ├── 主体 2 (subject_max)
  │     └── ...
  ├── 租户 B (tenant_max)
  │     └── ...
  └── ...
```

约束规则：
1. `sum(所有租户的 tenant_max) <= global_max_requests`
2. 对每个租户：`sum(其下所有主体的 subject_max) <= 该租户的 tenant_max`
3. 所有 max 值必须为正整数
4. 租户 ID 在全局范围内不重复
5. 主体 ID 在所属租户内不重复

请求处理流程（全程在锁内保证原子性）：
1. 先获取全局配额 → 失败则拒绝
2. 再获取对应租户配额 → 失败则回滚全局并拒绝
3. 最后获取对应主体配额（若该主体有配置）→ 失败则回滚租户和全局并拒绝
4. 全部成功则通过

## 使用示例

### 基础使用

```python
from solocoder_py.ratelimiter import (
    MultiLevelRateLimiter,
    RateLimitConfig,
    TenantQuota,
    SubjectQuota,
    QuotaExceededError,
)

config = RateLimitConfig(
    global_max_requests=1000,
    window_seconds=60.0,
    tenants=[
        TenantQuota(
            tenant_id="tenant_a",
            max_requests=500,
            subjects=[
                SubjectQuota(subject_id="user_1", max_requests=100),
                SubjectQuota(subject_id="user_2", max_requests=200),
            ],
        ),
        TenantQuota(tenant_id="tenant_b", max_requests=500),
    ],
)

limiter = MultiLevelRateLimiter(config)

try:
    limiter.try_acquire("tenant_a", "user_1")
    # 处理请求
except QuotaExceededError as e:
    print(f"Rate limited at {e.level} level for {e.key}")
    # 返回 429
```

### 测试中使用手动时钟

```python
from solocoder_py.ratelimiter import ManualClock

clock = ManualClock()
limiter = MultiLevelRateLimiter(config, clock=clock)

# 消耗配额
for _ in range(100):
    limiter.try_acquire("tenant_a", "user_1")

# 模拟时间流逝 60 秒
clock.advance(60.0)

# 配额已刷新
limiter.try_acquire("tenant_a", "user_1")  # 成功
```
