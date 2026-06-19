# Login Rate Limiting 登录限流与渐进锁定模块

本模块实现了一个基于内存数据结构的登录限流与渐进锁定系统，支持账户与 IP 子网双维度计数、阶梯式指数退避、账户锁定以及 CAPTCHA 升级机制。

## 模块功能

- **双维度失败计数**：按账户和 IP 子网（IPv4 /24，IPv6 /64）两级独立维护登录失败计数器
- **阶梯式指数退避**：根据累计失败次数逐步延长下一次允许尝试的等待时间，直至预设上限
- **账户锁定**：账户失败次数达到阈值后自动锁定，后续请求直接拒绝
- **CAPTCHA 升级钩子**：子网失败次数达到阈值后，该子网下所有登录请求需附加 CAPTCHA 验证
- **CAPTCHA 特权绕过**：CAPTCHA 验证通过后可绕过账户锁定和退避等待，直接进入密码校验
- **管理员解锁**：提供管理员接口手动解锁被锁定的账户
- **可注入时钟**：时间来源可通过依赖注入替换，便于测试控制时间流逝
- **并发安全**：分层细粒度锁设计保证多线程操作的正确性

## 核心类职责

### Clock（从 ratelimiter 模块复用）

时间来源抽象接口，定义 `now()` 方法返回当前时间戳。

- `SystemClock`：默认实现，使用系统单调时钟（`time.monotonic()`）
- `ManualClock`：手动时钟，用于测试，可通过 `advance()` 推进时间或 `set()` 设置时间

### LoginRateConfig

登录限流不可变配置类。构造时自动校验参数合法性。

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `account_lock_threshold` | `int` | `5` | 账户失败次数达到该值后自动锁定 |
| `subnet_captcha_threshold` | `int` | `10` | 子网失败次数达到该值后要求 CAPTCHA |
| `initial_backoff_seconds` | `int` | `1` | 首次失败后的初始等待秒数 |
| `max_backoff_seconds` | `int` | `300` | 等待时间的上限（秒） |
| `backoff_multiplier` | `int` | `2` | 每次失败后等待时间的倍增系数 |

### AccountState

单账户可变状态类。

| 字段 | 类型 | 说明 |
|------|------|------|
| `failure_count` | `int` | 该账户累计失败次数 |
| `last_failure_time` | `Optional[float]` | 最近一次失败的时间戳 |
| `is_locked` | `bool` | 账户是否处于锁定状态 |
| `locked_at` | `Optional[float]` | 账户被锁定的时间戳 |

**方法：**
- `reset()`：重置该账户的所有状态（失败次数归零、解除锁定）

### SubnetState

单子网可变状态类。

| 字段 | 类型 | 说明 |
|------|------|------|
| `failure_count` | `int` | 该子网累计失败次数 |
| `last_failure_time` | `Optional[float]` | 最近一次失败的时间戳 |

**方法：**
- `reset()`：重置该子网的所有状态

### CaptchaVerifier（Protocol）

CAPTCHA 验证器协议接口。外部实现需提供 `verify()` 方法。

**方法：**
- `verify(account: str, ip: str, captcha_solution: str) -> bool`：验证 CAPTCHA 解答是否正确

### DefaultCaptchaVerifier

默认 CAPTCHA 验证器，始终返回 `False`（即默认无 CAPTCHA 验证能力）。

### LoginAttemptResult

单次登录尝试的结果数据类。

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | `bool` | 登录是否成功 |
| `account_failures` | `int` | 当前账户累计失败次数 |
| `subnet_failures` | `int` | 当前子网累计失败次数 |
| `error` | `Optional[LoginRateError]` | 若失败，对应的异常对象 |

### LoginRateManager

登录限流管理器核心类。内部维护账户与子网的状态映射，提供完整的登录限流生命周期管理。

**核心方法：**

| 方法 | 说明 |
|------|------|
| `attempt_login(account, ip, password_verifier, captcha_solution=None)` | 处理登录请求，执行限流检查与密码验证 |
| `unlock_account(account)` | 管理员手动解锁指定账户 |
| `get_account_failure_count(account)` | 查询指定账户的累计失败次数 |
| `get_subnet_failure_count(subnet)` | 查询指定子网的累计失败次数 |
| `is_account_locked(account)` | 判断指定账户是否被锁定 |
| `reset_account(account)` | 重置指定账户的计数器 |
| `reset_subnet(subnet)` | 重置指定子网的计数器 |
| `reset_all()` | 重置所有计数器 |
| `has_account_counter(account)` | 判断指定账户是否有计数器记录 |
| `has_subnet_counter(subnet)` | 判断指定子网是否有计数器记录 |
| `get_backoff_seconds(account)` | 获取指定账户当前剩余等待秒数 |
| `calculate_backoff_for_failures(failure_count)` | 根据失败次数计算理论等待时间 |
| `set_captcha_verifier(verifier)` | 动态设置 CAPTCHA 验证器 |

### 异常类

| 异常 | 说明 |
|------|------|
| `LoginRateError` | 基类异常 |
| `InvalidAccountError` | 账户名格式非法 |
| `InvalidIPError` | IP 地址格式非法 |
| `AccountLockedError` | 账户已被锁定 |
| `BackoffActiveError` | 处于退避等待期，携带 `remaining_seconds` 字段 |
| `CaptchaRequiredError` | 需要 CAPTCHA 验证 |
| `CaptchaInvalidError` | CAPTCHA 验证失败 |
| `NoSuchAccountCounterError` | 查询的账户计数器不存在 |
| `NoSuchSubnetCounterError` | 查询的子网计数器不存在 |

## 阶梯式等退算法

本模块采用**指数退避（Exponential Backoff）**算法计算等待时间：

### 计算公式

```
backoff_seconds = min(initial_backoff_seconds × (backoff_multiplier ^ (failure_count - 1)), max_backoff_seconds)
```

### 示例（默认配置：initial=1, max=300, multiplier=2）

| 失败次数 | 等待时间（秒） |
|----------|----------------|
| 1        | 1              |
| 2        | 2              |
| 3        | 4              |
| 4        | 8              |
| 5        | 16             |
| 6        | 32             |
| 7        | 64             |
| 8        | 128            |
| 9        | 256            |
| 10+      | 300（上限）    |

### 算法特性

- **成倍增长**：每次失败后等待时间翻倍，有效对抗暴力破解
- **上限保护**：等待时间不会超过 `max_backoff_seconds`，避免无限增长导致用户永久无法登录
- **惰性判断**：仅在发起登录请求时判断是否仍处于等待期，不依赖定时器
- **向上取整**：剩余等待时间采用向上取整（`ceil`），保证用户不会在等待期结束前意外放行

## 账户 / IP 双维度限流策略

### 计数维度

1. **账户维度**：每个账户独立维护失败计数器、最后失败时间、锁定状态
2. **子网维度**：每个 IP 子网（IPv4 取前 3 段 `/24`，IPv6 取前 64 位 `/64`）独立维护失败计数器和最后失败时间

### 计数更新规则

- **登录失败**：同时递增**账户计数器**和**对应子网计数器**，更新各自的最后失败时间
- **登录成功**：同时重置**账户计数器**和**对应子网计数器**为零，解除账户锁定（若已锁定）

### 子网提取规则

- **IPv4**：将 IP 地址归入 `/24` 子网，如 `192.168.1.100` → `192.168.1.0/24`
- **IPv6**：将 IP 地址归入 `/64` 子网（标准子网前缀）

### 策略设计意图

- **账户维度**：防止针对单个账户的定向暴力破解
- **子网维度**：防止来自同一网络（如 NAT 出口、僵尸网络）的分布式暴力破解，即使攻击者尝试大量不同账户也会被拦截
- **两级独立**：两个维度的计数器互不影响，同一子网下不同账户的失败会累积到子网计数器

## CAPTCHA 升级机制

### 触发条件

当某个子网的累计失败次数达到 `subnet_captcha_threshold` 阈值后，该子网下的**所有**登录请求均被要求附加 CAPTCHA 验证。

### 处理流程

```
请求到达
  │
  ├─ 子网失败次数 ≥ 阈值？
  │    ├─ 否 → 继续正常流程
  │    └─ 是 → 是否提供了 CAPTCHA 解答？
  │              ├─ 否 → 返回 CaptchaRequiredError
  │              └─ 是 → CAPTCHA 验证是否通过？
  │                        ├─ 否 → 返回 CaptchaInvalidError
  │                        └─ 是 → 获得"特权通行"，跳过后续锁定/退避检查
  │
  └─ 继续执行账户锁定检查 → 退避等待检查 → 密码验证
```

### CAPTCHA 特权绕过

当 CAPTCHA 验证通过后，系统会授予该次请求**特权通行**权限，可以绕过以下两项检查：

1. **账户锁定检查**：即使账户已被锁定，仍可进入密码校验阶段
2. **退避等待检查**：即使账户仍处于退避等待期，也无需等待即可进行密码校验

该机制允许真实用户在触发安全机制后，通过额外身份验证证明自己是合法用户。

### 钩子接口

外部系统通过 `CaptchaVerifier` 协议注入 CAPTCHA 验证逻辑：

```python
class MyCaptchaVerifier:
    def verify(self, account: str, ip: str, captcha_solution: str) -> bool:
        # 调用第三方验证码服务或自行验证
        return verify_with_service(captcha_solution, ip)

manager.set_captcha_verifier(MyCaptchaVerifier())
```

## 登录请求完整处理流程

```
attempt_login(account, ip, password_verifier, captcha_solution)
  │
  ├─ 1. 验证账户名格式 → 非法抛 InvalidAccountError
  ├─ 2. 验证 IP 地址格式 → 非法抛 InvalidIPError
  ├─ 3. 提取子网标识
  │
  ├─ 4. 获取账户锁 + 子网锁（保证并发安全）
  │
  ├─ 5. 检查子网是否需 CAPTCHA
  │    ├─ 需要但未提供 → 返回 CaptchaRequiredError
  │    ├─ 提供但验证失败 → 返回 CaptchaInvalidError
  │    └─ 验证通过 → 设置 captcha_passed = True
  │
  ├─ 6. 检查账户是否锁定（captcha_passed 时跳过）
  │    └─ 已锁定 → 返回 AccountLockedError
  │
  ├─ 7. 检查是否处于退避等待期（captcha_passed 时跳过）
  │    └─ 等待中 → 返回 BackoffActiveError(remaining_seconds)
  │
  ├─ 8. 执行密码验证 password_verifier()
  │
  ├─ 9. 密码正确
  │    ├─ 重置账户计数器
  │    ├─ 重置子网计数器
  │    └─ 返回 success=True
  │
  └─ 10. 密码错误
       ├─ 递增账户计数器 + 更新最后失败时间
       ├─ 递增子网计数器 + 更新最后失败时间
       ├─ 若账户失败次数 ≥ 锁定阈值 → 标记账户锁定
       └─ 返回 success=False + 当前计数
```

## 并发安全约定

本模块采用**分层细粒度锁**设计，兼顾正确性与并发性能：

- `_struct_lock`：结构锁，保护账户/子网状态字典及对应锁字典的并发读写
- `_account_locks[account]`：每账户独立锁
- `_subnet_locks[subnet]`：每子网独立锁
- 单次登录操作在**账户锁 + 子网锁**的双重临界区内完成，不存在读取状态后释放锁再写入的跨步窗口
- 不同账户/子网的操作完全并行执行，互不阻塞

## 使用示例

### 基础使用

```python
from solocoder_py.login_rate import LoginRateManager

manager = LoginRateManager()

def verify_password():
    # 实际的密码验证逻辑
    return input_password == stored_password

result = manager.attempt_login(
    account="alice",
    ip="192.168.1.100",
    password_verifier=verify_password,
)

if result.success:
    print("登录成功")
elif result.error:
    print(f"登录失败: {result.error}")
```

### 自定义配置

```python
from solocoder_py.login_rate import LoginRateConfig, LoginRateManager

config = LoginRateConfig(
    account_lock_threshold=5,
    subnet_captcha_threshold=15,
    initial_backoff_seconds=2,
    max_backoff_seconds=600,
    backoff_multiplier=3,
)
manager = LoginRateManager(config=config)
```

### 接入 CAPTCHA 验证

```python
from solocoder_py.login_rate import LoginRateManager, CaptchaVerifier

class GoogleRecaptchaVerifier:
    def verify(self, account: str, ip: str, captcha_solution: str) -> bool:
        # 调用 Google reCAPTCHA 服务端验证接口
        return call_google_verify_api(captcha_solution, ip)

manager = LoginRateManager(captcha_verifier=GoogleRecaptchaVerifier())

result = manager.attempt_login(
    account="bob",
    ip="10.0.0.5",
    password_verifier=check_password,
    captcha_solution=user_submitted_captcha_token,
)
```

### 管理员解锁账户

```python
from solocoder_py.login_rate import LoginRateManager, NoSuchAccountCounterError

manager = LoginRateManager()

try:
    manager.unlock_account("locked_user")
    print("账户已解锁")
except NoSuchAccountCounterError:
    print("该账户无登录记录")
```

### 查询状态

```python
failures = manager.get_account_failure_count("alice")
locked = manager.is_account_locked("alice")
remaining = manager.get_backoff_seconds("alice")
subnet_failures = manager.get_subnet_failure_count("192.168.1.0/24")

print(f"账户失败次数: {failures}, 是否锁定: {locked}, 还需等待: {remaining}秒")
print(f"子网失败次数: {subnet_failures}")
```

### 测试中使用手动时钟

```python
from solocoder_py.login_rate import LoginRateManager, ManualClock, LoginRateConfig

clock = ManualClock(start_time=0.0)
config = LoginRateConfig(
    initial_backoff_seconds=10,
    max_backoff_seconds=300,
)
manager = LoginRateManager(config=config, clock=clock)

# 首次失败
manager.attempt_login("user", "192.168.1.1", lambda: False)
assert manager.get_backoff_seconds("user") == 10

# 立即重试被拒绝
result = manager.attempt_login("user", "192.168.1.1", lambda: True)
assert result.success is False
assert "请等待 10 秒" in str(result.error)

# 推进时间
clock.advance(10.0)

# 等待期结束，可以正常登录
result = manager.attempt_login("user", "192.168.1.1", lambda: True)
assert result.success is True
```
