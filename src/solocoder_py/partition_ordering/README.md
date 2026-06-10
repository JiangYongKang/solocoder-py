# Partition Ordering 分区消息有序处理模块

基于内存数据结构实现的分区消息有序处理域模块，提供按 key 分区路由、分区内严格保序、跨分区并发消费以及消费者组重平衡等核心能力。

## 模块功能

1. **按 key 分区路由**：基于 MD5 哈希算法，将相同 key 的消息稳定路由到同一分区，不同 key 可分布到不同分区，提升并发处理能力。
2. **分区内严格保序**：同一分区内的消息严格按照写入顺序（offset 递增）处理，不允许乱序确认或跳序消费，确保业务逻辑的正确性。
3. **跨分区并发处理**：不同分区之间完全隔离，可由同一或不同消费者并行消费，互不阻塞，整体吞吐量随分区数量线性扩展。
4. **重平衡后顺序保持**：当消费者实例增减触发分区重平衡时，自动完成分区所有权迁移，并保证迁移后分区内处理顺序与位点（offset）的连续性。

## 核心类职责

### `Partitioner`（分区路由器）

基于 key 计算目标分区 ID 的哈希路由器。

**核心方法**：
- `partition(key: str) -> int`：根据 key 的 MD5 哈希值计算目标分区 ID，相同 key 始终返回相同分区。
- `partition_stable(key: str) -> int`：`partition()` 的别名，强调路由的稳定性。

### `Message`（消息模型）

代表分区中的单条不可变消息。

**核心属性**：
- `offset`：分区内唯一递增位点
- `key`：消息业务键，用于分区路由
- `value`：消息体，支持任意类型
- `partition_id`：所属分区 ID
- `timestamp`：消息时间戳

### `PartitionedTopic`（分区主题/数据源）

模拟消息中间件的分区主题，使用内存列表存储各分区的消息。

**核心方法**：
- `produce(key, value, timestamp=None) -> Message`：按 key 自动路由到目标分区并写入消息。
- `produce_to_partition(partition_id, key, value, timestamp=None) -> Message`：写入指定分区。
- `get_messages(partition_id, start_offset, max_count=1) -> list[Message]`：从指定 offset 开始拉取消息。
- `get_latest_offset(partition_id) -> int`：获取分区最新 offset。
- `get_partition_size(partition_id) -> int`：获取分区消息总数。

### `OrderedPartitionConsumer`（有序分区消费者）

维护分区内严格保序语义的消费者，确保同一分区内消息按 offset 递增顺序处理。

**核心方法**：
- `assign_partition(partition_id)`：分配分区给当前消费者。
- `revoke_partition(partition_id) -> list[Message]`：撤销分区，返回未提交的 in-flight 消息。
- `poll(partition_id, max_messages=1) -> list[Message]`：从分区拉取消息；若存在未提交的 in-flight 消息则返回空列表。
- `poll_all(max_messages_per_partition=1) -> dict[int, list[Message]]`：从所有已分配分区拉取消息。
- `commit(partition_id, offset)`：提交位点；必须按 offset 递增顺序提交，否则抛出 `OutOfOrderCommitError`。
- `seek(partition_id, offset)`：重置消费位点，同时清空 in-flight 消息。
- `get_committed_offset(partition_id) -> int`：获取已提交位点。
- `get_in_flight_count(partition_id) -> int`：获取 in-flight 消息数量。

### `ConsumerGroupCoordinator`（消费者组协调器）

管理消费者组成员、分区分配与重平衡的协调服务。

**核心方法**：
- `join_group(consumer_id, listener=None) -> OrderedPartitionConsumer`：消费者加入组，触发重平衡，返回消费者实例。
- `leave_group(consumer_id)`：消费者离开组，触发重平衡。
- `get_consumer(consumer_id) -> OrderedPartitionConsumer`：获取组内消费者实例。
- `get_partition_owner(partition_id) -> Optional[str]`：查询分区当前所属消费者。
- `get_all_assignments() -> list[ConsumerAssignment]`：获取所有消费者的分区分配情况。
- `force_rebalance() -> int`：手动触发重平衡，返回新一代 ID。
- `is_rebalancing -> bool`：当前是否处于重平衡中。

### 异常类

- `PartitionOrderingError`：模块异常基类
- `PartitionNotFoundError`：分区不存在
- `UnknownPartitionError`：未知分区
- `OutOfOrderCommitError`：乱序提交（违反严格保序）
- `OffsetOutOfRangeError`：位点超出有效范围
- `ConsumerNotFoundError`：消费者不在组内
- `PartitionAlreadyAssignedError`：分区已被分配
- `RebalanceInProgressError`：重平衡进行中
- `NotAssignedPartitionError`：操作未分配的分区

## 分区保序策略

### 严格保序机制

```
                 produce(key, value)
                        │
                        ▼
                [Partitioner]
                hash(key) % N
                        │
                        ▼
            ┌───────────────────────┐
            │ Partition 0: [0,1,2,3]│
            │ Partition 1: [0,1,2]  │
            │ Partition 2: [0,1]    │
            └───────────────────────┘
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
    Consumer A     Consumer B     Consumer C
    owns P0,P2    owns P1        (none if only 2)
          │             │
          ▼             ▼
    poll() in order poll() in order
    commit(0,1,2...)  commit(0,1...)
```

**保序规则**：
1. 消费者从分区拉取一批消息后，在未提交前再次 `poll()` 将返回空列表，防止消息乱序。
2. `commit()` 必须严格按 offset 递增顺序调用，任何跳序提交都会触发 `OutOfOrderCommitError`。
3. 下一批次消息的起始位点 = `committed_offset + 1`，保证消费连续性。

## 重平衡策略

### 分配算法

使用 **Round-Robin 轮询分配**：将分区 ID 按 `partition_id % num_consumers` 均匀分配给各消费者。

### 重平衡触发时机

1. 新消费者加入组
2. 现有消费者离开组
3. 手动调用 `force_rebalance()`

### 重平衡流程

```
1. 标记 rebalancing = True
2. generation_id += 1
3. 计算新的分区-消费者映射（Round-Robin）
4. 对比新旧映射，确定各消费者的 revoked / assigned 分区
5. 对被撤销的分区：
   - 调用 consumer.revoke_partition()，返回未提交的 in-flight 消息
   - 重置该分区的 last_pulled_offset = committed_offset
6. 对新分配的分区：
   - 调用 consumer.assign_partition()
   - 从 committed_offset + 1 位点继续消费
7. 通知所有注册的 RebalanceListener
8. 标记 rebalancing = False
```

### 重平衡后顺序保证

- 分区迁移后，新消费者从该分区的 `committed_offset + 1` 位点继续消费。
- 旧消费者未提交的 in-flight 消息会随 `revoke_partition()` 返回，不影响位点连续性。
- 同一分区内消息的 offset 永不改变，重平衡仅改变所有权，不改变消息顺序。

## 使用示例

### 基础：单消费者按序处理

```python
from solocoder_py.partition_ordering import PartitionedTopic, OrderedPartitionConsumer

topic = PartitionedTopic(name="orders", num_partitions=4)

for i in range(10):
    topic.produce(key=f"user-{i % 3}", value={"order_id": i})

consumer = OrderedPartitionConsumer(consumer_id="worker-1", topic=topic)
for pid in range(topic.num_partitions):
    consumer.assign_partition(pid)

for pid in range(topic.num_partitions):
    while True:
        messages = consumer.poll(pid, max_messages=1)
        if not messages:
            break
        msg = messages[0]
        print(f"Processing P{msg.partition_id} offset={msg.offset}: {msg.value}")
        consumer.commit(pid, msg.offset)
```

### 跨分区并发消费

```python
import threading
from solocoder_py.partition_ordering import PartitionedTopic, OrderedPartitionConsumer

topic = PartitionedTopic(name="events", num_partitions=4)
for i in range(100):
    topic.produce(key=f"event-{i}", value=f"data-{i}")

def process_partition(pid):
    c = OrderedPartitionConsumer(consumer_id=f"worker-{pid}", topic=topic)
    c.assign_partition(pid)
    processed = []
    while True:
        msgs = c.poll(pid, max_messages=5)
        if not msgs:
            break
        for m in msgs:
            processed.append(m.offset)
            c.commit(pid, m.offset)
    print(f"Partition {pid} processed offsets: {processed}")

threads = [threading.Thread(target=process_partition, args=(pid,))
           for pid in range(topic.num_partitions)]
for t in threads:
    t.start()
for t in threads:
    t.join()
```

### 消费者组 + 重平衡

```python
from solocoder_py.partition_ordering import (
    ConsumerGroupCoordinator,
    PartitionedTopic,
    RebalanceEvent,
)

topic = PartitionedTopic(name="metrics", num_partitions=4)
for i in range(20):
    topic.produce(key=f"metric-{i}", value=i)

coord = ConsumerGroupCoordinator(group_id="metrics-group", topic=topic)

def on_rebalance(event: RebalanceEvent):
    print(f"[Rebalance gen={event.generation_id}] "
          f"consumer={event.consumer_id} "
          f"assigned={event.assigned_partitions} "
          f"revoked={event.revoked_partitions}")

c1 = coord.join_group("consumer-1", listener=on_rebalance)
print(f"c1 owns: {sorted(c1.assigned_partitions)}")

c2 = coord.join_group("consumer-2", listener=on_rebalance)
print(f"c1 owns: {sorted(c1.assigned_partitions)}")
print(f"c2 owns: {sorted(c2.assigned_partitions)}")

coord.leave_group("consumer-2")
print(f"After c2 left, c1 owns: {sorted(c1.assigned_partitions)}")
```

### 乱序提交保护

```python
from solocoder_py.partition_ordering import (
    OrderedPartitionConsumer,
    OutOfOrderCommitError,
    PartitionedTopic,
)

topic = PartitionedTopic(name="test", num_partitions=1)
for i in range(5):
    topic.produce(key="k", value=f"v-{i}")

consumer = OrderedPartitionConsumer(consumer_id="c", topic=topic)
consumer.assign_partition(0)

msgs = consumer.poll(0, max_messages=5)

try:
    consumer.commit(0, 2)
except OutOfOrderCommitError as e:
    print(f"Protected from out-of-order commit: {e}")

consumer.commit(0, 0)
consumer.commit(0, 1)
consumer.commit(0, 2)
consumer.commit(0, 3)
consumer.commit(0, 4)
print("All messages committed in order successfully")
```
