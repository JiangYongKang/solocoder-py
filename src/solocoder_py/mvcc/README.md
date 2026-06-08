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

## 版本号机制

### 版本号分配与消耗

本模块使用三种独立递增的计数器：

| 计数器 | 用途 | 分配时机 | 用户可见 |
|--------|------|----------|----------|
| `_next_version` | 数据版本号全局计数器 | 仅在事务 `commit()` 成功时分配，每个提交生成一个新的连续版本号 | **是**：`read_version()`、`Snapshot.snapshot_version`、`Version.version` 均使用此版本号 |
| `_next_transaction_id` | 事务 ID 全局计数器 | `begin_transaction()` 时分配，用于唯一标识事务 | 否：仅内部用于追踪事务状态 |
| `_committed_version` | 已提交的最大版本号 | `commit()` 成功后更新，始终等于最新成功提交的版本号 | 间接可见：`create_snapshot()` 快照版本等于此值 |

### 版本号连续性保证

**版本号没有空洞**：数据版本号只在事务成功提交时分配，每次提交严格 +1，因此版本号序列是严格连续的（1, 2, 3, ...）。用户通过 `read_version(key, N)` 读取时，任何正整数 N 要么是真实存在的已提交版本，要么报 `VersionNotFoundError`，不会遇到"看起来存在但实际不存在"的空洞版本号。

### start_version 的含义

事务 `Transaction.start_version` **不占用**任何真实数据版本号。它的值等于事务开始时的 `_committed_version`：

- `start_version = 0`：事务开始时尚未有任何已提交的数据（空库）。
- `start_version = N`：事务能看到截至版本 N 的所有已提交数据。

`start_version` 仅用于快照隔离判断（写写冲突检测、可见性判断），不是用户可通过 `read_version()` 读取的真实版本。

## 快照版本选取规则

`create_snapshot()` 返回的快照有两个关键属性：

- **`snapshot_id`**：每次调用分配的唯一递增 ID，用于内部追踪活跃快照。即使多次快照的版本号相同，它们也有独立的 `snapshot_id`，不会互相覆盖。释放其中一个快照不影响其他快照对旧版本的 GC 保护。
- **`snapshot_version`**：严格等于创建快照时当前已提交的最大版本号（`_committed_version`），确保：
  1. 快照仅包含创建时刻之前已成功提交的所有数据。
  2. 快照不会落在未提交事务占用的"占位"版本上（因为不存在占位版本）。
  3. 快照版本本身一定是一个真实的、已提交的、可通过 `read_version()` 访问的版本号（空库时为 0）。

快照创建时还会记录当时的活跃事务 ID 列表（`active_transactions`），用于排除那些在快照创建时已经开始但尚未提交的事务所做的写入。

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
如果没有活跃快照和活跃事务，则 safe_version = committed_version + 1（即所有已提交版本均可回收）
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

## 并发安全保证

### 线程安全机制

`MVCCStore` 的所有公共 API 均由 `threading.RLock`（可重入互斥锁）保护，确保多线程环境下的正确性：

- **锁范围**：每次 `begin_transaction`、`commit`、`rollback`、`read`、`write`、`create_snapshot`、`collect_garbage` 等公共操作都会先获取锁，执行完毕后释放。因此任意两个公共方法在多线程下**会互斥等待**，读与写之间、写与写之间、读与读之间都不会真正并发执行。
- **可重入性**：使用 `RLock` 而非普通 `Lock`，允许在持有锁的方法内部递归调用其他加锁方法（如 `commit` 内部调用 `_check_write_conflicts`）。
- **原子性**：`commit()` 的冲突检测、版本号分配、写入物化是一个原子操作，不会出现部分提交。
- **快照一致性**：`create_snapshot()` 原子地获取当前已提交版本和活跃事务列表，确保快照是自洽的。

> **说明**：虽然锁导致方法层面串行执行，但 MVCC 多版本机制仍然提供了重要的语义价值：写写冲突通过版本号检测而非锁超时来发现；快照读可以基于已创建的快照稳定读取历史版本，不受后续写入的影响（即 MVCC 的"快照隔离"语义在逻辑层面成立，只是物理上的方法调用被串行化了）。

### 并发场景下的隔离性

在多线程并发访问时，MVCC 快照隔离保证：

1. **快照读隔离**：一个线程持有的快照不会看到其他线程在快照创建后提交的数据。
2. **写写冲突检测**：两个线程同时修改同一 key 时，后提交者会因冲突被显式回滚（抛出 `WriteWriteConflictError`），不会出现丢失更新。
3. **事务读一致**：同一事务内多次读取结果一致，不会因为其他线程的提交而变化。
4. **GC 安全**：活跃快照和活跃事务会保护其需要的旧版本不被 GC 回收。

### 并发测试覆盖

测试文件 `tests/mvcc/test_mvcc_store.py` 中 `TestConcurrency` 类包含以下并发测试场景：

- `test_concurrent_writes_different_keys`：多线程写不同 key，验证无冲突时全部成功、冲突计数为 0、每个 key 值精确正确。
- `test_concurrent_writes_same_key_trigger_conflicts`：多线程竞争写同一 key，验证写写冲突正确触发且最终值合理。
- `test_concurrent_snapshot_reads_are_isolated`：快照读线程与写线程并发，验证快照值始终不变且无异常。
- `test_concurrent_mixed_operations`：读、写、快照创建/释放 15 个线程混合操作，验证无异常、写操作至少部分成功。
- `test_multiple_snapshots_same_version_not_overwritten`：同版本多个快照有独立 ID，释放一个不影响另一个。
- `test_release_one_snapshot_preserves_others_for_gc`：释放一个快照后，另一个同版本快照仍能保护旧版本不被回收。

## 运行测试

```bash
pytest tests/mvcc/ -v
```
