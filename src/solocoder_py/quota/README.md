# Quota 多租户配额域模块

## 模块功能

本模块实现了基于内存数据结构的多租户配额域功能，支持以下核心能力：

1. **双层配额模型**：每个租户可配置独立配额，同时系统存在全局总配额，资源申请时需同时校验两级限制。
2. **配额联动判定**：当租户级或全局级任一配额不足时拒绝本次申请，并给出明确拒绝原因（租户不足 / 全局不足 / 两者都不足）。
3. **用量累计与释放**：申请成功后增加用量，释放资源时回收用量，使用细粒度锁保证并发下用量统计一致不超发。
4. **用量重置**：按租户或全局手动触发重置用量，重置后新周期从零开始计量；全局重置会同步重置所有租户用量。

## 核心类职责

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
| `GlobalQuota` | 全局配额数据模型：配额ID、总限额、已用量、创建时间、重置时间；提供 `remaining` 属性和 `copy()` 方法 |
| `TenantQuota` | 租户配额数据模型：租户ID、租户限额、已用量、创建时间、重置时间；提供 `remaining` 属性和 `copy()` 方法 |
| `make_global_quota()` | 工厂函数，创建带唯一ID的全局配额 |
| `make_tenant_quota()` | 工厂函数，创建带唯一ID的租户配额 |

### manager.py

| 类名 | 职责 |
|------|------|
| `QuotaManager` | 配额管理器，线程安全，维护全局配额、租户配额字典、租户锁；提供全局/租户配额的创建、更新、查询、资源申请、释放、用量重置等核心操作 |

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

## 双层配额联动规则

资源申请（`acquire`）时按以下步骤执行（与 [manager.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/quota/manager.py#L105-L138) 中 `acquire()` 的实际执行顺序一致）：

1. **参数校验**：`amount` 必须为正整数，否则抛 `InvalidQuotaAmountError`
2. **存在性校验**：全局配额必须已设置、租户必须存在
3. **双层校验（原子操作）**：在同时持有「租户锁 + 全局锁」的情况下：
   - 读取 `tenant_remaining = tenant_quota.limit - tenant_quota.used`
   - 读取 `global_remaining = global_quota.limit - global_quota.used`
   - 若 `tenant_remaining < amount` **且** `global_remaining < amount` → 抛 `QuotaLimitExceededError(reason="both_tenant_and_global_insufficient")`
   - 若仅 `tenant_remaining < amount` → 抛 `QuotaLimitExceededError(reason="tenant_insufficient")`
   - 若仅 `global_remaining < amount` → 抛 `QuotaLimitExceededError(reason="global_insufficient")`
4. **原子扣减**：双层校验通过后，在同一临界区内同时增加 `tenant_quota.used` 和 `global_quota.used`

### 示例

全局配额 = 100，租户 A 配额 = 50，租户 B 配额 = 50：

| 操作 | 租户 A 已用 | 租户 B 已用 | 全局已用 | 结果 |
|------|------------|------------|---------|------|
| A 申请 30 | 30 | 0 | 30 | 成功 |
| B 申请 40 | 30 | 40 | 70 | 成功 |
| A 申请 25 | 30 | 40 | 70 | 失败：A 剩余 20 < 25（tenant_insufficient） |
| B 申请 20 | 30 | 40 | 70 | 失败：全局剩余 30 ≥ 20，但 B 剩余 10 < 20（tenant_insufficient） |
| B 申请 10 | 30 | 50 | 80 | 成功 |
| A 申请 20 | 30 | 50 | 80 | 失败：A 剩余 20 ≥ 20，但全局剩余 20 ≥ 20？→ 实际 A 剩余 20 且全局剩余 20，成功 |
| A 申请 21 | 50 | 50 | 100 | 失败：全局剩余 0 < 21（global_insufficient） |

## 释放机制

资源释放（`release`）规则：

1. `amount` 必须为正整数
2. 不能超过该租户的已用量，否则抛 `ReleaseExceedUsedError`
3. 不能超过全局已用量（防御性校验），否则抛 `ReleaseExceedUsedError`
4. 校验通过后，在同一临界区内同时减少 `tenant_quota.used` 和 `global_quota.used`

## 重置机制

| 方法 | 作用 |
|------|------|
| `reset_tenant_quota(tenant_id)` | 重置单个租户的用量为 0，同步减少全局已用量（相当于释放该租户的全部已用资源） |
| `reset_global_quota()` | 重置全局用量为 0，同时将所有租户的用量重置为 0 |
| `reset_all()` | 等同于 `reset_global_quota()` |

重置时会记录 `reset_at` 时间戳。

## 并发一致性保证

采用双层锁架构：

| 锁 | 保护范围 |
|----|----------|
| `_global_lock` (`threading.RLock`) | 全局配额对象、租户配额字典、租户锁字典 |
| 每个租户独立的 `threading.RLock` | 单个租户的配额读写 |

**核心原则**：`acquire` 和 `release` 操作需同时持有「租户锁 + 全局锁」，确保双层配额的扣减/释放是原子操作，杜绝并发下的超发问题。所有结构操作（创建租户、查询等）仅持全局锁。

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

manager.acquire("tenant-A", 30)  # 全局已用 110？→ 此时全局剩余 20，失败
# 实际：全局剩余 100-80=20，A 剩余 30，申请 30 → global_insufficient
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

## 运行测试

```bash
poetry run pytest tests/quota/ -q
```

测试覆盖以下场景：

- **正常流程**：全局/租户配额创建、资源申请、释放、重置
- **边界条件**：租户配额等于全局配额、申请量刚好等于剩余额度、重置临界时刻（重置前后行为差异）、更新配额限制后已用量自动截断
- **异常分支**：未知租户申请、释放超过已用量、负数/零数额校验、全局配额未设置时操作、超限原因精确区分（租户不足/全局不足/两者都不足）
- **并发一致性**：多线程并发申请无超发、并发申请与释放无异常
- **封装保护**：返回对象均为独立副本，修改返回值不影响内部状态
