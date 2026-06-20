# EWMA (指数加权移动平均) 模块

## 模块功能

本模块实现了在线（流式）指数加权移动平均（Exponentially Weighted Moving Average, EWMA）计算器，
使用内存数据结构维护计算状态，支持：

- 带平滑因子 α 的 EWMA 递推计算
- 预热期偏差校正（Bias Correction）
- NaN / Infinity 安全处理与污染隔离
- 状态重置功能

## 核心类职责

### `EWMA` 类

核心计算器类，维护 EWMA 的在线计算状态。

**构造参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `alpha` | `float` | 必选 | 平滑因子，范围 `(0, 1]`。α 越大，近期数据权重越高 |
| `warmup_period` | `int` | `0` | 预热期窗口长度（样本数）。在此期间对 EWMA 做偏差校正。`0` 表示不启用预热校正 |
| `initial_value` | `Optional[float]` | `None` | 初始 EWMA 值。若为 `None`，第一个数据点直接作为初始 S₁ |

**主要方法：**

- `update(value: float) -> Optional[float]`：输入一个新数据点，更新并返回当前 EWMA 值
- `update_all(values) -> Optional[float]`：批量输入数据序列
- `reset() -> None`：将状态重置为初始值（清除污染、计数归零）
- `copy() -> EWMA`：创建当前状态的深拷贝
- `get_result() -> EWMAResult`：获取包含完整状态信息的结果对象

**只读属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `alpha` | `float` | 平滑因子 |
| `warmup_period` | `int` | 预热期长度 |
| `count` | `int` | 已处理的有效数据点数量 |
| `value` | `Optional[float]` | 当前 EWMA 值（预热期内自动校正，预热期后为原始值） |
| `raw_value` | `Optional[float]` | 未经校正的原始 EWMA 值 S_t |
| `corrected_value` | `Optional[float]` | 始终应用偏差校正后的值 |
| `in_warmup` | `bool` | 当前是否处于预热期内 |
| `contaminated` | `bool` | 状态是否因 Infinity 输入而被污染 |
| `last_valid` | `Optional[float]` | 最近一个有效输入值 |

### `EWMAResult` 数据类

冻结数据类，封装 EWMA 的完整状态快照，包含：
`value`, `corrected_value`, `count`, `alpha`, `in_warmup`, `contaminated`

### 异常类层次

```
EWMAError
├── InvalidAlphaError       α 参数超出 (0, 1] 范围
├── InvalidWarmupError      warmup_period 为负数或非整数
└── InfinityEncounteredError 输入为 Infinity，状态被污染
```

---

## EWMA 递推公式

### 基础递推

指数加权移动平均的定义：

```
S_t = α · x_t + (1 - α) · S_{t-1}
```

其中：
- `α` ∈ (0, 1]：平滑因子（Smoothing Factor）
- `x_t`：第 t 个输入数据点
- `S_t`：第 t 步的 EWMA 值

展开递推公式可得：

```
S_t = α · Σ_{i=0}^{t-1} (1-α)^i · x_{t-i} + (1-α)^t · S_0
```

可见每个历史数据点 `x_{t-i}` 的权重为 `α · (1-α)^i`，随时间指数衰减。

半衰期（Half-life）与 α 的关系：

```
N_half = ln(0.5) / ln(1 - α)  ≈  0.693 / α    (当 α 较小时)
```

---

## 偏差校正推导

### 问题起源

当 `S_0 = 0` 且样本量 t 较小时，早期的 S_t 会系统性地偏向 0，
因为 `(1-α)^t · S_0` 这一项尚未衰减到可忽略的程度，
且权重和 `α · Σ_{i=0}^{t-1} (1-α)^i = 1 - (1-α)^t < 1` 小于 1。

### 校正公式

在预热期内，对 S_t 做如下归一化：

```
S_t_corrected = S_t / (1 - (1-α)^t)
```

### 数学推导

无偏初始化（S_0 = 0）下：

```
S_t = α · Σ_{i=0}^{t-1} (1-α)^i · x_{t-i}
```

权重总和为：

```
Σ weights = α · Σ_{i=0}^{t-1} (1-α)^i = 1 - (1-α)^t
```

因此归一化后：

```
E[S_t_corrected] = E[ Σ w_i · x_{t-i} ] / (1 - (1-α)^t )
                 = Σ w_i · E[x] / Σ w_i
                 = E[x]
```

即校正后的估计量对平稳序列的均值是无偏的。

当 t → ∞ 时，`(1-α)^t → 0`，校正因子 → 1，校正公式自动退化为普通 EWMA。

---

## 预热期策略

### 触发条件

设置 `warmup_period = N`（N > 0）后：
- 当 `count < N` 时，`in_warmup = True`，`value` 属性返回校正后的值
- 当 `count ≥ N` 时，`in_warmup = False`，`value` 属性返回原始 S_t

### 选择建议

预热期长度的选择可参考使校正因子接近 1 的样本量：

| 校正阈值 | 所需样本数 t |
|----------|-------------|
| 1 - (1-α)^t ≥ 0.95 | t ≥ ln(0.05)/ln(1-α) |
| 1 - (1-α)^t ≥ 0.99 | t ≥ ln(0.01)/ln(1-α) |

常用经验值：
- α = 0.1 → 预热期 ≈ 30 ~ 50
- α = 0.3 → 预热期 ≈ 10 ~ 15
- α = 0.5 → 预热期 ≈ 5 ~ 7

---

## NaN 安全机制

### 处理规则

1. **NaN 输入**：跳过该数据点，不更新任何内部状态（S_t、count、校正因子均保持不变），
   `update()` 返回当前有效 EWMA 值。可用于处理传感器丢失数据等场景。

2. **±Infinity 输入**：立即将 `contaminated` 标记为 `True`，
   抛出 `InfinityEncounteredError`，此后所有 `update()` 调用均会抛出异常。
   这可防止极端异常值将后续的 EWMA 计算永久污染。

3. **污染恢复**：调用 `reset()` 可清除 `contaminated` 标记，将状态重置为初始值，
   恢复正常计算能力。

4. **初始防御**：α 参数本身不允许为 NaN / Inf，在构造时即校验。

---

## 使用示例

### 基本用法

```python
from solocoder_py.ewma import EWMA

ewma = EWMA(alpha=0.5)

for x in [2.0, 4.0, 6.0, 8.0]:
    s = ewma.update(x)
    print(f"x={x}, EWMA={s:.3f}")

# x=2.0, EWMA=2.000
# x=4.0, EWMA=3.000
# x=6.0, EWMA=4.500
# x=8.0, EWMA=6.250

print(f"共处理 {ewma.count} 个数据点")
```

### 带预热期校正

```python
from solocoder_py.ewma import EWMA

alpha = 0.3
ewma = EWMA(alpha=alpha, warmup_period=10)

data = [1.0] * 20
for t, x in enumerate(data, 1):
    s = ewma.update(x)
    tag = " [warmup]" if ewma.in_warmup else ""
    print(f"t={t:2d}, value={s:.6f}{tag}")
```

### NaN 与 Inf 处理

```python
import math
from solocoder_py.ewma import EWMA, InfinityEncounteredError

ewma = EWMA(alpha=0.5, warmup_period=5)

ewma.update(10.0)
ewma.update(20.0)
val_before = ewma.value

# NaN 被安全跳过
ewma.update(math.nan)
assert ewma.value == val_before
assert ewma.count == 2

# 正常数据继续累积
ewma.update(30.0)

try:
    ewma.update(float("inf"))
except InfinityEncounteredError:
    print("检测到 Infinity，状态被标记为污染")

assert ewma.contaminated is True
ewma.reset()  # 重置，恢复正常
assert ewma.contaminated is False
```

### α = 1 时的直通模式

```python
ewma = EWMA(alpha=1.0)
for x in [3.0, 7.0, 2.0]:
    assert ewma.update(x) == x
```

### 重置与初始值

```python
ewma = EWMA(alpha=0.3, warmup_period=5, initial_value=50.0)
assert ewma.value == 50.0  # 未输入数据时即为初始值

ewma.update(100.0)
# S_1 = 0.3*100 + 0.7*50 = 65.0

ewma.reset()
assert ewma.value == 50.0  # 重置后回到初始值
```
