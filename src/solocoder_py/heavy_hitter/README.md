# Heavy Hitter 模块

本模块提供了一个 Top-K 重击者（Heavy Hitter）检测功能，能够在有限内存条件下近似识别数据流中的高频项。
结合了 Count-Min Sketch 概率数据结构和有限内存字典实现低频淘汰策略，适用于大规模数据流中的
热点检测、频度监控等场景。

## 模块功能

- **有限内存计数**：使用固定大小的内存空间维护高频项的近似计数，内存用量不随输入数据规模线性增长
- **低频淘汰机制**：当内存空间已满且有新项到达时，自动淘汰当前计数最低的项为新项腾出空间
- **近似频次查询**：基于 Count-Min Sketch 返回频次的下界估计值，实际频次不低于返回值的概率可控
- **Top-K 高频查询**：按计数近似值降序返回前 K 个高频项及其近似计数，K 值可动态配置
- **并发安全**：使用可重入锁保护共享状态，支持多线程安全操作
- **数据合并**：支持多个检测器的数据合并，适用于分布式场景下的汇总统计

## 核心类

### HeavyHitterDetector

Top-K 重击者检测器的核心类，维护高频项的近似计数。

| 方法 | 说明 |
|------|------|
| `record(item, count=1)` | 记录一个项的出现，可指定出现次数 |
| `estimate_count(item)` | 返回指定项的近似频次估计（下界），实际频次 >= 返回值 |
| `lower_bound(item)` | 返回指定项频次的下界估计，同 estimate_count |
| `upper_bound(item)` | 返回指定项频次的上界估计，返回值 >= 实际频次 |
| `contains(item)` | 判断项是否当前被跟踪（在有限内存中） |
| `get_top_k(k)` | 返回前 K 个高频项的列表，按计数降序 |
| `get_all_tracked()` | 返回所有当前被跟踪的项及其计数 |
| `clear()` | 清空所有统计数据 |
| `merge(other)` | 合并另一个检测器的统计数据 |

| 属性 | 说明 |
|------|------|
| `capacity` | 内存容量，最多可跟踪的项数 |
| `size` | 当前实际跟踪的项数 |
| `evicted_count` | 累计被淘汰的项数 |
| `total_items_processed` | 累计处理的总条目数 |

构造参数：

- `capacity`：内存容量，必须为正整数，表示最多可跟踪的项数
- `epsilon`：Count-Min Sketch 的误差因子，默认 0.001，表示上界误差不超过 `epsilon * N`
- `delta`：置信度参数，默认 0.99，表示下界估计在误差范围内的概率至少为 `delta`

### CountMinSketch

Count-Min Sketch 概率数据结构实现，用于提供近似频次的上下界估计。

| 方法 | 说明 |
|------|------|
| `add(item, count=1)` | 增加项的计数 |
| `estimate(item)` | 返回项的近似计数值（CMS 原始估计，为上界性质） |
| `lower_bound(item)` | 返回下界估计：`max(0, estimate - error_bound)`，实际频次 >= 返回值的概率 >= delta |
| `upper_bound(item)` | 返回上界估计：即 estimate，保证返回值 >= 实际频次 |
| `error_bound()` | 返回当前的误差边界值（epsilon * total_count） |
| `merge(other)` | 合并另一个兼容的 Sketch |
| `clear()` | 清空所有计数 |

| 属性 | 说明 |
|------|------|
| `width` | 计数器表的宽度（列数） |
| `depth` | 计数器表的深度（行数/哈希函数数） |
| `epsilon` | 误差因子参数 |
| `delta` | 置信度参数 |
| `total_count` | 累计添加的总计数 |

### HeavyHitter

数据类，表示一个高频项及其计数。

| 字段 | 说明 |
|------|------|
| `item` | 项的标识（任意可哈希类型） |
| `count` | 近似计数值（下界估计） |

## 有限内存计数与淘汰策略

### 数据结构设计

`HeavyHitterDetector` 结合了两种数据结构：

1. **有限字典**（`_store`）：固定容量的字典，用于维护当前认为是高频的项及其精确累加计数。
   内存占用为 `O(capacity)`，不随输入数据规模增长。

2. **Count-Min Sketch**（`_cms`）：概率数据结构，用于为所有项提供上下界频率估计，
   内存占用为 `O(width * depth)`，由 `epsilon` 和 `delta` 参数决定。

### 低频淘汰算法

当调用 `record(item)` 时：

1. 首先更新 Count-Min Sketch，将项加入全局统计
2. 如果该项已在有限字典中，直接累加其计数（精确计数，作为可靠下界）
3. 如果字典未满，将该项加入字典，初始计数为 `max(本次出现次数, CMS 下界估计)`
4. 如果字典已满：
   - 找到字典中计数最低的项（min_item, min_count）
   - 计算新项的竞争值：`entry_count = max(本次出现次数, CMS 下界估计)`
   - 如果 `entry_count > min_count`，淘汰 min_item，将新项加入字典
   - 否则，忽略该项（不加入字典，但 Count-Min Sketch 已更新）

**重要特性**：
- 淘汰后，被淘汰项的精确计数信息丢失，但其信息仍保留在 Count-Min Sketch 中，可通过 `estimate_count` 查询近似下界
- 新项竞争值与初始化值来源统一：均使用 `max(本次出现次数, CMS 下界估计)`，保证策略一致
- 只有当新项的下界估计严格大于当前最低频项时才会发生替换，保证高频项不会轻易被淘汰
- `estimate_count` 对于在字典中的项返回精确累加值（真正的下界），不在字典中返回 CMS 下界估计

## 近似查询的误差边界

### Count-Min Sketch 理论保证

Count-Min Sketch 提供以下概率保证：

对于任意项 `x`，设其真实频次为 `f(x)`，估计值为 `f_hat(x)`（即 `estimate()` 返回值），则：

```
P(f_hat(x) >= f(x)) = 1              # estimate 始终是上界
P(f_hat(x) <= f(x) + epsilon * N) >= delta   # 上界误差可控
```

由此可推导出：

```
lower_bound(x) = max(0, f_hat(x) - epsilon * N)
P(f(x) >= lower_bound(x)) >= delta   # 下界估计的置信度
```

其中：
- `N` 是数据流的总长度（`total_count`）
- `epsilon` 是误差因子（默认 0.001）
- `delta` 是置信度（默认 0.99）

### 尺寸计算

计数器表的尺寸由以下公式计算：

```
width = ceil(e / epsilon)    # e 为自然对数底数 (~2.718)
depth = ceil(ln(1 / delta))  # ln 为自然对数
```

默认参数（epsilon=0.001, delta=0.99）对应的尺寸：
- width ≈ ceil(2.718 / 0.001) = 2718
- depth ≈ ceil(ln(1/0.99)) ≈ ceil(4.605) = 5
- 总计数器数 ≈ 2718 * 5 = 13590 个整数

### 误差边界示例

| 数据规模 N | epsilon | 上界误差边界 epsilon*N | 下界保守偏移 |
|-----------|---------|----------------------|------------|
| 10,000    | 0.001   | 10                   | 10         |
| 100,000   | 0.001   | 100                  | 100        |
| 1,000,000 | 0.001   | 1000                 | 1000       |
| 10,000    | 0.01    | 100                  | 100        |

## 使用示例

### 基本使用

```python
from solocoder_py.heavy_hitter import HeavyHitterDetector

# 创建容量为 10 的检测器
detector = HeavyHitterDetector(capacity=10)

# 模拟数据流：A 出现 100 次，B 出现 50 次，其他各出现 1 次
for _ in range(100):
    detector.record("A")
for _ in range(50):
    detector.record("B")
for i in range(200):
    detector.record(f"item_{i}")

# 查询近似频次（下界估计，真实频次 >= 返回值）
print(detector.estimate_count("A"))  # 100（精确累加，在 store 中）
print(detector.estimate_count("B"))  # 50（精确累加，在 store 中）
print(detector.estimate_count("item_0"))  # 近似下界，可能为 0 或 1

# 查询上下界
print(detector.lower_bound("A"))  # 100（精确下界）
print(detector.upper_bound("A"))  # >= 100（CMS 上界估计）

# 查询 Top-5 高频项
top5 = detector.get_top_k(5)
for hh in top5:
    print(f"{hh.item}: {hh.count}")
# 输出类似:
# A: 100
# B: 50
# item_42: 1
# ...
```

### 边界场景

```python
# K 值等于内存容量
detector = HeavyHitterDetector(capacity=5)
# ... 记录数据 ...
top5 = detector.get_top_k(5)  # 合法，返回所有跟踪的项

# K 值超过内存容量（抛出异常）
try:
    top10 = detector.get_top_k(10)
except InvalidKError as e:
    print(e)  # k (10) cannot exceed capacity (5)

# 所有项频次相同
detector2 = HeavyHitterDetector(capacity=3)
for item in ["A", "B", "C", "D", "E"]:
    for _ in range(10):
        detector2.record(item)
# 前 3 个到达且频次相同的项会被保留，后续因频次不大于最小值不会替换
```

### 调整精度参数

```python
# 更高精度（但更多内存）
detector = HeavyHitterDetector(
    capacity=100,
    epsilon=0.0001,  # 误差更小
    delta=0.999,     # 置信度更高
)

# 更低精度（节省内存）
detector = HeavyHitterDetector(
    capacity=100,
    epsilon=0.01,    # 误差更大
    delta=0.9,       # 置信度稍低
)
```

### 合并多个检测器

```python
detector1 = HeavyHitterDetector(capacity=5)
detector2 = HeavyHitterDetector(capacity=5)

# 分别在两个数据流上统计
for _ in range(100):
    detector1.record("A")
for _ in range(50):
    detector2.record("B")

# 合并结果
detector1.merge(detector2)
print(detector1.estimate_count("A"))  # 下界估计 >= 100
print(detector1.estimate_count("B"))  # 下界估计 >= 50
```
