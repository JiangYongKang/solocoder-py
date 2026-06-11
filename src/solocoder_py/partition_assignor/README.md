# Partition Assignor

分区分配协调域模块，实现消费者组内的分区分配与再平衡协调。使用内存数据结构模拟分区与消费者状态，支持均衡分配、粘性保持和孤儿分区回收。

## 模块功能

- **消费者管理**：注册/注销消费者，维护消费者存活状态与心跳时间戳
- **分区管理**：添加/移除分区，跟踪分区归属
- **均衡再分配**：当消费者数量变化或分区数量变化时，触发再平衡，将分区尽可能均匀地分配给所有活跃消费者
- **粘性保持策略**：再分配时优先保持已有的消费者-分区分配关系，仅迁移必要数量的分区
- **孤儿分区回收**：消费者离开时将其分区标记为孤儿，再平衡时优先分配给其他消费者
- **分配变更追踪**：记录每次再平衡的分配变更详情（新增分配、回收分配）

## 核心类职责

### `PartitionAssignor`

分区分配协调器，是模块的核心入口类。

主要方法：
- `register_consumer(consumer_id: str)`：注册消费者
- `unregister_consumer(consumer_id: str)`：注销消费者，其持有的分区变为孤儿
- `add_partitions(partition_ids: Iterable[int])`：添加分区，新分区初始为孤儿状态
- `remove_partitions(partition_ids: Iterable[int])`：移除分区
- `rebalance() -> RebalanceResult`：触发分区再平衡
- `get_assignment(consumer_id: str) -> list[int]`：获取指定消费者的分区分配
- `get_all_assignments() -> dict[str, list[int]]`：获取所有消费者的分区分配
- `get_orphan_partitions() -> list[int]`：获取当前孤儿分区列表
- `heartbeat(consumer_id: str, timestamp: float)`：更新消费者心跳时间

### 数据模型

- `Partition`：分区实体，仅包含分区 ID
- `Consumer`：消费者实体，包含消费者 ID、状态、已分配分区集合和心跳时间
- `ConsumerStatus`：消费者状态枚举（ACTIVE / LEAVING / ORPHANED）
- `AssignmentChange`：分配变更记录，包含消费者 ID、新分配分区列表、被回收分区列表
- `RebalanceResult`：再平衡结果，包含世代 ID、完整分配结果、所有变更记录、回收的孤儿分区列表

### 异常类

- `PartitionAssignorError`：模块基础异常
- `ConsumerAlreadyRegisteredError`：消费者重复注册
- `ConsumerNotFoundError`：消费者不存在
- `PartitionNotFoundError`：分区不存在
- `InvalidPartitionIdError`：无效分区 ID（负数）
- `EmptyConsumerGroupError`：空消费者组无法执行再平衡

## 再分配算法与粘性保持策略

### 均衡分配计算

设活跃消费者数为 N，分区总数为 M：

- 基准配额：`base = M // N`
- 额外配额：`extra = M % N`
- 前 `extra` 个消费者分配 `base + 1` 个分区，其余分配 `base` 个分区

消费者顺序按消费者 ID 字典序排列，确保每次再平衡的目标分配一致。

### 粘性保持策略

再平衡时采用以下步骤最小化分区迁移：

1. **计算目标分配数**：为每个消费者确定应持有的分区数量
2. **保留已有分配**：对每个消费者，尽可能保留其当前持有的分区（最多保留到目标数量），按分区 ID 升序优先保留
3. **收集待重分配分区**：
   - 超额消费者超出目标数量的分区
   - 所有当前的孤儿分区
4. **补充不足**：将待重分配的分区按 ID 升序分配给尚未达到目标数量的消费者

该策略保证：
- 每个分区在同一时刻仅属于一个消费者
- 再平衡前后的分配差异最小化
- 孤儿分区优先得到处理

### 孤儿分区回收

当消费者被注销时，其持有的所有分区立即被标记为孤儿状态，进入 `orphan_partitions` 集合。下次再平衡时：

1. 孤儿分区与超额释放的分区共同组成待分配池
2. 孤儿分区优先被纳入分配流程
3. 再平衡完成后，孤儿分区集合被清空
4. `RebalanceResult` 中记录本次回收的所有孤儿分区

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
result = assignor.rebalance()

assignor.remove_partitions([0, 1])
result = assignor.rebalance()
```
