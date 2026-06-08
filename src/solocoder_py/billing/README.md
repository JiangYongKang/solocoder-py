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
| `PricingNotFoundError` | 上报用量时该时刻不存在有效定价 |
| `InvalidTierConfigError` | 阶梯价格配置区间不连续或重叠 |
| `FutureUsageError` | 上报未来时间的用量 |
| `PeriodSettledError` | 对已结算账期执行修改操作 |
| `InvalidPeriodError` | 账期参数非法 |
| `AccountNotFoundError` | 查询不存在账户的账单 |
| `ResourceNotFoundError` | 上报未注册资源的用量 |

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

## 定价生效时间校验策略

用量上报时，系统会校验该上报时间点（`reported_at`）是否存在有效的资源定价，而非账期起点。校验逻辑如下：

1. **资源注册校验**：上报时首先校验资源类型是否已通过 `configure_tiered_pricing` 注册，未注册抛出 `ResourceNotFoundError`。
2. **时间点匹配**：使用 `reported_at` 作为查询时间点，从该资源所有已注册的定价配置中，查找 `effective_from <= reported_at` 的最新一条定价配置。
3. **边界判定**：定价生效时间采用**闭区间**判定，即 `reported_at == effective_from` 视为已生效。若 `reported_at < effective_from` 则视为该时刻定价尚未生效，抛出 `PricingNotFoundError`。

示例：账期 1/1 ~ 1/31，资源在 1/10 生效新定价。则 1/9 的用量上报会被拒绝，1/10 00:00:00 及之后的上报被接受。

## 并发线程安全保证

`BillingEngine` 通过 `threading.RLock` 可重入锁对所有读写操作提供线程安全保证：

- **所有公共方法加锁**：无论是写操作（`report_usage`、`settle_period`、`open_period`、`configure_tiered_pricing`）和读操作（`get_current_usage`、`estimate_current_cost`、`get_bills`、`get_bill`、`list_bills`、`list_periods`、`get_period`、`get_current_period`、`get_pricing_at`）均在方法入口加锁，确保多线程并发调用时不会读到中间不一致状态。
- **可重入锁**：内部私有方法（如 `_calculate_line_item`）不重复加锁，调用方已持有锁，避免死锁。
- **原子性保证**：用量累加、账期结算、账单生成等复合操作在锁内完成，保证中间状态对其他线程不可见。

## 金额精度处理

为避免 float 乘加运算引入尾数误差，系统对金额和用量进行精度归整：

- **金额精度**：默认保留 **2 位小数**，通过 `BillingEngine(amount_precision=2)` 可自定义。每段阶梯费用、分摊段费用、行项目费用、账单总金额在每次加总后均立即按 `ROUND_HALF_UP`（四舍五入）规则归整。
- **用量精度**：默认保留 **6 位小数**，通过 `quantity_precision=6` 可自定义。按比例分摊分配用量时按此精度归整。
- **归整策略**：采用 `decimal.Decimal` 将 float 转字符串后精确计算，避免二进制浮点表示误差，保证账单行项目各分段费用之和等于账单总金额。

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
