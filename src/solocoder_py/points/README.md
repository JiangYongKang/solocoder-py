# Points 积分账户域模块

## 模块功能

本模块实现了基于内存数据结构的积分账户域功能，支持以下核心能力：

1. **积分账户基本操作**：创建账户、获取积分、消耗积分、冻结积分、解冻积分、消费冻结积分，每个操作均校验积分余额是否充足。
2. **批次管理（FEFO）**：每笔积分入账作为一个独立批次，记录其积分数量和过期时间。消耗/冻结积分时按照「先到期先扣减」（First Expire, First Out）规则，从最早到期的批次开始依次扣除。
3. **过期回收**：支持按需或批量扫描已过期但尚未消耗的积分批次，将其从可用余额中回收，并记录回收日志。已冻结的积分不会被过期回收。
4. **线程安全**：使用细粒度的账户级锁 + 全局结构锁的双层锁架构，支持高并发场景下的余额一致性。

## 核心类职责

### exceptions.py

| 类名 | 职责 |
|------|------|
| `PointsError` | 积分模块异常基类 |
| `AccountError` | 账户相关异常基类 |
| `AccountNotFoundError` | 指定账户不存在 |
| `AccountExistsError` | 创建重复账户 |
| `InsufficientPointsError` | 可用积分余额不足 |
| `PointsExpiredError` | 积分已过期 |
| `InvalidAmountError` | 积分数额非法（负数或零） |
| `FreezeNotFoundError` | 指定冻结记录不存在 |
| `FreezeStateError` | 冻结记录状态非法（如对已解冻记录再次解冻） |

### models.py

| 类名/函数 | 职责 |
|-----------|------|
| `FreezeStatus` | 冻结状态枚举：`FROZEN`（冻结中）、`CONSUMED`（已消费）、`UNFROZEN`（已解冻） |
| `PointsBatch` | 积分批次数据模型：批次ID、所属账户、总积分、剩余可用积分、已冻结积分、创建时间、过期时间；提供 `is_expired()`、`copy()` 等方法 |
| `FrozenRecord` | 冻结记录数据模型：冻结ID、所属账户、冻结总金额、状态、创建时间、各批次扣减明细；提供 `mark_consumed()`、`mark_unfrozen()`、`copy()` 等方法 |
| `ExpiredLog` | 过期回收日志：日志ID、所属账户、回收批次ID、回收积分数、回收时间 |
| `PointsAccount` | 积分账户元数据：账户ID、创建时间 |
| `make_batch()` | 工厂函数，创建带唯一ID的积分批次 |
| `make_frozen_record()` | 工厂函数，创建带唯一ID的冻结记录 |
| `make_expired_log()` | 工厂函数，创建带唯一ID的过期回收日志 |
| `make_account()` | 工厂函数，创建积分账户 |

### account.py

| 类名 | 职责 |
|------|------|
| `PointsAccountManager` | 积分账户管理器，线程安全，维护账户表、批次表、冻结记录表、过期回收日志、账户锁；提供账户创建、积分入账、积分查询、消耗、冻结/解冻、过期回收等核心操作 |

## 异常层次

```
PointsError
└── AccountError
    ├── AccountNotFoundError     # 账户不存在
    ├── AccountExistsError       # 创建重复账户
    ├── InsufficientPointsError  # 积分余额不足（所有批次剩余之和 < 请求额）
    ├── PointsExpiredError       # 积分已过期（剩余总额 ≥ 请求额，但可用 < 请求额）
    ├── InvalidAmountError       # 积分数额非法（负数或零）
    ├── FreezeNotFoundError      # 冻结记录不存在
    └── FreezeStateError         # 冻结状态非法（对已消费/已解冻记录重复操作）
```

所有异常均继承自 `PointsError`，调用方可通过捕获 `PointsError` 统一处理积分相关错误。

### 异常区分说明

`InsufficientPointsError` 与 `PointsExpiredError` 的区别：

| 场景 | `total_remaining` | `available` | 请求额 | 抛出异常 |
|------|-------------------|-------------|--------|----------|
| 账户完全没有足够积分 | 80 | 80 | 100 | `InsufficientPointsError` |
| 积分存在但全部过期 | 100 | 0 | 50 | `PointsExpiredError` |
| 部分积分过期，可用不够 | 100（50过期+50有效） | 50 | 80 | `PointsExpiredError` |
| 一切正常 | 100 | 100 | 50 | 正常扣减，无异常 |

其中 `total_remaining` = 所有批次 `remaining_points` 之和（含过期），`available` = 未过期批次 `remaining_points` 之和。

## 积分批次扣减规则（FEFO）

### 可用积分定义

一个账户的**可用积分** = 所有未过期批次的 `remaining_points` 之和。

注意：
- 已过期批次的积分不计入可用积分
- 已冻结的积分（`frozen_points`）不计入可用积分，但仍属于账户的总积分

### FEFO 扣减算法

消耗积分或冻结积分时，按以下步骤执行：

1. **筛选未过期批次**：过滤掉 `expired_at <= now` 的批次
2. **按过期时间升序排序**：过期时间越早，优先级越高
3. **依次扣减**：从排序后的第一个批次开始，用该批次的 `remaining_points` 尽可能多地抵扣所需金额，不足部分继续从下一批次扣除
4. **余额校验**：扣减前先校验可用积分总额是否充足，不足则抛出 `InsufficientPointsError`
5. **冻结特殊处理**：冻结操作会将积分从 `remaining_points` 转移到 `frozen_points`，不减少总积分

#### 示例

假设账户有以下 3 个批次：

| 批次 | 剩余积分 | 过期时间 |
|------|----------|----------|
| A    | 100      | 2025-01-10 |
| B    | 200      | 2025-01-20 |
| C    | 150      | 2025-02-01 |

若在 2025-01-05 消耗 250 积分，扣减顺序如下：
- 批次 A：扣除 100（剩余 0）
- 批次 B：扣除 150（剩余 50）
- 批次 C：不扣减

扣减后可用积分 = 50 + 150 = 200。

## 冻结与解冻机制

### 冻结

冻结操作将积分从「可用」状态转为「冻结」状态，冻结期间：
- 该部分积分不计入可用积分，不可被消耗
- 该部分积分不会被过期回收
- 账户总积分不变

冻结同样遵循 FEFO 规则，从最早到期批次开始冻结。冻结记录会精确记住每个批次被冻结的积分数。

### 解冻

解冻操作将冻结记录中的积分按原冻结明细精确返还到对应批次：
- 每个批次的 `frozen_points` 减少，`remaining_points` 等额增加
- 解冻后积分恢复为可用状态

### 消费冻结积分

消费冻结积分直接减少对应批次的 `frozen_points`，总积分减少。这用于「先冻结预授权，后确认扣款」的场景。

### 状态流转

```
FROZEN (冻结中) ──consume_frozen_points()──► CONSUMED (已消费)
       │
       └────unfreeze_points()──────────────► UNFROZEN (已解冻)
```

处于 `CONSUMED` 或 `UNFROZEN` 状态的冻结记录不可再次操作。

## 过期回收机制

### 回收规则

调用 `recycle_expired_points()` 时：
- 扫描所有（或指定账户）的批次
- 对满足 `is_expired() == true` 且 `remaining_points > 0` 的批次，将其剩余可用积分清零
- 已冻结的积分（`frozen_points`）**不会被回收**
- 每次回收生成一条 `ExpiredLog` 记录

### 幂等性

过期回收是幂等操作：同一批次已被回收后再次扫描不会产生新的回收日志。

### 使用方式

- **按需回收**：`manager.recycle_expired_points(account_id="user-1")` 回收指定账户
- **全局回收**：`manager.recycle_expired_points()` 回收所有账户
- **定时回收**：可结合调度器周期性调用全局回收

## 并发一致性保证

采用与 `ledger` 模块类似的双层锁架构：

| 锁 | 保护范围 |
|----|----------|
| `_global_lock` (`threading.RLock`) | 账户字典、批次字典、冻结记录字典、日志字典、账户锁字典 |
| 每个账户独立的 `threading.RLock` | 单个账户的批次余额读写 |

**核心原则**：永远不同时持有全局锁和账户锁。所有公共方法要么只持有全局锁做结构操作，要么只持有账户锁做余额操作。

## 封装保护

所有返回 `PointsAccount`、`PointsBatch`、`FrozenRecord`、`ExpiredLog` 对象的公共方法均返回对象的深拷贝，调用方对返回值的任何修改不会影响管理器内部状态。

## 使用示例

### 创建账户与积分入账

```python
from datetime import datetime, timedelta
from solocoder_py.points import PointsAccountManager

manager = PointsAccountManager()

account = manager.create_account("user-001")

now = datetime.now()
manager.add_points("user-001", 100, now + timedelta(days=10))
manager.add_points("user-001", 200, now + timedelta(days=30))

print(manager.get_available_points("user-001"))  # 300
print(manager.get_total_points("user-001"))      # 300
```

### 消耗积分（FEFO 自动扣减）

```python
deductions = manager.consume_points("user-001", 150)
# deductions: {batch_id_1: 100, batch_id_2: 50}
print(manager.get_available_points("user-001"))  # 150
```

### 冻结与解冻

```python
frozen = manager.freeze_points("user-001", 80)
print(frozen.is_frozen)                           # True
print(manager.get_available_points("user-001"))   # 70
print(manager.get_frozen_points("user-001"))      # 80
print(manager.get_total_points("user-001"))       # 150

manager.unfreeze_points(frozen.freeze_id)
print(manager.get_available_points("user-001"))   # 150
print(manager.get_frozen_points("user-001"))      # 0
```

### 消费冻结积分（预授权确认扣款）

```python
frozen = manager.freeze_points("user-001", 50)
manager.consume_frozen_points(frozen.freeze_id)
print(manager.get_total_points("user-001"))       # 100
```

### 过期回收

```python
manager.add_points("user-001", 500, now - timedelta(days=1))  # 已过期
print(manager.get_available_points("user-001"))  # 150 (过期不计入可用)
print(manager.get_total_points("user-001"))      # 650

logs = manager.recycle_expired_points("user-001")
print(len(logs))                                   # 1
print(logs[0].recycled_points)                     # 500
print(manager.get_total_points("user-001"))        # 150

history = manager.get_expired_logs("user-001")
print(len(history))                                # 1
```

### 在过期临界点消耗

```python
t0 = datetime.now()
manager.add_points("user-001", 100, t0 + timedelta(seconds=100))

# 过期前 50 秒正常消耗
manager.consume_points("user-001", 30, now=t0 + timedelta(seconds=50))

# 过期后无法消耗
try:
    manager.consume_points("user-001", 70, now=t0 + timedelta(seconds=200))
except InsufficientPointsError:
    print("积分已过期，无法消耗")
```

## 运行测试

```bash
poetry run pytest tests/points/ -q
```

测试覆盖以下场景：

- **正常流程**：账户创建、积分入账、FEFO 扣减、冻结/解冻、过期回收
- **边界条件**：积分在过期临界点消耗、多个批次混合扣减、扣减金额刚好等于某批次余额、解冻精确还原批次
- **异常分支**：余额不足时冻结或消耗、消耗/冻结已过期积分、对已解冻记录再次操作、非法数额校验
- **封装保护**：所有返回对象均为独立副本，修改返回值不影响内部状态
- **异常层次**：所有异常均继承自 `PointsError`
- **并发一致性**：并发消耗无超额、并发入账与消耗无异常
