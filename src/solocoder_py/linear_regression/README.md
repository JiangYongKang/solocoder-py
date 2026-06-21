# Linear Regression 模块 - 简单线性回归在线学习器

本模块实现了一个基于内存数据结构的**简单线性回归在线学习器**，支持单样本梯度下降更新、点预测和 R² 拟合优度计算。所有统计量均在在线更新过程中增量维护，无需存储全部历史数据。

## 模块功能

- **在线自适应优化更新**：每接收一个 (x, y) 样本对，使用带自适应梯度裁剪的 SGD 更新模型参数 w（斜率）和 b（截距），兼顾收敛速度和数值稳定性
- **点预测**：给定 x 值，使用当前模型参数返回预测值 ŷ = w·x + b
- **R² 拟合优度计算**：基于所有已接收样本计算决定系数 R²，衡量模型对数据的解释程度
- **在线统计量维护**：在样本更新过程中增量维护必要的中间统计量（样本数、x/y 的和与平方和、xy 乘积和），无需存储历史数据
- **输入验证**：严格校验学习率和样本数据的合法性，拒绝无效输入

## 核心类职责

### SimpleLinearRegression

简单线性回归器核心类，负责模型参数的在线更新、预测和拟合优度计算。

| 方法/属性 | 描述 |
|-----------|------|
| `__init__(learning_rate)` | 初始化回归器，指定学习率 |
| `update(x, y)` | 接收单个样本，使用自适应梯度裁剪的 SGD 更新模型参数 |
| `predict(x)` | 基于当前模型参数预测 x 对应的 y 值 |
| `r2_score()` | 计算模型的 R² 决定系数 |
| `w` | 当前模型斜率参数（只读属性） |
| `b` | 当前模型截距参数（只读属性） |
| `n_samples` | 已接收的样本总数（只读属性） |
| `learning_rate` | 基础学习率（只读属性） |

## 自适应梯度裁剪优化更新公式与推导

### 模型形式

简单线性模型：

```
ŷ = w·x + b
```

其中：
- w 为斜率（权重）
- b 为截距（偏置）
- x 为输入特征
- ŷ 为预测值

### 损失函数

使用均方误差（MSE）作为损失函数。对于单个样本 (x, y)：

```
L = (1/2)·(ŷ - y)² = (1/2)·(w·x + b - y)²
```

系数 1/2 是为了求导后形式更简洁，不影响最优解。

### 梯度推导

对损失函数分别求 w 和 b 的偏导数：

对 w 求偏导：
```
∂L/∂w = (ŷ - y)·x
```

对 b 求偏导：
```
∂L/∂b = (ŷ - y)
```

### 自适应梯度裁剪优化器

标准 SGD 中 `dw = error·x` 与 `db = error` 的量级差异极大（x 越大差异越大），会导致：
- 当 x 取值范围很大（如 0~1000+）时，dw 急剧膨胀，参数发散为 NaN
- 若使用极小学习率防止 w 发散，则 b 几乎不动，收敛极慢

完全归一化的 Adam 优化器虽然解决了稳定性问题，但在小学习率、单轮遍历的在线学习场景中收敛过慢，因为梯度被完全归一化后有效步长 ≈ 学习率，与梯度大小无关。

本模块采用 **SGD + 自适应梯度裁剪** 的折中方案：
- 使用梯度二阶矩（指数移动平均）估计典型梯度量级
- 当梯度在典型量级范围内时，行为等同于普通 SGD，收敛速度快
- 当梯度异常大（可能导致发散）时，自动裁剪到安全阈值

核心公式：

```
v_t = β₂·v_{t-1} + (1-β₂)·g_t²      （二阶矩，梯度平方累积）
v̂_t = v_t / (1 - β₂ᵗ)                （偏置校正）
max_grad = C·√v̂_t                     （自适应裁剪阈值）
g_clipped = clip(g_t, -max_grad, max_grad)
θ_t = θ_{t-1} - lr·g_clipped         （参数更新）
```

其中：
- β₂ = 0.999（二阶矩指数衰减率）
- C = 10.0（裁剪系数，允许梯度达到典型值的 10 倍）
- g_t 为当前梯度（dw 或 db）

### 稳定性保障原理

二阶矩 `√v̂_t` 相当于每个参数自身梯度量级的运行时估计。当 `dw = error·x` 因 x 很大而达到异常量级时，裁剪阈值会自动收紧，将梯度限制在安全范围内。而正常梯度不会被裁剪，保持 SGD 的快速收敛特性。

这就实现了：
- 常规梯度下保持 SGD 的快速收敛速度
- 异常梯度下自动裁剪，防止 NaN 发散
- w 和 b 的更新尺度自动解耦，互不干扰
- 无需用户手动根据 x 范围精细调节学习率

### 参数更新伪代码

```
输入：样本 (x, y)，学习率 lr
1. 计算预测值：ŷ = w·x + b
2. 计算误差：error = ŷ - y
3. 计算梯度：
   dw = error·x
   db = error
4. 更新二阶矩（梯度平方累积）：
   v_w = β₂·v_w + (1-β₂)·dw²
   v_b = β₂·v_b + (1-β₂)·db²
5. 偏置校正：
   v̂_w = v_w / (1 - β₂ᵗ)
   v̂_b = v_b / (1 - β₂ᵗ)
6. 自适应裁剪：
   max_dw = C·√v̂_w
   max_db = C·√v̂_b
   clipped_dw = clip(dw, -max_dw, max_dw)
   clipped_db = clip(db, -max_db, max_db)
7. 更新参数：
   w = w - lr·clipped_dw
   b = b - lr·clipped_db
```

## R² 计算公式与在线统计量维护

### R²（决定系数）定义

R² 衡量模型对数据变异的解释程度，取值范围通常为 [0, 1]，但模型很差时也可能为负。

```
R² = 1 - SS_res / SS_tot
```

其中：
- SS_res（残差平方和）：Σ(yᵢ - ŷᵢ)²
- SS_tot（总平方和）：Σ(yᵢ - ȳ)²
- ȳ 为 y 的均值

### 在线统计量

为了在不存储全部历史数据的情况下计算 R²，需要增量维护以下统计量：

| 统计量 | 符号 | 更新公式 |
|--------|------|----------|
| 样本数 | n | n += 1 |
| x 的和 | Σx | Σx += x |
| y 的和 | Σy | Σy += y |
| x 的平方和 | Σx² | Σx² += x² |
| y 的平方和 | Σy² | Σy² += y² |
| xy 乘积和 | Σxy | Σxy += x·y |

### SS_tot 的计算

```
SS_tot = Σy² - (Σy)² / n
```

推导：
```
SS_tot = Σ(yᵢ - ȳ)²
       = Σ(yᵢ² - 2·yᵢ·ȳ + ȳ²)
       = Σyᵢ² - 2·ȳ·Σyᵢ + n·ȳ²
       = Σy² - 2·(Σy/n)·Σy + n·(Σy/n)²
       = Σy² - (Σy)²/n
```

### SS_res 的计算

```
SS_res = Σy² + w²·Σx² + n·b² - 2·w·Σxy - 2·b·Σy + 2·w·b·Σx
```

推导：
```
SS_res = Σ(yᵢ - ŷᵢ)²
       = Σ(yᵢ - w·xᵢ - b)²
       = Σ[yᵢ² + w²·xᵢ² + b² - 2·w·xᵢ·yᵢ - 2·b·yᵢ + 2·w·b·xᵢ]
       = Σy² + w²·Σx² + n·b² - 2·w·Σxy - 2·b·Σy + 2·w·b·Σx
```

### 特殊情况处理

- 当样本数 n < 2 时，R² 返回 0.0（无法计算方差）
- 当 SS_tot = 0（所有 y 值相同）时，R² 返回 0.0（分母为零）

## 使用示例

### 基本使用

```python
from solocoder_py.linear_regression import SimpleLinearRegression

# 创建回归器，指定学习率
reg = SimpleLinearRegression(learning_rate=0.01)

# 逐样本更新模型
data_points = [(1.0, 3.0), (2.0, 5.0), (3.0, 7.0), (4.0, 9.0)]
for x, y in data_points:
    reg.update(x, y)

# 查看模型参数
print(f"w = {reg.w:.4f}")
print(f"b = {reg.b:.4f}")
print(f"样本数 = {reg.n_samples}")

# 点预测
x_test = 5.0
y_pred = reg.predict(x_test)
print(f"预测 f({x_test}) = {y_pred:.4f}")

# 计算 R²
r2 = reg.r2_score()
print(f"R² = {r2:.4f}")
```

### 完美线性数据拟合

```python
from solocoder_py.linear_regression import SimpleLinearRegression

true_w = 2.0
true_b = 3.0
reg = SimpleLinearRegression(learning_rate=0.001)

# 用 y = 2x + 3 的数据训练（单轮遍历）
for x in range(100):
    y = true_w * x + true_b
    reg.update(float(x), y)

print(f"真实 w={true_w}, 拟合 w={reg.w:.4f}")
print(f"真实 b={true_b}, 拟合 b={reg.b:.4f}")
print(f"R² = {reg.r2_score():.6f}")
```

### 异常处理

```python
from solocoder_py.linear_regression import (
    SimpleLinearRegression,
    InvalidLearningRateError,
    InvalidSampleError,
    NotFittedError,
)

# 负学习率会抛出异常
try:
    reg = SimpleLinearRegression(learning_rate=-0.01)
except InvalidLearningRateError as e:
    print(f"错误: {e}")

# NaN 样本会抛出异常
reg = SimpleLinearRegression(learning_rate=0.01)
try:
    reg.update(float("nan"), 5.0)
except InvalidSampleError as e:
    print(f"错误: {e}")

# 未训练时调用 predict 会抛出异常
try:
    reg2 = SimpleLinearRegression(learning_rate=0.01)
    reg2.predict(5.0)
except NotFittedError as e:
    print(f"错误: {e}")
```

### 零学习率（参数冻结）

```python
from solocoder_py.linear_regression import SimpleLinearRegression

# 学习率为 0 时，参数不更新，但样本统计量仍会累计
reg = SimpleLinearRegression(learning_rate=0.0)
w_before = reg.w
b_before = reg.b

for x in range(10):
    reg.update(float(x), 2.0 * x + 1.0)

assert reg.w == w_before
assert reg.b == b_before
assert reg.n_samples == 10
print(f"参数未变，但已接收 {reg.n_samples} 个样本")
```

### 学习率选择建议

由于采用自适应梯度裁剪，学习率对 x 取值范围具有较好的鲁棒性，推荐学习率：

| 场景 | 推荐学习率 |
|------|------------|
| 小学习率、单轮遍历 | 0.01 ~ 0.001 |
| 极小学习率、多轮遍历 | 0.0001 ~ 0.00001 |
| 零学习率（冻结参数，仅统计） | 0.0 |

自适应梯度裁剪在保证数值稳定性的同时，保留了 SGD 的快速收敛特性。即使使用很小的学习率和少量样本，参数也能有效向最优值逼近。
