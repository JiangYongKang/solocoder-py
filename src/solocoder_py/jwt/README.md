# JWT 模块

本模块提供 JSON Web Token (JWT) 的签发与校验功能，支持密钥轮换、算法白名单、以及 aud/iss 声明的强制校验。

## 模块功能

- **JWT 签发（encode）**：基于 HMAC 签名算法（HS256/HS384/HS512）生成符合 JWT 规范的令牌
- **JWT 校验（decode）**：解析并验证 JWT 的签名、算法合法性、声明字段有效性
- **密钥轮换**：支持多版本密钥并存，使用 kid（Key ID）标识，平滑切换密钥，旧密钥保留至超期自动清理
- **算法白名单**：签发和校验时强制校验算法是否在白名单中，拒绝 none 等不安全算法
- **aud/iss 强制校验**：强制验证签发者（iss）和受众（aud）声明，不可跳过

## 核心类与职责

### `JWTConfig`（[models.py](models.py)）
全局配置对象，包含：
- `issuer`：默认签发者，签发 JWT 时自动写入 iss 字段
- `audiences`：默认受众列表，签发 JWT 时自动写入 aud 字段
- `allowed_algorithms`：算法白名单，默认包含 `{"HS256", "HS384", "HS512"}`
- `default_algorithm`：默认使用的签名算法
- `default_expire_seconds`：默认过期时长（秒）
- `key_retire_seconds`：密钥退休前保留时长（秒），到期后从密钥集自动移除
- `current_service_id`：当前服务标识，用于 aud 校验
- `allowed_issuers`：合法签发者列表，用于 iss 校验

### `SigningKey`（[models.py](models.py)）
单个签名密钥的数据模型，字段：
- `kid`：密钥唯一标识
- `secret`：HMAC 密钥字节串
- `algorithm`：该密钥使用的算法
- `created_at`：创建时间戳
- `retire_at`：退休时间戳，超过该时间后将被清理
- `is_active`：是否为当前活跃密钥

### `KeyStore`（[store.py](store.py)）
内存密钥存储与轮换管理器，职责：
- 维护多版本密钥集（dict，kid → SigningKey）
- 追踪当前活跃密钥（active_kid）
- 密钥创建 / 轮换 / 删除
- 定期清理已超过 retire_at 的密钥（每次访问时惰性清理）
- 提供根据 kid 查找密钥的能力

### `JWTService`（[core.py](core.py)）
JWT 签发与校验的对外服务类，封装：
- `encode(claims, options)`：签发 JWT
- `decode(token)`：校验并解析 JWT，返回 `VerifiedJWT`
- `rotate_key(...)`：快速触发密钥轮换

### 其它辅助类型
- `VerifiedJWT`：校验通过后的 JWT，以 dict-like 方式访问载荷字段
- `DecodedJWT`：未校验签名的原始解码结果
- `SignOptions`：签发时的可选参数（算法、过期时长、额外头字段等）
- `JWTClock`：时间接口（可注入 ManualClock 用于测试）

### 异常类（[exceptions.py](exceptions.py)）
| 异常 | 触发场景 |
|---|---|
| `JWTError` | 所有异常的基类 |
| `MalformedTokenError` | JWT 格式错误（缺分隔点、Base64/JSON 非法等） |
| `InvalidSignatureError` | 签名校验失败 |
| `InvalidAlgorithmError` | 算法不在白名单或与密钥算法不匹配 |
| `KeyNotFoundError` | kid 在密钥集中不存在 |
| `EmptyKeyStoreError` | 密钥集为空时尝试签发 |
| `ExpiredTokenError` | exp 已过期 |
| `ImmatureTokenError` | nbf 未到生效时间 |
| `InvalidIssuerError` | iss 不在合法列表 |
| `InvalidAudienceError` | 当前服务不在 aud 列表 |
| `MissingClaimError` | 缺少必需的声明（iss/aud/exp） |

## JWT 签发流程

```
claims(dict) + SignOptions
        │
        ▼
  白名单算法校验 ──不在──► InvalidAlgorithmError
        │
       在
        │
        ▼
  获取活跃密钥 ──无──► EmptyKeyStoreError
        │
        ▼
  填充标准声明：
    - iss = config.issuer
    - aud = config.audiences
    - exp = now + default_expire_seconds
    - iat = now（可关闭）
    - jti = 随机 ID（可关闭）
        │
        ▼
  构造 JWT 头部：
    - typ: "JWT"
    - alg: 指定算法
    - kid: 活跃密钥的 kid
        │
        ▼
  header / payload → JSON → Base64URL 编码
        │
        ▼
  signing_input = header_b64 + "." + payload_b64
        │
        ▼
  HMAC(algorithm, secret, signing_input) → signature
        │
        ▼
  JWT = header_b64 + "." + payload_b64 + "." + Base64URL(signature)
```

## JWT 校验流程

```
token(str)
    │
    ▼
  拆分为 3 段（header.payload.signature）
    │ 段数≠3 ──► MalformedTokenError
    ▼
  各段 Base64URL 解码
    │ 失败 ──► MalformedTokenError
    ▼
  header / payload 解析为 JSON
    │ 失败 ──► MalformedTokenError
    ▼
  header.alg 白名单校验 ──不在──► InvalidAlgorithmError
    │
    ▼
  header.kid 存在校验 ──缺──► JWTError
    │
    ▼
  KeyStore 按 kid 查密钥 ──不存在──► KeyNotFoundError
    │
    ▼
  密钥.algorithm 与 header.alg 匹配
    │ 不匹配 ──► InvalidAlgorithmError
    ▼
  重新计算签名，与 token.signature 常量时间比较
    │ 不匹配 ──► InvalidSignatureError
    ▼
  声明强制校验（顺序不可跳过）：
    1. iss 存在且在 allowed_issuers ──缺/不符──► MissingClaimError / InvalidIssuerError
    2. aud 存在且包含 current_service_id ──缺/不符──► MissingClaimError / InvalidAudienceError
    3. exp 存在且未过期 ──缺/过期──► MissingClaimError / ExpiredTokenError
    4. nbf 若存在则已到生效时间 ──未到──► ImmatureTokenError
    │
    ▼
  返回 VerifiedJWT
```

## 密钥轮换策略与 kid 机制

### kid 机制
每个密钥拥有唯一的 `kid` 标识。签发 JWT 时，`kid` 写入 JWT 头部的 `kid` 字段；校验时根据头部 `kid` 精确查找对应密钥，再用该密钥验证签名。

### 轮换流程

```
  [Key-v1] (active, retire_at=T+86400)
      │
      │  rotate_key()
      ▼
  [Key-v1] (retired, retire_at=T+86400)   ← 仍在校验旧 JWT
  [Key-v2] (active,  retire_at=T'+86400)  ← 签发新 JWT
      │
      │  时间推进至 T+86400
      ▼
  (Key-v1 被清理，仅 Key-v2 保留)
```

**核心规则**：
1. `rotate_key()` 创建新密钥并设为 active，旧密钥的 `is_active` 置 false 但继续保留
2. 旧密钥保留至 `retire_at = created_at + key_retire_seconds`，到期后通过惰性清理自动移除
3. 轮换期间，所有已签发的旧 JWT 仍可通过旧密钥校验通过，不会因切换而失效
4. 超期后旧密钥被彻底移除，对应 JWT 将因 `KeyNotFoundError` 而无法校验（通常这些 JWT 自身也已过期）

## 算法白名单规则

白名单由 `JWTConfig.allowed_algorithms`（set）配置，默认支持 HMAC 系列：

- `HS256`：HMAC-SHA256
- `HS384`：HMAC-SHA384
- `HS512`：HMAC-SHA512

**签发时**：
- 若请求的算法不在白名单 → `InvalidAlgorithmError`
- 活跃密钥使用的算法必须与请求算法一致

**校验时**：
- JWT 头部 `alg` 不在白名单 → `InvalidAlgorithmError`（含 `none` 等算法攻击）
- 查找到的密钥算法必须与头部 `alg` 匹配

注意：白名单中不允许包含 `none` 等非 HMAC 算法，构造 `JWTConfig` 时会直接拒绝。

## aud / iss 校验逻辑

**iss（签发者）强制校验**：
- 校验 payload 中必须存在 `iss` 字段（字符串）
- `iss` 值必须出现在 `allowed_issuers` 列表中
- 默认 `allowed_issuers = [issuer]`，可配置多个合法签发者

**aud（受众）强制校验**：
- 校验 payload 中必须存在 `aud` 字段（字符串或字符串数组）
- 当前服务 `current_service_id` 必须出现在 aud 列表中（数组命中任意一个即通过）
- 若 `current_service_id` 未配置，退而使用 `audiences[0]` 作为期望

两个校验均不可关闭，任何一个失败都直接拒绝该 JWT。

## 使用示例

### 基本签发与校验

```python
from solocoder_py.jwt import JWTConfig, JWTService

# 1. 配置
config = JWTConfig(
    issuer="my-auth-server",
    audiences=["api-gateway", "internal-service"],
    current_service_id="api-gateway",
    default_expire_seconds=3600,
    key_retire_seconds=86400,
)

# 2. 创建服务并添加初始密钥
service = JWTService(config)
service.key_store.add_key(algorithm="HS256", kid="key-2026-06")

# 3. 签发
token = service.encode({
    "sub": "user-123",
    "role": "admin",
    "email": "user@example.com",
})
# token 形如: eyJhbGciOiJIUzI1NiIs...

# 4. 校验
verified = service.decode(token)
print(verified["sub"])     # user-123
print(verified["role"])    # admin
print(verified.get("nonexistent", "default"))  # default
```

### 密钥轮换

```python
# 先用旧密钥签发
old_token = service.encode({"sub": "before-rotation"})

# 触发轮换
service.rotate_key(kid="key-2026-07")
# 或指定算法: service.rotate_key(algorithm="HS384", kid="key-2026-07-hs384")

# 新签发的 JWT 自动使用新密钥
new_token = service.encode({"sub": "after-rotation"})

# 旧 JWT 依然有效（旧密钥未退休）
assert service.decode(old_token)["sub"] == "before-rotation"
assert service.decode(new_token)["sub"] == "after-rotation"
```

### 使用可注入时钟（测试场景）

```python
from solocoder_py.seat.clock import ManualClock
from solocoder_py.jwt import JWTClock, SignOptions, ExpiredTokenError

manual = ManualClock(start_time=1_718_150_400.0)
clock = JWTClock.from_clock(manual)

config = JWTConfig(issuer="test", audiences=["svc"], current_service_id="svc")
service = JWTService(config, clock=clock)
service.key_store.add_key(algorithm="HS256", kid="k1")

token = service.encode({"sub": "u"}, SignOptions(expire_seconds=60))

# 未过期
assert service.decode(token)["sub"] == "u"

# 推进时间
manual.advance(60)

# 过期
try:
    service.decode(token)
except ExpiredTokenError:
    print("token expired as expected")
```

### 限制算法白名单

```python
strict_config = JWTConfig(
    issuer="auth",
    audiences=["svc"],
    allowed_algorithms={"HS512"},   # 仅允许 HS512
    default_algorithm="HS512",
    current_service_id="svc",
)
svc = JWTService(strict_config)
svc.key_store.add_key(algorithm="HS512", kid="only-512")

# 正常（使用 HS512）
t = svc.encode({"sub": "u"}, SignOptions(algorithm="HS512"))

# 拒绝（不在白名单）
svc.encode({"sub": "u"}, SignOptions(algorithm="HS256"))
# → InvalidAlgorithmError
```
