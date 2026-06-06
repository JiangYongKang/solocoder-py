# Token 模块

访问令牌刷新域模块，实现了基于令牌族（Token Family）的安全认证机制，支持 access token 与 refresh token 的签发、轮换刷新以及重用检测。

## 模块功能

1. **Token 签发**：用户登录后同时签发 access token（短有效期，用于 API 访问）和 refresh token（长有效期，用于刷新 access token）。两个 token 均采用密码学安全的随机字符串生成。

2. **轮换签发（Rotation）**：使用 refresh token 刷新时，服务端同时生成新的 access token 和新的 refresh token 返回给客户端，旧的 refresh token 立即标记为已使用，失效不可再用。

3. **令牌族（Token Family）管理**：同一用户一次登录产生的初始 token 对以及后续所有轮换产生的 token 对同属一个令牌族。族内 refresh token 按代际（generation）递增排列。

4. **重用检测与全族吊销**：若服务端收到一个已经被使用过的 refresh token（非最新代），判定该令牌族可能已泄露，立即将族内所有 token 标记为吊销状态，拒绝该族后续任何请求。

## 核心类职责

### models.py

| 类 | 职责 |
| --- | --- |
| `TokenStatus` | 枚举类型，表示 token 的状态：`ACTIVE`、`USED`、`REVOKED`、`EXPIRED` |
| `AccessToken` | 访问令牌数据结构，包含 token 字符串、用户 ID、族 ID、签发时间、过期时间、状态；提供 `is_active` / `is_expired` 属性 |
| `RefreshToken` | 刷新令牌数据结构，在 AccessToken 基础上增加 `generation`（代际）字段 |
| `TokenPair` | access token 与 refresh token 的组合对 |
| `TokenFamily` | 令牌族，管理同一登录会话下所有代的 refresh token 及所有 access token，提供 `revoke_all()` 方法进行全族吊销 |

### repository.py

| 类 | 职责 |
| --- | --- |
| `TokenRepository` | 基于内存字典的令牌存储仓库，提供 TokenFamily、AccessToken、RefreshToken 的增删查改操作，以及按族吊销接口 |

### service.py

| 类 / 异常 | 职责 |
| --- | --- |
| `TokenService` | 令牌服务的核心门面类，封装签发、刷新、验证、吊销等业务逻辑 |
| `TokenError` | 所有令牌相关异常的基类 |
| `TokenNotFoundError` | token 不存在 |
| `TokenExpiredError` | token 已过期 |
| `TokenRevokedError` | token 或其所属族已被吊销 |
| `TokenReusedError` | refresh token 被重用（触发全族吊销） |

## 令牌生命周期与轮换流程

### 文本描述

```
[用户登录]
    |
    v
签发初始 TokenPair (access_token + refresh_token, generation=1)
    |
    +---> 客户端持有 TokenPair
    |
[客户端 API 请求] ---> access_token 校验通过 ---> 返回业务数据
    |
    | (access_token 即将过期或已过期)
    v
[客户端使用 refresh_token 刷新]
    |
    +---> 服务端校验 refresh_token:
    |       1. 是否存在
    |       2. 所属族是否被吊销
    |       3. 是否已过期
    |       4. 是否为 ACTIVE 状态 (若已 USED -> 触发重用检测 -> 全族吊销)
    |
    +---> 校验通过：
    |       - 将旧 refresh_token 标记为 USED
    |       - 生成新 access_token
    |       - 生成新 refresh_token (generation = 旧 generation + 1)
    |       - 返回新的 TokenPair
    |
    +---> 客户端更新本地存储为新 TokenPair
    |
    v
(循环：继续轮换)

[重用检测触发]
    |
    v
旧 refresh_token 被再次提交
    |
    +---> 检测到状态 != ACTIVE
    |
    +---> 立即将整个 TokenFamily 标记为 revoked
    |       - 所有 generations 的 refresh_token -> REVOKED
    |       - 所有 access_token -> REVOKED
    |
    +---> 抛出 TokenReusedError
    |
    v
该族内任何 token 后续请求均被拒绝
```

## 使用示例

```python
from datetime import timedelta
from solocoder_py.token import (
    TokenService,
    TokenExpiredError,
    TokenRevokedError,
    TokenReusedError,
)

# 1. 创建服务实例（可自定义 TTL）
service = TokenService(
    access_token_ttl=timedelta(minutes=15),
    refresh_token_ttl=timedelta(days=7),
)

# 2. 用户登录，签发 token 对
token_pair = service.issue_token_pair("user-123")
access = token_pair.access_token.token
refresh = token_pair.refresh_token.token

# 3. 校验 access token
try:
    validated = service.validate_access_token(access)
    print(f"User: {validated.user_id}")
except TokenExpiredError:
    print("Access token expired, need to refresh")
except TokenRevokedError:
    print("Token revoked, please re-login")

# 4. 使用 refresh token 轮换
try:
    new_pair = service.refresh_token_pair(refresh)
    access = new_pair.access_token.token
    refresh = new_pair.refresh_token.token  # 客户端更新本地 refresh token
except TokenReusedError:
    print("Token reuse detected! Family revoked, please re-login immediately")
except TokenExpiredError:
    print("Refresh token expired, please re-login")

# 5. 主动吊销整个令牌族（用户登出场景）
service.revoke_family(token_pair.access_token.family_id)
```
