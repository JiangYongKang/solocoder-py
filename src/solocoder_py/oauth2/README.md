# OAuth2 授权码状态管理器模块

## 模块功能

本模块实现了基于内存数据结构的 OAuth2 授权码状态管理器，完整覆盖授权码流程中的三大安全机制：

1. **PKCE（Proof Key for Code Exchange）挑战校验**：支持 `S256` 和 `plain` 两种 `code_challenge_method`，防止授权码被截获后滥用。
2. **state 参数防 CSRF**：通过一次性 state 参数校验，防止跨站请求伪造攻击。
3. **授权码一次性消费**：授权码具有有限的过期时间，且只能被消费一次，内置并发竞态保护防止同一授权码被重复使用。

## 核心类职责

### exceptions.py

| 类名 | 职责 |
|------|------|
| `OAuth2Error` | OAuth2 模块异常基类 |
| `PKCEError` | PKCE 相关异常基类 |
| `UnsupportedChallengeMethodError` | 不支持的 code_challenge_method |
| `CodeVerifierMismatchError` | code_verifier 与 code_challenge 不匹配 |
| `StateError` | state 参数相关异常基类 |
| `StateMissingError` | state 参数为空或缺失 |
| `StateInvalidError` | state 参数与存储值不一致 |
| `StateAlreadyUsedError` | state 已被使用（防重放） |
| `AuthorizationCodeError` | 授权码相关异常基类 |
| `AuthorizationCodeNotFoundError` | 授权码不存在 |
| `AuthorizationCodeExpiredError` | 授权码已过期 |
| `AuthorizationCodeAlreadyConsumedError` | 授权码已被消费 |
| `AuthorizationSessionNotFoundError` | 授权会话不存在 |
| `InvalidParameterError` | 参数校验失败 |

### models.py

| 类名 | 职责 |
|------|------|
| `CodeChallengeMethod` | 枚举：`PLAIN`（plain）、`S256`（S256）|
| `AuthorizationSession` | 授权会话数据模型，存储会话 ID、PKCE 挑战、state、授权码及其消费状态等 |

### manager.py

| 类名 | 职责 |
|------|------|
| `OAuth2StateManager` | 线程安全的状态管理器，维护所有授权会话和授权码的内存存储，提供 PKCE 校验、state 验证、授权码生成与消费等核心操作 |

## PKCE 校验流程

PKCE（RFC 7636）用于防止授权码在回调过程中被截获后滥用，适用于公共客户端（如移动端、SPA）。

### S256 模式（推荐）

```
客户端                                         服务器
  │                                              │
  │ 1. 生成 code_verifier (随机字符串)            │
  │    code_verifier = "dBjftJeZ4CVP..."         │
  │                                              │
  │ 2. 计算 code_challenge                       │
  │    code_challenge = BASE64URL(SHA256(verifier))│
  │                                              │
  │ 3. /authorize?code_challenge=xxx&method=S256  │──────►│
  │                                              │        存储 challenge & method
  │                                              │◄──────│ 4. 返回授权码 code
  │                                              │
  │ 5. /token?code=xxx&code_verifier=verifier    │──────►│
  │                                              │        5a. 取存储的 challenge
  │                                              │        5b. computed = B64URL(SHA256(verifier))
  │                                              │        5c. 比较 computed == stored_challenge
  │                                              │        5d. 匹配通过，签发令牌
```

### plain 模式（不推荐，仅用于兼容性）

```
客户端                                         服务器
  │                                              │
  │ 1. code_verifier = code_challenge            │
  │    (直接使用相同的随机字符串)                  │
  │                                              │
  │ 2. /authorize?code_challenge=xxx&method=plain│──────►│
  │                                              │        存储 challenge & method
  │                                              │◄──────│ 3. 返回授权码 code
  │                                              │
  │ 4. /token?code=xxx&code_verifier=verifier    │──────►│
  │                                              │        4a. 直接比较 verifier == stored_challenge
  │                                              │        4b. 匹配通过，签发令牌
```

### 关键实现点

- **S256 变换**：对 `code_verifier` 做 SHA-256 哈希后进行 Base64URL 编码（去除末尾 `=` 填充）
- **安全比较**：使用 `secrets.compare_digest` 进行恒定时间比较，防止时序攻击
- **校验时机**：PKCE 校验在令牌端点消费授权码时强制执行

## state 防 CSRF 机制

state 参数用于防止 CSRF（跨站请求伪造）攻击，确保授权回调来自合法的客户端。

### 工作流程

```
客户端                                         服务器
  │                                              │
  │ 1. 生成随机 state 并本地保存                  │
  │                                              │
  │ 2. /authorize?state=abc123&...               │──────►│
  │                                              │        存储 state 与会话绑定
  │                                              │◄──────│ 3. 302 重定向到 redirect_uri?code=xxx&state=abc123
  │                                              │
  │ 4. 客户端验证 state == 本地保存值              │
  │    (同时服务器端也会验证)                      │
  │                                              │
  │ 5. /token?code=xxx                           │──────►│
  │                                              │        state 已在回调阶段消费
```

### 安全策略

| 策略 | 说明 |
|------|------|
| **state 不可为空** | 授权请求必须携带 state，不允许空值或缺失 |
| **一次性消费** | 每个 state 只能被成功验证一次，验证后立即标记为已消费 |
| **防重放** | 已消费的 state 再次验证时抛出 `StateAlreadyUsedError` |
| **恒定时间比较** | 使用 `secrets.compare_digest` 防止时序攻击 |

## 授权码一次性消费策略

授权码是短期凭证，必须防止被重复使用。

### 生命周期

```
生成 (generate_authorization_code)
    │
    ▼
有效 (未过期 + 未消费)
    │
    ├──► 过期 ──► AuthorizationCodeExpiredError
    │
    ▼
消费 (consume_authorization_code)  ──► 成功：返回会话，标记已消费
    │
    ▼
已消费 ──► 再次使用：AuthorizationCodeAlreadyConsumedError
```

### 关键策略

| 策略 | 说明 |
|------|------|
| **有限过期** | 授权码具有过期时间（默认 10 分钟），过期后自动失效 |
| **原子消费** | 消费操作在线程锁内完成，确保原子性 |
| **并发竞态保护** | 使用 `threading.Lock` 防止多线程环境下同一授权码被两次消费 |
| **消费后立即标记** | 验证通过后立即将 `authorization_code_consumed` 设为 `True` |

## 使用示例

### 完整授权码 + PKCE S256 流程

```python
from datetime import timedelta
from solocoder_py.oauth2 import OAuth2StateManager

manager = OAuth2StateManager()

# ============ 1. 客户端发起授权请求 ============
code_verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
code_challenge = OAuth2StateManager.compute_s256_challenge(code_verifier)

session_id, state = manager.create_authorization_session(
    code_challenge=code_challenge,
    code_challenge_method="S256",
    client_id="my-client-app",
    redirect_uri="https://app.example.com/callback",
    scope="read:user write:data",
)

# 将 session_id 存入客户端 cookie，state 返回给客户端

# ============ 2. 用户授权后回调，验证 state ============
# 假设从回调 URL 中获取到返回的 state
callback_state = state  # 实际从请求参数获取
manager.verify_state(session_id, callback_state)

# ============ 3. 生成授权码 ============
authorization_code = manager.generate_authorization_code(
    session_id, expires_in=timedelta(minutes=5)
)

# 将授权码通过重定向返回给客户端

# ============ 4. 客户端用授权码交换令牌 ============
# 客户端提交 code_verifier 和 authorization_code
session = manager.consume_authorization_code(authorization_code, code_verifier)

print(f"Client ID: {session.client_id}")
print(f"Scope: {session.scope}")
print(f"Redirect URI: {session.redirect_uri}")
# 验证通过，签发 access_token
```

### PKCE plain 模式

```python
code_verifier = "my-plain-verifier-string-12345"
code_challenge = code_verifier  # plain 模式下两者相同

session_id, state = manager.create_authorization_session(
    code_challenge=code_challenge,
    code_challenge_method="plain",
)

# ... state 验证、生成授权码 ...

session = manager.consume_authorization_code(authorization_code, code_verifier)
```

### 使用自定义 state

```python
custom_state = "my-pre-generated-random-state-value"
session_id, state = manager.create_authorization_session(
    code_challenge=code_challenge,
    code_challenge_method="S256",
    state=custom_state,
    auto_generate_state=False,
)
assert state == custom_state
```

### 会话管理

```python
# 查询会话状态
session = manager.get_session(session_id)
if session:
    print(f"Code consumed: {session.authorization_code_consumed}")
    print(f"State verified: {session.state_verified}")

# 通过授权码反查会话
session = manager.get_session_by_code(authorization_code)

# 失效会话
manager.invalidate_session(session_id)

# 清理所有过期授权码对应的会话
cleaned_count = manager.cleanup_expired()

# 统计当前会话数
print(f"Active sessions: {manager.count_sessions()}")

# 清空所有数据
manager.clear()
```

### 配置管理器参数

```python
from datetime import timedelta

manager = OAuth2StateManager(
    default_code_expires_in=timedelta(minutes=5),
    default_session_id_length=48,
    default_authorization_code_length=48,
    default_state_length=48,
)
```

## 运行测试

```bash
pytest tests/oauth2/ -v
```
