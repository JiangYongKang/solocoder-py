# 防篡改审计日志模块

本模块提供基于哈希链的防篡改审计日志功能，支持事件记录、时间顺序校验、以及完整的完整性验证。所有日志条目通过密码学哈希形成链式结构，任何对历史条目的篡改都能被检测到。

## 模块功能

- **哈希链日志条目**：每条日志包含 SHA-256 哈希，由本条目的全部内容加上上一条目的哈希计算得出，形成不可分割的链式结构
- **时间顺序保护**：日志按时间顺序追加，新条目的时间戳不得早于上一条，防止历史插入
- **完整性验证**：支持对整个链或指定范围进行完整性校验，精确指出篡改发生的位置
- **内存存储**：使用内存数据结构存储，高性能，适合高吞吐审计场景
- **可测试时钟**：支持注入自定义时钟，便于单元测试

## 核心类与职责

### `AuditLogEntry`（[models.py](models.py)）

单条审计日志条目，`frozen` dataclass，字段不可修改：

| 字段 | 类型 | 说明 |
|---|---|---|
| `index` | `int` | 条目在链中的位置，从 0 开始 |
| `event_type` | `str` | 事件类型，如 "CREATE"、"UPDATE"、"DELETE" |
| `subject` | `str` | 操作主体，如用户、服务 |
| `target` | `str` | 操作对象，如资源、实体 |
| `timestamp` | `float` | Unix 时间戳，秒级 |
| `details` | `Any` | 可选的附加信息 |
| `previous_hash` | `str` | 上一条目的哈希值，创世条目为空字符串 |
| `hash` | `str` | 本条目的 SHA-256 哈希值 |

**关键方法**：
- `content_for_hash()`: 返回用于哈希计算的字符串，格式为 `index|event_type|subject|target|timestamp|details|previous_hash`
- `compute_hash()`: 计算并返回本条目的 SHA-256 哈希

### `AuditLogStore`（[store.py](store.py)）

审计日志存储与管理器，负责日志追加、哈希链维护和时间戳校验：

| 方法 | 说明 |
|---|---|
| `append(event_type, subject, target, details, timestamp)` | 追加新日志，自动计算哈希 |
| `get_entry(index)` | 获取指定索引的条目 |
| `get_entries(start, end)` | 获取指定范围的条目列表 |
| `get_all_entries()` | 获取全部条目 |
| `_unsafe_replace_entry(index, entry)` | 测试用方法，直接替换条目（用于模拟篡改） |

| 属性 | 说明 |
|---|---|
| `is_empty` | 链是否为空 |
| `length` | 链中条目数量 |
| `last_entry` | 最新一条目，空链返回 `None` |

### `AuditLogValidator`（[validator.py](validator.py)）

完整性验证器，负责验证哈希链的完整性和正确性：

| 方法 | 说明 |
|---|---|
| `verify_chain(entries, start, end)` | 验证指定范围的条目链，返回 `VerificationReport` |
| `verify_entry(entry, previous_hash)` | 验证单个条目 |

### `VerificationReport`（[models.py](models.py)）

验证结果报告：

| 字段 | 类型 | 说明 |
|---|---|---|
| `is_valid` | `bool` | 验证是否全部通过 |
| `total_entries` | `int` | 参与验证的条目总数 |
| `passed_ranges` | `List[tuple]` | 验证通过的范围列表，如 `[(0, 5), (8, 10)]` |
| `failed_ranges` | `List[tuple]` | 验证失败的范围列表 |
| `tampered_indices` | `List[int]` | 被篡改的条目索引列表 |
| `first_tampered_index` | `Optional[int]` | 第一个被篡改的条目索引 |
| `results` | `List[VerificationResult]` | 每个条目的详细验证结果 |

**关键方法**：
- `summary()`: 返回人类可读的验证摘要

### `VerificationResult`（[models.py](models.py)）

单个条目的验证结果：

| 字段 | 类型 | 说明 |
|---|---|---|
| `index` | `int` | 条目索引 |
| `valid` | `bool` | 是否通过验证 |
| `expected_hash` | `str` | 期望的哈希值 |
| `actual_hash` | `str` | 实际存储的哈希值 |
| `message` | `str` | 验证详情 |

### 异常类（[exceptions.py](exceptions.py)）

| 异常 | 触发场景 |
|---|---|
| `AuditLogError` | 所有异常的基类 |
| `EmptyAuditLogError` | 对空链执行不允许的操作 |
| `TimestampRegressionError` | 新条目的时间戳早于上一条 |
| `InvalidIndexError` | 访问的索引超出范围 |

## 哈希链结构

```
+-------------------+        +-------------------+        +-------------------+
|   Entry #0        |        |   Entry #1        |        |   Entry #2        |
|-------------------|        |-------------------|        |-------------------|
| index: 0          |        | index: 1          |        | index: 2          |
| event: "CREATE"   |        | event: "UPDATE"   |        | event: "DELETE"   |
| subject: "admin"  |   +--->| subject: "admin"  |   +--->| subject: "admin"  |
| target: "alice"   |   |    | target: "alice"   |   |    | target: "alice"   |
| timestamp: 1.0    |   |    | timestamp: 2.0    |   |    | timestamp: 3.0    |
| details: {...}    |   |    | details: {...}    |   |    | details: {...}    |
|                   |   |    |                   |   |    |                   |
| previous_hash: "" |   |    | previous_hash: H0 |   |    | previous_hash: H1 |
| hash: H0          +---+    | hash: H1          +---+    | hash: H2          |
+-------------------+        +-------------------+        +-------------------+
         |                            |                            |
         v                            v                            v
   SHA256(content                   SHA256(content                 SHA256(content
   + "")                            + H0)                           + H1)
```

**创世条目（Entry #0）**：
- `previous_hash = ""`（空字符串）
- `hash = SHA256("0|CREATE|admin|alice|1.0|...|")`

**后续条目（Entry #N）**：
- `previous_hash = hash(Entry #N-1)`
- `hash = SHA256("N|UPDATE|admin|alice|...|hash(Entry #N-1)")`

## 防篡改机制原理

### 1. 哈希链保证内容不可篡改

每个条目的哈希计算包含：
- 条目自身的所有字段（索引、事件类型、主体、对象、时间戳、详情）
- **上一个条目的哈希值**

这意味着：
- 修改任何条目的任何内容 → 该条目的哈希变化
- 该条目的哈希变化 → 下一条目的 `previous_hash` 不匹配
- 级联效应 → 从篡改点开始，后续所有条目都验证失败

### 2. 时间顺序保证不可插入

追加新条目时强制校验：
- 新条目时间戳 ≥ 上一条目时间戳
- 允许相等（同一时间点的多个事件）
- 禁止回退（`TimestampRegressionError`）

### 3. 覆盖篡改检测

即使攻击者修改条目内容后，同时更新该条目及其后续所有条目的哈希来"修复"链条，也能被检测：
- 除非攻击者拥有完整的原始链进行对比，否则无法知道"正确"的哈希值
- 验证时可从任意已知正确的点开始，后续条目如果被整体重新哈希也会暴露

## 完整性验证策略

### 全链验证

```
entries = store.get_all_entries()
report = validator.verify_chain(entries)
```

验证流程：
```
for entry in entries:
    1. 若不是第一条，检查 entry.previous_hash == 前一条.hash
    2. 基于 entry.content + 前一条.hash 重新计算期望哈希
    3. 检查 entry.hash == 期望哈希
    4. 如果任一检查失败：
        - 标记该条目为篡改
        - 记录 first_tampered_index
        - 后续所有条目标记为不可信（Chain broken）
```

### 范围验证

```
report = validator.verify_chain(entries, start=5, end=15)
```

- 从 `start` 条目前一个条目的哈希开始验证
- 验证 `[start, end)` 范围内的所有条目
- 适用于增量验证或分段验证场景

### 验证报告解读

假设链中有 10 条，第 3 条被篡改：

```python
report.is_valid              # False
report.first_tampered_index  # 3
report.tampered_indices      # [3, 4, 5, 6, 7, 8, 9]
report.passed_ranges         # [(0, 2)]
report.failed_ranges         # [(3, 9)]
report.summary()
# "Verification FAILED: 7 tampered entries (indices: 3, 4, 5, 6, 7, 8, 9). First tampered at index 3."
```

## 使用示例

### 基本使用

```python
from solocoder_py.auditlog import AuditLogStore, AuditLogValidator

# 创建日志存储
store = AuditLogStore()

# 追加日志
store.append(
    event_type="CREATE",
    subject="admin",
    target="user:alice",
    details={"role": "editor"},
)

store.append(
    event_type="UPDATE",
    subject="admin",
    target="user:alice",
    details={"role": "admin"},
)

store.append(
    event_type="LOGIN",
    subject="alice",
    target="system",
)

# 验证完整性
validator = AuditLogValidator()
entries = store.get_all_entries()
report = validator.verify_chain(entries)

if report.is_valid:
    print("审计日志完整，未被篡改")
else:
    print(f"发现篡改！第一个篡改点在索引 {report.first_tampered_index}")
    print(report.summary())
```

### 带自定义时钟（用于测试）

```python
from solocoder_py.seat.clock import ManualClock
from solocoder_py.auditlog import AuditLogStore

manual_clock = ManualClock(start_time=1_700_000_000.0)
store = AuditLogStore(clock=manual_clock)

# 控制时间流逝
store.append(event_type="EVENT1", subject="user", target="res")
manual_clock.advance(3600)  # 推进 1 小时
store.append(event_type="EVENT2", subject="user", target="res")
```

### 模拟篡改与验证

```python
from dataclasses import replace
from solocoder_py.auditlog import AuditLogStore, AuditLogValidator

store = AuditLogStore()
for i in range(5):
    store.append(
        event_type=f"EVENT_{i}",
        subject=f"user_{i}",
        target=f"resource_{i}",
    )

# 模拟篡改：修改索引 2 的事件类型
entries = store.get_all_entries()
tampered = replace(entries[2], event_type="TAMPERED_EVENT")
store._unsafe_replace_entry(2, tampered)

# 验证
validator = AuditLogValidator()
report = validator.verify_chain(store.get_all_entries())

assert report.is_valid is False
assert report.first_tampered_index == 2
assert 2 in report.tampered_indices
assert 3 in report.tampered_indices  # 后续条目也不可信
```

### 显式指定时间戳

```python
store = AuditLogStore()

# 手动指定时间戳
t = 1_700_000_000.0
store.append(
    event_type="EVENT",
    subject="user",
    target="res",
    timestamp=t,
)

# 同一时间戳允许（高并发场景）
store.append(
    event_type="EVENT2",
    subject="user2",
    target="res2",
    timestamp=t,  # 允许相等
)

# 时间戳回退会被拒绝
try:
    store.append(
        event_type="EVENT3",
        subject="user3",
        target="res3",
        timestamp=t - 100,  # 早于上一条
    )
except TimestampRegressionError as e:
    print(f"时间戳回退被拒绝：{e}")
```

## 单元测试

测试位于 [tests/auditlog/](../../../tests/auditlog/)，覆盖：

- **正常流程**：哈希链形成、完整性验证通过、时间戳递增
- **边界条件**：空链验证、单条目验证、时间戳相等、2000 条性能测试
- **异常分支**：篡改检测、时间戳回退、创世条目篡改、多点篡改、哈希覆盖攻击

运行测试：
```bash
python -m pytest tests/auditlog/ -v
```
