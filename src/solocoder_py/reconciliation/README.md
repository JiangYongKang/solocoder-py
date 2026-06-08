# 支付对账引擎 (Reconciliation Engine)

## 模块功能

本模块实现了一个内存级的支付对账引擎，用于对比本方系统流水与渠道方（银行/支付网关）流水数据，识别匹配成功、单边差异、容差核销等多种场景，并生成对账汇总报告。

## 核心类职责

### Transaction
标准化交易流水记录，统一存储本方与渠道方流水。
- 关键字段：`txn_id`（交易流水号，可为 None）、`amount`（交易金额）、`txn_time`（交易时间）、`status`（交易状态）、`side`（本方/渠道方标识）、`order_id`（关联订单号）
- `has_txn_id` 属性：判断流水是否具有有效流水号（非 None 且非空字符串）

### ToleranceConfig
容差配置，用于判定金额差异是否在可接受范围内。
- `absolute_tolerance`：绝对容差，默认 0.01 元
- `relative_tolerance`：相对容差，默认 0.01%（0.0001）
- `is_within_tolerance()`：判断两金额是否在容差范围内
- `diff_amount()`：计算金额差异

### Discrepancy
单边差异记录，存储未匹配成功的流水及差异原因分类。
- `type`：差异类型（见 DiscrepancyType）
- 关联本方或渠道方交易记录

### MatchedPair
匹配成功的双边流水对。
- `match_type`：匹配类型（EXACT/TOLERANCE/FALLBACK）
- `diff_amount`：金额差异（internal - channel）
- `write_off`：是否已核销（容差核销标记）

### ReconciliationReport
对账报告，汇总对账结果。
- 总笔数、总金额、匹配数
- 容差核销统计
- 本方/渠道方单边差异分类统计
- `summary()`：生成字典形式的汇总信息

### ReconciliationEngine
对账引擎核心类，提供流水导入、对账执行、报告查询等功能。

## 匹配规则

### 1. 交易流水号精确匹配（主键匹配）
优先按 `txn_id` 在两边流水中查找一一对应的记录。**仅当两边记录都具有有效流水号时才参与 ID 匹配**。

匹配成功条件：
- 流水号一致
- 交易状态一致
- 金额四舍五入至两位小数后相等 → `MatchType.EXACT`
- 或金额在容差范围内 → `MatchType.TOLERANCE`（自动核销）

### 2. 金额+时间降级匹配（Fallback 匹配）
当流水号无法匹配（含流水号缺失场景）时，使用金额+交易时间组合规则进行降级匹配。

**流水号缺失降级策略**：
- 若某条流水的所有候选流水号字段（本方：`txn_id`/`transaction_id`/`order_id`；渠道方：`txn_id`/`trade_no`/`transaction_id`）均为空或缺失，则 `txn_id` 设为 `None`
- `txn_id` 为 `None` 或空字符串的流水**不参与流水号 ID 匹配**，直接进入 Fallback 匹配路径
- 多条缺失流水号的流水使用独立的内部键存储，不会因假流水号相同被错误去重或错误配对

**Fallback 金额比较精度约定**：
- 金额比较先按两位小数四舍五入（`round(amount, 2)`），再判断是否相等
- 此举避免浮点运算微小误差（如 12.345000001 vs 12.345）导致的匹配失败
- 若四舍五入后不相等，仍会继续检查是否在容差配置范围内

匹配成功条件：
- 金额四舍五入至两位小数后相等，或在容差范围内
- 交易时间差在配置的时间窗口内（默认 5 分钟）
- 交易状态一致 → `MatchType.FALLBACK`（匹配成功）
- 交易状态不一致 → 标记为 `STATUS_MISMATCH` 差异（不匹配，保留分类信息）

## 容差核销机制

当匹配到的双边流水金额差异满足以下任一条件时，视为匹配成功并自动核销：
1. 绝对差额 ≤ `absolute_tolerance`（默认 0.01 元）
2. 相对差额 ≤ `relative_tolerance`（默认 0.01%）

容差核销的记录会：
- 在 `MatchedPair` 中标记 `write_off = True`
- 差异金额计入 `tolerance_write_off_diff_amount`
- 统计入容差核销笔数 `tolerance_write_off_count`

**匹配金额口径定义**：
- 汇总报告中的 `matched_amount`（匹配成功金额）统一使用**渠道方金额**（`channel_txn.amount`）作为核销口径
- 理由：渠道方（银行/支付网关）的金额是实际资金清算的最终依据，容差核销本质上是本方调账以对齐渠道方金额
- 精确匹配时本方与渠道方金额相等，口径一致；容差核销时差异通过 `tolerance_write_off_diff_amount` 单独反映，确保对账报告的资金口径可追溯

## 单边差异分类

### 本方单边差异
- `CHANNEL_MISSING`：渠道方无对应记录
- `AMOUNT_MISMATCH`：金额不一致且超出容差
- `STATUS_MISMATCH`：交易状态不匹配（含 ID 匹配路径与 Fallback 匹配路径发现的状态不一致）

### 渠道方单边差异
- `INTERNAL_MISSING`：本方系统无对应记录
- `AMOUNT_MISMATCH`：金额不一致且超出容差
- `STATUS_MISMATCH`：交易状态不匹配

## 使用示例

```python
from datetime import datetime
from solocoder_py.reconciliation import ReconciliationEngine, ToleranceConfig

engine = ReconciliationEngine(
    tolerance=ToleranceConfig(absolute_tolerance=0.01, relative_tolerance=0.0001)
)

# 导入本方流水
engine.import_internal_transactions([
    {"txn_id": "T001", "amount": 100.00, "txn_time": "2024-01-01T10:00:00", "status": "success"},
])

# 导入渠道方流水（格式不同时自动归一化）
engine.import_channel_transactions([
    {"trade_no": "T001", "amount": 100.00, "trade_time": "2024-01-01T10:00:00", "status": "success"},
])

# 执行对账
report = engine.reconcile()

# 查看汇总
print(report.summary())
```
