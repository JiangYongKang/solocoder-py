# Linear Regression 模块 - 简单线性回归在线学习器

本模块实现了一个基于内存数据结构的**简单线性回归在线学习器**，支持单样本梯度下降更新、点预测和 R² 拟合优度计算。所有统计量均在在线更新过程中增量维护，无需存储全部历史数据。

## 模块功能

- **在线梯度下降更新**：每接收一个 (x, y) 样本对，使用随机梯度下降法更新模型参数 w（斜率）和 b（截距）
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
| `update(x, y)` | 接收单个样本，使用梯度下降更新模型参数 |
| `predict(x)` | 基于当前模型参数预测 x 对应的 y 值 |
| `r2_score()` | 计算模型的 R² 决定系数 |
| `w` | 当前模型斜率参数（只读属性） |
| `b` | 当前模型截距参数（只读属性） |
| `n_samples` | 已接收的样本总数（只读属性） |
| `learning_rate` | 学习率（只读属性） |

## 梯度下降更新公式与推导

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

### 参数更新公式

使用梯度下降法沿负梯度方向更新参数：

```
w = w - lr·∂L/∂w = w - lr·(ŷ - y)·x
b = b - lr·∂L/∂b = b - lr·(ŷ - y)
```

其中 lr 为学习率，控制每次更新的步长。

### 更新算法伪代码

```
输入：样本 (x, y)，学习率 lr
1. 计算预测值：ŷ = w·x + b
2. 计算误差：error = ŷ - y
3. 计算梯度：
   dw = error·x
   db = error
4. 更新参数：
   w = w - lr·dw
   b = b - lr·db
```

**注意**：学习率的选择需要根据数据范围调整。x 的取值范围越大，需要的学习率越小，否则可能导致梯度发散。

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

# 用 y = 2x + 3 的数据训练
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

学习率的选择取决于 x 的取值范围：

| x 的范围 | 推荐学习率 |
|----------|------------|
| 0 ~ 10 | 0.01 ~ 0.05 |
| 0 ~ 100 | 0.0001 ~ 0.001 |
| 0 ~ 1000 | 1e-6 ~ 1e-5 |

如果学习率过大，可能导致参数发散（数值爆炸）。如果学习率过小，则收敛速度慢，需要更多样本才能达到较好的拟合效果。
