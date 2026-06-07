# Idempotency 模块

幂等键存储域，用于保证相同请求在重复执行时产生相同的副作用和响应结果。使用内存数据结构存储幂等记录，适合单机场景下的幂等性保障。

## 功能概述

- **幂等键生命周期管理**：完整记录请求从处理中、成功、失败到过期的状态流转
- **请求指纹绑定**：首次使用幂等键时绑定请求指纹，后续不同指纹请求会被拒绝
- **并发首请求胜出**：多线程同时使用相同幂等键时，仅允许一个进入处理状态
- **结果回放**：已成功记录可直接返回原始响应，失败结果支持三种回放策略
- **TTL 过期清理**：记录超期后在下一次访问时惰性过期，释放键空间供新请求使用
- **可注入时钟**：通过 `Clock` 抽象统一时间源，测试中可用 `ManualClock` 精确控制时间

## 核心类职责

### Clock / SystemClock / ManualClock

时钟抽象，与 `ratelimiter`、`circuit_breaker` 等模块保持一致的接口：

- `Clock`：抽象基类，定义 `now() -> float` 方法，返回单调递增的秒级时间戳
- `SystemClock`：生产环境默认实现，基于 `time.monotonic()`
- `ManualClock`：测试专用实现，支持 `advance(seconds)` 手动推进时间和 `set(value)` 直接设定时间，无需 `sleep()` 等待真实时间流逝

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

数据类，封装单条幂等记录的完整信息，所有时间字段使用 **float 秒级时间戳**：
- `key`：幂等键，业务方传入的唯一标识
- `request_fingerprint`：请求指纹，用于绑定并校验请求内容一致性
- `state`：当前处理状态
- `response_data`：成功时的响应结果
- `error_message`：失败时的错误信息
- `created_at`：记录创建时间戳（float 秒）
- `expires_at`：记录过期时间戳（float 秒）

关键方法：
- `mark_success(data)` / `mark_failed(msg)` / `mark_expired()`：状态转换
- `refresh_ttl(ttl_seconds, clock)`：刷新 TTL
- `fingerprint_matches(fp)`：校验指纹
- `is_expired(clock)` / `remaining_ttl(clock)`：基于可注入时钟计算过期状态
- **`snapshot()`**：返回字段完全相同的独立副本，用于对外暴露只读视图，**避免 `__post_init__` 对过期记录的校验异常**

### IdempotencyResult

操作结果封装，返回给调用方：
- `record`：当前幂等记录的快照（独立副本，不影响内部状态）
- `is_replay`：是否为回放（已有结果直接返回）
- `should_execute`：是否需要执行实际业务逻辑

### IdempotencyStore

幂等存储核心类，使用内存字典存储记录，提供线程安全的访问接口。

可配置参数（均为 float 秒）：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `default_ttl_seconds` | `86400.0`（24小时） | 新记录默认 TTL |
| `failure_replay_policy` | `REJECT` | 失败结果回放策略 |
| `wait_timeout_seconds` | `30.0` | 并发等待超时 |
| `wait_poll_interval_seconds` | `0.05` | 轮询检查间隔 |
| `_clock` | `SystemClock()` | 注入的时钟实例，测试中替换为 `ManualClock` |

主要方法：

| 方法 | 说明 |
|------|------|
| `begin_request(key, fingerprint, ttl_seconds=None)` | 开始幂等请求，决定是否需要执行业务 |
| `complete_success(key, fingerprint, data)` | 标记请求处理成功并记录响应 |
| `complete_failure(key, fingerprint, error)` | 标记请求处理失败并记录错误 |
| `execute_with_idempotency(key, fingerprint, op, ttl_seconds=None)` | 便捷封装：自动完成 begin/complete 流程 |
| `get_record(key)` | 查询记录快照（只读，返回独立副本） |
| `exists(key)` | 判断键是否存在 |
| `invalidate(key)` | 主动失效指定键 |
| `clear()` | 清空所有记录 |
| `cleanup_expired()` | 主动清理所有过期记录，返回清理数量 |

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

## 并发处理流程（Event 通知机制）

> **并发安全修复说明**：早期实现使用 `threading.Condition`，在释放 `_global_lock` 到获取 `condition` 锁之间存在竞态窗口——若另一线程在此期间完成 `complete_success()` 并发出 `notify_all()`，等待线程会错过通知，导致永久阻塞。
>
> 现已改为每个 `_RecordHolder` 持有一个 `threading.Event`（`ready`），配合轮询检查，彻底消除竞态：
> - `complete_success()` / `complete_failure()` 在持有 `_global_lock` 的状态下直接调用 `event.set()`，无中间窗口
> - 等待线程每次循环在锁内读取最新状态，若仍为 `PROCESSING` 则调用 `event.wait(timeout=poll_interval)`
> - `Event` 的语义是**一次性信号**：即使 `set()` 发生在 `wait()` 之前，`wait()` 也会立即返回 `True`，不会丢失通知

```
线程 A ── begin_request ──► [持有 _global_lock] 创建 PROCESSING 记录，event=未就绪
                                                        │
线程 B ── begin_request ──► [持有 _global_lock] 发现 PROCESSING，读取 event 引用，释放锁
                                                        │
线程 B ── event.wait(poll_interval) ◄────── 线程 A ── complete_success() ── [持有 _global_lock] 设置 state=SUCCESS + event.set()
            │                                                    │
            └─ event 已被 set()，立即返回 ──► [下一轮循环持有 _global_lock] 读取 state=SUCCESS，返回回放结果
```

并发规则：
- **首请求胜出**：第一个进入的线程获得执行权
- **同指纹等待**：相同指纹的后续请求等待首请求完成，然后读取结果
- **不同指纹拒绝**：不同指纹的请求立即抛出 `IdempotencyKeyMismatchError`
- **超时机制**：等待超过 `wait_timeout_seconds` 时抛出 `IdempotencyKeyConflictError`

## 时钟注入与测试

所有时间计算均通过可注入的 `Clock` 接口进行，测试中使用 `ManualClock` 精确控制时间流逝，无需 `sleep()` 等待真实时间：

```python
from solocoder_py.idempotency import IdempotencyStore, ManualClock

clock = ManualClock(start_time=0.0)
store = IdempotencyStore(
    default_ttl_seconds=60.0,
    _clock=clock,
)

store.begin_request("k", "fp")
store.complete_success("k", "fp", {"data": 1})

# 无需 sleep，直接推进时钟
clock.advance(61.0)

# 立即观测到过期效果
result = store.begin_request("k", "fp")
assert result.should_execute is True  # TTL 已过期，允许重新处理
```

## 过期记录查询行为

`get_record(key)` 返回的是 **`IdempotencyRecord.snapshot()` 产生的独立副本**：

- 对外暴露的记录与内部存储完全隔离，调用方修改副本不会影响 Store 内部状态
- 对于已过期的记录（`state == EXPIRED`，且 `expires_at <= created_at`），`snapshot()` 通过构造同状态副本时 **跳过 `expires_at > created_at` 校验**，确保查询过期记录不会抛出 `ValueError`
- 返回的 `EXPIRED` 记录保留原始 `created_at` 和 `expires_at` 字段，便于排查

## 快速使用

```python
from solocoder_py.idempotency import IdempotencyStore, FailureReplayPolicy

store = IdempotencyStore(
    default_ttl_seconds=86400.0,
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
