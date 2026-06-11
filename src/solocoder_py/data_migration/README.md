# 数据迁移执行域模块

## 模块功能

本模块实现了基于内存数据结构模拟的数据迁移执行域，支持以下核心能力：

1. **分批迁移**：将源数据按固定批次大小分割，逐批迁移到目标端。每批迁移完成后才开始下一批，系统记录每批的迁移状态。
2. **进度断点续传**：迁移过程中如果系统中断（模拟崩溃或重启），系统能从上次已完成的批次之后恢复迁移，不需要从头开始。检查点持久化记录当前已完成的批次位置和完整迁移状态。
3. **失败回滚**：如果某一批迁移执行失败，系统支持将该批次之前所有已迁移的数据回滚到迁移前的状态，保证目标端不保留不完整的数据。回滚操作也是分批执行的，与正向迁移的批次对应。
4. **回滚断点续传**：回滚过程中如果系统中断，重启后可以从断点继续回滚，确保最终能完全回滚。
5. **失败状态自动恢复**：如果中断前迁移处于失败或回滚中状态，恢复时自动触发完整回滚，确保数据一致性。
6. **灵活的扩展点**：支持自定义 ID 提取器、自定义批次迁移器、自定义批次回滚器、自定义检查点存储，可适配不同的数据源和目标存储。
7. **线程安全**：所有操作通过可重入锁保护，支持多线程并发访问。

## 核心类职责

### exceptions.py

| 类名 | 职责 |
|------|------|
| `DataMigrationError` | 数据迁移模块异常基类 |
| `BatchMigrationError` | 批次迁移失败异常，携带失败批次索引 |
| `RollbackError` | 回滚失败异常，携带失败批次索引 |
| `CheckpointError` | 检查点操作异常 |
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
| `CheckpointStore` | 检查点存储抽象基类，定义 save/load/load_state/clear 接口 |
| `InMemoryCheckpointStore` | 内存检查点存储实现，保存检查点和完整迁移状态 |
| `DataMigrator` | 数据迁移器核心类，管理分批迁移、断点续传、失败回滚的完整生命周期 |

## 检查点接口设计约定

### CheckpointStore 抽象接口

`CheckpointStore` 继承自 `abc.ABC`，所有四个方法均为 `@abstractmethod`，子类**必须**实现全部抽象方法，否则在实例化阶段即抛出 `TypeError`。这确保了任何自定义检查点存储在投入使用前就满足完整契约，不会出现运行时因未实现方法而被静默绕过的情况。

```python
from abc import ABC, abstractmethod

class CheckpointStore(ABC):
    @abstractmethod
    def save(self, checkpoint: int, state: MigrationState) -> None:
        """保存当前检查点和完整迁移状态"""

    @abstractmethod
    def load(self) -> Optional[int]:
        """加载最近保存的检查点（批次索引），返回 None 或 -1 表示无检查点"""

    @abstractmethod
    def load_state(self) -> Optional[MigrationState]:
        """加载最近保存的完整迁移状态，用于检测失败/回滚状态"""

    @abstractmethod
    def clear(self) -> None:
        """清除所有检查点数据"""
```

### 接口契约强制约束

- **实例化校验**：未实现全部抽象方法的子类在 `__init__` 阶段即报 `TypeError`，无法创建实例。例如只实现了 `save` 而缺少 `load_state` 的类会直接报错。
- **`load_state` 不可省略**：`load_state` 是自动检测失败/回滚状态的关键方法。如果实现返回 `None`，则从失败状态恢复时无法自动触发回滚（不会报错，但回滚自动检测机制失效）。因此建议始终返回完整的 `MigrationState` 对象。
- **不依赖具体子类类型判断**：`DataMigrator` 通过统一的抽象接口与检查点存储交互，不使用 `isinstance` 判断具体子类类型。任何符合 `CheckpointStore` 接口的实现都可以无缝替换。

### 状态完整性

`save(checkpoint, state)` 方法同时接收批次索引和完整 `MigrationState` 对象。实现应同时持久化这两部分信息，确保恢复时能完整重建迁移上下文。

### 检查点更新时机

- 每批迁移**成功**完成后，更新检查点
- 迁移**失败**时，也会更新检查点（持久化失败状态）
- 每批回滚**成功**完成后，更新检查点
- 回滚**失败**时，也会更新检查点（持久化失败状态）

### 自定义检查点存储示例

```python
from solocoder_py.data_migration import CheckpointStore, MigrationState
import json

class FileCheckpointStore(CheckpointStore):
    def __init__(self, filepath: str):
        self.filepath = filepath

    def save(self, checkpoint: int, state: MigrationState) -> None:
        data = {
            "checkpoint": checkpoint,
            "state": state.to_dict()  # 需要自行实现序列化
        }
        with open(self.filepath, "w") as f:
            json.dump(data, f)

    def load(self) -> Optional[int]:
        try:
            with open(self.filepath, "r") as f:
                data = json.load(f)
            return data["checkpoint"]
        except FileNotFoundError:
            return None

    def load_state(self) -> Optional[MigrationState]:
        try:
            with open(self.filepath, "r") as f:
                data = json.load(f)
            return MigrationState.from_dict(data["state"])  # 需要自行实现反序列化
        except FileNotFoundError:
            return None

    def clear(self) -> None:
        import os
        if os.path.exists(self.filepath):
            os.remove(self.filepath)
```

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
  │        ├── 保存检查点（含完整状态）
  │        └── 失败：状态设为 FAILED，保存检查点（含失败状态），抛出异常
  │ ④ 全部成功：状态设为 COMPLETED
  │ ⑤ 中途失败：状态设为 FAILED，记录失败批次，保存检查点
  ▼
返回 MigrationState
```

**分批保证**：
- **原子性**：每个批次的迁移作为一个整体，要么全部成功，要么全部失败
- **顺序性**：批次按索引顺序依次迁移，前一批完成后才开始下一批
- **可观测性**：每批迁移后更新检查点并持久化，失败时也持久化失败状态

### 断点续传机制

检查点（checkpoint）记录了最后一个成功完成的批次索引。迁移过程中每完成一个批次就更新并保存检查点（包括完整的迁移状态）。

重启后恢复流程（`resume_from_checkpoint`）：

1. 从检查点存储中加载 checkpoint 值
2. 加载完整的迁移状态（通过 `load_state()`）
3. **失败恢复路径**：如果上次状态是 `FAILED` 或 `ROLLING_BACK`，仅恢复批次状态标记（不写数据），然后自动触发回滚
4. **正常续传路径**：恢复迁移状态，标记 0..checkpoint 批次为已完成，**同时将这些批次的数据写回目标存储**，然后从 checkpoint + 1 批次继续迁移

### 状态与数据一致性保证

**核心原则**：断点恢复时，迁移状态（metadata）与目标存储数据（payload）必须保持一致。

**差异化恢复策略**：

`_restore_migration_state(checkpoint, write_data)` 方法根据恢复场景采用不同策略：

| 恢复场景 | `write_data` | 0..checkpoint 批次状态 | checkpoint+1..N 批次状态 | 原因 |
|----------|-------------|----------------------|-------------------------|------|
| 正常续传 | `True` | 设为 COMPLETED，**并**写回数据 | 保持 PENDING | 目标存储可能为空，需要补全数据保持一致性；后续批次尚未迁移 |
| 失败恢复 → 回滚 | `False` | 设为 COMPLETED | 保持 PENDING（失败批次为 FAILED） | 数据即将被回滚删除，避免无效写删循环 |
| 回滚断点续传 | `False` | 设为 COMPLETED | 设为 ROLLED_BACK | 这些批次已经回滚完成，状态应与实际一致 |

**正常续传路径的数据一致性**：
- 当目标存储是非持久化的（如内存字典），恢复时自动重写已完成批次的数据，确保状态与数据一致
- 当目标存储本身是持久化的（如数据库），且数据在中断后仍然存在，重写操作要求自定义 `batch_migrator` 保证幂等性

**失败恢复路径的效率保证**：
- 在检测到上次迁移处于失败状态时，系统只恢复批次状态标记（`completed_batches`、`checkpoint`、各批次 `status`），不做无效的数据写入
- 随后 `rollback()` 基于恢复的状态标记，仅回滚目标存储中实际存在的数据
- 避免了"先写入已完成批次数据 → 紧接着回滚删除同一批数据"的无效写删循环

**回滚断点续传的状态完整性**：
- 回滚中断恢复时，checkpoint 之前的批次标记为 COMPLETED（尚未回滚），checkpoint 之后的批次标记为 ROLLED_BACK（已回滚）
- 这样 `rollback()` 只需从 checkpoint 位置继续逆序回滚，无需重复处理已回滚的批次
- 整条路径上 `write_data=False`，不会向目标存储写入任何数据，完全由 `rollback()` 负责删除操作

**使用约定**：
1. 如果目标存储本身是持久化的（如数据库、文件系统），且可以保证在系统中断后数据仍然存在，建议将同一持久化目标存储传递给新的 migrator 实例，避免不必要的重复写入
2. 如果目标存储是非持久化的（如内存字典），或者无法保证数据完整性，正常续传路径会自动重写数据，确保一致性
3. 自定义 `batch_migrator` 必须保证幂等性，即同一批数据多次写入的结果与单次写入相同

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

### 断点续传（持久化目标存储）

```python
from solocoder_py.data_migration import InMemoryCheckpointStore

checkpoint_store = InMemoryCheckpointStore()
target_store = {}  # 实际场景中目标存储应持久化

# 第一次迁移，中途中断
migrator1 = DataMigrator(
    source_data=source_data,
    target_store=target_store,
    batch_size=10,
    checkpoint_store=checkpoint_store,
    id_extractor=lambda r: r["id"],
)
migrator1.migrate_next_batch()
migrator1.migrate_next_batch()
print(f"中断时检查点: {migrator1.state.checkpoint}")  # 1
print(f"目标数据量: {len(target_store)}")  # 20

# 系统重启后，从断点继续
migrator2 = DataMigrator(
    source_data=source_data,
    target_store=target_store,  # 传入已持久化的目标存储
    batch_size=10,
    checkpoint_store=checkpoint_store,
    id_extractor=lambda r: r["id"],
)
state = migrator2.resume_from_checkpoint()
print(f"恢复后状态: {state.status}")  # COMPLETED
print(f"总完成批次: {state.completed_batches}")
print(f"最终目标数据量: {len(target_store)}")  # 100
```

### 断点续传（非持久化目标存储）

即使目标存储没有持久化，恢复机制也能保证数据一致性：

```python
checkpoint_store = InMemoryCheckpointStore()

# 第一次迁移，中途中断（目标存储是临时内存字典）
migrator1 = DataMigrator(
    source_data=source_data,
    batch_size=10,
    checkpoint_store=checkpoint_store,
    id_extractor=lambda r: r["id"],
)
migrator1.migrate_next_batch()
migrator1.migrate_next_batch()

# 系统重启，创建全新的 migrator（目标存储是空的）
migrator2 = DataMigrator(
    source_data=source_data,
    batch_size=10,
    checkpoint_store=checkpoint_store,
    id_extractor=lambda r: r["id"],
)

# resume_from_checkpoint 会自动重写已完成批次的数据
state = migrator2.resume_from_checkpoint()
print(f"目标数据量: {len(migrator2.target_data)}")  # 100（自动补全）
```

### 失败回滚

```python
from solocoder_py.data_migration import BatchMigrationError

target_store = {}

def unreliable_batch_migrator(records):
    for record in records:
        if record["id"] == 42:
            raise RuntimeError("目标系统故障")
        target_store[record["id"]] = record

migrator = DataMigrator(
    source_data=source_data,
    target_store=target_store,
    batch_size=10,
    id_extractor=lambda r: r["id"],
    batch_migrator=unreliable_batch_migrator,
)

try:
    migrator.migrate()
except BatchMigrationError as e:
    print(f"批次 {e.batch_index} 迁移失败，开始回滚...")
    state = migrator.rollback()
    print(f"回滚完成: {state.is_rolled_back}")
    print(f"目标数据已清空: {len(target_store) == 0}")
```

### 从失败状态自动恢复

系统中断时如果迁移处于失败状态，恢复时自动触发回滚：

```python
checkpoint_store = InMemoryCheckpointStore()
target_store = {}
fail_count = [0]

def sometimes_failing_migrator(records):
    for record in records:
        if record["id"] == 42 and fail_count[0] == 0:
            fail_count[0] += 1
            raise RuntimeError("目标系统临时故障")
        target_store[record["id"]] = record

# 第一次迁移失败
migrator1 = DataMigrator(
    source_data=source_data,
    target_store=target_store,
    batch_size=10,
    checkpoint_store=checkpoint_store,
    id_extractor=lambda r: r["id"],
    batch_migrator=sometimes_failing_migrator,
)

try:
    migrator1.migrate()
except BatchMigrationError:
    print("迁移失败，系统中断...")

# 系统重启后，恢复时自动检测到失败状态并回滚
migrator2 = DataMigrator(
    source_data=source_data,
    target_store=target_store,
    batch_size=10,
    checkpoint_store=checkpoint_store,
    id_extractor=lambda r: r["id"],
    batch_migrator=sometimes_failing_migrator,
)

state = migrator2.resume_from_checkpoint()
print(f"自动回滚完成: {state.is_rolled_back}")  # True
print(f"目标数据已清空: {len(target_store) == 0}")  # True

# 现在可以重新尝试迁移（fail_count 已重置，或者问题已修复）
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
