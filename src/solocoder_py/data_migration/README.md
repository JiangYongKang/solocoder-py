# 数据迁移执行域模块

## 模块功能

本模块实现了基于内存数据结构模拟的数据迁移执行域，支持以下核心能力：

1. **分批迁移**：将源数据按固定批次大小分割，逐批迁移到目标端。每批迁移完成后才开始下一批，系统记录每批的迁移状态。
2. **进度断点续传**：迁移过程中如果系统中断（模拟崩溃或重启），系统能从上次已完成的批次之后恢复迁移，不需要从头开始。检查点持久化记录当前已完成的批次位置。
3. **失败回滚**：如果某一批迁移执行失败，系统支持将该批次之前所有已迁移的数据回滚到迁移前的状态，保证目标端不保留不完整的数据。回滚操作也是分批执行的，与正向迁移的批次对应。
4. **回滚断点续传**：回滚过程中如果系统中断，重启后可以从断点继续回滚，确保最终能完全回滚。
5. **灵活的扩展点**：支持自定义 ID 提取器、自定义批次迁移器、自定义批次回滚器，可适配不同的数据源和目标存储。
6. **线程安全**：所有操作通过可重入锁保护，支持多线程并发访问。

## 核心类职责

### exceptions.py

| 类名 | 职责 |
|------|------|
| `DataMigrationError` | 数据迁移模块异常基类 |
| `BatchMigrationError` | 批次迁移失败异常，携带失败批次索引 |
| `RollbackError` | 回滚失败异常，携带失败批次索引 |
| `CheckpointError` | 检查点操作异常 |
| `EmptySourceError` | 源数据为空时的异常 |
| `InvalidBatchSizeError` | 批次大小不合法时的异常 |

### models.py

| 类名 | 职责 |
|------|------|
| `BatchStatus` | 批次状态枚举：PENDING、MIGRATING、COMPLETED、FAILED、ROLLED_BACK |
| `MigrationStatus` | 整体迁移状态枚举：IDLE、MIGRATING、COMPLETED、FAILED、ROLLING_BACK、ROLLED_BACK |
| `BatchInfo` | 批次信息数据模型，包含批次索引、起始位置、结束位置、状态、记录数、错误信息 |
| `MigrationState` | 迁移状态数据模型，包含整体状态、总记录数、批次大小、总批次数、已完成批次数、失败批次、批次列表、检查点等 |

### migrator.py

| 类名 | 职责 |
|------|------|
| `CheckpointStore` | 检查点存储抽象基类，定义 save/load/clear 接口 |
| `InMemoryCheckpointStore` | 内存检查点存储实现，保存检查点和完整迁移状态 |
| `DataMigrator` | 数据迁移器核心类，管理分批迁移、断点续传、失败回滚的完整生命周期 |

## 分批迁移与断点续传机制

### 分批迁移流程

```
调用方
  │
  │ migrator.migrate()
  ▼
DataMigrator.migrate()
  │
  │ ① 获取锁，进入临界区
  │ ② 计算起始批次：start_batch = checkpoint + 1
  │ ③ 循环处理每个批次：
  │    └── _migrate_batch(batch_index)
  │        ├── 将批次状态设为 MIGRATING
  │        ├── 调用批次迁移逻辑（默认或自定义）
  │        ├── 成功：状态设为 COMPLETED，completed_batches++
  │        ├── 更新 checkpoint = 当前批次索引
  │        ├── 保存检查点
  │        └── 失败：状态设为 FAILED，抛出 BatchMigrationError
  │ ④ 全部成功：状态设为 COMPLETED
  │ ⑤ 中途失败：状态设为 FAILED，记录失败批次
  ▼
返回 MigrationState
```

**分批保证**：
- **原子性**：每个批次的迁移作为一个整体，要么全部成功，要么全部失败
- **顺序性**：批次按索引顺序依次迁移，前一批完成后才开始下一批
- **可观测性**：每批迁移后更新检查点并持久化

### 断点续传机制

检查点（checkpoint）记录了最后一个成功完成的批次索引。迁移过程中每完成一个批次就更新并保存检查点。

重启后恢复流程：
1. 从检查点存储中加载 checkpoint 值
2. 恢复迁移状态：标记 0..checkpoint 批次为已完成
3. 从 checkpoint + 1 批次继续迁移

如果检查点显示迁移处于失败或回滚中状态，恢复时会自动触发回滚，确保数据一致性。

### 失败回滚机制

当迁移失败时，可以调用 `rollback()` 进行回滚。回滚从最后一个完成的批次开始，逆序逐批回滚。

```
回滚方向：批次 N → 批次 N-1 → ... → 批次 0
```

回滚过程中同样会更新检查点（指向上一个仍保留在目标中的批次），因此回滚本身也支持断点续传。

### 回滚断点续传

如果回滚过程中系统中断，重启后可以调用 `resume_rollback_from_checkpoint()` 继续回滚。系统会从检查点位置继续逆序回滚剩余批次。

## 使用示例

### 基本迁移

```python
from solocoder_py.data_migration import DataMigrator

source_data = [{"id": i, "name": f"user-{i}"} for i in range(100)]

migrator = DataMigrator(
    source_data=source_data,
    batch_size=20,
    id_extractor=lambda r: r["id"],
)

state = migrator.migrate()

print(f"迁移完成: {state.is_completed}")
print(f"总批次数: {state.total_batches}")
print(f"已完成批次: {state.completed_batches}")
print(f"目标数据量: {len(migrator.target_data)}")
```

### 逐步迁移（控制每批节奏）

```python
migrator = DataMigrator(source_data=source_data, batch_size=10)

while migrator.migrate_next_batch():
    state = migrator.state
    print(f"已完成 {state.completed_batches}/{state.total_batches} 批 "
          f"({state.progress_percent:.1f}%)")
```

### 断点续传

```python
from solocoder_py.data_migration import InMemoryCheckpointStore

checkpoint_store = InMemoryCheckpointStore()

# 第一次迁移，中途中断
migrator1 = DataMigrator(
    source_data=source_data,
    batch_size=10,
    checkpoint_store=checkpoint_store,
    id_extractor=lambda r: r["id"],
)
migrator1.migrate_next_batch()
migrator1.migrate_next_batch()
print(f"中断时检查点: {migrator1.state.checkpoint}")  # 1

# 系统重启后，从断点继续
target_store = {}  # 实际场景中目标存储应持久化
migrator2 = DataMigrator(
    source_data=source_data,
    target_store=target_store,
    batch_size=10,
    checkpoint_store=checkpoint_store,
    id_extractor=lambda r: r["id"],
)
state = migrator2.resume_from_checkpoint()
print(f"恢复后状态: {state.status}")  # COMPLETED
print(f"总完成批次: {state.completed_batches}")
```

### 失败回滚

```python
def unreliable_batch_migrator(records):
    for record in records:
        if record["id"] == 42:
            raise RuntimeError("目标系统故障")
        # 写入目标存储...

migrator = DataMigrator(
    source_data=source_data,
    batch_size=10,
    batch_migrator=unreliable_batch_migrator,
)

try:
    migrator.migrate()
except BatchMigrationError as e:
    print(f"批次 {e.batch_index} 迁移失败，开始回滚...")
    state = migrator.rollback()
    print(f"回滚完成: {state.is_rolled_back}")
    print(f"目标数据已清空: {len(migrator.target_data) == 0}")
```

### 自定义目标存储

```python
from solocoder_py.data_migration import DataMigrator

# 使用自定义字典作为目标存储
target = {}

migrator = DataMigrator(
    source_data=source_data,
    target_store=target,
    batch_size=20,
    id_extractor=lambda r: r["id"],
)

migrator.migrate()
assert len(target) == len(source_data)
```

### 重置迁移器

```python
migrator.migrate()
assert migrator.state.is_completed

migrator.reset()
assert migrator.state.status == MigrationStatus.IDLE
assert len(migrator.target_data) == 0
```

## 状态说明

### 批次状态

| 状态 | 说明 |
|------|------|
| `PENDING` | 待迁移，批次尚未开始 |
| `MIGRATING` | 迁移中，批次正在处理 |
| `COMPLETED` | 已完成，批次迁移成功 |
| `FAILED` | 失败，批次迁移失败 |
| `ROLLED_BACK` | 已回滚，批次数据已从目标移除 |

### 整体迁移状态

| 状态 | 说明 |
|------|------|
| `IDLE` | 空闲，尚未开始迁移 |
| `MIGRATING` | 迁移中，正在执行批次迁移 |
| `COMPLETED` | 已完成，所有批次迁移成功 |
| `FAILED` | 失败，某批次迁移失败 |
| `ROLLING_BACK` | 回滚中，正在执行批次回滚 |
| `ROLLED_BACK` | 已回滚，所有批次数据已移除 |

## 运行测试

```bash
poetry run pytest tests/data_migration/ -v
```
