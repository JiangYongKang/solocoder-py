# TOTP 双因素认证模块

基于 RFC 6238 规范的 TOTP (Time-based One-Time Password) 双因素认证实现，使用内存数据结构管理密钥与验证状态。

## 模块功能

- **共享密钥生成**：生成符合 RFC 6238 规范的 Base32 编码共享密钥，至少 20 字节（160 位）随机熵，支持为用户批量生成独立密钥
- **多算法支持**：支持 SHA1、SHA256、SHA512 三种哈希算法，算法字段真正驱动底层 HMAC 计算
- **TOTP 码验证**：验证用户提交的 TOTP 动态口令，验证失败时抛出领域异常
- **时间窗口漂移容错**：支持配置前后 N 个时间窗口的容错范围，容忍客户端与服务器时间不同步
- **重放攻击防护**：同一时间窗口内的 TOTP 码只能使用一次，防止重放攻击
- **恢复码备份**：生成一组一次性恢复码，在用户丢失设备时用于绕过 TOTP 验证
- **内存存储**：使用内存数据结构存储所有状态，适合快速原型开发和测试

## 核心类职责

### TotpService

TOTP 服务的主入口类，封装了所有 TOTP 相关操作。验证失败时抛出对应的领域异常：

- `generate_secret_for_user(user_id, overwrite=False)` - 为单个用户生成 TOTP 密钥和恢复码
- `generate_secrets_for_users(user_ids, overwrite=False)` - 批量为多个用户生成密钥
- `verify_totp(user_id, code, drift_windows=None)` - 验证 TOTP 码，失败抛出 `InvalidTotpCodeError`
- `verify_recovery_code(user_id, code)` - 验证恢复码，失败抛出 `InvalidRecoveryCodeError`
- `regenerate_recovery_codes(user_id)` - 重新生成恢复码（旧码全部作废）
- `get_recovery_codes_remaining(user_id)` - 查询剩余可用恢复码数量
- `has_secret(user_id)` - 检查用户是否已设置 TOTP
- `get_secret_uri(user_id)` - 获取 otpauth URI 用于扫码绑定
- `delete_secret(user_id)` - 删除用户的 TOTP 配置

### InMemoryTotpStore

内存存储类，管理所有用户的 TOTP 记录：

- 存储用户密钥、恢复码哈希、已使用的 TOTP 码记录
- 支持增删改查操作
- 自动清理过期的时间窗口使用记录

### TotpSecret

TOTP 密钥数据模型：

- 保存密钥、发行方、位数、周期、算法等信息
- `get_uri()` 方法生成 otpauth://totp/ 格式的 URI，用于客户端扫码

### UserTotpRecord

用户 TOTP 记录，包含：

- 用户密钥（TotpSecret）
- 恢复码列表（RecoveryCode）
- 已使用的 TOTP 码记录（按时间窗口索引）
- 窗口清理方法：自动移除过期窗口的使用记录

### RecoveryCode

恢复码数据模型：

- `code_hash`: 恢复码的 SHA-256 哈希值
- `consumed`: 是否已被使用的标记

## TOTP 算法原理

TOTP (Time-based One-Time Password) 基于 HOTP (HMAC-based One-Time Password) 算法，将时间戳作为计数器值：

### 算法步骤

1. **时间计数器计算**：
   ```
   T = floor((当前Unix时间戳 - T0) / X)
   ```
   其中 T0 通常为 0（Unix 纪元），X 为时间步长（默认 30 秒）。

2. **HOTP 计算**：
   - 将计数器 T 编码为 8 字节大端整数
   - 使用 HMAC 算法（支持 SHA1、SHA256、SHA512），以共享密钥为 key，计数器为消息，计算 HMAC 值
   - 对 HMAC 结果进行动态截断（Dynamic Truncation）：
     - 取 HMAC 最后一个字节的低 4 位作为偏移量 offset
     - 从 offset 开始取 4 字节，转换为 32 位无符号整数并去掉最高位
     - 对 10^digits 取模得到最终的 N 位数字验证码

3. **结果格式化**：将数字补零到指定位数（默认 6 位）。

### 算法参数

- **密钥长度**：至少 20 字节（160 位）随机熵，Base32 编码存储
- **时间步长**：默认 30 秒
- **验证码位数**：默认 6 位（支持 6-8 位）
- **哈希算法**：默认 SHA1（RFC 6238 标准），支持 SHA1、SHA256、SHA512

## 时间窗口漂移容错策略

由于客户端和服务器的时钟可能存在轻微不同步，模块支持配置漂移窗口数：

### 工作原理

- **当前窗口**：以服务器当前时间所在的 30 秒窗口为基准
- **向前检查**：检查未来 N 个窗口（预防服务器时钟慢于客户端）
- **向后检查**：检查过去 N 个窗口（预防客户端时钟慢于服务器）
- **总窗口数**：2 * N + 1 个窗口（默认 N=1，共 3 个窗口 90 秒范围）

### 配置方式

```python
# 默认：前后各 1 个窗口，共 3 个窗口
service = TotpService(drift_windows=1)

# 仅检查当前窗口
service = TotpService(drift_windows=0)

# 放宽到前后各 2 个窗口
service = TotpService(drift_windows=2)

# 单次验证时临时指定漂移窗口数
service.verify_totp("user1", "123456", drift_windows=3)
```

### 重放防护机制

- 每个成功验证的 TOTP 码会被记录到对应的时间窗口中
- 同一窗口内的相同 TOTP 码再次提交会被拒绝
- 过期窗口的记录会自动清理，避免内存无限增长

## 恢复码备份机制

恢复码用于在用户丢失 TOTP 设备时紧急登录，每个恢复码只能使用一次。

### 生成与存储

- 默认生成 8 个恢复码
- 每个恢复码为 16 字节随机熵的 Base32 编码（约 26 个字符）
- 恢复码以 SHA-256 哈希形式存储，明文仅在生成时返回一次
- 恢复码验证使用常量时间比较，防止时序攻击

### 使用规则

- 每个恢复码只能使用一次，使用后标记为已消费
- 恢复码大小写不敏感，自动去除首尾空白
- 成功的恢复码验证绕过 TOTP 码校验
- 所有恢复码用完后，可调用 `regenerate_recovery_codes()` 生成新的一组
- 重新生成恢复码会使所有旧恢复码立即失效

### 安全设计

- 哈希存储：即使数据库泄露，攻击者也无法直接获取恢复码明文
- 一次性使用：每个码只能用一次，降低泄露风险
- 常量时间比较：防止基于响应时间的侧信道攻击

## 使用示例

### 基础使用

```python
from solocoder_py.totp import TotpService

# 创建服务
service = TotpService(issuer="MyApp")

# 为用户生成 TOTP 密钥
result = service.generate_secret_for_user("alice@example.com")

print(f"密钥: {result.secret}")
print(f"扫码URI: {result.uri}")
print(f"恢复码: {result.recovery_codes}")

# 验证 TOTP 码
from solocoder_py.totp import InvalidTotpCodeError

try:
    verification = service.verify_totp("alice@example.com", "123456")
    print("验证成功！")
except InvalidTotpCodeError as e:
    print(f"验证失败: {e}")
```

### 使用恢复码

```python
from solocoder_py.totp import InvalidRecoveryCodeError, RecoveryCodeConsumedError

# 用户使用恢复码登录
try:
    result = service.verify_recovery_code("alice@example.com", "abcdefghijklmnop")
    remaining = result.recovery_codes_remaining
    print(f"登录成功，剩余恢复码: {remaining}")
except InvalidRecoveryCodeError:
    print("恢复码无效")
except RecoveryCodeConsumedError:
    print("恢复码已被使用")
```

### 重新生成恢复码

```python
# 所有恢复码用完后重新生成
new_codes = service.regenerate_recovery_codes("alice@example.com")
print(f"新恢复码: {new_codes}")
```

### 自定义配置

```python
service = TotpService(
    issuer="MyCompany",
    secret_bytes=32,          # 32 字节密钥熵（最小 20 字节）
    algorithm="SHA256",        # 哈希算法：SHA1、SHA256、SHA512
    digits=8,                  # 8 位验证码
    period=30,                 # 30 秒时间窗口
    drift_windows=2,           # 前后各 2 个窗口容错
    recovery_code_count=10,    # 10 个恢复码
)
```

### 批量生成密钥

```python
users = ["user1", "user2", "user3"]
results = service.generate_secrets_for_users(users)

for result in results:
    print(f"{result.user_id}: {result.uri}")
```

### 直接计算 TOTP 码

```python
from solocoder_py.totp import generate_secret, compute_totp

# 生成密钥（最小 20 字节）
secret = generate_secret(20)

# 计算当前 TOTP 码（默认 SHA1）
code = compute_totp(secret)
print(f"当前验证码: {code}")

# 使用 SHA256 算法计算
code_sha256 = compute_totp(secret, algorithm="SHA256")
print(f"SHA256 验证码: {code_sha256}")

# 指定时间戳计算
code_at_time = compute_totp(secret, timestamp=1700000000)
```
