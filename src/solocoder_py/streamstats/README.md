# Stream Stats 流式统计算子模块

基于 Welford 及其扩展算法的单趟（one-pass）流式统计算子，使用内存数据结构存储在线计算的中间状态，无需存储全部历史数据即可完成多种统计指标的增量计算。

## 功能概览

- **单趟流式计算**：逐个接收数据值，仅维护若干中间累加量，无需存储历史数据
- **五类统计指标**：计数、均值、方差（支持总体方差与样本方差）、偏度、超额峰度
- **算子合并**：两个独立算子可合并为一个，结果等价于全量数据从零计算
- **数值稳定性**：Welford 算法具有优秀的数值稳定性，避免直接累加大数导致精度丢失
- **异常隔离**：NaN / Inf / 非数值类型输入被拒绝且不破坏已有统计状态

## 核心类职责

### StreamStats (stats.py)

`StreamStats` 是模块的核心类，负责：

- 维护中间状态：`n`（计数）、`mean`（均值）、`M2`（二阶中心矩累加量）、`M3`（三阶中心矩累加量）、`M4`（四阶中心矩累加量）
- 提供 `add(value)` 和 `add_all(values)` 流式数据输入接口
- 提供各统计指标的属性访问：`count`、`mean`、`variance`、`variance_sample`、`variance_population`、`skewness`、`kurtosis`、`stddev_sample`、`stddev_population`
- 提供 `merge(other)` 算子合并方法，以及 `+` / `+=` 运算符重载
- 提供 `copy()` 深拷贝、`get_result()` 汇总为 `StatsResult`

### 数据模型与异常 (models.py)

| 类名 | 职责 |
|------|------|
| `StatsResult` | 不可变数据类，封装 count / mean / variance / skewness / kurtosis 五项结果，不足数据时对应字段为 `None` |
| `StreamStatsError` | 模块基异常 |
| `InvalidValueError` | 非法输入值（NaN / Inf / 非数值）异常，携带 `value` 属性 |
| `MergeError` | 合并操作相关异常 |

## Welford 单趟计算原理与增量更新公式

### 经典 Welford 算法（均值与方差）

设已接收 $n$ 个数据，均值为 $\bar{x}_n$，二阶中心矩累加量 $M_{2,n} = \sum_{i=1}^{n} (x_i - \bar{x}_n)^2$。

接收新值 $x_{n+1}$ 时，增量更新公式：

$$
\begin{aligned}
n_{new} &= n + 1 \\
\delta &= x_{n+1} - \bar{x}_n \\
\bar{x}_{new} &= \bar{x}_n + \frac{\delta}{n_{new}} \\
M_{2,new} &= M_{2,n} + \delta \cdot (x_{n+1} - \bar{x}_{new})
\end{aligned}
$$

### 扩展到更高阶矩（偏度与峰度）

为了支持偏度（三阶）和峰度（四阶），需要同时维护 $M_3$ 和 $M_4$：

$$
M_{k,n} = \sum_{i=1}^{n} (x_i - \bar{x}_n)^k
$$

定义：

$$
\begin{aligned}
\delta_n &= \frac{\delta}{n_{new}} \\
\delta_n^2 &= \delta_n \cdot \delta_n \\
term_1 &= \delta \cdot \delta_n \cdot n
\end{aligned}
$$

则各阶矩的增量更新：

$$
\begin{aligned}
M_{4,new} &= M_4 + term_1 \cdot \delta_n^2 \cdot (n_{new}^2 - 3 n_{new} + 3) + 6 \cdot \delta_n^2 \cdot M_2 - 4 \cdot \delta_n \cdot M_3 \\
M_{3,new} &= M_3 + term_1 \cdot \delta_n \cdot (n_{new} - 2) - 3 \cdot \delta_n \cdot M_2 \\
M_{2,new} &= M_2 + term_1
\end{aligned}
$$

更新顺序必须从高阶到低阶（$M_4 \to M_3 \to M_2$），因为高阶矩的更新依赖低阶矩的旧值。

## 偏度与峰度的计算公式

### 样本方差

$$
s^2 = \frac{M_2}{n - 1}
$$

### 总体方差

$$
\sigma^2 = \frac{M_2}{n}
$$

本模块默认 `variance` 属性返回**样本方差**（即无偏估计，除以 $n-1$），总体方差通过 `variance_population` 获取。

### 偏度（三阶标准化矩）

偏度衡量分布的不对称程度：

$$
g_1 = \frac{\sqrt{n} \cdot M_3}{M_2^{3/2}}
$$

- $g_1 = 0$：对称分布（如正态）
- $g_1 > 0$：右偏（长尾在右侧）
- $g_1 < 0$：左偏（长尾在左侧）

本模块要求 $n \ge 3$ 且 $M_2 > 0$，否则返回 `None`。

### 超额峰度（四阶标准化矩，减 3）

峰度衡量分布尾部的厚重程度。本模块实现**超额峰度**（excess kurtosis），以正态分布为基准（0）：

$$
g_2 = \frac{n \cdot M_4}{M_2^2} - 3
$$

- $g_2 = 0$：与正态分布尾部厚度相当（mesokurtic）
- $g_2 > 0$：尾部更厚（leptokurtic，如 t 分布）
- $g_2 < 0$：尾部更薄（platykurtic，如均匀分布）

本模块要求 $n \ge 4$ 且 $M_2 > 0$，否则返回 `None`。

## 合并算子的聚合公式

设两个独立算子 A 和 B，分别接收了 $n_A$ 和 $n_B$ 个数据，均值为 $\bar{x}_A, \bar{x}_B$，各阶矩 $M_{2,A}, M_{2,B}, M_{3,A}, M_{3,B}, M_{4,A}, M_{4,B}$。

合并后的总计数 $n_C = n_A + n_B$，均值差 $\delta = \bar{x}_B - \bar{x}_A$。

### 合并后的均值

$$
\bar{x}_C = \frac{n_A \bar{x}_A + n_B \bar{x}_B}{n_C}
$$

### 合并后的二阶矩（方差）

$$
M_{2,C} = M_{2,A} + M_{2,B} + \frac{n_A n_B}{n_C} \delta^2
$$

### 合并后的三阶矩（偏度）

$$
M_{3,C} = M_{3,A} + M_{3,B} + \frac{n_A n_B (n_A - n_B)}{n_C^2} \delta^3 + \frac{3 \delta}{n_C} (n_A M_{2,B} - n_B M_{2,A})
$$

### 合并后的四阶矩（峰度）

$$
M_{4,C} = M_{4,A} + M_{4,B} + \frac{n_A n_B (n_A^2 - n_A n_B + n_B^2)}{n_C^3} \delta^4 + \frac{6 \delta^2}{n_C^2} (n_A^2 M_{2,B} + n_B^2 M_{2,A}) + \frac{4 \delta}{n_C} (n_A M_{3,B} - n_B M_{3,A})
$$

合并操作可通过 `a.merge(b)`（原地修改 `a`）、`a + b`（返回新对象）、`a += b`（原地合并）三种方式完成。

## 使用示例

### 基础流式统计

```python
from solocoder_py.streamstats import StreamStats

s = StreamStats()
data = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5]
for v in data:
    s.add(v)

print(s.count)           # 11
print(s.mean)            # 约 4.0
print(s.variance)        # 样本方差
print(s.variance_population)  # 总体方差
print(s.skewness)        # 偏度
print(s.kurtosis)        # 超额峰度
```

### 获取汇总结果

```python
result = s.get_result()
# StatsResult(count=11, mean=4.0, variance=..., skewness=..., kurtosis=...)
```

### 批量输入

```python
s = StreamStats()
s.add_all([1, 2, 3, 4, 5])
```

### 算子合并

```python
a = StreamStats()
a.add_all([1, 2, 3, 4, 5])

b = StreamStats()
b.add_all([6, 7, 8, 9, 10])

# 原地合并
c = a.copy()
c.merge(b)

# 或使用运算符
merged = a + b

# 或原地
a += b
```

### 异常处理

```python
from solocoder_py.streamstats import StreamStats, InvalidValueError

s = StreamStats()
s.add_all([1, 2, 3])

try:
    s.add(float("nan"))
except InvalidValueError as e:
    print(f"拒绝非法值: {e.value}")

# 原有统计状态不受影响
print(s.count)  # 3
```

## 边界行为说明

| 场景 | count | mean | variance_sample | variance_population | skewness | kurtosis |
|------|-------|------|-----------------|---------------------|----------|----------|
| 空算子（无数据） | 0 | None | None | None | None | None |
| 仅 1 个数据点 | 1 | 值本身 | None | 0.0 | None | None |
| 仅 2 个数据点 | 2 | 两值均值 | 有定义 | 有定义 | None | None |
| 3+ 数据点，全相同 | n | 相同值 | 0.0 | 0.0 | None | None |
| 3+ 数据点，有方差 | n | 有定义 | 有定义 | 有定义 | 有定义 (n≥3) | 有定义 (n≥4) |

## 测试覆盖

测试代码位于 `tests/streamstats/` 目录：

- `test_normal_flows.py`：正常流程（均值方差与标准库对比、正态分布偏度峰度接近理论值、在线更新正确性、算子合并一致性）
- `test_edge_cases.py`：边界条件（空算子、单/双数据点、全相同值、悬殊数据量合并、拷贝独立性）
- `test_error_branches.py`：异常分支（NaN/Inf 隔离与状态保护、合并空算子、M2 非负稳定性、极端值精度验证）
