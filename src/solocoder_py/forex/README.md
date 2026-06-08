# Forex 多币种汇率换算域模块

## 模块功能

本模块实现了基于内存数据结构的多币种汇率换算引擎，支持以下核心能力：

1. **汇率管理**：支持添加和更新任意两种货币之间的直接汇率。每个汇率记录包含基准货币、目标货币、汇率值和版本号（时间戳），同一货币对可以有多个历史版本的汇率。
2. **直接换算**：给定金额、源货币和目标货币，如果存在该货币对的直接汇率，按该汇率换算；如果存在反向汇率（目标货币到源货币），通过取倒数的方式换算。
3. **三角换算**：当源货币到目标货币没有直接汇率时，通过中间货币进行换算，支持多跳路径查找，优先选择路径最短（跳数最少）的换算路径。
4. **精度舍入规则**：每种货币有独立的小数位数配置（如 JPY 为 0 位、USD 为 2 位、BTC 为 8 位）。换算结果按目标货币的小数位数进行舍入，舍入模式可配置（四舍五入 / 向下取整 / 向上取整），并记录舍入产生的损益。
5. **汇率版本时点回溯**：可以根据指定的版本号查找该时点生效的汇率版本进行换算，支持历史时点的金额回溯查询。
6. **循环路径检测**：支持检测汇率图中的循环套利路径。

## 核心类职责

### exceptions.py

| 类名 | 职责 |
|------|------|
| `ForexError` | 模块异常基类 |
| `CurrencyPrecisionNotFoundError` | 货币精度配置缺失 |
| `ExchangeRateNotFoundError` | 直接汇率不存在 |
| `NoConversionPathError` | 完全无可达换算路径 |
| `InvalidExchangeRateError` | 汇率参数非法（非正数、货币相同等） |
| `VersionNotFoundError` | 指定版本号不存在 |
| `CircularPathDetectedError` | 三角换算中检测到循环路径 |
| `PathExplosionError` | 中间货币过多导致路径爆炸 |

### models.py

| 类名 | 职责 |
|------|------|
| `RoundingMode` | 舍入模式枚举：`HALF_UP`（四舍五入）、`FLOOR`（向下取整）、`CEILING`（向上取整） |
| `ExchangeRate` | 汇率记录数据模型：基准货币、目标货币、汇率值、版本号；创建时自动校验合法性 |
| `CurrencyPrecision` | 货币精度配置：货币代码、小数位数 |
| `ConversionPath` | 换算路径数据模型：包含货币节点路径和途经的汇率列表，提供跳数统计和汇率乘积计算 |
| `ConversionResult` | 换算结果数据模型：原始金额、原始换算值、舍入后金额、舍入损益、换算路径、舍入模式、目标精度、使用的版本号 |

### engine.py

| 类名 | 职责 |
|------|------|
| `ForexConverter` | 汇率换算引擎，维护汇率多版本数据、货币精度配置；提供汇率增改查、精度设置、直接/三角换算、版本回溯、循环路径检测等核心功能 |

## 三角换算路径查找策略

### 查找优先级

换算引擎按照以下优先级寻找路径：

1. **直接汇率**：首先查找 `source → target` 的直接汇率，如存在直接使用。
2. **反向汇率倒数**：若直接汇率不存在，查找 `target → source` 的反向汇率，取倒数作为 `source → target` 的汇率。
3. **多跳 BFS 路径查找**：若以上均不存在，使用广度优先搜索（BFS）遍历汇率图，找到跳数最少的可达路径。

### BFS 路径查找算法

```
source → [查找邻居货币] → 队列遍历 → 找到 target
```

算法要点：

- **图的边**：每个已登记的汇率 `A→B` 提供两条有向边：
  - `A → B`（正向，权重 = rate）
  - `B → A`（反向，权重 = 1/rate）
- **遍历限制**：最大跳数由 `max_hops` 参数控制（默认 5 跳），防止路径爆炸。
- **路径爆炸防护**：BFS 过程中累计探索的路径数超过 1000 条时，抛出 `PathExplosionError`。
- **已访问集合**：每条路径维护独立的已访问货币集合，防止在单条路径中重复访问同一货币（即循环路径）。
- **最短路径优先**：BFS 天然保证首次访问目标货币时经过的是跳数最少的路径。

### 循环路径检测

`detect_circular_paths()` 方法通过深度优先搜索（DFS）从每个货币出发，查找回到起点的非平凡路径（长度 > 1），返回去重后的循环列表。每个循环会被规范化（旋转+反转后取字典序最小）以避免重复报告。

## 精度舍入策略

### 舍入流程

```
原始金额 × 路径汇率乘积 → raw_amount
           ↓
按目标货币 decimal_places 放大 (× 10^n)
           ↓
根据 rounding_mode 对放大后的值取整
           ↓
缩小回原量级 (÷ 10^n) → rounded_amount
           ↓
rounding_loss = rounded_amount - raw_amount
```

### 舍入模式详解

| 模式 | 行为 | 示例（保留 2 位小数） |
|------|------|----------------------|
| `HALF_UP` | 四舍五入：小数部分 ≥ 0.5 则进一位，否则舍去（负数对称处理） | 1.234 → 1.23；1.235 → 1.24；-1.235 → -1.24 |
| `FLOOR` | 向下取整：向负无穷方向取最近整数 | 1.239 → 1.23；-1.231 → -1.24 |
| `CEILING` | 向上取整：向正无穷方向取最近整数 | 1.231 → 1.24；-1.239 → -1.23 |

### 舍入损益

`rounding_loss = rounded_amount - raw_amount`

- 正值：舍入产生收益（金额增大）
- 负值：舍入产生损失（金额减小）
- 零：无需舍入或舍入后无变化

## 汇率版本机制

### 版本号分配

- 每次调用 `add_rate()` 时，若未指定版本号，引擎自动分配全局递增的版本号（从 1 开始）。
- 若手动指定版本号，引擎确保内部 `_next_version` 不小于指定值 + 1，保持单调性。
- 同一货币对可以添加多个版本的汇率，按版本号升序存储。

### 版本查找规则

`get_rate()` 和 `convert()` 接受可选的 `version` 参数：

- `version=None`：使用该货币对的最新版本（版本号最大）。
- `version=N`：查找所有 `version ≤ N` 的记录中版本号最大的那个（即该时点生效的最新汇率）。
- 若指定版本号小于该货币对的最早版本，返回 `None`（换算时将尝试其他路径）。

## 使用示例

### 基本汇率管理与直接换算

```python
from solocoder_py.forex import ForexConverter, RoundingMode

fx = ForexConverter()

fx.set_precision("USD", 2)
fx.set_precision("CNY", 2)
fx.set_precision("JPY", 0)
fx.set_precision("EUR", 2)
fx.set_precision("BTC", 8)

r1 = fx.add_rate("USD", "CNY", 7.2)
r2 = fx.add_rate("USD", "JPY", 150.0)

result = fx.convert(100, "USD", "CNY")
print(f"100 USD = {result.rounded_amount} CNY")
print(f"路径跳数: {result.path.hops}")
print(f"舍入损益: {result.rounding_loss}")

result_jpy = fx.convert(100, "USD", "JPY", rounding_mode=RoundingMode.FLOOR)
print(f"100 USD = {result_jpy.rounded_amount} JPY (向下取整)")
```

### 使用反向汇率（倒数换算）

```python
fx.add_rate("CNY", "USD", 1 / 7.2)
result = fx.convert(720, "CNY", "USD")
print(f"720 CNY = {result.rounded_amount} USD")
```

### 三角换算（多跳路径）

```python
fx.add_rate("USD", "EUR", 0.92)
fx.add_rate("EUR", "GBP", 0.85)

result = fx.convert(100, "USD", "GBP")
print(f"100 USD = {result.rounded_amount} GBP")
print(f"路径: {' → '.join(result.path.path)}")
print(f"跳数: {result.path.hops}")
```

### 版本回溯查询

```python
fx.add_rate("USD", "CNY", 6.8, version=100)
fx.add_rate("USD", "CNY", 7.0, version=200)
fx.add_rate("USD", "CNY", 7.2, version=300)

result_v150 = fx.convert(100, "USD", "CNY", version=150)
print(f"版本150时 100 USD = {result_v150.rounded_amount} CNY")  # 使用 7.0

result_v250 = fx.convert(100, "USD", "CNY", version=250)
print(f"版本250时 100 USD = {result_v250.rounded_amount} CNY")  # 使用 7.0

result_latest = fx.convert(100, "USD", "CNY")
print(f"最新版 100 USD = {result_latest.rounded_amount} CNY")   # 使用 7.2
```

### 三种舍入模式对比

```python
fx.set_precision("USD", 2)
fx.add_rate("EUR", "USD", 1.08567)

for mode in [RoundingMode.HALF_UP, RoundingMode.FLOOR, RoundingMode.CEILING]:
    result = fx.convert(100, "EUR", "USD", rounding_mode=mode)
    print(f"{mode.value}: raw={result.raw_amount:.6f}, "
          f"rounded={result.rounded_amount}, loss={result.rounding_loss:.6f}")
```

### 循环路径检测

```python
fx.add_rate("USD", "EUR", 0.92)
fx.add_rate("EUR", "GBP", 0.85)
fx.add_rate("GBP", "USD", 1.28)

cycles = fx.detect_circular_paths()
for cycle in cycles:
    print(" → ".join(cycle))
```

## 运行测试

```bash
pytest tests/forex/ -v
```
