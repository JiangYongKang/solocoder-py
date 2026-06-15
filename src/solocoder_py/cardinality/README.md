# HyperLogLog 基数估算器模块

## 模块功能

本模块基于 HyperLogLog（HLL）算法实现了一个内存高效的基数估算器，用于在极低的内存占用下估算大规模数据集中不同元素的数量（基数）。相比传统使用 `set` 去重统计的方式，HyperLogLog 可以在仅消耗 KB 级内存的情况下估算数十亿级数据的基数，且误差可控。

核心特性：

- **可配置精度**：通过标准误差参数或直接指定寄存器数量创建不同精度的估算器
- **并集运算**：两个同精度 HLL 实例可高效合并，得到并集基数估计
- **交集估算**：基于集合运算恒等式估算交集基数
- **线程安全**：核心操作均通过锁保护，支持多线程环境
- **内存数据源模拟**：内置数据源工具类，便于生成测试数据和验证算法

---

## 核心类与函数

### HyperLogLog 类

HyperLogLog 估算器的核心实现。

**初始化方式**：

```python
# 方式一：通过期望标准误差创建（推荐）
hll = HyperLogLog(standard_error=0.02)  # 约 2% 误差

# 方式二：直接指定寄存器数量（必须是 2 的幂，范围 16 ~ 65536）
hll = HyperLogLog(num_registers=4096)
```

**主要属性**：

| 属性 | 类型 | 说明 |
|------|------|------|
| `p` | `int` | 精度参数，寄存器数量 = 2^p |
| `num_registers` | `int` | 寄存器（桶）的总数 |
| `standard_error` | `float` | 实际标准误差值 |

**主要方法**：

| 方法 | 说明 |
|------|------|
| `add(element)` | 添加单个元素到集合 |
| `add_many(elements)` | 批量添加多个元素 |
| `cardinality()` | 返回估算的基数（整数） |
| `merge(other)` \| `union(other)` | 返回两个 HLL 的并集（新实例） |
| `intersection_cardinality(other)` | 返回交集基数的估算值 |
| `is_compatible(other)` | 判断两个实例精度是否兼容 |
| `clone()` | 克隆当前实例 |
| `clear()` | 清空所有寄存器 |

### 辅助函数

| 函数 | 说明 |
|------|------|
| `calculate_num_registers(standard_error)` | 根据目标标准误差计算所需寄存器数量 |
| `generate_random_strings(count, length, seed)` | 生成指定数量的随机字符串 |
| `generate_random_integers(count, low, high, seed)` | 生成指定范围的随机整数 |
| `create_data_source_with_duplicates(...)` | 创建带有重复元素的数据源 |
| `create_overlapping_data_sources(...)` | 创建两个具有指定重叠度的数据源 |

### MemoryDataSource 类

内存数据源模拟类，用于存储元素列表并支持与 HyperLogLog 的交互。

**主要方法**：

| 方法 | 说明 |
|------|------|
| `add(item)` / `add_many(items)` | 添加元素 |
| `items()` | 获取所有元素副本 |
| `exact_cardinality()` | 计算精确基数（使用 set） |
| `feed_to(hll)` | 将所有元素灌入 HLL |
| `sample(k)` | 随机采样 k 个元素 |

---

## HyperLogLog 工作原理

### 核心直觉

HyperLogLog 基于一个简单的概率观察：**如果将大量元素通过哈希函数均匀映射到位串，那么通过观察位串的前导零模式，可以反推出数据规模的量级**。

例如：
- 如果看到一个以 `0001...` 开头的哈希值（3个前导零），说明至少需要约 2^3 = 8 次尝试才大概率出现
- 如果看到以 `000001...` 开头（5个前导零），则至少需要约 2^5 = 32 次尝试

### 算法步骤

1. **哈希**：对每个元素计算 64 位哈希值 h

2. **分桶**：取哈希值的高 p 位作为桶索引 `idx`（共 2^p 个桶），即：
   ```
   idx = h >> (64 - p)
   ```

3. **计数**：对剩余的 (64-p) 位，计算从最高位开始的连续前导零个数 + 1，记为 `rho`

4. **更新寄存器**：每个寄存器存储该桶中观测到的最大 `rho` 值：
   ```
   registers[idx] = max(registers[idx], rho)
   ```

5. **估算基数**：使用调和平均综合所有桶的观测值：
   ```
   E = alpha_m * m^2 / sum(2^(-registers[i]))
   ```
   其中 `alpha_m` 是偏差修正系数，`m = 2^p`

6. **范围修正**：
   - **小范围修正**（E <= 2.5m）：当存在空桶时，改用线性计数
   - **大范围修正**（E > 2^32/30）：对哈希空间溢出进行修正

---

## 精度与寄存器数量的关系

### 标准误差公式

HyperLogLog 的渐近标准误差（Relative Standard Error, RSE）为：

```
SE ≈ 1.04 / sqrt(m)
```

其中 `m = 2^p` 是寄存器数量。

### 常见配置参考

| 目标 SE | p | m（寄存器数） | 内存占用 |
|---------|---|---------------|----------|
| ~26.0%  | 4 | 16            | 16 B     |
| ~18.4%  | 5 | 32            | 32 B     |
| ~13.0%  | 6 | 64            | 64 B     |
| ~9.2%   | 7 | 128           | 128 B    |
| ~6.5%   | 8 | 256           | 256 B    |
| ~4.6%   | 9 | 512           | 512 B    |
| ~3.25%  | 10| 1024          | 1 KB     |
| ~2.30%  | 11| 2048          | 2 KB     |
| ~1.62%  | 12| 4096          | 4 KB     |
| ~1.15%  | 13| 8192          | 8 KB     |
| ~0.81%  | 14| 16384         | 16 KB    |
| ~0.57%  | 15| 32768         | 32 KB    |
| ~0.41%  | 16| 65536         | 64 KB    |

**建议**：一般场景推荐使用 `standard_error=0.02` 或 `num_registers=4096`，在精度和内存间取得较好平衡。

---

## 集合并集与交集的估算方式

### 并集运算（Union）

HyperLogLog 天然支持无损并集运算，这是其最强大的特性之一。

**原理**：两个 HLL 实例 A 和 B 合并时，对每个寄存器取最大值：

```
merged[i] = max(A.registers[i], B.registers[i])
```

**性质**：
- **无损**：合并结果等价于将 A 和 B 的所有原始元素直接加入一个新 HLL
- **高效**：时间复杂度仅为 O(m)，与元素数量无关
- **可组合**：支持多实例级联合并（如在分布式系统中汇总各节点数据）

```python
# 三种等价写法
union = hll_a.union(hll_b)
union = hll_a.merge(hll_b)
union = hll_a | hll_b
```

### 交集估算（Intersection）

交集基数无法直接从 HLL 寄存器结构中提取，但可以利用**容斥原理**进行估算：

```
|A ∩ B| ≈ |A| + |B| - |A ∪ B|
```

**实现步骤**：
1. 分别估算 A 和 B 的基数：`|A|`、`|B|`
2. 计算 A 和 B 的并集并估算：`|A ∪ B|`
3. 应用容斥公式
4. **兜底处理**：由于误差累积，结果可能出现负数，此时强制返回 0

**注意**：交集估算的误差是三个 HLL 估算值的误差累积，因此精度通常低于单个基数估算，尤其是在两个集合重叠度较低时。

```python
inter_card = hll_a.intersection_cardinality(hll_b)
```

---

## 使用示例

### 基础使用

```python
from solocoder_py.cardinality import HyperLogLog

# 创建 2% 标准误差的估算器
hll = HyperLogLog(standard_error=0.02)

# 添加 100 万个唯一元素
for i in range(1_000_000):
    hll.add(f"user_{i}")

# 估算基数
estimated = hll.cardinality()
print(f"估算基数: {estimated}, 实际: 1000000")
# 输出大致在 980000 ~ 1020000 之间
```

### 并集操作（分布式统计）

```python
from solocoder_py.cardinality import HyperLogLog

# 模拟三个节点独立统计
hll_node1 = HyperLogLog(num_registers=4096)
hll_node2 = HyperLogLog(num_registers=4096)
hll_node3 = HyperLogLog(num_registers=4096)

for i in range(100000):
    if i % 3 == 0:
        hll_node1.add(f"id_{i}")
    elif i % 3 == 1:
        hll_node2.add(f"id_{i}")
    else:
        hll_node3.add(f"id_{i}")

# 汇总全局基数
global_hll = hll_node1 | hll_node2 | hll_node3
total = global_hll.cardinality()
print(f"全局独立访客数: {total}")
```

### 交集估算（A/B 实验重叠分析）

```python
from solocoder_py.cardinality import HyperLogLog

# A 组用户
group_a = HyperLogLog(standard_error=0.01)
for i in range(50000):
    group_a.add(f"user_{i}")

# B 组用户，其中 20000 与 A 组重叠
group_b = HyperLogLog(standard_error=0.01)
for i in range(30000, 80000):
    group_b.add(f"user_{i}")

# 估算重叠用户数
overlap = group_a.intersection_cardinality(group_b)
print(f"重叠用户估算: {overlap}, 实际: 20000")
```

### 使用内存数据源

```python
from solocoder_py.cardinality import (
    MemoryDataSource,
    HyperLogLog,
    create_overlapping_data_sources,
)

# 创建重叠数据源
ds_a, ds_b = create_overlapping_data_sources(
    "A组", "B组",
    unique_a=1000,
    unique_b=1200,
    overlap=500,
    seed=42,
)

# 灌入 HLL
hll_a = HyperLogLog(num_registers=16384)
hll_b = HyperLogLog(num_registers=16384)
ds_a.feed_to(hll_a)
ds_b.feed_to(hll_b)

# 对比精确值与估算值
print(f"A 组精确基数: {ds_a.exact_cardinality()}, 估算: {hll_a.cardinality()}")
print(f"B 组精确基数: {ds_b.exact_cardinality()}, 估算: {hll_b.cardinality()}")
print(f"交集精确值: 500, 估算: {hll_a.intersection_cardinality(hll_b)}")
```

### 不同精度的对比

```python
from solocoder_py.cardinality import HyperLogLog, generate_random_strings

items = generate_random_strings(100000, seed=42)
actual = len(set(items))

for se in [0.05, 0.02, 0.01]:
    hll = HyperLogLog(standard_error=se)
    hll.add_many(items)
    est = hll.cardinality()
    err = abs(est - actual) / actual * 100
    print(
        f"SE={se*100:.0f}% | "
        f"寄存器数={hll.num_registers:>5} | "
        f"估算={est:>6} | "
        f"误差={err:.2f}%"
    )
```

---

## 模块文件结构

```
cardinality/
├── __init__.py         # 模块导出
├── hyperloglog.py      # HyperLogLog 核心算法实现
├── datasource.py       # 内存数据源与工具函数
└── README.md           # 本文档
```
