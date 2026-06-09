# Ledger 双分录记账账本模块

## 模块功能

本模块实现了基于内存数据结构的双分录（Double-Entry Bookkeeping）记账账本系统，支持以下核心能力：

1. **账户管理**：每个账户有唯一标识、账户名称、账户类型和当前余额。支持创建账户、查询账户余额和账户交易历史。账户余额必须为非负数，不允许透支，除非明确标记为可透支账户。
2. **借贷平衡校验**：每笔交易包含至少一条借方分录和至少一条贷方分录，借方总金额必须等于贷方总金额。金额不平时拒绝交易。每笔交易有过账状态——暂存（draft）和已过账（posted），只有已过账的交易才会影响账户余额。
3. **原子转账**：一笔转账中的所有分录作为一个原子操作执行，要么全部分录过账成功，要么全部回滚。过账前先校验借贷平衡，再过账时对所有涉及账户按账户标识排序后依次加锁，避免死锁。
4. **并发余额一致性**：多个并发转账涉及相同账户时，通过锁机制保证余额读写的线性一致性。任何时刻查询账户余额都能看到截止当时所有已过账交易的完整结果，不会出现中间态。
5. **账本查询**：可以查询所有账户的当前余额、指定账户的交易分录明细（支持按时间范围和交易状态筛选）、以及整个账本的试算平衡表（所有借方总额是否等于所有贷方总额）。

## 核心类职责

### exceptions.py

| 类名 | 职责 |
|------|------|
| `LedgerError` | 账本模块异常基类 |
| `AccountError` | 账户相关异常基类 |
| `AccountNotFoundError` | 指定账户不存在 |
| `AccountExistsError` | 创建重复账户 |
| `OverdraftError` | 账户余额不足（透支） |
| `TransactionError` | 交易相关异常基类 |
| `TransactionNotFoundError` | 指定交易不存在（统一使用，而非通用 `ValueError`） |
| `TransactionStateError` | 交易状态非法（如对非暂存交易过账） |
| `TransactionBalanceError` | 交易借贷不平衡或缺少借方/贷方 |
| `DuplicatePostError` | 重复过账已过账交易 |
| `EntryValidationError` | 分录金额非法（负数） |

### models.py

| 类名/函数 | 职责 |
|-----------|------|
| `EntryType` | 分录类型枚举：`DEBIT`（借方）、`CREDIT`（贷方） |
| `TransactionStatus` | 交易状态枚举：`DRAFT`（暂存）、`POSTED`（已过账） |
| `AccountType` | 账户类型枚举：`ASSET`（资产）、`LIABILITY`（负债）、`EQUITY`（权益）、`REVENUE`（收入）、`EXPENSE`（费用） |
| `Account` | 账户数据模型：记录账户标识、名称、类型、是否可透支、当前余额、初始余额（`initial_balance`）；提供 `can_credit()`、`apply_debit()`、`apply_credit()`、`copy()` 方法 |
| `Entry` | 分录数据模型：记录分录 ID、所属账户、借贷类型、金额、描述、创建时间；提供 `copy()` 方法 |
| `Transaction` | 交易数据模型：记录交易 ID、分录列表、描述、创建时间、过账时间、状态；提供 `has_debit()`、`has_credit()`、`is_balanced`、`total_debit`、`total_credit`、`mark_posted()`、`copy()` 等方法 |
| `make_entry()` | 工厂函数，创建带唯一 ID 的分录 |
| `make_transaction()` | 工厂函数，创建带唯一 ID 的交易 |

### ledger.py

| 类名 | 职责 |
|------|------|
| `Ledger` | 账本引擎，线程安全，维护账户表、交易表、账户分录索引、`entry_id → transaction_id` 映射、账户锁；提供账户管理、交易创建、过账、转账、余额查询、分录查询、试算平衡等核心操作 |

## 异常类型约定

所有异常均继承自 `LedgerError`，形成统一的异常层次，调用方可通过捕获 `LedgerError` 一次性处理所有账本相关错误：

```
LedgerError
├── AccountError
│   ├── AccountNotFoundError   # 账户不存在
│   ├── AccountExistsError     # 创建重复账户
│   └── OverdraftError         # 透支（余额不足）
└── TransactionError
    ├── TransactionNotFoundError  # 交易不存在（已替代通用 ValueError）
    ├── TransactionStateError     # 交易状态非法
    ├── TransactionBalanceError   # 借贷不平衡或缺少借/贷方
    ├── DuplicatePostError        # 重复过账
    └── EntryValidationError      # 分录金额非法
```

- **账户不存在**：`get_account()`、`get_balance()` 抛出 `AccountNotFoundError`
- **交易不存在**：`get_transaction()`、`post_transaction()` 抛出 `TransactionNotFoundError`
- 两者均属于 `LedgerError` 子类，调用方可以 `except LedgerError` 统一捕获

## 借贷语义与平衡校验规则

### 借贷方向语义

本模块采用简化的双分录记账模型：

- **借方（DEBIT）**：账户余额增加（+）
- **贷方（CREDIT）**：账户余额减少（-）
- **透支校验**：仅在贷方（减少余额）操作时触发，不可透支账户的余额不允许小于 0

> 注意：这是一个教学/简化模型。真实会计中不同类型账户的借贷方向含义不同（资产/费用类借增贷减，负债/权益/收入类借减贷增）。本模块统一使用借增贷减以便于理解。

### 借贷平衡校验

每笔交易在过账前必须通过以下校验，否则抛出 `TransactionBalanceError`：

1. **至少一条借方分录**：`transaction.has_debit()` 必须为 `True`
2. **至少一条贷方分录**：`transaction.has_credit()` 必须为 `True`
3. **借贷总金额相等**：`transaction.total_debit == transaction.total_credit`

### 交易状态流转

```
DRAFT (暂存) ──post_transaction()──► POSTED (已过账)
       │                                    │
       │  不影响账户余额                      │  已影响账户余额
       │  可被过账                            │  不可重复过账
       ▼                                    ▼
```

- 创建交易时初始状态为 `DRAFT`，不影响任何账户余额
- 调用 `post_transaction()` 成功后状态变为 `POSTED`，全部分录生效
- 已过账交易不可再次过账，否则抛出 `DuplicatePostError`

## 原子转账与回滚机制

### 过账流程

`post_transaction(transaction_id)` 的执行流程：

```
1. 全局锁保护下读取交易并校验：
   - 交易必须存在
   - 状态必须为 DRAFT
   - 必须同时有借方和贷方分录
   - 借贷总金额必须相等
   - 所有涉及账户必须存在

2. 释放全局锁，按账户 ID 排序后依次获取所有涉及账户的锁

3. 持有账户锁后，再次检查交易是否已被过账（防止并发重复过账）

4. 透支预检查：对所有 CREDIT（减少余额）分录检查账户余额是否充足

5. 按顺序应用分录：
   - DEBIT 分录：调用 account.apply_debit(amount)，余额增加
   - CREDIT 分录：调用 account.apply_credit(amount)，余额减少
   - 每条分录应用前记录原余额，用于回滚

6. 任一分录应用失败（如透支）时：
   - 按逆序将所有已应用分录的账户余额恢复到原余额
   - 抛出异常，交易状态保持 DRAFT

7. 全部成功后：
   - 将交易状态标记为 POSTED，记录过账时间
   - 返回交易对象
```

### 死锁避免

当两笔或多笔交易涉及相同的一组账户时，如果获取锁的顺序不一致可能导致死锁。例如：

- 交易 A：先锁账户 1，再锁账户 2
- 交易 B：先锁账户 2，再锁账户 1

这会形成经典的 ABBA 死锁。本模块通过 `_lock_accounts()` 方法确保**所有交易都按账户标识的字典序排序后依次获取锁**，从而彻底避免死锁。

## 并发一致性保证策略

### 双层锁架构

本模块使用两层锁来平衡并发性能与一致性：

| 锁 | 保护范围 | 用途 |
|----|----------|------|
| `_global_lock` (`threading.RLock`) | 账户字典、交易字典、账户分录索引、账户锁字典 | 保护数据结构的结构性变更（新增账户、新增交易、查询账户/交易存在性） |
| 每个账户独立的 `threading.RLock` | 单个账户的余额字段 | 保护余额的并发读写一致性 |

### 关键原则

**永远不同时持有全局锁和账户锁**：这是避免死锁的核心设计。所有方法要么只持有全局锁做结构操作，要么只持有账户锁做余额操作，绝不在持有一种锁的同时请求另一种。

- `post_transaction()`：先用全局锁读取并校验交易和账户 → 释放全局锁 → 按序获取账户锁 → 执行余额变更和标记已过账
- `get_all_balances()`：先用全局锁快照账户 ID 列表 → 释放全局锁 → 按序获取所有账户锁 → 原子读取全部余额
- `get_balance()`：先用全局锁确认账户存在并获取引用 → 释放全局锁 → 获取该账户锁 → 读取余额（与 `post_transaction` 互斥，确保不会读到部分应用的中间态）
- `get_trial_balance()`：先用全局锁快照账户 ID、分录表、交易表、各账户 initial_balance → 释放全局锁 → 按序获取所有账户锁 → 读取余额并计算（与所有并发过账操作互斥，保证快照一致性）
- `get_account_entries()`：在全局锁下一次性完成账户存在性校验、`entry_id → transaction_id` 索引 O(1) 查找、交易筛选、返回副本构造

### 线性一致性保证

- **单账户余额查询（get_balance）**：读取余额时持有该账户锁，与 `post_transaction` 的余额写入互斥，因此任何时刻读取到的余额都是截至该时刻所有已完成过账交易的完整结果，绝不会读到部分分录已应用、部分未应用的中间态。
- **全局余额快照（get_all_balances / get_trial_balance）**：按账户 ID 排序同时持有所有账户锁，在持锁期间读取全部余额，保证快照是跨账户一致的——不会出现某些账户已反映某笔交易而另一些尚未反映的情况。
- **过账操作（post_transaction）**：对涉及的所有账户按 ID 排序获取账户锁，在持锁期间统一修改余额并标记交易 POSTED，释放锁后外界要么看到交易完全生效，要么完全未生效。
- **由于获取账户锁后才读取和修改余额，同一账户的所有读写操作是线性一致的**

## 试算平衡表校验逻辑

`get_trial_balance()` 提供的是**账户余额层面**的完整性验证，而非简单的单笔交易内部借贷相等校验（后者已在过账时保证）。返回值为四元组：

```
(total_debit_balances, total_credit_balances, balanced, account_details)
```

### 校验维度一：账户余额完整性（防篡改）

对每个账户，独立计算其期望余额，并与实际存储余额比对：

```
期望余额 = initial_balance + 该账户所有已过账 DEBIT 金额 - 该账户所有已过账 CREDIT 金额
integrity_ok = (期望余额 == 实际存储余额)
```

如果 `integrity_ok` 为 `False`，说明账户余额被外部直接修改（绕过账本 API），数据完整性已被破坏。

### 校验维度二：借贷余额平衡（会计恒等式）

- **借方余额合计**：所有余额为正的账户，其余额绝对值之和
- **贷方余额合计**：所有余额为负的账户，其余额绝对值之和
- 平衡条件：`total_debit_balances == total_credit_balances` 且所有账户 `integrity_ok` 均为 `True`

> 注意：要使借贷余额平衡，创建账户时的初始余额也应遵循会计恒等式（例如借记资产 1000 的同时贷记资本 1000），否则仅有正余额账户而无对应负余额账户，试算平衡将显示不平衡。

### account_details 结构

每个账户的明细为五元组：

| 位置 | 含义 |
|------|------|
| `[0]` | 该账户所有已过账 DEBIT 金额合计 |
| `[1]` | 该账户所有已过账 CREDIT 金额合计 |
| `[2]` | 当前存储的账户余额 |
| `[3]` | 根据分录重算得到的期望余额 |
| `[4]` | 完整性标志（`[2] == [3]`） |

## 封装保护

所有返回 `Account`、`Entry`、`Transaction` 对象的公共方法均返回对象的**深拷贝**，调用方对返回值的任何修改都不会影响账本内部状态：

- `create_account()`、`get_account()`、`list_accounts()` → 返回 `Account.copy()`
- `create_transaction()`、`create_multi_entry_transaction()`、`get_transaction()`、`list_transactions()`、`post_transaction()`、`transfer()` → 返回 `Transaction.copy()`
- `get_account_entries()` → 每个 `Entry` 和 `Transaction` 均返回副本

这防止了绕过账本 API 直接修改 `balance`、`status`、`amount` 等关键字段的风险。

## 分录索引与查询性能

为避免 `get_account_entries()` 在分录查询时对全量交易做 O(N²) 线性扫描，账本维护了一个 `_entry_to_transaction: Dict[str, str]` 哈希索引：

- **写入时建立索引**：每次 `create_transaction()` 或 `create_multi_entry_transaction()` 创建交易时，为每条分录建立 `entry_id → transaction_id` 映射
- **读取时 O(1) 查找**：查询分录所属交易时，直接通过索引字典定位，无需遍历所有交易
- **性能提升**：随着交易数量增长，查询耗时保持常数级，而非随数据量线性退化

## 使用示例

### 创建账户与简单转账

```python
from solocoder_py.ledger import Ledger

ledger = Ledger()

cash = ledger.create_account("cash", "现金", initial_balance=1000)
expense = ledger.create_account("expense", "办公费用")

txn = ledger.transfer(
    debit_account_id="expense",
    credit_account_id="cash",
    amount=300,
    description="购买办公用品",
)

print(ledger.get_balance("cash"))     # 700
print(ledger.get_balance("expense"))  # 300
print(txn.is_posted)                  # True
```

### 创建暂存交易后过账

```python
ledger.create_account("bank", "银行存款", initial_balance=5000)
ledger.create_account("revenue", "销售收入", initial_balance=0, allow_overdraft=True)

txn = ledger.create_transaction(
    debit_account_id="bank",
    credit_account_id="revenue",
    amount=1500,
    description="收到客户货款",
)

print(txn.is_draft)                    # True
print(ledger.get_balance("bank"))      # 5000（暂存不影响余额）

ledger.post_transaction(txn.transaction_id)
print(ledger.get_balance("bank"))      # 6500
print(ledger.get_balance("revenue"))   # -1500（可透支账户允许负余额）
```

### 多借多贷复杂交易

```python
ledger.create_account("inventory", "存货", initial_balance=0)
ledger.create_account("payable", "应付账款", initial_balance=0, allow_overdraft=True)

txn = ledger.create_multi_entry_transaction(
    entries=[
        ("inventory", EntryType.DEBIT, 5000, "采购入库"),
        ("bank", EntryType.CREDIT, 2000, "银行转账支付"),
        ("payable", EntryType.CREDIT, 3000, "剩余欠款"),
    ],
    description="采购存货，部分付款",
)
ledger.post_transaction(txn.transaction_id)

print(txn.is_balanced)          # True
print(txn.total_debit)          # 5000
print(txn.total_credit)         # 5000
```

### 查询与试算平衡

```python
# 查询所有账户余额
all_balances = ledger.get_all_balances()
for account_id, balance in sorted(all_balances.items()):
    print(f"{account_id}: {balance}")

# 查询指定账户的分录历史
entries = ledger.get_account_entries("cash")
for entry, txn in entries:
    print(f"{txn.created_at} [{entry.entry_type.value}] {entry.amount}: {entry.description}")

# 按状态和时间筛选
from solocoder_py.ledger import TransactionStatus
from datetime import datetime, timedelta
draft_entries = ledger.get_account_entries(
    "cash",
    status=TransactionStatus.DRAFT,
    start_time=datetime.now() - timedelta(days=1),
)

# 试算平衡表（账户余额层面的校验，非单笔交易层面）
total_debits, total_credits, balanced, account_details = ledger.get_trial_balance()
print(f"借方余额合计: {total_debits}, 贷方余额合计: {total_credits}, 平衡: {balanced}")

# account_details 提供每个账户的完整校验信息
for account_id, (total_dr, total_cr, stored_balance, expected_balance, integrity_ok) in account_details.items():
    print(f"账户 {account_id}: 借={total_dr}, 贷={total_cr}, "
          f"余额={stored_balance}, 期望={expected_balance}, 数据完整={integrity_ok}")
```

### 并发转账

```python
import threading

ledger = Ledger()
ledger.create_account("a", "账户A", initial_balance=100000)
ledger.create_account("b", "账户B", initial_balance=100000)

errors = []

def transfer_many(src, dst, count):
    try:
        for _ in range(count):
            ledger.transfer(src, dst, 1)
    except Exception as e:
        errors.append(e)

threads = [
    threading.Thread(target=transfer_many, args=("a", "b", 50000)),
    threading.Thread(target=transfer_many, args=("b", "a", 50000)),
]
for t in threads:
    t.start()
for t in threads:
    t.join()

assert len(errors) == 0
assert ledger.get_balance("a") == 100000
assert ledger.get_balance("b") == 100000
```

## 运行测试

```bash
poetry run pytest tests/ledger/ -q
```

测试覆盖以下场景：

- **正常流程**：账户创建、单笔记账、多分录交易过账、余额正确更新
- **边界条件**：零金额分录、多借多贷的复杂交易、所有账户刚好过账到零余额
- **异常分支**：借贷金额不平拒绝、重复过账已过账交易、并发转账的余额一致性、暂存交易不影响余额、透支校验
- **异常类型统一**：账户/交易不存在均抛出自定义 `LedgerError` 子类（`AccountNotFoundError` / `TransactionNotFoundError`），而非通用 `ValueError`
- **封装保护**：所有返回的 `Account`/`Transaction`/`Entry` 对象均为独立副本，修改返回值不影响账本内部状态
- **试算平衡表校验**：空账本、零初始余额转账、完整性检测（可发现外部篡改余额）、账户明细结构正确性
- **分录索引性能**：索引正确填充、索引查找较 O(N) 线性扫描有显著性能优势
- **并发一致性**：双向转账资金守恒、多账户无死锁、并发读写线性一致、并发透支校验准确
