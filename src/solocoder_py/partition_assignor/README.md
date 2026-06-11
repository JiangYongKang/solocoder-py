# Partition Assignor

分区分配协调域模块，实现消费者组内的分区分配与再平衡协调。使用内存数据结构模拟分区与消费者状态，支持均衡分配、粘性保持、孤儿分区回收和心跳超时检测。

## 模块功能

- **消费者管理**：注册/注销消费者，维护消费者存活状态与心跳时间戳
- **分区管理**：添加/移除分区，跟踪分区归属
- **心跳超时检测**：定期检测消费者心跳，将超时消费者标记为待离开状态
- **均衡再分配**：当消费者数量变化或分区数量变化时，触发再平衡，将分区尽可能均匀地分配给所有活跃消费者
- **粘性保持策略**：再分配时优先保持已有的消费者-分区分配关系，仅迁移必要数量的分区
- **孤儿分区回收**：消费者离开（主动注销或心跳超时）时将其分区标记为孤儿，再平衡时优先分配给其他消费者
- **分配变更追踪**：记录每次再平衡的分配变更详情（新增分配、回收分配）

## 核心类职责

### `PartitionAssignor`

分区分配协调器，是模块的核心入口类。

主要方法：
- `register_consumer(consumer_id: str)`：注册消费者
- `unregister_consumer(consumer_id: str)`：注销消费者，其持有的分区变为孤儿
- `add_partitions(partition_ids: Iterable[int])`：添加分区，新分区初始为未分配状态
- `remove_partitions(partition_ids: Iterable[int])`：移除分区
- `heartbeat(consumer_id: str, timestamp: float)`：更新消费者心跳时间
- `check_heartbeat_timeout(current_time: float, timeout_seconds: float) -> list[str]`：检测心跳超时的消费者，将其标记为 LEAVING 状态，返回超时消费者 ID 列表
- `rebalance() -> RebalanceResult`：触发分区再平衡，先处理 LEAVING 状态的消费者
- `get_assignment(consumer_id: str) -> list[int]`：获取指定消费者的分区分配
- `get_all_assignments() -> dict[str, list[int]]`：获取所有消费者的分区分配
- `get_unassigned_partitions() -> list[int]`：获取当前未分配的分区列表（新增的从未被分配过的分区）
- `get_orphan_partitions() -> list[int]`：获取当前孤儿分区列表（原消费者离开后的分区）
- `get_consumer(consumer_id: str) -> Consumer`：获取指定消费者

### 数据模型

- `Partition`：分区实体，仅包含分区 ID
- `Consumer`：消费者实体，包含消费者 ID、状态、已分配分区集合和心跳时间
- `ConsumerStatus`：消费者状态枚举（ACTIVE / LEAVING）
- `AssignmentChange`：分配变更记录，包含消费者 ID、新分配分区列表、被回收分区列表
- `RebalanceResult`：再平衡结果，包含世代 ID、完整分配结果、所有变更记录、回收的孤儿分区列表

### 异常类

- `PartitionAssignorError`：模块基础异常
- `ConsumerAlreadyRegisteredError`：消费者重复注册
- `ConsumerNotFoundError`：消费者不存在
- `PartitionNotFoundError`：分区不存在
- `InvalidPartitionIdError`：无效分区 ID（负数）
- `EmptyConsumerGroupError`：空消费者组无法执行再平衡

## 消费者状态流转

### 状态定义

- **ACTIVE**：消费者正常活跃，可持有分区并参与再分配
- **LEAVING**：消费者已检测到心跳超时，待在下一次 rebalance 时移除

### 状态流转路径

```
          注册            心跳正常
ACTIVE -----------> ACTIVE -----------> ACTIVE
  |                    |
  | 注销               | 心跳超时
  |                    |
  v                    v
(移除)           LEAVING
                       |
                       | rebalance
                       |
                       v
                   (移除)
```

1. 消费者注册时初始化为 ACTIVE 状态
2. 调用 `heartbeat()` 更新心跳时间戳，保持 ACTIVE 状态
3. 调用 `check_heartbeat_timeout()`，如果超时则状态变为 LEAVING
4. 调用 `unregister_consumer()` 直接移除消费者，其分区变为孤儿
5. 调用 `rebalance()` 时，LEAVING 状态的消费者被处理：
   - 其持有的分区被转移到 orphan_partitions
   - 消费者从组中移除
   - 然后进行正常的再分配

## 未分配分区与孤儿分区

### 概念区分

- **unassigned_partitions**（未分配分区）：新增的、从未被分配给任何消费者的分区
- **orphan_partitions**（孤儿分区）：曾被分配给某个消费者，但该消费者已离开（主动注销或心跳超时）后的分区

### 处理优先级

在再平衡时，两类分区都会被分配，但孤儿分区具有更高优先级：
1. 先处理超额释放的分区（消费者超额持有的分区）
2. 再处理 orphan_partitions（孤儿分区）
3. 最后处理 unassigned_partitions（未分配分区）

这确保了之前有消费者处理的分区能够更快地被重新分配，减少消费中断。

## 再分配算法与粘性保持策略

### 均衡分配计算

设活跃消费者数为 N，分区总数为 M：

- 基准配额：`base = M // N`
- 额外配额：`extra = M % N`
- 前 `extra` 个消费者分配 `base + 1` 个分区，其余分配 `base` 个分区

消费者顺序按消费者 ID 字典序排列，确保每次再平衡的目标分配一致。

### 粘性保持策略

再平衡时采用以下步骤最小化分区迁移：

1. **处理 LEAVING 消费者**：将 LEAVING 状态消费者的分区转为孤儿，移除该消费者
2. **计算目标分配数**：为每个 ACTIVE 消费者确定应持有的分区数量
3. **保留已有分配**：对每个消费者，尽可能保留其当前持有的分区（最多保留到目标数量），按分区 ID 升序优先保留
4. **收集待重分配分区**（按优先级）：
   - 超额消费者超出目标数量的分区
   - 所有当前的孤儿分区
   - 所有当前的未分配分区
5. **补充不足**：将待重分配的分区按 ID 升序分配给尚未达到目标数量的消费者

该策略保证：
- 每个分区在同一时刻仅属于一个消费者
- 再平衡前后的分配差异最小化
- 孤儿分区优先得到处理

### 孤儿分区回收

当消费者离开（主动注销或心跳超时）时，其持有的所有分区立即被标记为孤儿状态，进入 `orphan_partitions` 集合。下次再平衡时：

1. 孤儿分区优先被纳入分配流程（在未分配分区之前）
2. 再平衡完成后，孤儿分区集合和未分配分区集合都被清空
3. `RebalanceResult` 中记录本次回收的所有孤儿分区

## 使用示例

### 基本使用

```python
from solocoder_py.partition_assignor import PartitionAssignor

assignor = PartitionAssignor()

assignor.add_partitions(range(6))

assignor.register_consumer("consumer-0")
assignor.register_consumer("consumer-1")
assignor.register_consumer("consumer-2")

result = assignor.rebalance()
print(f"Generation: {result.generation_id}")
for cid, partitions in result.assignments.items():
    print(f"{cid}: {partitions}")
```

### 心跳与超时检测

```python
import time

assignor.heartbeat("consumer-0", time.time())
assignor.heartbeat("consumer-1", time.time())
assignor.heartbeat("consumer-2", time.time())

time.sleep(20)

timed_out = assignor.check_heartbeat_timeout(
    current_time=time.time(),
    timeout_seconds=30
)
if timed_out:
    print(f"Timed out consumers: {timed_out}")
    result = assignor.rebalance()
    print(f"Recovered orphan partitions: {result.orphan_partitions_recovered}")
```

### 消费者加入触发再平衡

```python
assignor.register_consumer("consumer-3")
result = assignor.rebalance()
print(f"Moved partitions: {sum(len(c.revoked_partitions) for c in result.changes)}")
```

### 消费者离开触发孤儿回收

```python
assignor.unregister_consumer("consumer-0")
print(f"Orphan partitions: {assignor.get_orphan_partitions()}")

result = assignor.rebalance()
print(f"Recovered orphans: {result.orphan_partitions_recovered}")
```

### 分区数量变更

```python
assignor.add_partitions([6, 7, 8])
print(f"Unassigned partitions: {assignor.get_unassigned_partitions()}")
result = assignor.rebalance()

assignor.remove_partitions([0, 1])
result = assignor.rebalance()
```
