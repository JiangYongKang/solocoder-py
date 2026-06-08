# 订阅生命周期域模块

## 模块功能

本模块实现了完整的订阅生命周期管理逻辑，使用内存数据结构管理订阅状态，包括：

1. **订阅状态机**：管理订阅从试用、活跃、暂停、降级处理、取消到过期的全生命周期状态流转
2. **订阅操作**：支持创建订阅、续费、降级、暂停、恢复、取消、立即终止等操作，每个操作记录时间和原因
3. **按日比例退款计算**：取消订阅时按已使用天数和剩余天数的比例计算退款金额，支持月付/季付/年付
4. **订阅计划管理**：管理订阅计划（名称、周期类型、价格），支持降级校验、可用计划查询和价格对比
5. **订阅状态查询**：支持查询当前状态、当前计划、降级请求、下一续费时间、退款预览、完整状态变更历史

## 核心类职责

### states.py

| 类名 | 职责 |
|------|------|
| `SubscriptionState` | 枚举类型，定义订阅所有状态（试用、活跃、暂停、降级处理中、已取消、已过期） |
| `SubscriptionStateMachine` | 状态机引擎，管理状态转移规则，校验转移合法性，执行状态转换 |
| `InvalidStateTransitionError` | 非法状态转移异常 |

### models.py

| 类名/函数 | 职责 |
|-----------|------|
| `BillingCycleType` | 计费周期类型枚举（月付、季付、年付） |
| `SubscriptionPlan` | 订阅计划，包含唯一名称、周期类型、价格 |
| `OperationType` | 操作类型枚举，记录所有订阅操作类别 |
| `SubscriptionOperation` | 操作记录，包含操作类型、时间、原因、详情 |
| `DowngradeRequest` | 降级请求，记录目标计划、申请时间、生效时间 |
| `PlanCatalog` | 订阅计划目录，管理计划的增删改查、降级可用计划查询、价格对比 |
| `calculate_refund` | 按日比例计算退款金额 |
| `Subscription` | 订阅聚合根，封装所有订阅操作（激活、续费、降级、暂停、恢复、取消、终止等） |
| `SubscriptionError` | 订阅操作异常基类 |
| `InvalidPlanError` | 无效订阅计划异常 |
| `InvalidDowngradeError` | 非法降级异常（降级到更高价格或更长周期） |
| `PauseExceededError` | 暂停天数超期异常 |
| `DuplicateOperationException` | 重复操作异常（如重复取消、重复终止） |

## 订阅状态机

### 状态说明

| 状态 | 说明 |
|------|------|
| 试用 (TRIAL) | 试用期内，可转为付费或取消 |
| 活跃 (ACTIVE) | 正常付费期内，可续费、降级、暂停、取消 |
| 暂停 (PAUSED) | 临时暂停，可恢复或到期自动取消 |
| 降级处理中 (DOWNGRADE_PENDING) | 降级请求已提交，当前周期结束后生效 |
| 已取消 (CANCELLED) | 不再续费，当前周期到期后变为过期 |
| 已过期 (EXPIRED) | 订阅已终止（终态） |

### 状态机图

```
                     ┌──────────────┐
            ┌────────│    试用      │────────┐
            │        └──────┬───────┘        │
            │               │                │
            ▼               ▼                ▼
     ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
     │   已取消     │ │    活跃      │ │   已过期     │
     └──────┬───────┘ └──────┬───────┘ └──────────────┘
            │          ┌─────┴─────┐
            │          │           │
            ▼          ▼           ▼
     ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐
     │   已过期     │ │    暂停      │ │  降级处理中      │
     └──────────────┘ └──────┬───────┘ └────────┬─────────┘
                     ┌───────┴───────┐           │
                     │               │           │
                     ▼               ▼           ▼
              ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
              │    活跃      │ │   已取消     │ │   已过期     │
              └──────┬───────┘ └──────────────┘ └──────────────┘
               ┌─────┴─────────────────────────────┐
               │                                     │
               ▼                                     ▼
        ┌──────────────┐                       ┌──────────────┐
        │  降级处理中  │                       │    暂停      │
        └──────┬───────┘                       └──────────────┘
               │
               ▼
        ┌──────────────┐
        │   已取消     │
        └──────────────┘
```

### 合法状态转移路径

| 当前状态 | 可转移至 |
|---------|---------|
| 试用 (TRIAL) | 活跃 (ACTIVE)、已取消 (CANCELLED)、已过期 (EXPIRED) |
| 活跃 (ACTIVE) | 活跃 (ACTIVE)、暂停 (PAUSED)、降级处理中 (DOWNGRADE_PENDING)、已取消 (CANCELLED)、已过期 (EXPIRED) |
| 暂停 (PAUSED) | 活跃 (ACTIVE)、已取消 (CANCELLED)、已过期 (EXPIRED) |
| 降级处理中 (DOWNGRADE_PENDING) | 活跃 (ACTIVE)、暂停 (PAUSED)、已取消 (CANCELLED)、已过期 (EXPIRED) |
| 已取消 (CANCELLED) | 已过期 (EXPIRED) |
| 已过期 (EXPIRED) | （终态，不可转移） |

## 退款计算规则

### 计算公式

```
退款金额 = 周期总费用 × (剩余天数 / 周期总天数)
```

### 计算说明

1. **周期总天数**：按实际日历天数计算（非固定 30/90/365 天）
   - 月付：从周期开始日到当月月末的实际天数（支持闰年 2 月 29 天）
   - 季付：从周期开始日到季度末的实际天数
   - 年付：从周期开始日到年末的实际天数

2. **剩余天数**：从退款计算日期到周期结束日的天数

3. **边界处理**：
   - 计算日期在周期开始之前：全额退款
   - 计算日期在周期结束之后：退款 0
   - 结果四舍五入保留 2 位小数

## 降级规则

降级时必须满足以下所有条件，否则抛出 `InvalidDowngradeError`：

1. 目标计划价格 **严格低于** 当前计划价格
2. 目标计划周期 **不长于** 当前计划周期（按月付=30天、季付=90天、年付=365天比较）

## 使用示例

### 基本订阅全生命周期

```python
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
from solocoder_py.subscription import (
    Subscription, SubscriptionPlan, BillingCycleType,
    SubscriptionState, PlanCatalog
)

# 创建计划目录
catalog = PlanCatalog()
basic_plan = SubscriptionPlan(
    name="basic-monthly",
    cycle_type=BillingCycleType.MONTHLY,
    price=Decimal("99.00")
)
pro_plan = SubscriptionPlan(
    name="pro-monthly",
    cycle_type=BillingCycleType.MONTHLY,
    price=Decimal("199.00")
)
catalog.add_plan(basic_plan)
catalog.add_plan(pro_plan)

# 创建订阅（带 7 天试用期）
now = datetime(2024, 1, 1, 10, 0, 0)
trial_end = now.date() + timedelta(days=7)
sub = Subscription(
    id=str(uuid.uuid4()),
    user_id="user-001",
    plan=pro_plan,
    created_at=now,
    trial_end_at=trial_end,
)
assert sub.state == SubscriptionState.TRIAL

# 试用期结束自动激活
check_time = datetime(2024, 1, 8, 10, 0, 0)
sub.check_expiry(now=check_time)
assert sub.state == SubscriptionState.ACTIVE

# 续费
sub.renew(now=check_time)

# 降级
sub.downgrade(basic_plan, now=check_time)
assert sub.state == SubscriptionState.DOWNGRADE_PENDING
assert sub.downgrade_request is not None

# 暂停 7 天
sub.pause(pause_days=7, now=check_time)
assert sub.state == SubscriptionState.PAUSED

# 恢复
resume_time = check_time + timedelta(days=7)
sub.resume(now=resume_time)

# 取消订阅
sub.cancel(now=resume_time)
assert sub.state == SubscriptionState.CANCELLED

# 预览退款金额
refund = sub.preview_refund(as_of=resume_time.date())
print(f"预计退款: {refund}")

# 立即终止（含退款）
terminate_refund = sub.terminate(now=resume_time)
assert sub.state == SubscriptionState.EXPIRED

# 查看状态变更历史
for op in sub.state_history:
    print(f"{op.operated_at}: {op.operation_type.value} - {op.reason}")
```

### 查询可用降级计划

```python
# 获取比当前计划便宜的可用降级计划
cheaper_plans = catalog.get_cheaper_plans(pro_plan)
for plan in cheaper_plans:
    diff = catalog.compare_price(pro_plan, plan)
    print(f"{plan.name}: ￥{plan.price} (便宜 ￥{diff})")
```

## 运行测试

```bash
pytest tests/subscription/ -v
```
