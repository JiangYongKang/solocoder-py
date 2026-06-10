# Exactly-Once Processing Module

精确一次处理（Exactly-Once Processing）域功能模块，使用内存数据结构模拟消息队列数据源，确保消息处理的幂等性、原子性和可恢复性。

## 模块功能

1. **消息去重机制**：每条消息携带唯一 `message_id`，消费端维护已处理消息记录，重复消息自动跳过并返回已处理结果
2. **原子化提交**：偏移量（Offset）与去重记录在同一原子操作中写入，避免部分写入导致的状态不一致
3. **崩溃重启恢复**：从最近检查点（Checkpoint）恢复状态，**保留去重记录用于拦截已处理消息**，未处理消息继续正常流转
4. **手动消息重放**：支持指定偏移范围重放消息，重放期间自动去重（含已提交和未提交记录），不产生重复的去重记录
5. **顺序消费偏移连续性**：`process_message_at` 随机访问不影响顺序消费偏移，跳跃时产生 `OffsetSkipWarning`（含完整跳过偏移列表）
6. **检查点单调性保证**：`committed_offset` 单调递增，重放产生的低偏移检查点不会覆盖已有的高偏移检查点

## 核心类职责

### 数据模型 (`models.py`)

| 类 | 职责 |
|---|---|
| `Message` | 消息载体，包含 `offset`、`message_id`、`payload`、`created_at` |
| `DedupRecord` | 去重记录，记录已处理消息的 ID、偏移、处理时间和结果数据 |
| `Checkpoint` | 检查点快照，记录已提交的偏移量和对应的去重记录数量 |
| `ProcessResult` | 单条消息处理结果，标识 NEW / DUPLICATE / SKIPPED_REPLAY 状态 |
| `CommitBatch` | 原子提交批次，封装待提交的偏移、去重记录和提交状态 |
| `ReplayResult` | 重放操作结果统计，包含处理数、去重数等指标 |

### 存储层 (`store.py`)

| 类 | 职责 |
|---|---|
| `InMemoryMessageSource` | 内存消息源，模拟 Kafka/RabbitMQ 等消息队列的发布/拉取语义 |
| `DedupStore` | 去重存储，基于 OrderedDict 的 LRU 容量管理，支持按 ID/偏移查询 |
| `CheckpointStore` | 检查点存储，管理检查点历史和两阶段提交的 Pending Batch |
| `Clock` / `SystemClock` / `ManualClock` | 时钟抽象，支持手动推进时间用于测试 |

### 核心处理器 (`processor.py`)

| 类 | 职责 |
|---|---|
| `ExactlyOnceProcessor` | 精确一次处理器，协调消息源、去重存储和检查点存储的完整流程 |

## 原子化提交与崩溃恢复机制

### 两阶段原子提交

```
Phase 1 (PREPARE):
  → processor.process_next() → 未提交记录累积到 _uncommitted_records
  → 达到 auto_commit_interval → checkpoint_store.prepare_batch()
  → 写入 Pending Batch（target_offset + dedup_records）
  → 标记 is_prepared = true

Phase 2 (COMMIT):
  → 步骤 1: dedup_store.put_batch()   // 写入去重记录
  → 步骤 2: 写入 Checkpoint           // 更新已提交偏移
  → 清除 Pending Batch + _uncommitted_records
  → 标记 is_committed = true
```

**原子性保证**：

| 崩溃时机 | 影响 | 恢复方式 |
|---|---|---|
| PREPARE 之前 | 无状态变更 | 重新消费即可 |
| PREPARE 之后，COMMIT 之前 | Pending Batch 存在；去重记录未写 | 恢复时 rollback Pending Batch；重新消费重复消息会被视为新消息 |
| 去重已写，Checkpoint 未写 | 去重记录存在；偏移未提交 | 恢复后会从旧偏移重放，但去重记录拦截已处理消息 |
| Checkpoint 已写 | 完整状态 | 从 Checkpoint 正常恢复 |

### 崩溃恢复流程

```python
processor.recover_or_start_fresh()
  → 调用 checkpoint_store.restore_from_checkpoint(dedup_store)
  → 保留 dedup_store 中的去重记录（用于拦截已处理消息）
  → 清除 pending 的 CommitBatch
  → 重置 current_offset 至 checkpoint.committed_offset
  → 后续 process_next() 从 committed_offset + 1 继续
```

**关键设计**：恢复时**不清空**去重存储。保留去重记录确保：
- 崩溃前去重记录已写入但检查点未写入的场景下，已处理消息不会被重复执行业务逻辑
- 恢复后从旧偏移重放时，去重记录能正确拦截已处理消息

### 检查点单调性保证

`committed_offset` 严格单调递增，不会出现低偏移检查点覆盖高偏移检查点的情况：

- **自动提交**：`_auto_checkpoint` 在提交前检查 `target_offset > current_committed_offset`，不满足时**静默跳过**提交（不抛异常），保留去重记录在 `_uncommitted_records` 中等待后续顺序消费推进后重新提交
- **重放提交**：`replay_range` 中，若重放产生的 `target_offset <= current_committed_offset`，仅将去重记录写入 `dedup_store`，不创建新检查点
- **崩溃恢复**：`recover_from_checkpoint` 始终从最新的（最高偏移的）检查点恢复

## 顺序消费偏移连续性保证

### process_message_at 与 process_next 的隔离

`process_message_at(offset)` 是**随机访问**方法，用于处理指定偏移的消息，它：
- **不修改** `_current_offset`：调用后顺序消费的偏移位置不变
- 去重记录加入 `_uncommitted_records`，在下次检查点提交时落盘
- 当跳跃偏移（跳过中间未处理消息）时，会设置 `last_skip_warning` 属性

`process_next()` 是**顺序消费**方法，始终从 `_current_offset + 1` 开始：
- `_current_offset` 只在 `process_next` 中递增
- 不受 `process_message_at` 的影响

### 偏移跳跃检测

```python
proc = ExactlyOnceProcessor.create(auto_commit_interval=100)

# 发布 10 条消息
for i in range(10):
    proc.publish_message(f"m{i}", i)

# 直接跳到 offset 5 处理
r = proc.process_message_at(5)
assert proc.last_skip_warning is not None
assert proc.last_skip_warning.expected_offset == 0
assert proc.last_skip_warning.actual_offset == 5
assert proc.last_skip_warning.skipped_offsets == [0, 1, 2, 3, 4]
assert proc.last_skip_warning.skipped_count == 5

# 顺序消费不受影响，仍从 offset 0 开始
r0 = proc.process_next()
assert r0.message.offset == 0
```

### last_skip_warning 生命周期

`last_skip_warning` 属性记录最近一次偏移跳跃告警，具有以下生命周期：

1. **产生**：`process_message_at` 检测到跳跃（`offset != expected_next`）时设置
2. **存活**：在顺序消费（`process_next`）尚未推进到跳跃偏移之前，告警持续存在
3. **清除**：当 `process_next` 将 `_current_offset` 推进到 `>= warning.actual_offset` 时，告警自动清除
4. **覆盖**：新的 `process_message_at` 跳跃会覆盖之前的告警

```python
# 跳跃到 offset 5
proc.process_message_at(5)
assert proc.last_skip_warning is not None  # 告警存在

# 顺序消费到 offset 4
for _ in range(5):
    proc.process_next()
assert proc.current_offset == 4
assert proc.last_skip_warning is not None  # 尚未追上，告警仍在

# 顺序消费到 offset 5（追上跳跃偏移）
proc.process_next()
assert proc.current_offset == 5
assert proc.last_skip_warning is None  # 告警已清除
```

### 混合批次检查点语义

当 `process_message_at` 和 `process_next` 交叉使用时，两者的去重记录会混合在 `_uncommitted_records` 中。检查点提交时的语义如下：

- **`committed_offset` = `_uncommitted_records` 最后一条记录的偏移**（按插入顺序，非偏移大小排序）
- 这意味着 `committed_offset` 反映的是**最后插入顺序消费的偏移位置**，而非已处理消息中的最大偏移
- 混合批次中的所有去重记录（包括随机访问产生的）都会被原子写入 `dedup_store`
- **崩溃恢复安全保证**：恢复后从 `committed_offset + 1` 继续顺序消费，随机访问处理的高偏移消息的去重记录已落盘，会被正确拦截为 DUPLICATE

```python
# 混合使用场景
proc.process_message_at(7, handler=lambda m: "ofo-7")  # 随机访问 offset 7
proc.process_next()  # 顺序消费 offset 0
proc.process_next()  # 顺序消费 offset 1

# 提交检查点：committed_offset = 1（最后一条记录的偏移）
cp = proc.commit_checkpoint()
assert cp.committed_offset == 1

# 但 dedup_store 中已有 m0、m1、m7 三条去重记录
assert proc.dedup_store.contains("m7")

# 恢复后：从 offset 2 继续消费
proc.recover_from_checkpoint()
# offset 7 的消息通过去重拦截，不会被重复处理
```

## 消息重放机制

重放期间保持处理器主状态不变：
1. 保存 `current_offset`、`_uncommitted_records`、`_uncommitted_results`
2. 遍历指定范围的消息，查询去重记录：
   - 已存在于 `dedup_store` → 跳过（`duplicate_count++`）
   - 已存在于 `_uncommitted_records` → 跳过（`duplicate_count++`）
   - 不存在 → 执行 handler，累积到临时去重列表
3. 临时去重列表通过原子提交写入：
   - 若 `target_offset > current_committed_offset` → 创建新检查点（单调递增）
   - 若 `target_offset <= current_committed_offset` → 仅写入去重记录，不创建检查点
4. 恢复主状态变量

重放的去重记录会标记 `replayed=True`，便于审计区分。

## 使用示例

### 基本消费流程

```python
from solocoder_py.exactly_once import ExactlyOnceProcessor

# 创建处理器（默认自动提交间隔=1）
proc = ExactlyOnceProcessor.create()

# 发布消息（模拟生产者）
for i in range(100):
    proc.publish_message(f"order-{i}", {"order_id": i, "amount": 100})

# 业务处理函数
processed = []
def handle_order(msg):
    order = msg.payload
    processed.append(order["order_id"])
    return {"status": "ok", "id": order["order_id"]}

# 消费全部消息
results = proc.process_all(handler=handle_order)

new_msgs = [r for r in results if r.is_new]
dup_msgs = [r for r in results if r.is_duplicate]
print(f"新消息: {len(new_msgs)}, 重复消息: {len(dup_msgs)}")
```

### 手动控制检查点

```python
proc = ExactlyOnceProcessor.create(auto_commit_interval=100)

for i in range(50):
    proc.publish_message(f"msg-{i}", f"data-{i}")

# 先处理全部（不触发自动提交）
proc.process_all(lambda m: None)
assert proc.committed_offset == -1

# 手动触发检查点
checkpoint = proc.commit_checkpoint()
print(f"已提交偏移: {checkpoint.committed_offset}")
print(f"去重记录数: {checkpoint.dedup_count}")
```

### 崩溃重启场景

```python
from solocoder_py.exactly_once import (
    ExactlyOnceProcessor,
    InMemoryMessageSource,
    DedupStore,
    CheckpointStore,
    ManualClock,
)

clock = ManualClock()
msg_src = InMemoryMessageSource(_clock=clock)
dedup = DedupStore(_clock=clock)
cp_store = CheckpointStore(_clock=clock)

proc = ExactlyOnceProcessor(
    message_source=msg_src,
    dedup_store=dedup,
    checkpoint_store=cp_store,
    _clock=clock,
    _auto_commit_interval=5,
)

# 生产 + 消费
for i in range(20):
    proc.publish_message(f"evt-{i}", {"idx": i})
proc.process_all(lambda m: None)

# --- 系统崩溃，重新启动 ---
# 创建新的处理器实例（共享底层存储）
proc2 = ExactlyOnceProcessor(
    message_source=msg_src,
    dedup_store=dedup,
    checkpoint_store=cp_store,
    _clock=clock,
)

# 从最近检查点恢复
# 注意：去重记录被保留，已处理消息会被拦截
proc2.recover_or_start_fresh()

# 继续生产 + 消费剩余消息
for i in range(20, 30):
    proc2.publish_message(f"evt-{i}", {"idx": i})
results = proc2.process_all()

# 验证: 旧消息被去重，新消息正常处理
new_count = sum(1 for r in results if r.is_new)
dup_count = sum(1 for r in results if r.is_duplicate)
assert new_count == 10
```

### 手动消息重放

```python
proc = ExactlyOnceProcessor.create()

for i in range(50):
    proc.publish_message(f"txn-{i}", i)

# 先处理一半
for _ in range(25):
    proc.process_next(lambda m: f"result-{m.payload}")

# 重放 [10, 40] 范围的消息
replay_result = proc.replay_range(
    start_offset=10,
    end_offset=40,
    handler=lambda m: f"replayed-{m.payload}"
)

print(f"总计: {replay_result.total_messages}")
print(f"  新处理: {replay_result.processed_count}")    # 15 条 (25~40)
print(f"  去重跳过: {replay_result.duplicate_count}") # 15 条 (10~24)
print(f"  新增去重记录: {replay_result.new_dedup_count}")
```

### 随机访问与偏移跳跃检测

```python
proc = ExactlyOnceProcessor.create(auto_commit_interval=100)

for i in range(10):
    proc.publish_message(f"m{i}", i)

# 随机访问 offset 5，不影响顺序消费
r = proc.process_message_at(5, handler=lambda m: f"out-of-order-{m.payload}")
assert r.is_new is True
assert proc.current_offset == -1  # 顺序偏移不变

# 检查跳跃告警（含完整跳过偏移列表）
if proc.last_skip_warning:
    w = proc.last_skip_warning
    print(f"警告: 从 offset {w.expected_offset} 跳到了 {w.actual_offset}")
    print(f"跳过的偏移: {w.skipped_offsets} (共 {w.skipped_count} 个)")

# 顺序消费不受影响
r0 = proc.process_next()
assert r0.message.offset == 0  # 从头开始
```

### 有限容量去重存储

```python
# 最多保留 1000 条去重记录（LRU 淘汰）
proc = ExactlyOnceProcessor.create(max_dedup_size=1000)

try:
    while True:
        result = proc.process_next(handler)
        if result is None:
            break
except DedupStoreOverflowError:
    # 容量不足，手动淘汰最旧的 500 条
    evicted = proc.force_evict_dedup(500)
    print(f"淘汰了 {len(evicted)} 条旧去重记录")
```

## 异常处理

| 异常 | 触发场景 | 处理建议 |
|---|---|---|
| `DedupStoreOverflowError` | 去重存储达到 `max_size` 上限 | 调用 `force_evict_dedup()` 淘汰旧记录 |
| `AtomicCommitInterruptedError` | 原子提交中途模拟崩溃 | 调用 `recover_or_start_fresh()` 恢复 |
| `MessageNotFoundError` | 查询不存在的消息偏移 | 检查偏移范围 |
| `CheckpointNotFoundError` | 无可用检查点时尝试恢复 | 使用 `recover_or_start_fresh()` 从 0 开始 |
| `OffsetSkipWarning` | `process_message_at` 跳过中间未处理消息 | 检查 `last_skip_warning.skipped_offsets` 确认具体跳过的偏移；顺序消费追上后告警自动清除 |

## 线程安全

- `InMemoryMessageSource`、`DedupStore`、`CheckpointStore`、`ExactlyOnceProcessor` 均使用 `threading.RLock` 保护内部状态
- 并发场景下，单条消息的「去重判定 → 业务处理 → 记录」流程通过锁保证互斥
- 处理器的 `process_next`/`commit_checkpoint` 等方法是线程安全的
