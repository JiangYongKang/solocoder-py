# 可过期分布式锁域模块

## 模块功能

本模块实现了基于内存数据结构模拟的可过期分布式锁，支持以下核心能力：

1. **锁的获取与释放**：客户端通过 `client_id` 和 `lock_name` 竞争获取锁，获取成功返回栅栏令牌；释放时需校验令牌，不匹配则拒绝。
2. **栅栏令牌（Fence Token）机制**：每次成功获取锁时生成单调递增令牌，持有更大令牌值的请求方拥有更高操作权限，防止旧持有者延迟写操作覆盖新数据。
3. **租约自动过期**：锁具有租约过期时间，超过时间未续约的锁自动失效，其他客户端可重新竞争。
4. **租约续约**：持有者可在租期内主动续约延长持有时间，续约需校验令牌和持有者身份。
5. **可重入语义**：同一 `client_id` 对同一 `lock_name` 可多次获取锁，内部维护重入计数；只有计数归零时锁才真正释放。

## 核心类职责

### exceptions.py

| 类名 | 职责 |
|------|------|
| `LockError` | 锁模块异常基类 |
| `LockNotAcquiredError` | 获取锁失败（被其他客户端持有且无超时） |
| `LockNotHeldError` | 锁未被持有（释放/续约时）或持有者身份不匹配 |
| `InvalidFenceTokenError` | 栅栏令牌校验失败 |
| `LockExpiredError` | 锁已过期（释放/续约时） |
| `LockAcquisitionTimeoutError` | 带超时获取锁超时未成功 |

### models.py

| 类名 | 职责 |
|------|------|
| `LockState` | 锁状态枚举：`FREE`（空闲）、`HELD`（被持有）、`EXPIRED`（已过期） |
| `LockEntry` | 锁条目数据模型，记录锁名称、状态、持有者、栅栏令牌、重入计数、租约过期时间等，提供获取、重入、释放、续约等状态变更方法 |

### manager.py

| 类名 | 职责 |
|------|------|
| `DistributedLockManager` | 分布式锁管理器，线程安全，维护所有锁的内存存储，提供锁的获取、尝试获取、释放、续约、令牌校验、锁信息查询、强制释放等操作 |

## 锁生命周期

```
                    acquire() 成功
     ┌──────────────────────────────────────────┐
     │                                          ▼
┌─────────┐  acquire() 成功              ┌─────────┐
│  FREE   │ ──────────────────────────►  │  HELD   │
└─────────┘                              └────┬────┘
     ▲                                       │
     │                                       │ lease 到期
     │                                       ▼
     │                                 ┌───────────┐
     │                                 │  EXPIRED  │
     │                                 └─────┬─────┘
     │                                       │
     │           新客户端 acquire()          │
     └───────────────────────────────────────┘

注：HELD 状态下可多次 reenter() 增加重入计数，
    或 renew() 延长租约；release() 每次递减重入计数，
    计数归零后回到 FREE。
```

### 状态转移说明

| 当前状态 | 触发事件 | 下一状态 | 说明 |
|---------|---------|---------|------|
| FREE | `acquire()` 成功 | HELD | 新持有者获取锁，分配新栅栏令牌 |
| HELD | 持有者 `acquire()`（重入） | HELD | 重入计数 +1，续租 |
| HELD | `release()` 且计数 > 1 | HELD | 重入计数 -1，仍被持有 |
| HELD | `release()` 且计数 = 1 | FREE | 完全释放锁 |
| HELD | `renew()` 成功 | HELD | 延长租约过期时间 |
| HELD | 租约到期 | EXPIRED | 锁超时失效 |
| EXPIRED | `acquire()`（任何客户端） | HELD | 原锁被清理，新持有者获取 |
| EXPIRED | `release()` / `renew()` | FREE | 触发 `LockExpiredError` 并清理 |

## 栅栏令牌机制

### 设计背景

在分布式环境中，网络延迟或 GC 停顿可能导致原锁持有者在租约过期后仍然认为自己持有锁，此时它发起的写操作可能已经被新持有者覆盖，造成数据不一致。

### 工作原理

1. **单调递增**：`DistributedLockManager` 内部维护一个全局递增的计数器。每次有客户端成功获取锁（包括重入之外的全新获取），计数器 +1 并将该值作为栅栏令牌返回。
2. **令牌校验**：释放锁、续约时服务端校验令牌，令牌不匹配则拒绝操作。
3. **资源侧防护**：业务方在对共享资源执行写操作前，可调用 `validate_fence_token()` 校验当前请求携带的令牌是否仍然是锁的最新令牌。同时，资源端可维护 `last_token`，只接受大于 `last_token` 的写请求，从根本上防止旧令牌覆盖新数据。

### 典型场景

```
时间轴：
T0: Client-A 获取锁，得到 fence_token=10
T1: Client-A 发生网络分区/GC 停顿，租约到期
T2: Client-B 获取同一把锁，得到 fence_token=11，写入资源 value=200
T3: Client-A 恢复，尝试用 token=10 写入 value=100
    → 资源端校验：10 < last_token(11)，拒绝写入
    → 数据安全，最终 value=200
```

## 使用示例

### 基本获取与释放

```python
from datetime import timedelta
from solocoder_py.lock import DistributedLockManager

manager = DistributedLockManager()

token = manager.acquire("order:123", "client-a", lease_duration=timedelta(seconds=30))
print(f"Got lock with fence token: {token}")

try:
    # 执行业务操作
    pass
finally:
    fully = manager.release("order:123", "client-a", token)
    print(f"Lock fully released: {fully}")
```

### 尝试获取（非阻塞）

```python
token = manager.try_acquire("resource-x", "client-b")
if token is not None:
    try:
        # 操作资源
        pass
    finally:
        manager.release("resource-x", "client-b", token)
else:
    print("Lock is held by another client, skipping")
```

### 带超时的获取

```python
from solocoder_py.lock import LockAcquisitionTimeoutError

try:
    token = manager.acquire(
        "resource-y", "client-c",
        timeout=timedelta(seconds=5),
        retry_interval=timedelta(milliseconds=100),
    )
except LockAcquisitionTimeoutError:
    print("Could not acquire lock within 5 seconds")
```

### 租约续约

```python
from solocoder_py.lock import InvalidFenceTokenError, LockExpiredError

token = manager.acquire("long-task", "worker-1", lease_duration=timedelta(seconds=10))

# 在长时间任务执行过程中定期续约
import time
for _ in range(5):
    time.sleep(2)
    try:
        manager.renew("long-task", "worker-1", token, lease_duration=timedelta(seconds=10))
    except (InvalidFenceTokenError, LockExpiredError) as e:
        print(f"Lost lock: {e}")
        break
```

### 可重入锁

```python
token = manager.acquire("db:conn", "client-a")
info = manager.get_lock_info("db:conn")
print(f"Reentrant count: {info.reentrant_count}")  # 1

# 同一 client 再次获取（重入）
token2 = manager.acquire("db:conn", "client-a")
assert token == token2  # 重入返回相同令牌
info = manager.get_lock_info("db:conn")
print(f"Reentrant count: {info.reentrant_count}")  # 2

# 需要释放相同次数才真正释放
manager.release("db:conn", "client-a", token)  # 计数变为 1
manager.release("db:conn", "client-a", token)  # 计数变为 0，完全释放
```

### 栅栏令牌防护资源写入

```python
class SharedResource:
    def __init__(self, lock_manager: DistributedLockManager):
        self._value = 0
        self._last_token = 0
        self._lock_mgr = lock_manager
        self._lock_name = "shared-resource"

    def update(self, new_value: int, client_id: str) -> bool:
        token = self._lock_mgr.try_acquire(self._lock_name, client_id)
        if token is None:
            return False
        try:
            return self._write(new_value, token)
        finally:
            self._lock_mgr.release(self._lock_name, client_id, token)

    def _write(self, new_value: int, token: int) -> bool:
        # 双重防护：先校验令牌是否仍然有效，再比较令牌新旧
        if not self._lock_mgr.validate_fence_token(self._lock_name, token):
            return False
        if token <= self._last_token:
            return False
        self._value = new_value
        self._last_token = token
        return True

    @property
    def value(self) -> int:
        return self._value
```

### 锁信息查询与管理

```python
# 查询锁状态
info = manager.get_lock_info("order:123")
if info:
    print(f"State: {info.state}")
    print(f"Held by: {info.client_id}")
    print(f"Fence token: {info.fence_token}")
    print(f"Reentrant count: {info.reentrant_count}")
    print(f"Remaining lease: {info.remaining_lease}")

# 检查是否被持有
assert manager.is_held("order:123") is True
assert manager.is_held_by("order:123", "client-a") is True

# 强制释放（慎用，用于管理操作）
manager.force_release("order:123")

# 清理所有锁
manager.clear()
print(f"Active locks: {manager.count()}")
```

## 运行测试

```bash
pytest tests/lock/ -v
```
