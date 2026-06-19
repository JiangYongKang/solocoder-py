# Session Store

会话存储域模块，使用内存数据结构管理用户会话。

## 功能概述

本模块提供一个线程安全的内存会话存储系统，支持以下核心功能：

- **滑动过期（Sliding Expiration）**：每次访问会话时自动延长过期时间
- **空闲超时登出（Idle Timeout）**：在指定空闲时间内无操作则自动失效
- **并发会话控制**：限制每个用户的最大并发会话数量，支持多种淘汰策略

## 核心类职责

### SessionStore
会话存储管理器，提供会话的创建、读取、更新、删除等操作。线程安全，支持多线程环境下的并发访问。

主要方法：
- `create_session(user_id, data, config)`：创建新会话
- `get_session(session_id)`：读取会话（同时刷新过期时间）
- `update_session(session_id, data)`：更新会话数据（同时刷新过期时间）
- `delete_session(session_id)`：删除会话
- `list_sessions_by_user(user_id)`：列出用户的所有有效会话
- `logout_all_sessions(user_id, reason)`：强制用户所有会话下线
- `clear()`：清空所有会话

### Session / SessionInfo
`Session` 是内部存储模型，`SessionInfo` 是对外返回的只读视图，包含：
- `session_id`：会话唯一标识
- `user_id`：所属用户标识
- `created_at`：创建时间戳
- `expires_at`：绝对过期时间戳
- `idle_expires_at`：空闲过期时间戳
- `ttl`：总有效期（秒）
- `idle_timeout`：空闲超时时间（秒）
- `data`：会话自定义数据
- `forcibly_logged_out`：是否被强制下线
- `forced_logout_reason`：强制下线原因

### SessionCreateConfig
会话创建配置：
- `ttl`：会话总有效期（秒），必须 > 0
- `idle_timeout`：空闲超时时间（秒），必须 > 0 且 <= ttl
- `max_concurrent_sessions`：每个用户最大并发会话数，必须 > 0
- `eviction_strategy`：超限时的淘汰策略

### EvictionStrategy
并发会话超限的淘汰策略枚举：
- `REJECT`：拒绝创建新会话，抛出 `SessionLimitExceededError`
- `EVICT_OLDEST`：淘汰最旧的会话，将其标记为强制下线

### Clock
时间抽象类，便于测试时注入假时钟。

## 过期机制说明

### 滑动过期（Sliding TTL）
- 会话创建时，设置 `expires_at = now + ttl`
- 每次成功调用 `get_session` 或 `update_session` 时：
  - 先检查 `now >= expires_at`，若成立则会话已过期，抛出 `SessionExpiredError`
  - 若未过期，刷新 `expires_at = now + ttl`
- 只要会话持续被使用，就永远不会过期
- 如果在整个 ttl 时间段内没有被访问，则自动失效

### 空闲超时登出（Idle Timeout）
- 会话创建时，设置 `idle_expires_at = now + idle_timeout`
- 每次成功调用 `get_session` 或 `update_session` 时：
  - 先检查 `now >= idle_expires_at`，若成立则抛出 `SessionIdleTimeoutError`
  - 若未超时，刷新 `idle_expires_at = now + idle_timeout`
- 即使 TTL 还未到期，只要在 idle_timeout 时间内没有任何操作，会话也会失效
- idle_timeout 必须小于或等于 ttl

### 强制下线（Forcible Logout）
以下情况会将会话标记为强制下线：
- 并发会话超限且策略为 `EVICT_OLDEST` 时，最旧的会话被淘汰
- 调用 `logout_all_sessions()` 强制用户所有会话下线

被标记为强制下线的会话：
- 后续访问会抛出 `SessionForciblyLoggedOutError`
- 错误消息中包含具体的下线原因

## 使用示例

### 基本使用

```python
from solocoder_py.session_store import (
    EvictionStrategy,
    SessionCreateConfig,
    SessionStore,
)

store = SessionStore()

config = SessionCreateConfig(
    ttl=3600.0,
    idle_timeout=1800.0,
    max_concurrent_sessions=3,
    eviction_strategy=EvictionStrategy.EVICT_OLDEST,
)

session = store.create_session(
    user_id="user-123",
    data={"role": "admin", "ip": "127.0.0.1"},
    config=config,
)

info = store.get_session(session.session_id)
print(info.data)

updated = store.update_session(session.session_id, {"last_action": "login"})
print(updated.data["last_action"])

store.delete_session(session.session_id)
```

### 拒绝策略

```python
from solocoder_py.session_store import (
    EvictionStrategy,
    SessionCreateConfig,
    SessionLimitExceededError,
    SessionStore,
)

config = SessionCreateConfig(
    ttl=3600.0,
    idle_timeout=1800.0,
    max_concurrent_sessions=2,
    eviction_strategy=EvictionStrategy.REJECT,
)
store = SessionStore(default_config=config)

store.create_session("user-1")
store.create_session("user-1")

try:
    store.create_session("user-1")
except SessionLimitExceededError:
    print("会话数量已达上限")
```

### 注入测试时钟

```python
from solocoder_py.session_store import Clock, SessionCreateConfig, SessionStore


class FakeClock(Clock):
    def __init__(self):
        self._time = 1000000.0

    def now(self) -> float:
        return self._time

    def advance(self, seconds: float) -> None:
        self._time += seconds


clock = FakeClock()
config = SessionCreateConfig(ttl=60.0, idle_timeout=30.0)
store = SessionStore(default_config=config, clock=clock)

session = store.create_session("user-1")

clock.advance(25.0)
info = store.get_session(session.session_id)

clock.advance(35.0)
info = store.get_session(session.session_id)

clock.advance(65.0)
from solocoder_py.session_store import SessionExpiredError
try:
    store.get_session(session.session_id)
except SessionExpiredError:
    print("会话已过期")
```
