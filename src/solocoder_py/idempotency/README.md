# Idempotency 模块

幂等键存储域，用于保证相同请求在重复执行时产生相同的副作用和响应结果。使用内存数据结构存储幂等记录，适合单机场景下的幂等性保障。

## 功能概述

- **幂等键生命周期管理**：完整记录请求从处理中、成功、失败到过期的状态流转
- **请求指纹绑定**：首次使用幂等键时绑定请求指纹，后续不同指纹请求会被拒绝
- **并发首请求胜出**：多线程同时使用相同幂等键时，仅允许一个进入处理状态
- **结果回放**：已成功记录可直接返回原始响应，失败结果支持三种回放策略
- **TTL 过期清理**：记录超期后在下一次访问时惰性过期，释放键空间供新请求使用

## 核心类职责

### IdempotencyState
枚举类型，定义幂等记录的四种状态：
- `PROCESSING`：处理中，表示请求正在执行业务逻辑
- `SUCCESS`：成功，请求处理完成并记录了响应数据
- `FAILED`：失败，请求处理过程中发生错误并记录了错误信息
- `EXPIRED`：已过期，记录超过 TTL 不再有效

### FailureReplayPolicy
枚举类型，定义失败结果的回放策略：
- `REJECT`：拒绝访问，已失败的记录再次访问时抛出异常
- `REPLAY`：回放失败，返回原始失败结果，不重试
- `RETRY`：允许重试，将记录重置为处理中状态，允许重新执行

### IdempotencyRecord
数据类，封装单条幂等记录的完整信息：
- `key`：幂等键，业务方传入的唯一标识
- `request_fingerprint`：请求指纹，用于绑定并校验请求内容一致性
- `state`：当前处理状态
- `response_data`：成功时的响应结果
- `error_message`：失败时的错误信息
- `created_at`：记录创建时间
- `expires_at`：记录过期时间

提供状态转换方法 `mark_success()`、`mark_failed()`、`mark_expired()`，以及 TTL 刷新 `refresh_ttl()` 和指纹校验 `fingerprint_matches()`。

### IdempotencyResult
操作结果封装，返回给调用方：
- `record`：当前幂等记录快照
- `is_replay`：是否为回放（已有结果直接返回）
- `should_execute`：是否需要执行实际业务逻辑

### IdempotencyStore
幂等存储核心类，使用内存字典存储记录，提供线程安全的访问接口。

主要方法：

| 方法 | 说明 |
|------|------|
| `begin_request(key, fingerprint, ttl)` | 开始幂等请求，决定是否需要执行业务 |
| `complete_success(key, fingerprint, data)` | 标记请求处理成功并记录响应 |
| `complete_failure(key, fingerprint, error)` | 标记请求处理失败并记录错误 |
| `execute_with_idempotency(key, fingerprint, op)` | 便捷封装：自动完成 begin/complete 流程 |
| `get_record(key)` | 查询记录快照（只读） |
| `exists(key)` | 判断键是否存在 |
| `invalidate(key)` | 主动失效指定键 |
| `clear()` | 清空所有记录 |
| `cleanup_expired()` | 主动清理所有过期记录 |

## 幂等键生命周期

```
                首次访问
  (不存在) ────────────────────► PROCESSING
                                   │
                                   ├──── 业务成功 ────► SUCCESS ◄─── 同指纹再次访问：结果回放
                                   │                                          │
                                   ├──── 业务失败 ────► FAILED                │
                                   │                    │                     │
                                   │                    ├─ REJECT: 抛异常     │
                                   │                    ├─ REPLAY: 返回失败   │
                                   │                    └─ RETRY: 回到PROCESSING
                                   │                                          │
                                   └──── 超过 TTL ────► EXPIRED ◄────────────┘
                                                           │
                                                           └─ 再次访问：创建新记录
```

### 生命周期说明

1. **创建**：首次访问幂等键时创建记录，状态为 `PROCESSING`，同时绑定请求指纹
2. **成功**：业务处理成功后调用 `complete_success()`，状态转为 `SUCCESS`，记录响应数据
3. **失败**：业务处理失败后调用 `complete_failure()`，状态转为 `FAILED`，记录错误信息
4. **过期**：超过 TTL 后，记录在下一次访问时被惰性标记为 `EXPIRED`
5. **重建**：已过期的键再次被访问时，旧记录被替换为全新的 `PROCESSING` 记录

## 并发处理流程

当多个线程同时使用相同的幂等键和指纹时：

```
线程 A ── begin_request ──► 获取锁，创建 PROCESSING 记录，返回 should_execute=True
线程 B ── begin_request ──► 获取锁，发现 PROCESSING，释放锁，等待 Condition
  ...
线程 A ── 执行业务逻辑 ──► complete_success()，通知所有等待线程
线程 B ── 被唤醒 ─────────► 重新检查，发现 SUCCESS，返回回放结果
```

并发规则：
- **首请求胜出**：第一个进入的线程获得执行权
- **同指纹等待**：相同指纹的后续请求等待首请求完成，然后读取结果
- **不同指纹拒绝**：不同指纹的请求立即抛出 `IdempotencyKeyMismatchError`
- **超时机制**：等待超过 `wait_timeout` 时抛出 `IdempotencyKeyConflictError`

## 快速使用

```python
from solocoder_py.idempotency import IdempotencyStore, FailureReplayPolicy
from datetime import timedelta

store = IdempotencyStore(
    default_ttl=timedelta(hours=24),
    failure_replay_policy=FailureReplayPolicy.REJECT,
)

# 方式一：手动控制
result = store.begin_request("order-123", "sha256-of-request")
if result.should_execute:
    try:
        data = create_order(...)
        store.complete_success("order-123", "sha256-of-request", data)
    except Exception as e:
        store.complete_failure("order-123", "sha256-of-request", str(e))
        raise

# 方式二：使用便捷封装
result = store.execute_with_idempotency(
    "order-123",
    "sha256-of-request",
    lambda: create_order(...),
)
```
