# Quota 多租户配额域模块

## 模块功能

本模块实现了基于内存数据结构的多租户配额域功能，支持以下核心能力：

1. **双层配额模型**：每个租户可配置独立配额，同时系统存在全局总配额，资源申请时需同时校验两级限制。
2. **配额联动判定**：当租户级或全局级任一配额不足时拒绝本次申请，并给出明确拒绝原因（租户不足 / 全局不足 / 两者都不足）。
3. **用量累计与释放**：申请成功后增加用量，释放资源时回收用量，使用统一的锁顺序保证并发下用量统计一致不超发。
4. **用量重置**：
   - 手动重置：按租户或全局手动触发重置用量，全局重置会同步重置所有租户用量。
   - 周期自动重置：支持按小时、日、周、月等周期自动重置，在每次操作（申请、释放、查询）前自动检测周期是否到期，到期后进入新周期从零开始计量。
5. **限额调整一致性**：调小租户或全局配额上限时，同步回收对应层级的已用量，始终保持 `sum(tenant_used) == global_used`。

## 核心类职责

### clock.py

| 类名 | 职责 |
|------|------|
| `Clock` (ABC) | 时钟抽象接口，提供 `now()` 方法返回当前时间 |
| `SystemClock` | 基于系统时间的真实时钟实现 |
| `ManualClock` | 可手动推进的模拟时钟，用于测试周期重置等时间相关场景，支持 `advance_seconds()` 和 `set()` |

### exceptions.py

| 类名 | 职责 |
|------|------|
| `QuotaError` | 配额模块异常基类 |
| `TenantError` | 租户相关异常基类 |
| `TenantNotFoundError` | 指定租户不存在 |
| `TenantExistsError` | 创建重复租户配额 |
| `QuotaLimitExceededError` | 配额超限，包含 `reason` 字段指明具体原因 |
| `InvalidQuotaAmountError` | 配额数额非法（负数或零） |
| `ReleaseExceedUsedError` | 释放量超过已用量 |
| `GlobalQuotaNotSetError` | 全局配额尚未设置 |

### models.py

| 类名/函数 | 职责 |
|-----------|------|
| `QuotaPeriod` | 配额周期枚举：`NONE`（无周期，仅手动重置）、`HOURLY`、`DAILY`、`WEEKLY`、`MONTHLY` |
| `GlobalQuota` | 全局配额数据模型：配额ID、总限额、周期类型、已用量、创建时间、周期起始时间、重置时间；提供 `remaining` 属性和 `copy()` 方法 |
| `TenantQuota` | 租户配额数据模型：租户ID、租户限额、周期类型、已用量、创建时间、周期起始时间、重置时间；提供 `remaining` 属性和 `copy()` 方法 |
| `make_global_quota()` | 工厂函数，创建带唯一ID的全局配额 |
| `make_tenant_quota()` | 工厂函数，创建带唯一ID的租户配额 |

### manager.py

| 类名 | 职责 |
|------|------|
| `QuotaManager` | 配额管理器，线程安全，通过注入 `Clock` 支持可测试的时间驱动；维护全局配额、租户配额字典、租户锁；提供全局/租户配额的创建、更新、查询、资源申请、释放、手动/周期用量重置等核心操作 |

## 异常层次

```
QuotaError
├── TenantError
│   ├── TenantNotFoundError        # 租户不存在
│   ├── TenantExistsError          # 创建重复租户
│   ├── QuotaLimitExceededError    # 配额超限（含 reason 字段）
│   ├── InvalidQuotaAmountError    # 数额非法（负数或零）
│   └── ReleaseExceedUsedError     # 释放量超过已用量
└── GlobalQuotaNotSetError         # 全局配额未设置
```

所有异常均继承自 `QuotaError`，调用方可通过捕获 `QuotaError` 统一处理配额相关错误。

### 配额超限原因（QuotaLimitExceededError.reason）

| reason 值 | 含义 |
|-----------|------|
| `tenant_insufficient` | 仅租户配额不足 |
| `global_insufficient` | 仅全局配额不足 |
| `both_tenant_and_global_insufficient` | 租户配额和全局配额均不足 |

## 周期配额与自动重置

### 周期类型

`QuotaPeriod` 枚举支持以下周期：

| 枚举值 | 含义 | 判定规则 |
|--------|------|----------|
| `NONE` | 无周期 | 从不自动重置，仅支持手动重置 |
| `HOURLY` | 按小时 | 从 `period_start` 起经过 ≥ 1 小时视为周期到期 |
| `DAILY` | 按日 | 从 `period_start` 起经过 ≥ 1 天视为周期到期 |
| `WEEKLY` | 按周 | 从 `period_start` 起经过 ≥ 7 天视为周期到期 |
| `MONTHLY` | 按月 | 从 `period_start` 起经过 ≥ 1 个自然月视为周期到期（按月份和日对齐） |

### 自动重置触发时机

所有会读写配额状态的公共方法（`acquire`、`release`、`reset_tenant_quota`、`get_tenant_quota`、`get_global_quota`、`list_tenants`）在执行前都会调用 `_maybe_reset_tenant_period()` 或 `_maybe_reset_global_period()` 检测周期：

- 若全局周期到期 → 重置所有租户及全局的 `used = 0`，更新 `period_start` 和 `reset_at`
- 若仅单个租户周期到期 → 重置该租户 `used = 0`，同步减少全局 `used`，更新 `period_start` 和 `reset_at`

### 使用时钟注入测试周期重置

生产环境使用默认的 `SystemClock`，测试时可注入 `ManualClock` 精确控制时间：

```python
from datetime import datetime
from solocoder_py.quota import ManualClock, QuotaManager, QuotaPeriod

clock = ManualClock(datetime(2025, 1, 1, 12, 0, 0))
manager = QuotaManager(_clock=clock)
manager.set_global_quota(100, period=QuotaPeriod.HOURLY)
manager.create_tenant_quota("t1", 100, period=QuotaPeriod.HOURLY)
manager.acquire("t1", 80)

clock.advance_seconds(59 * 60)
assert manager.get_tenant_quota("t1").used == 80  # 未到期

clock.advance_seconds(61)  # 超过 1 小时
assert manager.get_tenant_quota("t1").used == 0   # 自动重置
```

## 双层配额联动规则

资源申请（`acquire`）时按以下步骤执行（与 [manager.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/quota/manager.py#L219-L253) 中 `acquire()` 的实际执行顺序一致）：

1. **参数校验**：`amount` 必须为正整数，否则抛 `InvalidQuotaAmountError`
2. **周期检测**：检测并重置已到期的租户或全局周期用量
3. **存在性校验**：全局配额必须已设置、租户必须存在
4. **双层校验（原子操作）**：在「全局锁 → 租户锁」的统一锁顺序下：
   - 读取 `tenant_remaining = tenant_quota.limit - tenant_quota.used`
   - 读取 `global_remaining = global_quota.limit - global_quota.used`
   - 若 `tenant_remaining < amount` **且** `global_remaining < amount` → 抛 `QuotaLimitExceededError(reason="both_tenant_and_global_insufficient")`
   - 若仅 `tenant_remaining < amount` → 抛 `QuotaLimitExceededError(reason="tenant_insufficient")`
   - 若仅 `global_remaining < amount` → 抛 `QuotaLimitExceededError(reason="global_insufficient")`
5. **原子扣减**：双层校验通过后，在同一临界区内同时增加 `tenant_quota.used` 和 `global_quota.used`

## 释放机制

资源释放（`release`）规则：

1. `amount` 必须为正整数
2. 不能超过该租户的已用量，否则抛 `ReleaseExceedUsedError`
3. 不能超过全局已用量（防御性校验），否则抛 `ReleaseExceedUsedError`
4. 校验通过后，在同一临界区内同时减少 `tenant_quota.used` 和 `global_quota.used`

## 重置机制

| 方法 | 作用 |
|------|------|
| `reset_tenant_quota(tenant_id)` | 重置单个租户的用量为 0，同步减少全局已用量（相当于释放该租户的全部已用资源）；更新 `period_start` 和 `reset_at` |
| `reset_global_quota()` | 重置全局用量为 0，同时将所有租户的用量重置为 0；为全局和所有租户更新 `period_start` 和 `reset_at` |
| `reset_all()` | 等同于 `reset_global_quota()` |

## 限额调整语义

配额上限调整（无论调大还是调小）**只会改变 `limit` 字段，绝不会修改 `used` 字段**。`used` 始终反映租户真实持有的资源量，保证后续 `release` 行为与实际持有量一致。

### 调小配额上限

当调小 `limit` 后若出现 `used > limit`：

- `used` 保持不变，`remaining = limit - used` 会是负数（表示「超限状态」）
- 后续新的 `acquire` 会因为 `remaining < amount` 被正常拒绝
- 后续 `release` 可以按真实持有量正常释放，直到 `used` 归零

`sum(tenant_used) == global_used` 恒成立，因为限额调整不改动任何 `used`。

### 调大配额上限

仅更新 `limit`，已用量保持不变，`remaining` 随之增加。

## 并发一致性保证

采用「全局锁 → 租户锁」的**统一锁顺序**架构，彻底避免死锁：

| 锁 | 保护范围 |
|----|----------|
| `_global_lock` (`threading.RLock`) | 全局配额对象、租户配额字典、租户锁字典 |
| 每个租户独立的 `threading.RLock` | 单个租户的配额读写 |

**统一加锁顺序**：所有需要同时操作全局和租户数据的方法（`acquire`、`release`、`reset_tenant_quota`、`update_tenant_quota_limit`、`reset_global_quota`）都严格按照**先获取 `_global_lock`，再获取对应租户锁**的顺序执行，绝不反向嵌套。

- `acquire` / `release` / `update_tenant_quota_limit` / `reset_tenant_quota`：`_global_lock` → `tenant_lock`
- `reset_global_quota`：持有 `_global_lock`，内部依次获取各租户 `tenant_lock` 并立即释放

该策略保证：
1. 无死锁：任意两个线程获取锁的顺序一致，不会出现循环等待
2. 原子性：双层配额的扣减/释放在同一临界区内完成，用量不会出现中间可见状态
3. `sum(tenant_used) == global_used` 恒成立

## 封装保护

所有返回 `GlobalQuota`、`TenantQuota` 对象的公共方法均返回对象的深拷贝，调用方对返回值的任何修改不会影响管理器内部状态。

## 使用示例

### 初始化与租户创建

```python
from solocoder_py.quota import QuotaManager

manager = QuotaManager()

manager.set_global_quota(1000)

manager.create_tenant_quota("tenant-001", 500)
manager.create_tenant_quota("tenant-002", 300)
```

### 周期配额（按日重置）

```python
from solocoder_py.quota import QuotaPeriod

manager.set_global_quota(10000, period=QuotaPeriod.DAILY)
manager.create_tenant_quota("tenant-001", 5000, period=QuotaPeriod.DAILY)

manager.acquire("tenant-001", 3000)
# 次日再次操作时自动进入新周期，用量从零开始
```

### 资源申请与释放

```python
from solocoder_py.quota import QuotaLimitExceededError

manager.acquire("tenant-001", 200)
t1 = manager.get_tenant_quota("tenant-001")
g = manager.get_global_quota()
print(t1.used, t1.remaining)  # 200 300
print(g.used, g.remaining)    # 200 800

manager.release("tenant-001", 50)
print(manager.get_tenant_quota("tenant-001").used)  # 150
print(manager.get_global_quota().used)              # 150

try:
    manager.acquire("tenant-001", 1000)
except QuotaLimitExceededError as e:
    print(e.reason)  # "both_tenant_and_global_insufficient"
```

### 配额超限原因区分

```python
manager.set_global_quota(100)
manager.create_tenant_quota("tenant-A", 30)
manager.create_tenant_quota("tenant-B", 80)

manager.acquire("tenant-B", 80)  # 全局已用 80

try:
    manager.acquire("tenant-A", 50)
except QuotaLimitExceededError as e:
    print(e.reason)  # "tenant_insufficient"（A 仅 30 额度）

try:
    manager.acquire("tenant-A", 30)
except QuotaLimitExceededError as e:
    print(e.reason)  # "global_insufficient"（全局剩余 20）
```

### 用量重置

```python
manager.acquire("tenant-001", 100)
manager.acquire("tenant-002", 100)
print(manager.get_global_quota().used)  # 200

manager.reset_tenant_quota("tenant-001")
print(manager.get_tenant_quota("tenant-001").used)  # 0
print(manager.get_global_quota().used)              # 100

manager.reset_global_quota()
print(manager.get_tenant_quota("tenant-002").used)  # 0
print(manager.get_global_quota().used)              # 0
```

### 调小配额上限不影响真实持有，可正常释放

```python
manager.set_global_quota(1000)
manager.create_tenant_quota("t1", 500)
manager.create_tenant_quota("t2", 500)
manager.acquire("t1", 400)
manager.acquire("t2", 300)
assert manager.get_global_quota().used == 700

manager.update_tenant_quota_limit("t1", 200)  # 调小 t1 上限
assert manager.get_tenant_quota("t1").used == 400  # used 不变，反映真实持有
assert manager.get_tenant_quota("t1").remaining == -200  # 处于超限状态
assert manager.get_global_quota().used == 700
assert manager.get_tenant_quota("t2").used == 300
assert (manager.get_tenant_quota("t1").used
        + manager.get_tenant_quota("t2").used) == manager.get_global_quota().used

manager.release("t1", 400)  # 可以按真实持有量全部释放
assert manager.get_tenant_quota("t1").used == 0
assert manager.get_global_quota().used == 300
```

## 运行测试

```bash
poetry run pytest tests/quota/ -q
```

测试覆盖以下场景：

- **正常流程**：全局/租户配额创建、资源申请、释放、手动重置、周期自动重置
- **周期重置**：HOURLY、DAILY、WEEKLY、MONTHLY 四种周期到期检测与自动重置，MONTHLY 覆盖月末 30→31、31→28（非闰年2月）、闰年 2月29→3月29、2月29→次年2月28 等日历边界
- **边界条件**：租户配额等于全局配额、申请量刚好等于剩余额度、重置临界时刻（重置前后行为差异）、周期到期前后行为差异
- **异常分支**：未知租户申请、释放超过已用量、负数/零数额校验、全局配额未设置时操作、超限原因精确区分（租户不足/全局不足/两者都不足）
- **限额调整语义**：调小限额不截断 used（真实持有量不变）、remaining 可为负（超限状态）、后续 release 可按真实持有量正常释放、调大限额不影响已用量、多租户场景下 `sum(tenant_used) == global_used` 恒成立
- **全局周期重置一致性**：无论从 `get_global_quota` 入口还是 `get_tenant_quota/acquire/release` 入口检测到全局周期到期，都会全量重置所有租户用量
- **并发一致性**：多线程并发申请无超发、并发申请与释放无异常、全局重置与申请/释放交错执行无死锁且一致性成立
- **封装保护**：返回对象均为独立副本，修改返回值不影响内部状态
