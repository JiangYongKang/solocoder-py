# TCP 连接池模块

## 模块功能

本模块实现了基于内存数据结构模拟的 TCP 连接池，支持以下核心能力：

1. **连接池基本操作**：支持从连接池借用（borrow）连接和归还（return）连接。连接池在创建时指定目标地址和最大连接数。借用时如果池内有空闲连接则直接返回，如果池内连接数未达上限则创建新连接，如果已达上限则支持阻塞等待或立即返回失败（可配置）。

2. **空闲连接驱逐**：连接池定期扫描空闲连接，超过空闲超时时间的连接自动关闭并从池中移除。驱逐周期和空闲超时均可配置。被驱逐的连接如果正在被外部持有（已借出未归还），不会被驱逐。

3. **最大存活时间限制**：每个连接从创建开始记录存活时间，超过最大存活时间的连接在归还时直接关闭而非放回池中，无论该连接是否健康。正在被借用的连接不受存活时间限制，只有归还时才检查。

4. **借出前健康检查**：连接在借出给调用方之前，执行一次健康检查（检查连接状态）。健康检查失败则丢弃该连接并从池中移除，尝试下一个可用连接。如果所有可用连接健康检查均失败且无法创建新连接，则返回错误。

## 核心类职责

### exceptions.py

| 类名 | 职责 |
|------|------|
| `ConnPoolError` | 连接池模块异常基类 |
| `PoolClosedError` | 连接池已关闭时仍尝试借用连接 |
| `PoolExhaustedError` | 连接池已耗尽（达到最大连接数且无空闲连接） |
| `ConnectionNotFoundError` | 归还的连接不属于当前连接池 |
| `ConnectionClosedError` | 连接已关闭时仍尝试操作 |
| `HealthCheckFailedError` | 健康检查失败 |

### models.py

| 类名 | 职责 |
|------|------|
| `PoolWaitStrategy` | 等待策略枚举：`BLOCK`（阻塞等待）、`FAIL`（立即失败） |
| `ConnectionState` | 连接状态枚举：`IDLE`（空闲）、`BORROWED`（已借出）、`CLOSED`（已关闭） |
| `PoolStats` | 连接池统计数据模型，包括总连接数、空闲连接数、已借出连接数、已关闭连接数、借用次数、归还次数、驱逐次数、健康检查失败次数等 |
| `PoolConfig` | 连接池配置数据模型，包含最大连接数、等待策略、等待超时、空闲超时、驱逐周期、最大存活时间、是否开启借出前健康检查等配置项 |

### clock.py

| 类名 | 职责 |
|------|------|
| `Clock` | 时钟抽象基类，定义 `now()` 和 `sleep()` 两个抽象方法 |
| `RealClock` | 真实时钟实现，使用系统单调时间，用于生产环境 |
| `ManualClock` | 手动时钟实现，用于单线程测试环境。可通过 `advance()` 或 `set_time()` 手动推进时间，便于测试时间相关逻辑（如空闲驱逐、最大存活时间等）而无需真实等待 |

### connection.py

| 类名 | 职责 |
|------|------|
| `MockTCPConnection` | 模拟 TCP 连接类，使用内存数据结构模拟 TCP 连接的生命周期。支持连接创建、关闭、健康检查、发送/接收数据等操作。每个连接有唯一的 `conn_id`，记录创建时间、上次空闲开始时间、上次借出时间、借用次数等状态 |

### pool.py

| 类名 | 职责 |
|------|------|
| `ConnectionPool` | 连接池核心实现类。提供 `borrow()`（借用连接）、`return_conn()`（归还连接）、`evict_now()`（手动触发驱逐）、`close()`（关闭连接池）等主要方法。内部维护空闲连接队列、已借出连接集合，通过线程锁保证并发安全，支持条件变量实现阻塞等待 |

## 连接池生命周期模型

连接池的完整生命周期包括以下阶段：

### 1. 创建（Creation）

连接池通过 `ConnectionPool(host, port, config, clock)` 构造函数创建。创建时：
- 初始化空闲连接队列（空）和已借出连接集合（空）
- 如果配置了驱逐周期（`eviction_interval > 0`），启动后台驱逐线程
- 初始状态为"未关闭"

### 2. 借用（Borrow）

调用 `borrow()` 方法从连接池获取连接，流程如下：

```
调用 borrow()
    │
    ├─► 连接池已关闭？ ──是──► 抛出 PoolClosedError
    │
    ├─► 有空闲连接？
    │      │
    │      ├─是──► 从空闲队列取出连接
    │      │        │
    │      │        ├─► 开启健康检查？ ──是──► 健康检查失败？
    │      │        │                           │
    │      │        │                           ├─是──► 销毁连接，继续尝试下一个
    │      │        │                           └─否──► 标记为已借出，返回连接
    │      │        │
    │      │        └─► 不检查健康 ──► 标记为已借出，返回连接
    │      │
    │      └─否──► 未达最大连接数？
    │                      │
    │                      ├─是──► 创建新连接，标记为已借出，返回
    │                      │
    │                      └─否──► 等待策略？
    │                                      │
    │                                      ├─FAIL ──► 抛出 PoolExhaustedError
    │                                      │
    │                                      └─BLOCK ──► 等待归还通知，超时后抛出 PoolExhaustedError
```

### 3. 归还（Return）

调用 `return_conn(conn)` 方法将连接归还到连接池，流程如下：

```
调用 return_conn(conn)
    │
    ├─► 连接池已关闭？ ──是──► 销毁连接，返回
    │
    ├─► 连接在已借出集合中？ ──否──► 抛出 ConnectionNotFoundError
    │
    ├─► 连接已关闭？ ──是──► 销毁连接，通知等待者，返回
    │
    ├─► 超过最大存活时间？ ──是──► 销毁连接，通知等待者，返回
    │
    └─► 加入空闲队列，通知等待者
```

### 4. 驱逐（Eviction）

驱逐由后台线程定期执行（或手动调用 `evict_now()`），流程如下：

```
执行驱逐
    │
    ├─► 遍历所有空闲连接
    │
    └─► 对每个空闲连接：
            ├─► 空闲时间 >= 空闲超时？
            │       │
            │       ├─是──► 从空闲队列移除，销毁连接
            │       └─否──► 保留
            │
            └─► 已借出的连接不受影响
```

### 5. 关闭（Close）

调用 `close()` 方法关闭连接池，流程如下：

```
调用 close()
    │
    ├─► 已经关闭？ ──是──► 直接返回
    │
    ├─► 标记为已关闭
    │
    ├─► 停止驱逐线程
    │
    ├─► 关闭所有空闲连接
    │
    ├─► 关闭所有已借出连接
    │
    └─► 通知所有等待者（抛出 PoolClosedError）
```

### 生命周期状态转移图

```
                    borrow()
     ┌───────────────────────────────────┐
     │                                   ▼
  ┌──────┐  return_conn()            ┌─────────┐
  │ IDLE │ ◄──────────────────────── │ BORROWED│
  └──────┘                           └─────────┘
     │                                   │
     │ 空闲超时/关闭/超存活时间            │ 关闭/超存活时间(归还时)
     ▼                                   ▼
  ┌───────────────────────────────────────────┐
  │                  CLOSED                    │
  └───────────────────────────────────────────┘
```

## 健康检查策略

### 借出前健康检查

当 `PoolConfig.health_check_on_borrow = True` 时，每次从空闲队列取出连接后、返回给调用方之前，会执行一次健康检查。

**检查方式**：调用连接的 `health_check()` 方法。对于模拟连接，检查内部 `_healthy` 标志和 `_closed` 状态。

**检查失败的处理**：
1. 立即关闭并销毁该连接
2. 健康检查失败计数 +1
3. 继续尝试从空闲队列取下一个连接
4. 如果所有空闲连接都检查失败且未达到最大连接数，则创建新连接
5. 如果所有空闲连接都检查失败且已达到最大连接数，则返回错误

**异常安全**：如果 `health_check()` 方法抛出异常，连接会被视为不健康并销毁，不会导致连接池崩溃。

## 使用示例

### 基本使用：借用和归还

```python
from solocoder_py.connpool import ConnectionPool, PoolConfig

config = PoolConfig(max_size=10)
pool = ConnectionPool(host="localhost", port=6379, config=config)

# 借用连接
conn = pool.borrow()
print(f"Borrowed: {conn.conn_id}")

# 使用连接
conn.send(b"PING")
resp = conn.recv()
print(f"Response: {resp}")

# 归还连接
pool.return_conn(conn)

# 关闭连接池
pool.close()
```

### 上下文管理器

```python
from solocoder_py.connpool import ConnectionPool, PoolConfig

config = PoolConfig(max_size=5)

with ConnectionPool("localhost", 6379, config) as pool:
    conn = pool.borrow()
    # 使用连接...
    pool.return_conn(conn)
# 离开 with 块时自动关闭连接池
```

### 配置等待策略：立即失败

```python
from solocoder_py.connpool import (
    ConnectionPool, PoolConfig, PoolWaitStrategy, PoolExhaustedError
)

config = PoolConfig(
    max_size=2,
    wait_strategy=PoolWaitStrategy.FAIL,
)

pool = ConnectionPool("localhost", 6379, config)

conn1 = pool.borrow()
conn2 = pool.borrow()

try:
    conn3 = pool.borrow()
except PoolExhaustedError as e:
    print(f"Pool exhausted: {e}")

pool.return_conn(conn1)
pool.return_conn(conn2)
pool.close()
```

### 配置等待策略：阻塞等待

```python
from solocoder_py.connpool import (
    ConnectionPool, PoolConfig, PoolWaitStrategy
)

config = PoolConfig(
    max_size=2,
    wait_strategy=PoolWaitStrategy.BLOCK,
    wait_timeout=5.0,  # 最多等待 5 秒
)

pool = ConnectionPool("localhost", 6379, config)

# 借用连接... 如果池满会阻塞等待直到有连接归还或超时
conn = pool.borrow()
pool.return_conn(conn)
pool.close()
```

### 空闲连接驱逐

```python
from solocoder_py.connpool import (
    ConnectionPool, PoolConfig, ManualClock
)

# 使用手动时钟便于测试
clock = ManualClock()
config = PoolConfig(
    max_size=10,
    idle_timeout=60.0,      # 空闲超过 60 秒被驱逐
    eviction_interval=30.0,  # 每 30 秒检查一次
)

pool = ConnectionPool("localhost", 6379, config, clock)

# 创建一些连接
conns = [pool.borrow() for _ in range(3)]
for c in conns:
    pool.return_conn(c)

print(f"Idle connections: {pool.idle_size()}")  # 3

# 推进时间 50 秒
clock.advance(50.0)
pool.evict_now()  # 手动触发驱逐
print(f"After 50s: {pool.idle_size()}")  # 3 (未超时)

# 再推进 15 秒（总共 65 秒）
clock.advance(15.0)
pool.evict_now()
print(f"After 65s: {pool.idle_size()}")  # 0 (全部超时被驱逐)

pool.close()
```

### 最大存活时间

```python
from solocoder_py.connpool import (
    ConnectionPool, PoolConfig, ManualClock
)

clock = ManualClock()
config = PoolConfig(
    max_size=5,
    max_lifetime=300.0,  # 连接最多存活 300 秒
    eviction_interval=0,
)

pool = ConnectionPool("localhost", 6379, config, clock)

conn = pool.borrow()
conn_id = conn.conn_id
pool.return_conn(conn)

# 推进时间 200 秒
clock.advance(200.0)
conn2 = pool.borrow()
print(f"Same connection: {conn2.conn_id == conn_id}")  # True
pool.return_conn(conn2)

# 再推进 150 秒（总共 350 秒，超过 300 秒最大存活时间）
clock.advance(150.0)
conn3 = pool.borrow()
# 归还时会检查存活时间，超过则关闭
pool.return_conn(conn3)
print(f"Connection closed: {conn3.is_closed}")  # True
print(f"Pool idle size: {pool.idle_size()}")  # 0

pool.close()
```

### 健康检查

```python
from solocoder_py.connpool import (
    ConnectionPool, PoolConfig
)

config = PoolConfig(
    max_size=5,
    health_check_on_borrow=True,
    eviction_interval=0,
)

pool = ConnectionPool("localhost", 6379, config)

conn = pool.borrow()
conn.set_unhealthy()  # 模拟连接损坏
pool.return_conn(conn)

# 下次借用时，健康检查会发现连接不健康，自动丢弃并创建新连接
conn2 = pool.borrow()
print(f"New connection: {conn2.conn_id != conn.conn_id}")  # True
print(f"Old connection closed: {conn.is_closed}")  # True
print(f"Health check failures: {pool.stats.health_check_failed_count}")  # 1

pool.return_conn(conn2)
pool.close()
```

### 查看连接池统计

```python
from solocoder_py.connpool import ConnectionPool, PoolConfig

config = PoolConfig(max_size=10)
pool = ConnectionPool("localhost", 6379, config)

# ... 执行一些操作 ...

stats = pool.stats
print(f"Total connections created: {stats.total_connections}")
print(f"Idle: {stats.idle_connections}")
print(f"Borrowed: {stats.borrowed_connections}")
print(f"Closed: {stats.closed_connections}")
print(f"Borrow count: {stats.borrow_count}")
print(f"Return count: {stats.return_count}")
print(f"Evicted count: {stats.evicted_count}")
print(f"Health check failures: {stats.health_check_failed_count}")

pool.close()
```

## 实现设计说明

### 线程安全

连接池的所有公共方法都通过内部的 `threading.Lock` 保证线程安全。阻塞等待使用 `threading.Condition` 实现，归还连接时会通知等待的线程。

### 可注入时钟

通过可注入的 `Clock` 抽象，使得时间相关的逻辑（空闲驱逐、最大存活时间）可以在单线程测试环境中通过手动推进时间进行精确测试，无需真实等待。

### 模拟连接

使用 `MockTCPConnection` 模拟 TCP 连接的生命周期，不依赖真实网络连接，便于单元测试和学习连接池原理。

## 运行测试

```bash
pytest tests/connpool/ -v
```
