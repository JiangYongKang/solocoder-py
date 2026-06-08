# 优惠券折扣计算引擎

## 模块功能

本模块提供一个基于内存数据结构的优惠券折扣计算引擎，核心能力包括：

- **多种优惠券类型**：支持满减券、折扣券、阶梯券三种类型，每种券支持有效期、使用门槛、优惠封顶等配置
- **优惠券叠加计算**：一个订单可同时使用多张优惠券，按优先级从高到低依次计算，每张券在前一张券减免后的剩余金额基础上继续减免
- **互斥校验机制**：通过互斥组（mutex groups）管理优惠券之间的冲突关系，默认满减券与折扣券互斥、两张满减券之间互斥，规则可灵活配置
- **优惠封顶控制**：单张券可设置最大优惠金额封顶，订单总优惠可设置全局封顶，优惠金额超过封顶时自动截断
- **计算结果明细**：每次计算输出每张券的优惠金额、是否被互斥排除、是否被有效期排除、是否触发封顶、各阶段金额变化，便于对账和前端展示

## 核心类职责

### 异常类（exceptions.py）

| 类名 | 含义 |
|------|------|
| `CouponError` | 优惠券模块基类异常 |
| `CouponExpiredError` | 优惠券已过期或尚未生效 |
| `CouponMutexError` | 多张优惠券存在互斥冲突，包含冲突的券 ID 和互斥组名 |
| `DuplicateCouponError` | 同一次计算中使用了重复的优惠券 ID |
| `InvalidCouponError` | 优惠券参数非法（如负金额、折扣率超出范围等） |

### 数据模型（models.py）

| 类名 | 职责 |
|------|------|
| `CouponType` | 优惠券类型枚举：`FIXED_AMOUNT`（满减）、`PERCENTAGE`（折扣）、`TIERED`（阶梯） |
| `TierDiscountType` | 阶梯券优惠类型枚举：`FIXED_AMOUNT`（固定金额减免）、`PERCENTAGE`（比例打折） |
| `Tier` | 单个阶梯区间：包含 `min_amount`、`max_amount`（可为 None 表示无上限）、优惠类型、优惠值 |
| `Coupon` | 优惠券抽象基类，包含 `coupon_id`、`name`、`valid_from`、`valid_until`、`mutex_groups`、`priority`、`max_discount`（单券封顶）等通用字段 |
| `FixedAmountCoupon` | 满减券：达到 `threshold` 门槛后减免 `discount_amount` |
| `PercentageCoupon` | 折扣券：达到 `threshold` 门槛后按 `discount_rate`（0~1）比例打折 |
| `TieredCoupon` | 阶梯券：根据订单金额匹配不同 `tiers` 区间，按区间对应规则优惠。阶梯区间必须严格连续（不重叠、无缺口） |
| `CouponDetail` | 单张券计算明细：包含应用状态、排除原因、优惠金额、计算前后金额、是否封顶等 |
| `CalculationResult` | 整体计算结果：包含原始金额、最终应付金额、总优惠金额、是否触发全局封顶、各券明细列表 |

### 计算引擎（engine.py）

| 类名 | 职责 |
|------|------|
| `CouponEngine` | 折扣计算引擎核心入口，构造时可指定 `check_time`（校验时间）、`global_max_discount`（全局封顶）、`auto_resolve_mutex`（是否自动按优先级解决互斥冲突）。核心方法 `calculate(order_amount, coupons)` 执行完整计算流程并返回 `CalculationResult` |

模块常量：
- `DEFAULT_FIXED_MUTEX_GROUP = "amount_based"`：满减券默认互斥组
- `DEFAULT_PERCENTAGE_MUTEX_GROUP = "amount_based"`：折扣券默认互斥组
- `DEFAULT_TIERED_MUTEX_GROUP = "tiered"`：阶梯券默认互斥组

## 互斥校验规则

### 默认互斥组

当优惠券未显式指定 `mutex_groups` 时，引擎会自动分配默认互斥组：

- 满减券（`FixedAmountCoupon`）→ `["amount_based"]`
- 折扣券（`PercentageCoupon`）→ `["amount_based"]`
- 阶梯券（`TieredCoupon`）→ `["tiered"]`

### 互斥判定逻辑

两张优惠券只要**共享任意一个互斥组**，即判定为互斥，不能同时使用。

因此默认行为是：
- 满减券 ↔ 满减券：共享 `amount_based` → **互斥**
- 满减券 ↔ 折扣券：共享 `amount_based` → **互斥**
- 折扣券 ↔ 折扣券：共享 `amount_based` → **互斥**
- 阶梯券 ↔ 满减券/折扣券：分属不同组 → **可叠加**
- 阶梯券 ↔ 阶梯券：共享 `tiered` → **互斥**

### 自定义互斥组

通过在创建优惠券时显式传入 `mutex_groups` 列表可以覆盖默认行为，灵活配置互斥关系。例如将两张满减券分别放入不同组，即可实现满减券之间的叠加。

### 互斥冲突处理

- **严格模式（默认）**：检测到互斥冲突时，立即抛出 `CouponMutexError`
- **自动解决模式**（`auto_resolve_mutex=True`）：按 `priority` 从高到低排序，保留优先级高的券，优先级低的券被标记为 `excluded_by_mutex=True` 排除；优先级相同时按 `coupon_id` 字典序保留

## 叠加计算顺序

多张可叠加优惠券按以下规则排序后依次计算：

1. **按 `priority` 降序**：数值越大越先计算
2. **priority 相同时按 `coupon_id` 字典序升序**

每张券在上一张券计算后的剩余金额基础上继续减免，即串行叠加而非基于原始金额平行计算。

示例：订单金额 200 元，使用 8 折券（priority=10）+ 满 100 减 10 券（priority=1）：
1. 先打 8 折：200 × 0.8 = 160 元，优惠 40 元
2. 再满减 10：160 - 10 = 150 元，优惠 10 元
3. 最终应付 150 元，总优惠 50 元

## 封顶规则

### 单券封顶

每张券可通过 `max_discount` 设置最大优惠金额。当券计算出的优惠金额 ≥ `max_discount` 时，实际优惠按 `max_discount` 计，该券明细中的 `capped=True`。

### 全局封顶

`CouponEngine` 可通过 `global_max_discount` 设置订单总优惠上限。当所有券的优惠总金额 ≥ `global_max_discount` 时，总优惠被截断为 `global_max_discount`，`CalculationResult.global_capped=True`。

全局封顶截断时，从**优先级最低**的已应用券开始往回扣减，直至总优惠不超过封顶值，被扣减的券明细中 `capped` 也会被标记为 `True`。

**金额链一致性保证**：全局封顶回退完成后，引擎会以第一张券的 `amount_before` 为起点，按优先级顺序重新推导所有已应用券的 `amount_before` 和 `amount_after`，确保相邻两张券之间前一张的 `amount_after` 恒等于后一张的 `amount_before`，最后一张券的 `amount_after` 等于 `CalculationResult.final_amount`，各阶段金额形成完整无断裂的链条。

### 金额下限保护

无论何种优惠组合，最终应付金额不会低于 0，单张券优惠也不会超过当前计算阶段的剩余金额。

### 入参不可变性

`calculate()` 方法在执行过程中**不会修改调用方传入的优惠券对象**。若优惠券未指定互斥组需要补默认值，引擎使用 `dataclasses.replace()` 创建副本处理，原始对象的所有字段（包括 `mutex_groups`）在调用前后保持一致。

## 阶梯券连续性校验

`TieredCoupon` 在构造时会对 `tiers` 列表执行严格的连续性校验，校验失败会抛出 `InvalidCouponError`。校验规则包括：

1. **非空性**：`tiers` 至少包含 1 个区间
2. **末位开放**：只有最后一个区间的 `max_amount` 可以为 `None`（表示无上限），其余区间必须指定明确上限
3. **无重叠**：排序后相邻区间中，后一区间的 `min_amount` 不得小于前一区间的 `max_amount`
4. **无缺口**：排序后相邻区间中，后一区间的 `min_amount` 必须等于前一区间的 `max_amount`

通过连续性校验后，所有区间按 `min_amount` 升序排列并覆盖从首个区间起点到无穷大的完整金额范围，任意非负订单金额必然落入且仅落入一个区间。

合法示例：
```python
tiers = [
    Tier(0,   100,  TierDiscountType.FIXED_AMOUNT, 5),
    Tier(100, 300,  TierDiscountType.FIXED_AMOUNT, 20),
    Tier(300, None, TierDiscountType.FIXED_AMOUNT, 50),
]
```

非法示例（存在 50~100 的缺口）：
```python
tiers = [
    Tier(0,   50,  TierDiscountType.FIXED_AMOUNT, 5),
    Tier(100, 200, TierDiscountType.FIXED_AMOUNT, 20),  # ❌ 与上一区间不连续
]
```

## 使用示例

```python
from datetime import datetime, timedelta
from solocoder_py.coupon import (
    CouponEngine,
    FixedAmountCoupon,
    PercentageCoupon,
    Tier,
    TierDiscountType,
    TieredCoupon,
)

now = datetime(2025, 6, 1)
vf = now - timedelta(days=30)
vu = now + timedelta(days=30)

# 1. 创建各类优惠券
coupon_10_off = FixedAmountCoupon(
    coupon_id="fix-001",
    name="满100减10",
    valid_from=vf,
    valid_until=vu,
    threshold=100,
    discount_amount=10,
    mutex_groups=["g1"],
)

coupon_20pct = PercentageCoupon(
    coupon_id="pct-001",
    name="8折券",
    valid_from=vf,
    valid_until=vu,
    threshold=0,
    discount_rate=0.2,
    mutex_groups=["g2"],
    priority=10,
)

tiered = TieredCoupon(
    coupon_id="tier-001",
    name="阶梯满减",
    valid_from=vf,
    valid_until=vu,
    tiers=[
        Tier(0, 100, TierDiscountType.FIXED_AMOUNT, 5),
        Tier(100, 300, TierDiscountType.FIXED_AMOUNT, 20),
        Tier(300, None, TierDiscountType.FIXED_AMOUNT, 50),
    ],
    mutex_groups=["g3"],
)

# 2. 创建引擎并计算
engine = CouponEngine(check_time=now, global_max_discount=100)
result = engine.calculate(250.0, [coupon_10_off, coupon_20pct, tiered])

print(f"原始金额: {result.original_amount}")
print(f"最终应付: {result.final_amount}")
print(f"总优惠: {result.total_discount}")
print(f"是否触发全局封顶: {result.global_capped}")

for d in result.details:
    print(
        f"  [{d.coupon_name}] 应用={d.applied} "
        f"优惠={d.discount_amount:.2f} "
        f"{d.amount_before:.2f} → {d.amount_after:.2f} "
        f"封顶={d.capped}"
    )
```
