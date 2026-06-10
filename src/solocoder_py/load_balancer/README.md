# 负载均衡器模块

本模块实现了一个基于内存数据结构的负载均衡器，支持多种实例选择策略、健康状态管理、故障熔断恢复以及连接计数生命周期管理。

## 模块功能

- **多策略选址**：支持轮询（Round Robin）、加权随机（Weighted Random）和最少连接（Least Connections）三种实例选择策略，并允许按请求动态切换策略
- **实例健康状态管理**：实例可标记为健康/不健康，不健康实例不能被分配新请求，恢复健康后可重新参与调度
- **故障实例熔断剔除**：当实例连续失败达到阈值时自动熔断并从可用池剔除；熔断窗口结束后进入半开探测，探测成功再恢复可用
- **连接计数生命周期**：在最少连接策略下，分配请求时增加连接数，请求完成后正确释放连接数，避免计数泄漏导致调度偏差
- **可注入时钟**：时间来源可通过依赖注入替换，便于在测试中精确控制时间流逝
- **线程安全**：所有核心状态操作均通过 `threading.RLock` 保护，支持多线程并发访问

## 核心类职责

### SelectionStrategy
选址策略枚举。

- `ROUND_ROBIN`：轮询策略，按顺序依次选择实例
- `WEIGHTED_RANDOM`：加权随机策略，按权重比例随机选择实例
- `LEAST_CONNECTIONS`：最少连接策略，选择当前活跃连接数最少的实例

### InstanceHealth
实例健康状态枚举。

- `HEALTHY`：健康状态，实例可正常处理请求
- `UNHEALTHY`：不健康状态，实例被手动标记为不可用

### CircuitState
熔断状态枚举（每个实例独立维护）。

- `CLOSED`：熔断器关闭，实例正常参与调度
- `OPEN`：熔断器打开，实例连续失败过多，暂时不可用
- `HALF_OPEN`：半开状态，熔断窗口结束，允许少量探测请求验证实例是否恢复

### LoadBalancerConfig
负载均衡器全局配置数据类，构造时自动校验参数合法性。

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `default_strategy` | SelectionStrategy | ROUND_ROBIN | 默认选址策略 |
| `failure_threshold` | int | 3 | 连续失败熔断阈值，必须 > 0 |
| `recovery_timeout_seconds` | float | 30.0 | 熔断恢复超时时间（秒），必须 > 0 |
| `half_open_max_probes` | int | 1 | 半开状态最大探测请求数，必须 > 0 |

### InstanceConfig
单个实例的注册配置数据类，构造时自动校验参数合法性。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `instance_id` | str | 实例唯一标识，不能为空 |
| `address` | str | 实例地址（可选） |
| `weight` | int | 实例权重，必须 >= 0；权重为 0 的实例不参与调度 |

### Instance
后端实例的状态数据类。

核心字段：
- `instance_id`：实例唯一标识
- `address`：实例地址
- `weight`：实例权重
- `health`：健康状态（InstanceHealth）
- `circuit_state`：熔断器状态（CircuitState）
- `active_connections`：当前活跃连接数
- `consecutive_failures`：连续失败计数
- `circuit_opened_at`：熔断器打开时间戳
- `half_open_probe_count`：半开状态已发送探测请求数
- `allocated_requests`：已分配请求 ID 集合（用于连接释放校验）

核心方法：
- `is_available()`：判断实例是否可用于正常调度（健康+熔断关闭+权重>0）
- `is_available_for_half_open()`：判断实例是否可用于半开探测
- `mark_healthy()` / `mark_unhealthy()`：手动设置健康状态
- `record_success()`：记录请求成功，重置连续失败计数；半开状态下成功则关闭熔断器
- `record_failure(now, failure_threshold)`：记录请求失败，返回是否触发熔断
- `try_transition_to_half_open(now, recovery_timeout)`：尝试从 OPEN 转为 HALF_OPEN
- `acquire_connection(request_id)`：获取连接，增加活跃连接计数并记录请求 ID
- `release_connection(request_id)`：释放连接，减少活跃连接计数；返回是否成功释放
- `clone()`：深拷贝

### Lease
请求租约类，用于管理请求分配后的生命周期。

通过上下文管理器使用：
```python
with lb.acquire() as lease:
    # 使用 lease.instance_id 处理请求
    # 若上下文内抛出异常，自动标记为失败
```

核心属性与方法：
- `instance_id`：被分配的实例 ID
- `request_id`：请求唯一 ID
- `release(success=True)`：显式释放租约，传入请求是否成功

### LoadBalancer
负载均衡器主类。

核心方法：
- `register_instance(instance_id, address="", weight=1)`：注册实例
- `register_instance_from_config(config)`：通过 InstanceConfig 注册实例
- `unregister_instance(instance_id)`：注销实例
- `mark_healthy(instance_id)` / `mark_unhealthy(instance_id)`：手动标记实例健康状态
- `get_instance(instance_id)`：获取指定实例的快照副本
- `get_all_instances()` / `get_available_instances()`：获取所有/可用实例的快照副本
- `is_registered(instance_id)`：判断实例是否已注册
- `set_strategy(strategy)`：设置全局选址策略
- `acquire(strategy=None)`：获取请求租约，可按请求指定选址策略；返回 Lease 对象

### Clock
时间来源抽象接口。

- `Clock`：抽象基类，定义 `now()` 方法
- `SystemClock`：默认实现，使用系统单调时钟 `time.monotonic()`
- `ManualClock`：手动时钟，测试专用，支持 `advance(seconds)` 推进或 `set(time)` 设置时间

## 三种选址策略

### 轮询策略 (Round Robin)
按实例列表顺序依次循环分配请求。使用内部计数器维护当前位置，每次选择后计数器加 1，对实例数取模得到索引。

特点：
- 简单公平，每个实例获得的请求数相同
- 不考虑实例权重或负载差异

### 加权随机策略 (Weighted Random)
按实例权重比例随机分配请求。使用权重前缀和 + 二分查找实现高效随机选择。

特点：
- 权重越高的实例被选中的概率越大
- 权重为 0 的实例不参与选择
- 权重相同的实例被选中概率相同

### 最少连接策略 (Least Connections)
选择当前活跃连接数最少的实例；若多个实例连接数相同，从中随机选一个。

特点：
- 感知实例负载，连接数越少的实例获得更多请求
- 连接计数在租约获取时递增，租约释放时递减
- 需要配合 `Lease` 的 `release()` 正确使用，避免计数泄漏

## 熔断与恢复流程

### 状态机流转

```
  请求成功
   ┌──────┐
   │      ▼
CLOSED ────────────────────────────────────► OPEN
  ▲                连续失败数 >= 阈值         │
  │                                             │
  │                                             │ 熔断超时
  │                                             │
  │      探测成功                                ▼
  └───────────────────── HALF_OPEN ◄───────────┘
                         探测失败 ──────────────┘
```

### 详细规则

1. **CLOSED → OPEN**：实例连续失败计数达到 `failure_threshold`，熔断器打开
2. **OPEN → HALF_OPEN**：熔断窗口超过 `recovery_timeout_seconds`，熔断器进入半开状态
3. **HALF_OPEN → CLOSED**：半开状态下探测请求全部成功，熔断器关闭，恢复正常调度
4. **HALF_OPEN → OPEN**：半开状态下任意探测请求失败，熔断器重新打开，重置熔断时间

### 调度中的熔断处理

- 处于 OPEN 状态的实例不参与正常调度
- 处于 HALF_OPEN 状态的实例优先于正常实例被选中（用于探测），但最多同时发送 `half_open_max_probes` 个探测请求
- 半开探测请求的成功/失败结果决定熔断器是恢复关闭还是重新打开

## 连接计数生命周期

### 计数递增
调用 `lb.acquire()` 成功获取 `Lease` 时，被选中实例的 `active_connections` +1，请求 ID 被记录到 `allocated_requests` 集合中。

### 计数递减
`Lease` 有两种释放方式：
1. **上下文管理器**：使用 `with lb.acquire() as lease:` 时，若代码块正常退出则标记成功，若抛出异常则标记失败；无论成功失败，连接计数都会 -1
2. **显式调用**：手动调用 `lease.release(success=True/False)`，同样会递减连接计数

### 泄漏保护
- 每个实例维护已分配请求的 ID 集合
- 尝试释放未分配的请求 ID 时，`release_connection()` 返回 False，向上抛出 `ConnectionLeakError`
- 这能帮助业务层检测连接计数泄漏问题

## 使用示例

### 基础：注册实例与轮询调度

```python
from solocoder_py.load_balancer import LoadBalancer, ManualClock, SelectionStrategy

clock = ManualClock()
lb = LoadBalancer(clock=clock)

lb.register_instance("server-1", weight=1)
lb.register_instance("server-2", weight=1)
lb.register_instance("server-3", weight=1)

for _ in range(6):
    with lb.acquire() as lease:
        print(f"Request assigned to: {lease.instance_id}")
# 输出: server-1, server-2, server-3, server-1, server-2, server-3
```

### 加权随机策略

```python
from solocoder_py.load_balancer import LoadBalancer, SelectionStrategy

lb = LoadBalancer()
lb.register_instance("server-high", weight=5)
lb.register_instance("server-low", weight=1)
lb.set_strategy(SelectionStrategy.WEIGHTED_RANDOM)

counts = {"server-high": 0, "server-low": 0}
for _ in range(6000):
    with lb.acquire() as lease:
        counts[lease.instance_id] += 1

# server-high 约 5000 次, server-low 约 1000 次
```

### 最少连接策略

```python
from solocoder_py.load_balancer import LoadBalancer, SelectionStrategy

lb = LoadBalancer()
lb.register_instance("fast-server", weight=1)
lb.register_instance("slow-server", weight=1)
lb.set_strategy(SelectionStrategy.LEAST_CONNECTIONS)

# 模拟 slow-server 上有一个长连接
lease1 = lb.acquire()
assert lease1.instance_id in ("fast-server", "slow-server")

# 后续请求会优先分配给连接数少的实例
lease2 = lb.acquire()
assert lease2.instance_id != lease1.instance_id

lease1.release()
lease2.release()
```

### 按请求动态切换策略

```python
from solocoder_py.load_balancer import LoadBalancer, SelectionStrategy

lb = LoadBalancer()  # 默认 ROUND_ROBIN
lb.register_instance("s1", weight=3)
lb.register_instance("s2", weight=1)

# 默认轮询
with lb.acquire() as lease:
    ...  # ROUND_ROBIN

# 单次请求使用加权随机
with lb.acquire(strategy=SelectionStrategy.WEIGHTED_RANDOM) as lease:
    ...  # WEIGHTED_RANDOM

# 后续又回到默认策略
with lb.acquire() as lease:
    ...  # ROUND_ROBIN
```

### 健康状态管理

```python
from solocoder_py.load_balancer import LoadBalancer, InstanceHealth

lb = LoadBalancer()
lb.register_instance("server-1")
lb.register_instance("server-2")

# 手动标记 server-1 不健康
lb.mark_unhealthy("server-1")
assert lb.get_instance("server-1").health == InstanceHealth.UNHEALTHY

# 不健康实例不会被选中
for _ in range(10):
    with lb.acquire() as lease:
        assert lease.instance_id == "server-2"

# 恢复健康
lb.mark_healthy("server-1")
assert lb.get_instance("server-1").health == InstanceHealth.HEALTHY
```

### 熔断与恢复

```python
from solocoder_py.load_balancer import (
    LoadBalancer, LoadBalancerConfig, ManualClock, CircuitState
)

clock = ManualClock()
config = LoadBalancerConfig(
    failure_threshold=2,
    recovery_timeout_seconds=10.0,
    half_open_max_probes=1,
)
lb = LoadBalancer(config=config, clock=clock)
lb.register_instance("server-1")

# 连续失败触发熔断
with lb.acquire() as lease:
    pass  # 隐式成功
lease_fail_1 = lb.acquire()
lease_fail_1.release(success=False)  # 第 1 次失败
lease_fail_2 = lb.acquire()
lease_fail_2.release(success=False)  # 第 2 次失败 → 熔断

assert lb.get_instance("server-1").circuit_state == CircuitState.OPEN

# 熔断期间实例不可用
# ... lb.acquire() 会抛 NoAvailableInstanceError（如果只有这一个实例）

# 等待熔断恢复超时
clock.advance(10.0)

# 进入半开状态，允许探测
with lb.acquire() as lease:
    assert lease.instance_id == "server-1"
    # 上下文正常退出 → 探测成功 → 熔断器关闭

assert lb.get_instance("server-1").circuit_state == CircuitState.CLOSED
```

### 显式控制请求成功/失败

```python
from solocoder_py.load_balancer import LoadBalancer

lb = LoadBalancer()
lb.register_instance("server-1")

# 方式 1：使用上下文管理器，自动根据异常判断
try:
    with lb.acquire() as lease:
        # 调用远程服务
        raise RuntimeError("remote error")
except RuntimeError:
    pass  # lease 自动标记为失败

# 方式 2：手动控制
lease = lb.acquire()
try:
    # 调用远程服务
    result = "ok"
    lease.release(success=True)
except Exception:
    lease.release(success=False)
    raise
```

### 权重为零的实例

```python
from solocoder_py.load_balancer import LoadBalancer

lb = LoadBalancer()
lb.register_instance("disabled", weight=0)
lb.register_instance("active", weight=1)

# 权重为 0 的实例不参与调度
for _ in range(10):
    with lb.acquire() as lease:
        assert lease.instance_id == "active"
```
