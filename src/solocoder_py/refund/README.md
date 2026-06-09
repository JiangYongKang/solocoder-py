# 退款与拒付处理域模块

## 模块功能

本模块实现了完整的退款与拒付（Chargeback）处理域逻辑，包括：

1. **退款状态机**：管理退款申请从创建到终态的全生命周期状态流转，包括审核中、已退款、已拒绝、已拒付、已取消等状态
2. **部分退款累计校验**：支持一笔支付发起多次部分退款，累计退款金额不得超过原始支付金额，超额退款自动拦截
3. **拒付（Chargeback）处理**：当发生拒付时，自动回退已退款金额，重新计算可退余额，并更新对应退款单的状态
4. **内存数据仓储**：使用内存数据结构模拟数据源，提供支付、退款、拒付的持久化操作

## 核心类职责

### states.py

| 类名 | 职责 |
|------|------|
| `RefundState` | 枚举类型，定义退款所有状态（退款申请、审核中、已退款、已拒绝、已拒付、已取消） |
| `RefundStateMachine` | 状态机引擎，管理状态转移规则，校验转移合法性，执行状态转换 |
| `InvalidStateTransitionError` | 非法状态转移异常 |

### exceptions.py

| 类名 | 职责 |
|------|------|
| `RefundError` | 退款模块基础异常 |
| `PaymentError` / `PaymentNotFoundError` / `PaymentExistsError` | 支付相关异常 |
| `RefundAmountError` / `ExcessRefundError` / `InvalidRefundAmountError` | 退款金额校验异常 |
| `RefundStateError` / `RefundNotFoundError` / `RefundExistsError` | 退款状态与存在性异常 |
| `ChargebackError` / `ChargebackExistsError` / `ChargebackAmountError` | 拒付处理异常 |

### models.py

| 类名 | 职责 |
|------|------|
| `Payment` | 支付实体，记录支付金额、币种、累计退款金额、累计拒付金额，提供可退款余额计算、增加退款、回退退款等操作 |
| `Refund` | 退款单实体，封装退款状态流转（开始审核、通过、拒绝、取消、拒付），记录退款金额、原因、时间戳等 |
| `Chargeback` | 拒付记录实体，关联支付与特定退款单（可选），记录拒付金额与原因 |
| `make_payment` / `make_refund` / `make_chargeback` | 工厂函数，自动生成 UUID 作为实体 ID |

### repository.py

| 类名 | 职责 |
|------|------|
| `RefundRepository` | 内存数据仓储，提供 Payment、Refund、Chargeback 的增删改查及按关联 ID 查询操作 |

### engine.py

| 类名 | 职责 |
|------|------|
| `RefundEngine` | 退款领域服务引擎，封装完整业务流程：创建支付、发起退款、开始审核、通过/拒绝/取消退款、处理拒付、查询可退余额等 |

## 状态机图

```
                        ┌─────────────┐
            ┌───────────│  退款申请    │───────────┐
            │           └──────┬──────┘           │
            │                  │                  │
            ▼                  ▼                  ▼
     ┌─────────────┐    ┌─────────────┐     ┌─────────────┐
     │   已取消     │    │   审核中     │     │             │
     └─────────────┘    └──────┬──────┘     │             │
                          ┌────┼────┐         │             │
                          ▼    ▼    ▼         │             │
                   ┌──────────┐ ┌──────────┐ │             │
                   │  已退款   │ │  已拒绝   │ │             │
                   └─────┬────┘ └──────────┘ │             │
                         │                    │             │
                         ▼                    │             │
                   ┌──────────┐               │             │
                   │  已拒付   │◄──────────────┘             │
                   └──────────┘                              │
                         ▲                                   │
                         └───────────────────────────────────┘
```

### 合法状态转移路径

| 当前状态 | 可转移至 | 说明 |
|---------|---------|------|
| 退款申请 | 审核中、已取消 | 退款创建后可进入审核或用户主动取消 |
| 审核中 | 已退款、已拒绝、已拒付 | 审核通过、拒绝，或在审核期间发生拒付 |
| 已退款 | 已拒付 | 退款完成后银行发起拒付 |
| 已拒绝 | （终态） | 审核拒绝后不可再变更 |
| 已拒付 | （终态） | 拒付完成后不可再变更 |
| 已取消 | （终态） | 用户取消后不可再变更 |

## 部分退款与拒付核心规则

### 可退余额计算

```
可退余额 = 原始支付金额 - 已退款金额
```

**说明**：当发生拒付时，通过 `rollback_refunded_amount` 回退已退款金额，从而自动恢复可退余额。`charged_back_amount` 仅作为统计追踪字段，不直接参与可退余额计算。

### 部分退款规则

- 单笔退款金额必须为正数
- 累计退款金额不得超过原始支付金额
- 超额退款在申请时即被拦截，抛出 `ExcessRefundError`

### 拒付处理规则

- 可针对特定退款单发起拒付（传入 `refund_id`），或不关联具体退款单（`refund_id=None`）
- 拒付金额不得超过对应退款单金额（关联退款单时）或累计已退款金额（不关联时）
- 关联退款单且状态为 `已退款` 时，自动回退支付的已退款金额
- 关联退款单时，自动将退款单状态流转为 `已拒付`
- 拒付完成后，可退余额自动恢复（已退款金额减少），允许重新发起退款

## 使用示例

### 基本退款流程

```python
from decimal import Decimal
from solocoder_py.refund import RefundEngine, RefundRepository, RefundState

engine = RefundEngine(RefundRepository())

# 1. 创建支付
payment = engine.create_payment(user_id="user-001", amount=Decimal("1000.00"))

# 2. 发起退款申请
refund = engine.request_refund(
    payment_id=payment.id,
    amount=Decimal("300.00"),
    reason="商品质量问题",
)
assert refund.state == RefundState.REFUND_REQUESTED

# 3. 开始审核
engine.start_review(refund.id)
refund = engine.repository.get_refund(refund.id)
assert refund.state == RefundState.UNDER_REVIEW

# 4. 审核通过（退款到账）
engine.approve_refund(refund.id)
refund = engine.repository.get_refund(refund.id)
assert refund.state == RefundState.REFUNDED

# 5. 验证可退余额
payment = engine.repository.get_payment(payment.id)
assert payment.refunded_amount == Decimal("300.00")
assert payment.available_refund_amount == Decimal("700.00")
```

### 多次部分退款（累计校验）

```python
from decimal import Decimal
from solocoder_py.refund import RefundEngine, RefundRepository, ExcessRefundError

engine = RefundEngine(RefundRepository())
payment = engine.create_payment(user_id="user-001", amount=Decimal("100.00"))

# 第一次退 30
r1 = engine.request_refund(payment.id, Decimal("30.00"))
engine.start_review(r1.id)
engine.approve_refund(r1.id)
assert engine.get_available_refund_amount(payment.id) == Decimal("70.00")

# 第二次退 50
r2 = engine.request_refund(payment.id, Decimal("50.00"))
engine.start_review(r2.id)
engine.approve_refund(r2.id)
assert engine.get_available_refund_amount(payment.id) == Decimal("20.00")

# 第三次超额退款会被拦截
try:
    engine.request_refund(payment.id, Decimal("30.00"))
except ExcessRefundError as e:
    print(f"超额退款被拦截: 请求{e.requested}, 可退{e.available}")
    # 输出: 超额退款被拦截: 请求30.0, 可退20.0
```

### 审核拒绝与取消

```python
from decimal import Decimal
from solocoder_py.refund import RefundEngine, RefundRepository, RefundState

engine = RefundEngine(RefundRepository())
payment = engine.create_payment(user_id="user-001", amount=Decimal("500.00"))

# 审核拒绝
refund = engine.request_refund(payment.id, Decimal("100.00"))
engine.start_review(refund.id)
engine.reject_refund(refund.id)
assert engine.repository.get_refund(refund.id).state == RefundState.REJECTED
# 拒绝后不扣减可退余额
assert engine.get_available_refund_amount(payment.id) == Decimal("500.00")

# 用户主动取消（需在审核前）
refund2 = engine.request_refund(payment.id, Decimal("50.00"))
engine.cancel_refund(refund2.id)
assert engine.repository.get_refund(refund2.id).state == RefundState.CANCELLED
```

### 拒付（Chargeback）处理

```python
from decimal import Decimal
from solocoder_py.refund import RefundEngine, RefundRepository, RefundState

engine = RefundEngine(RefundRepository())
payment = engine.create_payment(user_id="user-001", amount=Decimal("1000.00"))

# 先完成一笔退款
refund = engine.request_refund(payment.id, Decimal("500.00"))
engine.start_review(refund.id)
engine.approve_refund(refund.id)
assert engine.get_available_refund_amount(payment.id) == Decimal("500.00")

# 银行发起拒付，关联该退款单
chargeback = engine.process_chargeback(
    payment_id=payment.id,
    refund_id=refund.id,
    amount=Decimal("500.00"),
    reason="持卡人否认交易",
)

# 退款单状态变更为已拒付
assert engine.repository.get_refund(refund.id).state == RefundState.CHARGED_BACK

# 已退款金额回退，可退余额恢复
payment = engine.repository.get_payment(payment.id)
assert payment.refunded_amount == Decimal("0.00")
assert payment.charged_back_amount == Decimal("500.00")
assert payment.available_refund_amount == Decimal("1000.00")

# 可以重新发起退款
new_refund = engine.request_refund(payment.id, Decimal("800.00"))
engine.start_review(new_refund.id)
engine.approve_refund(new_refund.id)
assert engine.get_available_refund_amount(payment.id) == Decimal("200.00")
```

### 非法状态转移拦截

```python
from decimal import Decimal
from solocoder_py.refund import (
    RefundEngine, RefundRepository, RefundStateError
)

engine = RefundEngine(RefundRepository())
payment = engine.create_payment(user_id="user-001", amount=Decimal("1000.00"))
refund = engine.request_refund(payment.id, Decimal("300.00"))

# 未经审核直接通过会抛异常
try:
    engine.approve_refund(refund.id)
except RefundStateError as e:
    print(f"状态错误: {e}")
    # 输出: 状态错误: Cannot approve refund in state: 退款申请
```

## 运行测试

```bash
pytest tests/refund/ -v
```
