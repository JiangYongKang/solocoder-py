# MVCC 内存多版本存储域模块

## 模块功能

本模块实现了基于内存数据结构模拟的多版本并发控制（MVCC）键值存储，支持以下核心能力：

1. **多版本写入**：每个 key 的每次写操作生成一个新版本，版本号全局单调递增；读操作可指定读取特定历史版本。
2. **快照隔离读**：读取操作可获取一个快照版本号，该快照下仅能读取快照创建时已提交的数据，无法看到未提交或后续提交的数据。
3. **写写冲突检测**：当两个并发事务对同一个 key 进行写操作时，后提交的事务会检测其起始版本与当前最新已提交版本是否一致，不一致则检测到冲突并回滚。
4. **事务提交与回滚**：事务内的写操作在提交前对其他事务不可见；提交后版本生效，回滚时该事务的所有变更被撤销，不影响其他事务。
5. **旧版本回收（GC）**：当没有活跃事务或快照需要读取某个旧版本时，该版本可被安全回收；回收策略保证不会误删仍在使用中的版本。
6. **删除操作**：支持删除 key，删除以墓碑（tombstone）版本形式记录，保留历史可追溯。

## 核心类职责

### exceptions.py

| 类名 | 职责 |
|------|------|
| `MVCCError` | MVCC 模块异常基类 |
| `TransactionError` | 事务相关异常基类 |
| `TransactionStateError` | 事务状态非法（如对已提交事务执行写入） |
| `WriteWriteConflictError` | 写写冲突，两个并发事务修改同一 key |
| `VersionNotFoundError` | 指定版本不存在 |
| `VersionReclaimedError` | 指定版本已被垃圾回收 |
| `KeyNotFoundError` | 指定 key 不存在（或已被删除） |
| `SnapshotInvalidError` | 快照版本非法 |

### models.py

| 类名 | 职责 |
|------|------|
| `TransactionStatus` | 事务状态枚举：`ACTIVE`（活跃）、`COMMITTED`（已提交）、`ABORTED`（已回滚） |
| `Version` | 版本记录数据模型：记录 key、value、版本号、所属事务 ID、是否为墓碑 |
| `Snapshot` | 快照数据模型：记录快照版本号和创建时的活跃事务 ID 列表，提供 `is_visible()` 判断版本可见性 |
| `Transaction` | 事务数据模型：记录事务 ID、起始版本、状态、事务内写入缓冲区、提交版本；提供提交/回滚状态变更方法 |

### store.py

| 类名 | 职责 |
|------|------|
| `MVCCStore` | MVCC 存储引擎，线程安全，维护多版本数据、事务表、活跃快照；提供事务开始/提交/回滚、读写、快照创建/释放、版本查询、垃圾回收等核心操作 |

## MVCC 可见性规则

### 版本可见性判断

对于版本 `V` 和快照 `S`（或事务 T 的起始快照）：

```
版本 V 可见 当且仅当：
  1. V.version <= S.snapshot_version   （版本不晚于快照）
  AND
  2. V.transaction_id NOT IN S.active_transactions  （版本所属事务在快照创建时已提交/回滚）
  AND
  3. NOT V.is_tombstone  （版本不是删除墓碑）
```

### 快照隔离语义

- **读取不阻塞写入，写入不阻塞读取**：读操作基于快照，写操作创建新版本，互不干扰。
- **事务内读已快照**：事务 T 内的读操作基于 T 的 `start_version` 创建的快照，事务执行期间该快照保持稳定，不受其他事务提交影响。
- **事务内写可见**：事务 T 可以读取自己写入但尚未提交的数据（读己之写）。
- **不可重复读被避免**：同一事务内两次读取同一 key 结果一致（除非事务自身修改了该 key）。
- **幻读不做特殊处理**：本模块为单 key 粒度，不涉及范围扫描，因此不处理幻读。

## 事务冲突处理流程

```
Txn-A: begin()
       read(key1) → v0
       write(key1, vA)
       ────────────────────────────────────────────
       冲突检测：key1 最新已提交版本 > Txn-A.start_version ?
                         │
              ┌──────────┴──────────┐
              │ 否                   │ 是
              ▼                      ▼
        commit() 成功           WriteWriteConflictError
        key1 新版本生效         事务回滚，写入被丢弃
```

### 冲突检测细节

1. 事务在 `begin()` 时获取 `start_version`。
2. 事务执行期间，所有写入缓存在事务本地，不对外可见。
3. `commit()` 时，对事务内每个写入的 key：
   - 查找该 key 的最新已提交版本（排除未提交和已回滚的）。
   - 如果最新已提交版本 > `start_version`，说明在本事务执行期间有其他事务修改了该 key，触发 `WriteWriteConflictError`。
4. 所有 key 均无冲突，则分配 `commit_version`，将事务缓冲的写入物化为新版本，对外可见。

### 回滚流程

1. `rollback()` 检查事务状态必须为 `ACTIVE`。
2. 将事务状态标记为 `ABORTED`。
3. 清空事务本地写入缓冲区（不产生任何版本，其他事务完全不受影响）。

## 旧版本回收（GC）机制

### 安全版本计算

GC 首先确定一个安全版本 `safe_version`：

```
safe_version = min(
    min(所有活跃快照的 snapshot_version),
    min(所有活跃事务的 start_version)
)
如果没有活跃快照和活跃事务，则 safe_version = next_version（即所有版本均可回收）
```

所有版本号 `< safe_version` 的旧版本**可能**可以被回收。

### 回收策略

对每个 key 的版本链：

1. **非墓碑版本**：保留 `< safe_version` 范围内最新的那一个（保证快照至少能读到一个有效值），其余回收。
2. **墓碑版本**：如果存在更早的版本，则该墓碑可以回收（更早的版本可以被快照读到）；如果墓碑是最早的版本，则保留（防止误读到不存在的数据）。
3. **版本号 ≥ safe_version** 的版本一律保留（可能被活跃事务或快照访问）。

### 回收保证

- 活跃快照持有的 `snapshot_version` 会阻止该版本及更早的关键版本被回收。
- 活跃事务持有的 `start_version` 会阻止该版本及更早的关键版本被回收。
- 已回收的版本会被记录在 `_reclaimed_versions` 集合中，后续访问触发 `VersionReclaimedError`。

## 使用示例

### 基本读写与版本

```python
from solocoder_py.mvcc import MVCCStore

store = MVCCStore()

txn = store.begin_transaction()
store.write(txn, "user:1", {"name": "Alice", "age": 30})
cv1 = store.commit(txn)
print(f"Committed version: {cv1}")

txn2 = store.begin_transaction()
store.write(txn2, "user:1", {"name": "Alice", "age": 31})
cv2 = store.commit(txn2)

print(store.read("user:1"))             # 最新版本：age=31
print(store.read_version("user:1", cv1))  # 指定版本：age=30
```

### 快照隔离读

```python
from solocoder_py.mvcc import MVCCStore

store = MVCCStore()

txn = store.begin_transaction()
store.write(txn, "counter", 10)
store.commit(txn)

snap = store.create_snapshot()

txn2 = store.begin_transaction()
store.write(txn2, "counter", 20)
store.commit(txn2)

print(store.read("counter"))          # 20 (最新)
print(store.read("counter", snap))    # 10 (快照时间点的值)

store.release_snapshot(snap)
```

### 事务与写写冲突

```python
from solocoder_py.mvcc import MVCCStore, WriteWriteConflictError

store = MVCCStore()

txn_initial = store.begin_transaction()
store.write(txn_initial, "balance", 100)
store.commit(txn_initial)

txn_a = store.begin_transaction()
balance_a = store.transaction_read(txn_a, "balance")
store.write(txn_a, "balance", balance_a - 10)

txn_b = store.begin_transaction()
balance_b = store.transaction_read(txn_b, "balance")
store.write(txn_b, "balance", balance_b - 20)

store.commit(txn_a)
print(f"After A: balance = {store.read('balance')}")  # 90

try:
    store.commit(txn_b)
except WriteWriteConflictError:
    print("Txn-B aborted due to write-write conflict")
    store.rollback(txn_b)
```

### 旧版本回收

```python
from solocoder_py.mvcc import MVCCStore

store = MVCCStore()

for i in range(10):
    txn = store.begin_transaction()
    store.write(txn, "key", i)
    store.commit(txn)

print(f"Versions before GC: {len(store.get_versions('key'))}")  # 10

reclaimed = store.collect_garbage()
print(f"Reclaimed: {reclaimed}")

print(f"Versions after GC: {len(store.get_versions('key'))}")   # 1 (仅保留最新)
```

### 使用快照保护版本不被回收

```python
store = MVCCStore()

txn1 = store.begin_transaction()
store.write(txn1, "key", "v1")
cv1 = store.commit(txn1)

snap = store.create_snapshot()  # 持有旧版本

for i in range(2, 6):
    txn = store.begin_transaction()
    store.write(txn, "key", f"v{i}")
    store.commit(txn)

store.collect_garbage()
print(store.read("key", snap))  # v1（快照保护，未被回收）
print(store.read_version("key", cv1))  # v1

store.release_snapshot(snap)
store.collect_garbage()  # 现在旧版本可以被回收
```

## 运行测试

```bash
pytest tests/mvcc/ -v
```
