# 事件溯源聚合根存储域模块

## 模块功能

本模块实现了基于内存数据结构模拟的事件溯源（Event Sourcing）聚合根存储域，支持以下核心能力：

1. **聚合根事件追加**：每个聚合根拥有独立事件流，事件包含聚合 ID、事件类型、事件载荷、版本号和发生时间。追加事件时保证版本连续，不允许覆盖已有事件。
2. **从事件重建聚合状态**：支持按聚合 ID 读取全部事件并按顺序重放，恢复当前聚合状态。重放过程中校验事件顺序和版本号一致性。
3. **快照机制**：当事件数量达到阈值后自动创建快照，后续重建状态时从最近快照开始回放增量事件，避免每次从头重放。
4. **乐观并发版本校验**：写入方追加事件时需要提供期望版本，若当前版本与期望版本不一致则拒绝写入并返回明确错误，防止并发写入丢失。
5. **事件查询与审计**：支持按聚合 ID、版本范围和事件类型查询事件，保留事件追加顺序，便于审计追踪。

## 核心类职责

### exceptions.py

| 类名 | 职责 |
|------|------|
| `EventSourcingError` | 事件溯源模块异常基类 |
| `AggregateNotFoundError` | 聚合根不存在（读取/加载时） |
| `VersionConflictError` | 乐观并发版本冲突，携带期望版本与实际版本 |
| `EventVersionGapError` | 事件流中出现版本号断裂 |
| `EventOverwriteError` | 尝试覆盖已存在版本的事件 |
| `InvalidEventError` | 事件本身无效（如聚合 ID 不匹配） |
| `SnapshotNotFoundError` | 快照不存在 |

### models.py

| 类名 | 职责 |
|------|------|
| `DomainEvent` | 领域事件数据模型，记录 `aggregate_id`、`event_type`、`payload`、`version`、`occurred_at` |
| `Snapshot` | 快照数据模型，记录某一版本时刻聚合根的完整状态 |
| `AggregateRoot` | 聚合根抽象基类，提供事件应用、重放、快照序列化/反序列化、待提交事件管理等通用能力 |

### store.py

| 类名 | 职责 |
|------|------|
| `EventStore` | 事件存储中心（线程安全），维护所有聚合的事件流与快照，提供事件追加、读取、聚合加载/保存、快照管理、事件查询等操作 |

## 事件流与快照恢复流程

### 写入流程（追加事件 + 乐观并发控制）

```
调用方（聚合根）
    │
    │ 产生 pending_events（带连续版本号）
    ▼
EventStore.save_aggregate(aggregate)
    │
    │ 在单一线程锁保护下原子执行：
    │   ① 计算 expected_version = aggregate.version - len(pending)
    │   ② append_events(id, pending, expected_version)
    │      ├── 校验：存储当前版本 == expected_version → 否则 VersionConflictError
    │      ├── 校验：每个事件版本号连续且匹配 → 否则 EventVersionGapError
    │      ├── 校验：不覆盖已有事件 → 否则 EventOverwriteError
    │      └── 追加到事件流
    │   ③ 若 should_create_snapshot()，在内存中构造快照对象并保存
    │
    │ ④ 仅在上述步骤全部成功后，清除聚合根的 pending_events
    │    —— 任何异常均不会提前清除 pending_events，便于调用方重试
    ▼
完成
```

**save_aggregate 行为约定**：
- 原子性：事件追加与快照创建在同一把锁内完成，要么都成功，要么都不产生可见副作用（快照构造本身失败时事件同样已写入，由 `Snapshot` 的 `__post_init__` 校验保证构造失败前不会写入存储）。
- 幂等安全：无 `pending_events` 时直接返回，不做任何写入。
- 异常语义：抛异常时 `aggregate.pending_events` 保持不变，调用方可选择重新加载聚合后再次提交。

### 读取流程（从快照 + 增量事件恢复）

```
EventStore.load_aggregate(id, AggregateClass)
    │
    │ ① 获取最新快照 get_latest_snapshot(id)
    │
    ├── 有快照：
    │     ├── from_snapshot() 恢复到快照版本
    │     └── get_events(id, from_version=snapshot.version+1)
    │         重放增量事件
    │
    └── 无快照：
          └── get_events(id) 获取全部事件
              from_events() 从头重放
    ▼
返回完整状态的聚合根实例
```

**版本约束说明**：
- 事件版本号从 `1` 开始连续递增；`Snapshot.version` 允许为 `0`，表示"聚合创建前"的初始快照。
- `get_events(id, from_version=0)` 与省略 `from_version` 等价，返回所有事件（即从版本 1 起的完整事件流），与 `Snapshot.version == 0` 对齐使用。
- `get_events(id, to_version=0)` 返回空列表。
- `from_version` 与 `to_version` 均不允许为负数。

### 快照触发策略

- 配置 `snapshot_threshold`（默认 100）
- 每次 `save_aggregate` 后检查：
  - 无快照时：总事件数 >= 阈值 → 创建
  - 有快照时：(当前版本 - 最新快照版本) >= 阈值 → 创建

## 使用示例

### 定义聚合根

```python
from typing import Any, Dict
from solocoder_py.event_sourcing import AggregateRoot, DomainEvent


class BankAccount(AggregateRoot):
    def __init__(self, aggregate_id: str) -> None:
        super().__init__(aggregate_id)
        self._balance: int = 0
        self._owner: str = ""

    @classmethod
    def get_aggregate_type(cls) -> str:
        return "BankAccount"

    @property
    def balance(self) -> int:
        return self._balance

    @property
    def owner(self) -> str:
        return self._owner

    def _apply(self, event: DomainEvent) -> None:
        if event.event_type == "AccountOpened":
            self._owner = event.payload["owner"]
        elif event.event_type == "Deposited":
            self._balance += event.payload["amount"]
        elif event.event_type == "Withdrawn":
            self._balance -= event.payload["amount"]

    def get_snapshot_state(self) -> Dict[str, Any]:
        return {"balance": self._balance, "owner": self._owner}

    def restore_from_snapshot(self, state: Dict[str, Any], version: int) -> None:
        self._balance = state["balance"]
        self._owner = state["owner"]
        self._version = version

    def open(self, owner: str) -> None:
        self._record(DomainEvent(
            aggregate_id=self.id,
            event_type="AccountOpened",
            payload={"owner": owner},
            version=self.version + 1,
        ))

    def deposit(self, amount: int) -> None:
        self._record(DomainEvent(
            aggregate_id=self.id,
            event_type="Deposited",
            payload={"amount": amount},
            version=self.version + 1,
        ))

    def withdraw(self, amount: int) -> None:
        self._record(DomainEvent(
            aggregate_id=self.id,
            event_type="Withdrawn",
            payload={"amount": amount},
            version=self.version + 1,
        ))
```

### 基本使用

```python
from solocoder_py.event_sourcing import EventStore, VersionConflictError

store = EventStore(snapshot_threshold=10)

account = BankAccount("acc-001")
account.open("Alice")
account.deposit(1000)
account.withdraw(200)
store.save_aggregate(account)

loaded = store.load_aggregate("acc-001", BankAccount)
print(f"Owner: {loaded.owner}")      # Alice
print(f"Balance: {loaded.balance}")  # 800
print(f"Version: {loaded.version}")  # 3
```

### 乐观并发控制

```python
store = EventStore()

account = BankAccount("acc-002")
account.open("Bob")
store.save_aggregate(account)

session_a = store.load_aggregate("acc-002", BankAccount)
session_b = store.load_aggregate("acc-002", BankAccount)

session_a.deposit(500)
store.save_aggregate(session_a)  # 成功

session_b.deposit(300)
try:
    store.save_aggregate(session_b)
except VersionConflictError as e:
    print(f"冲突！期望版本 {e.expected_version}，实际版本 {e.actual_version}")
    # 重新加载后重试
    session_b = store.load_aggregate("acc-002", BankAccount)
    session_b.deposit(300)
    store.save_aggregate(session_b)
```

### 事件查询与审计

```python
# 查询单个聚合的所有事件
all_events = store.get_events("acc-001")

# 按版本范围查询
events_v2_to_v5 = store.get_events("acc-001", from_version=2, to_version=5)

# 按事件类型查询
deposit_events = store.get_events("acc-001", event_type="Deposited")

# 跨聚合全局查询
all_deposits = store.query_events(event_type="Deposited")

# 获取所有聚合 ID
ids = store.list_aggregate_ids()

# 检查聚合是否存在
exists = store.aggregate_exists("acc-001")

# 获取当前版本
version = store.get_current_version("acc-001")
```

### 快照手动管理

```python
# 手动创建快照
account = store.load_aggregate("acc-001", BankAccount)
snapshot = store.create_snapshot(account)

# 获取最新快照
latest = store.get_latest_snapshot("acc-001")
if latest:
    print(f"快照版本: {latest.version}")
    print(f"快照状态: {latest.state}")

# 获取指定版本或更早的快照
snap = store.get_snapshot_at_or_before("acc-001", version=5)
```

## 运行测试

```bash
pytest tests/event_sourcing/ -v
```
