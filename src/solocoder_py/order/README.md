# 订单结算域模块 (TASK_001)

## 模块功能

本模块实现了完整的订单结算域逻辑，包括：

1. **订单状态机**：管理订单从创建到完成的全生命周期状态流转
2. **订单履约**：支持部分履约场景，可分多次发货，记录每次发货明细
3. **促销系统**：支持多种促销类型及叠加规则，自动校验促销互斥性
4. **内存数据仓储**：使用内存数据结构模拟数据源，提供订单持久化操作

## 核心类职责

### states.py

| 类名 | 职责 |
|------|------|
| `OrderState` | 枚举类型，定义订单所有状态（待支付、已支付、已发货、已签收、已完成、已取消、退款中、已退款、售后中） |
| `OrderStateMachine` | 状态机引擎，管理状态转移规则，校验转移合法性，执行状态转换 |
| `InvalidStateTransitionError` | 非法状态转移异常 |

### models.py

| 类名 | 职责 |
|------|------|
| `OrderLineItem` | 订单行项目，记录商品ID、单价、数量、已履约数量，计算小计金额 |
| `ShipmentItem` | 发货明细项，记录行项目ID和本次发货数量 |
| `Shipment` | 发货单，包含多个发货明细项、创建时间、物流单号 |
| `Order` | 订单聚合根，包含多个行项目、促销、发货单，封装订单操作（支付、取消、发货、签收、完成、退款、售后等） |
| `ShipmentQuantityError` | 发货数量异常 |
| `OrderFulfillmentError` | 订单履约异常 |

### promotions.py

| 类名 | 职责 |
|------|------|
| `PromotionType` | 促销类型枚举（满减、直减、折扣、特价） |
| `Promotion` | 促销活动，包含类型、面值/折扣率、适用门槛，提供价格计算 |
| `PromotionEngine` | 促销引擎，校验促销互斥规则，按优先级叠加计算最终价格 |
| `MutuallyExclusivePromotionsError` | 互斥促销同时应用异常 |

### repository.py

| 类名 | 职责 |
|------|------|
| `OrderRepository` | 内存数据仓库，提供订单的增删改查操作 |

## 状态机图

```
                        ┌─────────────┐
            ┌───────────│  待支付     │───────────┐
            │           └──────┬──────┘           │
            │                  │                  │
            ▼                  ▼                  ▼
     ┌─────────────┐    ┌─────────────┐           │
     │   已取消    │    │   已支付     │           │
     └─────────────┘    └──────┬──────┘           │
                               │                  │
                    ┌──────────┴──────────┐       │
                    ▼                     ▼       │
             ┌─────────────┐       ┌─────────────┐│
             │   已发货     │       │  退款中     ││
             └──────┬──────┘       └──────┬──────┘│
                    │                     │       │
                    ▼                     ▼       │
             ┌─────────────┐       ┌─────────────┐│
             │   已签收     │       │   已退款    │◄┘
             └──────┬──────┘       └─────────────┘
          ┌─────────┴─────────┐
          ▼                   ▼
   ┌─────────────┐     ┌─────────────┐
   │   已完成     │     │   售后中     │
   └─────────────┘     └──────┬──────┘
                          ┌───┴───┐
                          ▼       ▼
                   ┌──────────┐ ┌──────────┐
                   │  已退款   │ │  已完成   │
                   └──────────┘ └──────────┘
```

### 合法状态转移路径

| 当前状态 | 可转移至 |
|---------|---------|
| 待支付 | 已支付、已取消 |
| 已支付 | 已发货、退款中 |
| 已发货 | 已签收 |
| 已签收 | 已完成、售后中 |
| 已完成 | （终态） |
| 已取消 | （终态） |
| 退款中 | 已退款 |
| 已退款 | （终态） |
| 售后中 | 已退款、已完成 |

## 促销规则

### 促销类型

| 类型 | 说明 | value 字段 | threshold 字段 |
|------|------|-----------|---------------|
| 满减 | 满 threshold 元减 value 元 | 减免金额 | 满足金额门槛 |
| 直减 | 直接减 value 元（无门槛） | 减免金额 | 0（无门槛） |
| 折扣 | 按 value 折扣率计价 | 0-1 之间的折扣率 | 满足金额门槛（可选） |
| 特价 | 满足门槛后固定特价 value 元 | 固定价格 | 满足金额门槛 |

### 互斥规则

以下促销类型不能同时应用：

- **满减 ↔ 直减**
- **折扣 ↔ 特价**

### 叠加优先级

当多个兼容促销同时应用时，按以下优先级依次计算：

1. 特价 (Special Price)
2. 折扣 (Discount)
3. 满减 (Full Reduction)
4. 直减 (Direct Reduction)

## 使用示例

### 基本订单全生命周期

```python
from decimal import Decimal
from solocoder_py.order import (
    Order, OrderLineItem, OrderState, ShipmentItem
)
import uuid

# 创建订单
line_items = [
    OrderLineItem(
        id=str(uuid.uuid4()),
        product_id="prod-001",
        product_name="商品A",
        unit_price=Decimal("99.00"),
        quantity=2,
    )
]
order = Order(id=str(uuid.uuid4()), user_id="user-001", line_items=line_items)

# 支付
order.pay()
assert order.state == OrderState.PAID

# 发货
shipment = order.ship([
    ShipmentItem(line_item_id=line_items[0].id, quantity=2)
], tracking_number="SF123456789")
assert order.state == OrderState.SHIPPED

# 签收（需所有行项目履约完成）
order.deliver()
assert order.state == OrderState.DELIVERED

# 完成
order.complete()
assert order.state == OrderState.COMPLETED
```

### 部分履约（多次发货）

```python
# 订单包含5件商品
item = OrderLineItem(
    id="li-1", product_id="p-1", product_name="商品",
    unit_price=Decimal("10.00"), quantity=5
)
order = Order(id="o-1", user_id="u-1", line_items=[item])
order.pay()

# 第一次发2件
order.ship([ShipmentItem(line_item_id="li-1", quantity=2)])
assert item.fulfilled_quantity == 2
assert order.is_fully_fulfilled is False

# 第二次发3件
order.ship([ShipmentItem(line_item_id="li-1", quantity=3)])
assert item.fulfilled_quantity == 5
assert order.is_fully_fulfilled is True

# 现在可以签收
order.deliver()
```

### 促销叠加计算

```python
from solocoder_py.order import (
    Promotion, PromotionType, PromotionEngine
)

engine = PromotionEngine()

# 9折（折扣）
discount = Promotion(
    id="p1", name="新人9折",
    type=PromotionType.DISCOUNT, value=Decimal("0.9")
)

# 满100减20（满减）- 与折扣兼容
full_reduction = Promotion(
    id="p2", name="满100减20",
    type=PromotionType.FULL_REDUCTION,
    value=Decimal("20.00"), threshold=Decimal("100.00")
)

# 计算最终价格：200 * 0.9 = 180，180 - 20 = 160
final = engine.calculate_final_price(
    Decimal("200.00"), [discount, full_reduction]
)
assert final == Decimal("160.00")

# 互斥促销（满减 + 直减）会抛异常
from solocoder_py.order import MutuallyExclusivePromotionsError

direct_reduction = Promotion(
    id="p3", name="直减10元",
    type=PromotionType.DIRECT_REDUCTION, value=Decimal("10.00")
)
try:
    engine.calculate_final_price(
        Decimal("200.00"), [full_reduction, direct_reduction]
    )
except MutuallyExclusivePromotionsError:
    print("促销互斥，不能同时使用")
```

### 使用内存仓储

```python
from solocoder_py.order import OrderRepository

repo = OrderRepository()
repo.save(order)

# 查询
found = repo.find_by_id(order.id)
all_orders = repo.find_all()

# 删除
repo.delete(order.id)
repo.clear()
```

## 运行测试

```bash
pytest tests/order/ -v
```
