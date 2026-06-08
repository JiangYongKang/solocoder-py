# 预写日志（Write-Ahead Log）域模块

## 模块功能

本模块实现了基于内存数据结构模拟的预写日志（Write-Ahead Log, WAL）域，支持以下核心能力：

1. **日志顺序追加**：日志条目按追加顺序分配单调递增的日志序列号（LSN），每次追加返回新 LSN，保证 LSN 的连续递增性。
2. **按 LSN 截断回收**：支持按指定 LSN 截断并回收之前的日志条目，截断点之前的条目不可再读取，截断后的最小可读 LSN 被准确维护。
3. **崩溃后重放恢复**：支持从指定 LSN 开始重放所有后续条目，重放时按追加顺序依次取出，可查询当前最小可读 LSN 和最大 LSN。
4. **日志条目持久化保证**：追加操作完成后日志条目即可读，在截断前即使发生崩溃也能靠重放恢复。
5. **截断安全校验**：不能截断超过当前最大 LSN 的位置，也不能截断已被回收的区间。截断后尝试读取已回收区间的条目返回明确错误。
6. **线程安全**：所有操作通过可重入锁保护，支持多线程并发访问。

## 核心类职责

### exceptions.py

| 类名 | 职责 |
|------|------|
| `WalError` | WAL 模块异常基类 |
| `TruncatedLsnError` | 尝试读取或重放已被截断的 LSN，携带请求 LSN 和当前最小可读 LSN |
| `InvalidTruncateLsnError` | 截断 LSN 不合法（小于最小可读 LSN 或大于最大 LSN），携带完整上下文 |
| `LsnNotFoundError` | 请求的 LSN 超出当前最大 LSN，携带有效范围 |
| `EmptyWalError` | 日志为空时进行不允许的操作（如读取、截断） |

### models.py

| 类名 | 职责 |
|------|------|
| `LogEntry` | 日志条目数据模型，包含 `lsn`（日志序列号）、`data`（任意数据载荷）、`created_at`（创建时间戳） |

### wal.py

| 类名 | 职责 |
|------|------|
| `WriteAheadLog` | 预写日志核心实现（线程安全），维护日志条目存储、LSN 分配、最小可读 LSN 跟踪，提供追加、读取、范围读取、重放、截断等操作 |

## WAL 追加与重放流程

### 追加流程

```
调用方
  │
  │ wal.append(data)
  ▼
WriteAheadLog.append(data)
  │
  │ ① 获取锁，进入临界区
  │ ② 分配 LSN = self._next_lsn（从 0 开始单调递增）
  │ ③ 构造 LogEntry(lsn, data, created_at=now)
  │    └── LogEntry.__post_init__ 校验 LSN >= 0
  │ ④ 将条目存入 self._entries[lsn]
  │ ⑤ self._next_lsn += 1，为下一次追加准备
  │ ⑥ 释放锁
  ▼
返回新分配的 LSN
```

**追加保证**：
- **原子性**：锁保护下 LSN 分配与条目存储一气呵成，无中间可见状态
- **持久性**（内存语义）：方法返回时条目已存在于内存结构中，可通过 `read()` 立即读取
- **LSN 连续性**：每次追加仅使 `_next_lsn` 增 1，保证 LSN 从 0 开始严格单调连续

### 读取流程

```
调用方
  │
  │ wal.read(lsn)
  ▼
WriteAheadLog.read(lsn)
  │
  │ ① 获取锁
  │ ② 若 WAL 为空 → EmptyWalError
  │ ③ 若 lsn < min_readable_lsn → TruncatedLsnError
  │ ④ 若 lsn > max_lsn → LsnNotFoundError
  │ ⑤ 返回 self._entries[lsn]
  ▼
LogEntry
```

### 重放流程

```
调用方
  │
  │ wal.replay(from_lsn?)
  ▼
WriteAheadLog.replay(from_lsn)
  │
  │ ① 获取锁
  │ ② 若 WAL 为空 → 返回空迭代器
  │ ③ 确定起始 LSN：from_lsn 或 min_readable_lsn
  │ ④ 若起始 LSN < min_readable_lsn → TruncatedLsnError
  │ ⑤ 若起始 LSN > max_lsn → 返回空迭代器
  │ ⑥ 从起始 LSN 开始按顺序收集 self._entries 中的条目
  │    （遇到不存在的 LSN 即停止，保证不跳过重放）
  │ ⑦ 释放锁
  ▼
Iterator[LogEntry]  —— 按追加顺序排列
```

**重放语义**：
- 重放顺序与追加顺序严格一致
- 重放结果是迭代器的快照，后续对 WAL 的修改不影响已返回的迭代器

### 截断流程

```
调用方
  │
  │ wal.truncate(lsn)
  ▼
WriteAheadLog.truncate(lsn)
  │
  │ ① 获取锁
  │ ② 若 WAL 为空 → EmptyWalError
  │ ③ 若 lsn < min_readable_lsn → InvalidTruncateLsnError（已回收区间）
  │ ④ 若 lsn > max_lsn → InvalidTruncateLsnError（超出当前范围）
  │ ⑤ 从 min_readable_lsn 到 lsn（含）逐个删除 self._entries 中的条目
  │ ⑥ 更新 self._min_readable_lsn = lsn + 1
  │ ⑦ 释放锁
  ▼
完成
```

**截断语义**：
- 截断是单向操作：被回收的 LSN 区间无法恢复
- 截断后 LSN 序列的连续性不变（LSN 不重新编号，只是部分不可读）
- 截断不会影响未来追加操作的 LSN 分配

## LSN 语义说明

- **LSN 编号**：从 `0` 开始，每次追加分配下一个连续整数
- **min_readable_lsn**：当前可读取的最小 LSN，初始为 `0`，每次截断到 `lsn` 后变为 `lsn + 1`
- **max_lsn**：当前已追加的最大 LSN，空 WAL 时为 `-1`
- **空 WAL 判定**：`is_empty = (_next_lsn == 0) 或 (min_readable_lsn > max_lsn)`，即"从未追加过"或"所有条目均已截断"

## 使用示例

### 基本追加与读取

```python
from solocoder_py.wal import WriteAheadLog

wal = WriteAheadLog()

# 顺序追加，返回单调递增的 LSN
lsn0 = wal.append({"op": "create", "id": 101, "name": "Alice"})
lsn1 = wal.append({"op": "deposit", "id": 101, "amount": 1000})
lsn2 = wal.append({"op": "withdraw", "id": 101, "amount": 200})
assert lsn0 == 0 and lsn1 == 1 and lsn2 == 2

# 读取单条
entry = wal.read(1)
assert entry.lsn == 1
assert entry.data["op"] == "deposit"

# 范围读取
entries = wal.read_range(0, 2)
assert [e.lsn for e in entries] == [0, 1, 2]

# 查询边界
assert wal.min_readable_lsn == 0
assert wal.max_lsn == 2
assert wal.is_empty is False
```

### 截断与回收

```python
wal = WriteAheadLog()
for i in range(10):
    wal.append(f"tx-{i}")

# 截断到 LSN=2（LSN 0、1、2 被回收）
wal.truncate(2)

assert wal.min_readable_lsn == 3
entry = wal.read(3)
assert entry.data == "tx-3"

# 读取已回收 LSN 会报错
from solocoder_py.wal import TruncatedLsnError
try:
    wal.read(2)
except TruncatedLsnError as e:
    print(f"LSN {e.lsn} 已回收，最小可读 LSN = {e.min_readable_lsn}")

# 不能截断已回收或超出范围的 LSN
from solocoder_py.wal import InvalidTruncateLsnError
try:
    wal.truncate(0)   # 已回收
except InvalidTruncateLsnError:
    pass

try:
    wal.truncate(999)  # 超出 max_lsn
except InvalidTruncateLsnError:
    pass
```

### 崩溃后重放恢复

```python
# 模拟：系统运行中记录了一批事务
wal = WriteAheadLog()
wal.append({"tx": 1, "status": "commit"})
wal.append({"tx": 2, "status": "commit"})
wal.append({"tx": 3, "status": "prepare"})
wal.append({"tx": 4, "status": "commit"})

# 假设已经完成对 tx-1 的 checkpoint，截断之
wal.truncate(0)

# ===== 模拟崩溃重启 =====
# 从最小可读 LSN 开始重放所有事务
recovered_state = {}
for entry in wal.replay():
    tx_id = entry.data["tx"]
    recovered_state[tx_id] = entry.data["status"]

assert recovered_state == {
    2: "commit",
    3: "prepare",
    4: "commit",
}

# 也可以从指定 LSN 开始重放
for entry in wal.replay(from_lsn=3):
    assert entry.lsn >= 3
```

### 线程安全并发追加

```python
import threading

wal = WriteAheadLog()
results = []
lock = threading.Lock()

def writer(start, count):
    local = []
    for i in range(count):
        lsn = wal.append(f"t{start}-{i}")
        local.append(lsn)
    with lock:
        results.extend(local)

threads = [threading.Thread(target=writer, args=(i, 50)) for i in range(4)]
for t in threads:
    t.start()
for t in threads:
    t.join()

# 所有 LSN 互不重复且覆盖 0..199
assert sorted(results) == list(range(200))
assert wal.max_lsn == 199
```

### 清空日志

```python
wal = WriteAheadLog()
wal.append("data")
wal.clear()

assert wal.is_empty is True
assert wal.min_readable_lsn == 0
assert wal.max_lsn == -1

# 清空后 LSN 重新从 0 开始
assert wal.append("new") == 0
```

## 运行测试

```bash
poetry run pytest tests/wal/ -v
```
