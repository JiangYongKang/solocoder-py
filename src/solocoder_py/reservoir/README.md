# Reservoir Sampling (蓄水池抽样)

本模块提供了内存高效的数据流抽样算法实现，包括经典的等概率蓄水池抽样和加权蓄水池抽样变体。两者均在 O(k) 空间内运行，其中 k 为蓄水池容量，无需先将全部数据读入内存，即可在单次数据扫描过程中完成抽样。

## 模块功能

- `ReservoirSampler`: 经典等概率蓄水池抽样（Algorithm R）
- `WeightedReservoirSampler`: 加权蓄水池抽样（A-Res 算法），概率与权重成正比
- 两种抽样器均支持可配置库容 k、流式单条/批量喂入、查询当前样本、统计已处理数量、关闭后拒绝继续喂入等功能

## 核心类职责

### ReservoirSampler

等概率蓄水池抽样器，维护一个容量为 k 的蓄水池。数据流中的第 i 个元素到达时：

- 若 i ≤ k：直接放入蓄水池
- 若 i > k：以 k/i 的概率选择该元素，并以 1/k 的概率替换蓄水池中的某一元素

最终数据流中每个元素被选中的概率均为 k/n（n 为数据流总长度）。

### WeightedReservoirSampler

加权蓄水池抽样器，采用 A-Res 算法。每个元素带有权重 w_i，最终样本中各元素被选中的概率与 w_i 成正比。

核心方法：对每个元素生成一个随机键 key = u^(1/w_i)，其中 u ~ Uniform(0, 1)。始终保持键值最大的 k 个元素在蓄水池中（用最小堆维护）。

### WeightedItem

加权元素数据模型，封装元素值、权重和计算出的随机键，并支持基于键的比较运算符供堆排序使用。

### SamplerState

抽样器状态快照，包含容量、已处理总数、关闭标志和当前蓄水池内容，便于调试和序列化。

## 等概率蓄水池抽样的数学原理与证明思路

### 命题

对于容量为 k 的蓄水池，数据流长度为 n ≥ k，算法 R 保证每个元素被保留在最终蓄水池中的概率均为 k/n。

### 归纳证明

**基础情形（n = k）：** 所有元素都直接放入蓄水池，每个元素被保留的概率为 1 = k/k，命题成立。

**归纳假设：** 假设处理完第 m 个元素（m ≥ k）后，每个前 m 个元素在蓄水池中的概率均为 k/m。

**归纳步骤（处理第 m+1 个元素）：**

1. 第 m+1 个元素被放入蓄水池的概率 = k/(m+1)
2. 对于前 m 个元素中的任意一个 X，X 在处理完第 m 个元素后仍在蓄水池中的概率（由归纳假设）= k/m
3. X 不被第 m+1 个元素替换的条件概率：
   - 第 m+1 个元素未被选中：概率 1 - k/(m+1) = (m+1-k)/(m+1)
   - 或第 m+1 个元素被选中，但替换的不是 X：概率 [k/(m+1)] × [(k-1)/k] = (m+1-k)/(m+1) × ...
   - 合并：不被替换的概率 = 1 - [k/(m+1)] × [1/k] = m/(m+1)
4. 因此 X 在第 m+1 步后仍在蓄水池中的概率：
   = (k/m) × (m/(m+1)) = k/(m+1)

由数学归纳法，命题对所有 n ≥ k 成立。

## 加权变体的算法选择

加权蓄水池抽样有多种经典算法，本模块选择 **A-Res (Algorithm with Reservoir of size k using random sampling)**，原因如下：

### A-Res 算法原理

1. 为每个元素 x_i（权重 w_i）生成一个随机键：k_i = u_i^(1/w_i)，其中 u_i 是 (0, 1) 上的均匀分布随机数
2. 维护一个大小为 k 的最小堆，堆中存储键最大的 k 个元素
3. 新元素到达时：
   - 堆不满：直接入堆
   - 堆满且新元素键 > 堆顶键：弹出堆顶，新元素入堆
   - 否则丢弃新元素

### 为什么 A-Res 的概率与权重成正比

对于两个元素 x_a（权重 w_a）和 x_b（权重 w_b）：

P(k_a > k_b) = P(u_a^(1/w_a) > u_b^(1/w_b))
              = P(u_a > u_b^(w_a/w_b))
              = ∫₀¹ (1 - t^(w_a/w_b)) dt
              = w_b / (w_a + w_b)

因此 P(k_a > k_b) 与 w_a 成正比，推广到全部 n 个元素，保留前 k 个最大键值等价于按权重比例抽样。

### 算法对比

| 算法 | 时间复杂度 | 是否需要权重总和 | 适用场景 |
|------|-----------|----------------|---------|
| A-Res | O(n log k) | 不需要 | 权重未知/流式到达 |
| A-Chao | O(n) 平均 | 需要先验知识 | 权重范围已知 |
| 拒绝采样 | O(n) 最佳，最坏无界 | 需要最大权重 | 权重差异不大 |

A-Res 无需预先知道权重范围，实现简洁，在绝大多数场景下性能足够，因此作为本模块的默认实现。

## 使用示例

### 等概率抽样

```python
from solocoder_py.reservoir import ReservoirSampler

sampler = ReservoirSampler(capacity=10, seed=42)

# 流式喂入数据
for i in range(1000):
    sampler.feed(i)

# 或批量喂入
sampler.feed_many(range(1000, 2000))

print(f"已处理: {sampler.total_processed}")     # 2000
print(f"样本数: {sampler.sample_count}")         # 10
print(f"样本:   {sampler.samples()}")            # [random 10 items from 0..1999]

# 关闭抽样器
final = sampler.close()
```

### 加权抽样

```python
from solocoder_py.reservoir import WeightedReservoirSampler

sampler = WeightedReservoirSampler(capacity=5, seed=42)

data = [("rare", 0.1), ("common", 1.0), ("abundant", 5.0)]
for item, weight in data:
    for _ in range(100):
        sampler.feed(item, weight)

# abundant 出现概率约为 rare 的 50 倍
print(sampler.samples())
```

### 查询与状态

```python
state = sampler.get_state()
print(state.capacity)
print(state.total_processed)
print(state.closed)
print(state.reservoir)

# 容器协议
for item in sampler:
    print(item)

if 42 in sampler:
    print("命中样本")

print(len(sampler))
```
