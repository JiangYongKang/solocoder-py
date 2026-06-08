# 计量计费域

## 模块功能

本模块提供一个基于内存数据结构的计量计费引擎，核心能力包括：

- **用量累计**：支持按资源类型和账户维度记录用量数据，每次上报用量时累加到当前账期
- **阶梯定价**：每种资源可配置多级阶梯定价，不同用量区间对应不同单价，分段计算后累加
- **按比例分摊**：当账期中间资源价格发生变化时，按价格生效的时间比例拆分用量并计算费用
- **账期切分**：账期有起止时间，结束时自动结算并生成账单，新账期用量从零开始累计
- **账单查询**：支持查询当前账期的实时费用估算，以及历史账单的详细费用明细

## 核心类职责

### 数据模型（models.py）

| 类名 | 职责 |
|------|------|
| `PricingTier` | 单个定价阶梯，定义用量区间 `[min_units, max_units)` 和对应的 `unit_price` |
| `TieredPricing` | 某资源的阶梯定价配置，包含多个 `PricingTier`，提供阶梯校验和分段计费计算 |
| `TierCalculationDetail` | 单阶梯计费明细，记录该阶梯的适用区间、单价、用量和费用 |
| `PriceChange` | 价格变更记录，指定新定价及生效时间 |
| `UsageRecord` | 单次用量上报记录，包含账户、资源、用量和上报时间 |
| `BillingPeriod` | 账期实体，维护起止时间、状态、用量记录和按账户-资源维度的累计用量 |
| `BillingPeriodStatus` | 账期状态枚举：`ACTIVE`（活跃中）、`SETTLED`（已结算） |
| `ProportionalSplitDetail` | 按比例分摊明细，记录某段价格生效时间内的时间占比、分配用量和费用 |
| `BillingLineItem` | 账单行项目，对应单个账户的单个资源在账期内的计费结果 |
| `Bill` | 完整账单，包含账期信息、账户、多个行项目和总金额 |

### 异常类（exceptions.py）

| 异常名 | 触发场景 |
|--------|----------|
| `BillingError` | 计费模块基类异常 |
| `PricingNotFoundError` | 资源未配置定价时计费 |
| `InvalidTierConfigError` | 阶梯价格配置区间不连续或重叠 |
| `FutureUsageError` | 上报未来时间的用量 |
| `PeriodSettledError` | 对已结算账期执行修改操作 |
| `InvalidPeriodError` | 账期参数非法 |

### 引擎（engine.py）

| 类名 | 职责 |
|------|------|
| `BillingEngine` | 计费引擎核心入口，管理定价配置、账期生命周期、用量上报、费用计算和账单生成 |

## 阶梯定价计算规则

阶梯定价按用量区间分段计算，每一段的用量乘以对应区间的单价，各段费用累加得到总费用。

### 配置示例

```
资源 storage 的阶梯定价：
  0    - 100  单位：单价 1.0 元
  100  - 500  单位：单价 0.8 元
  500  - ∞    单位：单价 0.6 元
```

对应的 `PricingTier` 配置：

```python
from solocoder_py.billing import PricingTier

tiers = [
    PricingTier(min_units=0, max_units=100, unit_price=1.0),
    PricingTier(min_units=100, max_units=500, unit_price=0.8),
    PricingTier(min_units=500, max_units=None, unit_price=0.6),
]
```

注意：区间采用左闭右开 `[min_units, max_units)` 的语义。

### 计算示例

累计用量 = 600 单位

| 阶梯区间 | 区间容量 | 本段用量 | 单价 | 本段费用 |
|----------|----------|----------|------|----------|
| [0, 100) | 100 | 100 | 1.0 | 100.0 |
| [100, 500) | 400 | 400 | 0.8 | 320.0 |
| [500, ∞) | ∞ | 100 | 0.6 | 60.0 |

总费用 = 100.0 + 320.0 + 60.0 = **480.0 元**

## 按比例分摊逻辑

当账期内发生价格变更时，需要按每个价格生效的时间段占比，将累计用量拆分到各价格段，再分别按阶梯定价计算。

### 分摊规则

1. 确定账期内所有生效的价格配置及其时间区间
2. 对每个价格段，计算其覆盖时长占整个账期时长的比例 `time_ratio`
3. 分配用量 = 总累计用量 × time_ratio
4. 对每个分配用量，使用对应价格的阶梯定价单独计算费用
5. 总费用 = 各价格段费用之和

### 分摊示例

账期：1 月 1 日 00:00 ~ 1 月 31 日 00:00（共 30 天）
价格变更：1 月 16 日 00:00 起涨价
- 1/1 ~ 1/16：单价 1.0 元（单阶梯）
- 1/16 ~ 1/31：单价 1.5 元（单阶梯）
累计用量：200 单位

计算过程：
- 前半段时间占比 = 15/30 = 0.5，分配用量 = 200 × 0.5 = 100，费用 = 100 × 1.0 = 100
- 后半段时间占比 = 15/30 = 0.5，分配用量 = 200 × 0.5 = 100，费用 = 100 × 1.5 = 150
- 总费用 = 100 + 150 = **250 元**

## 使用示例

```python
from datetime import datetime, timedelta
from solocoder_py.billing import (
    BillingEngine,
    PricingTier,
)

engine = BillingEngine()

# 1. 配置阶梯定价
engine.configure_tiered_pricing(
    resource_type="storage",
    tiers=[
        PricingTier(min_units=0, max_units=100, unit_price=1.0),
        PricingTier(min_units=100, max_units=500, unit_price=0.8),
        PricingTier(min_units=500, max_units=None, unit_price=0.6),
    ],
)

# 2. 开启账期（30天）
period_start = datetime(2024, 1, 1)
engine.open_period(period_start, timedelta(days=30))

# 3. 上报用量
engine.report_usage("acc-001", "storage", 50)
engine.report_usage("acc-001", "storage", 150)

# 4. 查询当前累计用量
usage = engine.get_current_usage("acc-001", "storage")
print(f"累计用量: {usage}")  # 200

# 5. 查询实时费用估算
estimates = engine.estimate_current_cost("acc-001")
for resource, line in estimates.items():
    print(f"{resource}: 费用 {line.total_cost}")

# 6. 结算账期，生成账单
bills = engine.settle_period()
for bill in bills:
    print(f"账单 {bill.id}: 总金额 {bill.total_amount}")
    for item in bill.line_items:
        print(f"  {item.resource_type}: {item.total_units} 单位, 费用 {item.total_cost}")
```
