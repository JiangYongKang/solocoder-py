# 法定人数读写协调器域模块 (Quorum Read/Write Coordinator)

## 模块功能

本模块实现了基于内存数据结构的法定人数（Quorum）读写协调器域逻辑，模拟分布式系统中多副本数据的一致性读写机制，包括：

1. **法定人数写入（Quorum Write）**：写入操作向 N 个副本发起并发写入，需要至少 W 个副本确认成功才算写入成功。写入时附带单调递增的版本号，每个 key 的版本号随写入递增。
2. **法定人数读取（Quorum Read）**：读取操作向 N 个副本发起读取，需要至少 R 个副本响应。通过 W+R>N 保证每次读取至少能读到一个最新写入的数据，从 R 个响应中返回版本号最高的数据。
3. **读修复（Read Repair）**：读取时若发现某些副本版本落后或数据缺失，自动将最新版本数据写回到版本落后的副本，异步修复副本间的数据不一致。
4. **版本冲突裁决（Version Conflict Resolution）**：当多个写入并发修改同一个 key 导致副本间出现版本冲突时，通过"高版本号胜出 + 最后写入胜出（Last-Write-Wins）"策略裁决冲突，并将最终获胜版本写回所有可达副本。
5. **副本状态查询与故障模拟**：支持查询每个副本存储的数据、当前版本号、读写成功率和延迟统计；支持手动标记副本为不可达以模拟网络分区、节点宕机等故障场景。

## 核心类职责

### models.py

| 类名 | 职责 |
|------|------|
| `ReplicaStatus` | 枚举类型，定义副本两种状态：ONLINE（在线）、UNREACHABLE（不可达） |
| `StoredValue` | 存储值模型，封装实际值（value）、版本号（version）和写入时间戳（timestamp） |
| `ReplicaStats` | 副本统计信息，包含副本 ID、状态、存储 key 数量、读写总次数与成功次数、读写延迟样本列表，以及读写成功率、平均延迟等计算属性 |
| `WriteResult` | 写入结果，包含 key、写入值、版本号、成功/失败副本 ID 列表、`required_w`（写入法定人数阈值）；`success` 属性需满足 `successful_replicas >= required_w` |
| `ReadResult` | 读取结果，包含 key、读取到的值、版本号、成功/失败副本 ID 列表、`required_r`（读取法定人数阈值）、修复的副本 ID 列表、是否检测到冲突、冲突裁决的获胜值；`success` 属性需满足 `successful_replicas >= required_r` |

### exceptions.py

| 类名 | 职责 |
|------|------|
| `QuorumError` | 法定人数模块异常基类 |
| `InvalidQuorumConfigError` | 非法法定人数配置异常（N/W/R 参数不满足约束） |
| `QuorumWriteError` | 法定人数写入失败异常（成功副本数 < W） |
| `QuorumReadError` | 法定人数读取失败异常（响应副本数 < R） |
| `ReplicaUnreachableError` | 副本真实不可达异常（由 `mark_unreachable()` 标记的离线/网络分区） |
| `ReplicaInjectedFailureError` | 副本人工注入故障异常（由 `set_fail_reads()` / `set_fail_writes()` 触发，携带 `operation` 字段标明是 read 还是 write 操作）。与 `ReplicaUnreachableError` 区分，便于精确统计故障类型 |
| `VersionConflictError` | 版本冲突异常（可通过 resolve_conflict 的 raise_on_conflict 参数触发） |

### replica.py

| 类名 | 职责 |
|------|------|
| `Replica` | 副本存储模型，封装内存字典存储，提供 `read(key)` / `write(key, value, version)` 接口，内置版本号校验（拒绝低版本写入）、读写统计与延迟采样、状态开关（在线/不可达）、人工故障注入（读失败、写失败、人工延迟） |

### coordinator.py

| 类名 | 职责 |
|------|------|
| `QuorumCoordinator` | 法定人数读写协调器，管理副本集合与 N/W/R 参数，维护每个 key 的版本号计数器，提供 `write()` / `read()` / `resolve_conflict()` 核心接口，以及副本状态管理、统计查询等辅助方法 |

## 法定人数读写规则

### 参数约束

法定人数配置必须满足以下条件，否则抛出 `InvalidQuorumConfigError`：

- N > 0（副本总数）
- 0 < W ≤ N（写入法定人数）
- 0 < R ≤ N（读取法定人数）
- **W + R > N**（读写重叠保证，确保每次读取至少能读到一个最新写入）

最小重叠配置为 **W + R = N + 1**，例如：
- N=3, W=2, R=2（最常见配置）
- N=5, W=3, R=3
- N=5, W=2, R=4（读多写少场景）
- N=5, W=4, R=2（写多读少场景）

### 写入流程

```
                ┌─────────────────────┐
                │  客户端发起 write() │
                └──────────┬──────────┘
                           │
                           ▼
               ┌─────────────────────────┐
               │ 协调器分配下一个版本号 V │
               │ (key 当前版本 +1)        │
               └──────────┬──────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────────┐
        │  向全部 N 个副本并发写入 (key, value, V)  │
        │                                         │
        │  每个副本:                               │
        │    若副本不可达 → 失败                   │
        │    若 V < 已存储版本 → 拒绝(视为失败)     │
        │    否则 → 写入成功, 返回 ack              │
        └────────────────────┬────────────────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
                ▼                         ▼
       成功副本数 ≥ W              成功副本数 < W
                │                         │
                ▼                         ▼
       返回 WriteResult           抛出 QuorumWriteError
       (含成功/失败列表)
```

### 读取流程

```
                ┌─────────────────────┐
                │  客户端发起 read()  │
                └──────────┬──────────┘
                           │
                           ▼
        ┌─────────────────────────────────────────┐
        │     向全部 N 个副本并发读取 key           │
        │                                         │
        │  每个副本:                               │
        │    若不可达 → 失败                       │
        │    否则 → 返回 StoredValue 或 None       │
        └────────────────────┬────────────────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
                ▼                         ▼
       响应副本数 ≥ R              响应副本数 < R
                │                         │
                ▼                         ▼
     ┌──────────────────────┐    抛出 QuorumReadError
     │  从响应中选出版本号    │
     │  最高的 StoredValue   │
     │  (版本相同则取时间戳   │
     │   最新的,即 LWW)      │
     └───────────┬──────────┘
                 │
        ┌────────┴────────┐
        │                 │
        ▼                 ▼
  所有响应版本一致     检测到版本不一致
        │                 │
        │                 ▼
        │         perform_repair=True?
        │           ┌─────┴──────┐
        │           │            │
        │           ▼            ▼
        │        执行读修复    跳过修复
        │        (将最新值写   仅返回结果
        │         回落后副本)
        │           │
        └─────┬─────┘
              ▼
       返回 ReadResult
       (含冲突标记/修复列表)
```

### 读修复流程

当读取检测到副本间版本不一致时，若开启 `perform_repair=True`（默认开启），协调器会：

1. 选出版本号最高（版本相同则时间戳最新）的获胜值
2. 遍历所有参与读取的副本：
   - 若副本无此 key 数据 → 需要修复
   - 若副本版本 < 获胜版本 → 需要修复
3. 对每个需要修复且状态为 ONLINE 的副本，执行写入操作将获胜值写回
4. 将成功修复的副本 ID 记录在 `ReadResult.repaired_replicas`

### 版本冲突裁决流程

`resolve_conflict(key, raise_on_conflict=False)` 用于显式裁决指定 key 的版本冲突：

1. 从所有 ONLINE 副本读取该 key 的值
2. 若无任何副本持有数据 → 返回 None
3. 检测版本是否存在差异：
   - 若 `raise_on_conflict=True` 且存在冲突 → 抛出 `VersionConflictError`
4. 选出获胜值（高版本号 + LWW 时间戳）
5. 将获胜值写回所有 ONLINE 副本
6. 返回获胜的 `StoredValue`

## 使用示例

### 基本读写

```python
from solocoder_py.quorum import QuorumCoordinator, Replica

# 创建 3 个副本,配置 W=2, R=2 (W+R=4>3, 最小重叠)
replicas = [Replica(id=f"replica-{i}") for i in range(3)]
coord = QuorumCoordinator(replicas=replicas, w=2, r=2)

# 写入 (自动分配版本号 1)
wresult = coord.write("user:1", {"name": "Alice", "age": 30})
assert wresult.version == 1
assert len(wresult.successful_replicas) == 3

# 再次写入 (版本号 2)
wresult2 = coord.write("user:1", {"name": "Alice", "age": 31})
assert wresult2.version == 2

# 读取 (返回最高版本)
rresult = coord.read("user:1")
assert rresult.value["age"] == 31
assert rresult.version == 2
```

### 模拟副本故障与降级

```python
from solocoder_py.quorum import QuorumCoordinator, Replica

replicas = [Replica(id=f"node-{i}") for i in range(5)]
coord = QuorumCoordinator(replicas=replicas, w=3, r=3)

# 模拟 node-0 宕机
coord.mark_replica_unreachable("node-0")

# 写入仍可成功 (剩余 4 个 ONLINE 副本, 满足 W=3)
coord.write("k", "v")

# 模拟更多节点故障
coord.mark_replica_unreachable("node-1")
coord.mark_replica_unreachable("node-2")

# 仅剩 2 个 ONLINE 副本, 不满足 W=3
from solocoder_py.quorum import QuorumWriteError
try:
    coord.write("k2", "v2")
except QuorumWriteError as e:
    print(f"写入失败: {e}")  # 写入失败: 2/3 replicas acknowledged

# 节点恢复
coord.mark_replica_online("node-0")
```

### 读修复场景

```python
from solocoder_py.quorum import QuorumCoordinator, Replica

replicas = [Replica(id=f"r-{i}") for i in range(3)]
coord = QuorumCoordinator(replicas=replicas, w=2, r=2)

# 前两次写入所有副本正常
coord.write("config", {"timeout": 10})  # v1
coord.write("config", {"timeout": 30})  # v2

# 模拟第 3 个副本写入失败 (网络抖动)
replicas[2].set_fail_writes(True)
coord.write("config", {"timeout": 60})  # v3, 仅 r-0 和 r-1 成功
replicas[2].set_fail_writes(False)

# 此时 r-2 仍为 v2, 读取时自动修复
rresult = coord.read("config")
assert rresult.value["timeout"] == 60
assert rresult.conflict_detected is True
assert "r-2" in rresult.repaired_replicas

# 修复后 r-2 已更新到 v3
assert replicas[2].get_version("config") == 3
```

### 版本冲突裁决

```python
from solocoder_py.quorum import QuorumCoordinator, Replica

# 人为制造版本不一致 (模拟并发写入)
replicas = [Replica(id=f"r-{i}") for i in range(3)]
replicas[0].write("counter", 10, version=1)
replicas[1].write("counter", 50, version=3)   # 最高版本
replicas[2].write("counter", 30, version=2)

coord = QuorumCoordinator(replicas=replicas, w=2, r=2)

# 显式裁决冲突
winner = coord.resolve_conflict("counter")
assert winner.value == 50
assert winner.version == 3

# 裁决后所有副本已同步到获胜值
for r in replicas:
    assert r.read("counter").value == 50
    assert r.read("counter").version == 3

# 也可选择冲突时抛出异常
from solocoder_py.quorum import VersionConflictError
replicas[0].write("x", 1, 1)
replicas[1].write("x", 2, 2)
try:
    coord.resolve_conflict("x", raise_on_conflict=True)
except VersionConflictError as e:
    print(f"冲突: {e}")
```

### 查询副本状态与统计

```python
from solocoder_py.quorum import QuorumCoordinator, Replica

replicas = [Replica(id=f"r-{i}") for i in range(3)]
coord = QuorumCoordinator(replicas=replicas, w=2, r=2)

for _ in range(10):
    coord.write("k", "v")
    coord.read("k")

# 查询所有副本统计
for stats in coord.get_all_replica_stats():
    print(f"副本 {stats.replica_id}:")
    print(f"  状态: {stats.status}")
    print(f"  存储 Keys: {stats.keys_count}")
    print(f"  写入成功率: {stats.write_success_rate:.2%}")
    print(f"  读取成功率: {stats.read_success_rate:.2%}")
    print(f"  平均写入延迟: {stats.avg_write_latency_ms:.2f} ms")
    print(f"  平均读取延迟: {stats.avg_read_latency_ms:.2f} ms")

# 查询所有副本数据快照
all_data = coord.get_all_data_across_replicas()
for rid, data in all_data.items():
    print(f"{rid}: { {k: (v.value, v.version) for k, v in data.items()} }")
```

## 异常类型区分策略

为了精确区分副本故障的来源，模块定义了两种不同的异常类型，调用方可以分别捕获以做不同处理（统计告警、故障恢复等）：

| 异常类型 | 触发条件 | 场景说明 |
|----------|----------|----------|
| `ReplicaUnreachableError` | 副本状态为 `UNREACHABLE` | 真实的网络分区、节点宕机；由 `mark_unreachable()` 显式标记 |
| `ReplicaInjectedFailureError` | 调用 `set_fail_reads(True)` 或 `set_fail_writes(True)` | 测试/演练时的人工故障注入；异常携带 `replica_id` 和 `operation`（`"read"` / `"write"`）字段 |

**协调器行为**：`QuorumCoordinator` 在执行读写时会同时捕获这两种异常，统一将该副本计入 `failed_replicas`，不做进一步区分。若调用方需要分别统计两种故障，可直接调用 `Replica.read()` / `Replica.write()` 并分别捕获异常。

```python
from solocoder_py.quorum import Replica, ReplicaUnreachableError, ReplicaInjectedFailureError

r = Replica(id="r1")

try:
    r.read("k")
except ReplicaUnreachableError:
    print("真实节点不可达")
except ReplicaInjectedFailureError as e:
    print(f"人工注入 {e.operation} 故障")
```

## 操作结果 success 属性语义

`WriteResult` 和 `ReadResult` 均带有布尔属性 `success`，用于表明该操作是否满足法定人数要求：

| 结果类型 | success 判断条件 | 说明 |
|----------|------------------|------|
| `WriteResult` | `len(successful_replicas) >= required_w` | `required_w` 即协调器配置的 `w` |
| `ReadResult` | `len(successful_replicas) >= required_r` | `required_r` 即协调器配置的 `r` |

**设计要点**：
- `success` 语义严格对齐法定人数阈值，而非"有任意一个成功"。避免调用方仅检查 `success` 就误以为达到了一致性保证。
- 当协调器的 `write()` / `read()` 方法正常返回时，`success` 恒为 `True`——因为方法本身在不满足法定人数时会抛出 `QuorumWriteError` / `QuorumReadError`。
- `required_w` / `required_r` 字段随结果对象一并返回，便于调用方在日志、监控中记录实际阈值配置。

```python
result = coord.write("k", "v")
assert result.required_w == coord.w
assert result.success is True        # 方法不抛异常时一定为 True
assert len(result.successful_replicas) >= result.required_w
```

## 延迟统计计入规则

副本通过 `ReplicaStats.read_latencies_ms` / `ReplicaStats.write_latencies_ms` 列表保存延迟样本，并通过 `avg_read_latency_ms` / `avg_write_latency_ms` 暴露平均值。为确保性能指标可用，统计遵循以下规则：

| 场景 | 是否计入延迟统计 | 说明 |
|------|------------------|------|
| 读/写操作成功 | ✅ 计入 | 仅统计核心存储操作耗时（字典查询/写入） |
| 副本不可达（`ReplicaUnreachableError`） | ❌ 不计入 | 请求未真正到达存储逻辑，无性能意义 |
| 人工注入故障（`ReplicaInjectedFailureError`） | ❌ 不计入 | 测试注入的失败，不应污染生产指标 |
| 写入因版本落后被拒绝（返回 `False`） | ❌ 不计入 | 仅做版本比较，未执行实际写入 |
| 人工注入延迟（`set_artificial_latency()`） | ❌ 不计入 | 延迟在计时前通过 `time.sleep()` 注入，不计入操作本身耗时 |

**计数规则**：
- `total_reads` / `total_writes` 统计**所有调用次数**（包括不可达和注入失败的调用），用于计算成功率。
- `successful_reads` / `successful_writes` 仅统计真正成功完成存储操作的次数。
- 成功率 = `successful / total`，可反映节点真实可用率。

```python
r = Replica(id="r1")
r.set_fail_reads(True)
for _ in range(5):
    try:
        r.read("k")
    except Exception:
        pass
r.set_fail_reads(False)
r.read("k")

stats = r.get_stats()
assert stats.total_reads == 6          # 总调用次数含失败
assert stats.successful_reads == 1     # 仅 1 次成功
assert len(stats.read_latencies_ms) == 1  # 仅 1 条延迟样本
assert stats.read_success_rate == 1 / 6
```

## 运行测试

```bash
pytest tests/quorum/ -v
```
