# Bloom Filter 模块

本模块实现了两类布隆过滤器 (Bloom Filter)：**标准布隆过滤器 (BloomFilter)** 和 **计数布隆过滤器 (CountingBloomFilter)**。
两者均为基于内存数据结构的概率型数据结构，使用位数组/计数器数组与多哈希函数实现高效的集合成员查询，
具有**无假阴性**（不存在一定返回不存在）、**可能有假阳性**（存在返回可能存在）的特性。

---

## 模块功能

| 功能 | BloomFilter | CountingBloomFilter |
|------|:-----------:|:-------------------:|
| 添加元素 `add()` | ✅ | ✅ |
| 查询元素 `__contains__` / `might_contain()` | ✅ | ✅ |
| 估算误判率 `false_positive_rate()` | ✅ | ✅ |
| 删除元素 `remove()` | ❌ | ✅ |
| 并集操作 `union()` / `\|` | ✅ | ✅ |
| 交集操作 `intersection()` / `&` | ✅ | ✅ |
| 规格兼容性检查 `is_compatible()` | ✅ | ✅ |
| 根据预期参数自动优化 `m, k` | ✅ | ✅ |

---

## 核心类职责

### BloomFilter

标准布隆过滤器，使用 `bytearray` 实现紧凑的位数组存储。

**构造方式**（二选一）：
1. 直接指定位数组长度 `m` 和哈希函数个数 `k`：
   ```python
   BloomFilter(m=10000, k=7)
   ```
2. 根据预期插入元素数量 `expected_n` 和目标误判率 `target_p` 自动计算最优参数：
   ```python
   BloomFilter(expected_n=1000, target_p=0.01)
   ```

| 属性/方法 | 描述 |
|-----------|------|
| `m` | 位数组长度（只读） |
| `k` | 哈希函数个数（只读） |
| `count` | 已插入元素的近似计数（只读，线程安全） |
| `add(element)` | 添加元素到过滤器。若该元素的 `k` 个位全部已置位，则 `count` 不递增（避免重复计数） |
| `__contains__(element)` / `might_contain(element)` | 查询元素是否"可能存在"。返回 `False` 表示**一定不存在**；返回 `True` 表示**可能存在**（存在假阳性可能） |
| `false_positive_rate()` | 根据当前 `count`、`m`、`k` 估算理论假阳性概率 |
| `is_compatible(other)` | 判断另一个过滤器是否与本过滤器同规格（`m` 和 `k` 均相同且类型匹配） |
| `union(other)` / `__or__` | 求两个同规格过滤器的并集。结果过滤器中某位置位当且仅当至少一个源过滤器中该位置位。`count` 取两过滤器 `count` 之和（上界为 `m`），详见下方"count 近似估算语义" |
| `intersection(other)` / `__and__` | 求两个同规格过滤器的交集。结果过滤器中某位置位当且仅当两个源过滤器中该位均置位。`count` 取两过滤器 `count` 的较小值，详见下方"count 近似估算语义" |

### CountingBloomFilter

计数布隆过滤器变体，每个位置使用 8 位计数器（最大值 255）替代单一比特位，从而支持元素删除。

**构造方式**：与 `BloomFilter` 相同，支持 `(m, k)` 或 `(expected_n, target_p)` 两种方式。

| 属性/方法 | 描述 |
|-----------|------|
| `m` | 计数器数组长度（只读） |
| `k` | 哈希函数个数（只读） |
| `count` | 已插入元素的累计次数（每次 `add` 都会递增，即使重复添加也递增） |
| `add(element)` | 添加元素，对应 `k` 个位置的计数器各加 1（饱和至 255），`count` 递增 1 |
| `remove(element)` | 删除元素。先验证所有 `k` 个位置的计数器均大于 0，然后各减 1，`count` 递减 1；若任一计数器为 0 则抛出 `ValueError` |
| `__contains__(element)` / `might_contain(element)` | 当且仅当所有 `k` 个位置的计数器均大于 0 时返回 `True` |
| `false_positive_rate()` | 理论假阳性率估算（公式与 `BloomFilter` 相同） |
| `union(other)` | 并集操作：对应位置计数器**相加**（饱和至 255），`count` 取两过滤器 `count` 之和（上界为 `m`） |
| `intersection(other)` | 交集操作：对应位置计数器取**最小值**，`count` 取两过滤器 `count` 的较小值 |

### 辅助函数

| 函数 | 描述 |
|------|------|
| `calculate_optimal_m(expected_n, target_p)` | 根据预期元素数 `n` 和目标误判率 `p`，计算最优位数组长度 `m` |
| `calculate_optimal_k(expected_n, m)` | 根据预期元素数 `n` 和位数组长度 `m`，计算最优哈希函数个数 `k` |

---

## 假阳性概率推导

### 基本假设

布隆过滤器的假阳性概率分析基于以下假设：

1. **哈希函数相互独立且均匀分布**：每个哈希函数将元素独立均匀地映射到位数组的任一位置。
2. **所有元素的哈希选择相互独立**。
3. 使用**双重哈希** (double hashing) 技巧生成 `k` 个哈希值：
   ```
   h_i(x) = (h1(x) + i * h2(x)) mod m
   ```
   其中 `h1` 和 `h2` 为两个独立的 64 位 FNV-1a 哈希函数（使用不同的 offset basis）。

### 概率推导

设位数组长度为 `m`，使用 `k` 个哈希函数，已插入 `n` 个不同元素。

**Step 1**：插入一个元素时，某一特定位**未被置位**的概率为：
```
P(某一位未被 1 次哈希命中) = 1 - 1/m
```

**Step 2**：经过 `k` 次哈希后，该位仍未被置位的概率：
```
P(某一位未被 k 次哈希命中) = (1 - 1/m)^k
```

**Step 3**：经过 `n` 个元素（每个产生 `k` 次哈希）后，该位仍为 0 的概率：
```
P(某一位为 0 | n 个元素) = (1 - 1/m)^(kn)
```

当 `m` 较大时，利用极限 `lim_{m→∞} (1 - 1/m)^m = e^{-1}`，上式可近似为：
```
P(某一位为 0) ≈ e^{-kn/m}
```

**Step 4**：该位为 1 的概率：
```
P(某一位为 1) ≈ 1 - e^{-kn/m}
```

**Step 5**：查询一个**未插入**的元素时，其 `k` 个哈希位全部被置位的概率（即假阳性率）为：
```
FPR = P(k 个位全部为 1) ≈ (1 - e^{-kn/m})^k
```

这就是 `false_positive_rate()` 方法使用的公式。

### 最优参数选择

给定预期插入元素数 `n` 和目标误判率 `p`，可推导出最优的 `m` 和 `k`：

**最优位数组长度**：令 `FPR = p`，解关于 `m` 的方程：
```
p = (1 - e^{-kn/m})^k
```
当 `k` 取最优值时，可得：
```
m = - (n * ln p) / (ln 2)^2
```

**最优哈希函数个数**：将 `m` 代入 `p` 的表达式，对 `k` 求导并令导数为 0，得：
```
k = (m / n) * ln 2
```

---

## 计数变体 vs 基本变体

| 维度 | BloomFilter | CountingBloomFilter |
|------|:-----------:|:-------------------:|
| 存储单元 | 1 bit / slot | 8 bits (1 byte) / slot |
| 空间开销 | `ceil(m / 8)` 字节 | `m` 字节（约为基本变体的 8 倍） |
| 删除操作 | ❌ 不支持 | ✅ 支持（计数器递减） |
| 计数器溢出 | N/A | 单个计数器最大 255，溢出后不再递增（不会回绕） |
| 重复添加的计数 | 仅首次添加增加 `count` | 每次 `add` 都增加 `count`（与删除对称） |
| 删除后的假阳性 | N/A | **不会劣化**：计数器归零后该位逻辑上等效于清零，查询时会正确返回"不存在" |
| 适用场景 | 静态/只增集合，如缓存击穿防护、URL 去重 | 动态集合（需增删），如 LRU 辅助、黑名单动态管理 |

### 删除操作的正确性保证

`CountingBloomFilter.remove()` 的实现采用**两阶段验证**：
1. **预检查阶段**：遍历 `k` 个索引，若有任一位置的计数器为 0，立即抛出 `ValueError`，不做任何修改。
2. **执行阶段**：确认所有位置计数器均 > 0 后，对每个位置执行递减操作。

这保证了删除操作的**原子性**——要么全部成功，要么全部不修改。

由于计数器精确记录了每个位置被置位的"引用次数"，删除时仅递减计数，不会出现"误清零"其他元素共享位置的情况。因此，只要 `add` 和 `remove` 严格配对，删除操作不会导致假阳性率劣化。

---

## count 属性的近似估算语义

布隆过滤器的 `count` 属性是元素数量的**近似估算值**，而非精确计数。由于布隆过滤器本质上不存储元素本身，无法精确追踪重复插入。合并操作（并集/交集）后的 `count` 估算具有以下语义和误差范围：

### 单过滤器的 count 语义

| 类型 | count 语义 | 误差特性 |
|------|-----------|---------|
| `BloomFilter` | 记录"首次新增"的元素次数：仅当 `add` 时至少有一个比特位从 0 变为 1，`count` 才递增。重复 `add` 同一元素不会使 `count` 递增。 | 对于无重复插入的集合，`count` 等于实际插入元素数。若有重复插入，`count` 会低估。 |
| `CountingBloomFilter` | 记录 `add` 调用的累计次数：每次 `add` 都会使 `count` 递增 1，无论该元素是否已存在。 | 若同一元素重复插入 `n` 次，`count` 会比实际不同元素数多 `n-1`。删除操作严格与 `add` 配对，保证 `count` 反映累计净添加次数。 |

### 并集操作后的 count 估算

并集 `result = a | b` 的 `count` 取值为：

```
result.count = min(a.count + b.count, m)
```

**误差分析**：
- **下界**：`max(a.count, b.count)` —— 当 b 的元素全部是 a 的子集时，真实并集元素数等于 `max(a.count, b.count)`，此时估算值 `a.count + b.count` 会**高估**。
- **上界**：`min(a.count + b.count, m)` —— 当 a 和 b 完全不相交时，真实并集元素数接近 `a.count + b.count`，此时估算值较为准确。
- **最坏情况**：若两集合高度重叠，估算值可能显著高估。例如两过滤器各含 100 个完全相同的元素，估算值为 200，但真实并集仅 100 个元素。

**与旧实现的对比**：
- 旧实现：`result.count = max(a.count, b.count)` —— 对不相交集合会严重低估（如两集合各 50 个不相交元素，实际应为 100，但仅估算为 50）
- 新实现：`result.count = min(a.count + b.count, m)` —— 对上界做了更合理的估计，对不相交集合更准确

### 交集操作后的 count 估算

交集 `result = a & b` 的 `count` 取值为：

```
result.count = min(a.count, b.count)
```

**误差分析**：
- **上界**：`min(a.count, b.count)` —— 这是交集中可能存在的最大元素数（不可能超过较小集合的大小）。
- **误差方向**：总是**高估**或等于真实交集大小。当两集合完全相同时，估算准确；当两集合完全不相交时，估算值为 `min(a.count, b.count)`，但真实交集元素数为 0，此时误差最大。

### 使用建议

1. **不要依赖 count 做精确判断**：`count` 仅用于估算假阳性率和大致规模，不可用作精确计数。
2. **FPR 估算的保守性**：由于并集 `count` 使用 `a.count + b.count` 作为上界，`false_positive_rate()` 返回的是**保守估计值**（即最坏情况下的误判率），实际误判率不会高于该值。
3. **CountingBloomFilter 的配对要求**：必须保证 `add` 和 `remove` 严格配对调用，否则 `count` 和计数器会失去同步。

---

## 使用示例

### 示例 1：基础用法（BloomFilter）

```python
from solocoder_py.bloom_filter import BloomFilter

# 使用预期参数自动优化：预期 1000 个元素，目标误判率 1%
bf = BloomFilter(expected_n=1000, target_p=0.01)

# 添加元素
bf.add("apple")
bf.add("banana")
bf.add("cherry")

# 查询：无假阴性
assert "apple" in bf          # 一定存在，返回 True
assert bf.might_contain("banana")  # 同上
assert "durian" not in bf     # 一定不存在，返回 False（无假阴性）

# 查看当前状态
print(f"m = {bf.m}, k = {bf.k}")  # 如 m=9586, k=7
print(f"已插入元素数 ≈ {bf.count}")
print(f"当前误判率 ≈ {bf.false_positive_rate():.6f}")
```

### 示例 2：计数过滤器支持删除

```python
from solocoder_py.bloom_filter import CountingBloomFilter

# 指定 m=5000, k=5
cbf = CountingBloomFilter(m=5000, k=5)

# 添加元素
cbf.add("user_1")
cbf.add("user_2")
cbf.add("user_3")
print(cbf.count)  # 3

# 删除元素
cbf.remove("user_2")
print(cbf.count)  # 2

# 验证：被删除的元素查询返回不存在
assert "user_1" in cbf
assert "user_2" not in cbf  # 删除后正确返回不存在
assert "user_3" in cbf

# 尝试删除从未添加的元素 → 抛异常
try:
    cbf.remove("ghost_user")
except ValueError as e:
    print(f"正确捕获异常: {e}")

# 重复添加 / 多次删除
cbf.add("temp")
cbf.add("temp")
print(cbf.count)  # 4 (两次 add 各递增 1)
cbf.remove("temp")
print(cbf.count)  # 3
assert "temp" in cbf   # 删一次还在
cbf.remove("temp")
print(cbf.count)  # 2
assert "temp" not in cbf  # 删完两次才消失
```

### 示例 3：并集与交集

```python
from solocoder_py.bloom_filter import BloomFilter

# 必须使用相同规格才能合并
bf_a = BloomFilter(m=10000, k=7)
bf_b = BloomFilter(m=10000, k=7)

bf_a.add("x")
bf_a.add("y")
bf_b.add("y")
bf_b.add("z")

# 并集：包含两个过滤器的所有元素
bf_union = bf_a | bf_b
assert "x" in bf_union
assert "y" in bf_union
assert "z" in bf_union

# 交集：仅包含同时存在于两者的元素
bf_inter = bf_a & bf_b
assert "y" in bf_inter
# 注意："x" 和 "z" 只在一个过滤器中，不在交集中（但受假阳性影响，不做断言）

# 不同规格的过滤器合并 → 抛异常
bf_c = BloomFilter(m=5000, k=3)
try:
    bf_a.union(bf_c)
except ValueError as e:
    print(f"合并异常: {e}")
```

### 示例 4：手动计算最优参数

```python
from solocoder_py.bloom_filter import calculate_optimal_m, calculate_optimal_k

n = 5000       # 预期插入 5000 个元素
p = 0.001      # 目标误判率 0.1%

m = calculate_optimal_m(n, p)
k = calculate_optimal_k(n, m)

print(f"预期 n={n}, 目标 FPR={p}")
print(f"最优 m = {m} 位 ≈ {m/8/1024:.2f} KB")
print(f"最优 k = {k} 个哈希函数")
# 输出示例：
# 最优 m = 71872 位 ≈ 8.78 KB
# 最优 k = 10 个哈希函数
```

---

## 线程安全说明

所有公共方法均使用 `threading.RLock` 进行保护：

- 单对象操作（`add`、`remove`、`__contains__`、`count`、`false_positive_rate`）：获取自身锁。
- 双对象操作（`union`、`intersection`、`is_compatible`）：同时获取 `self._lock` 和 `other._lock`，保证状态快照的一致性。

在 CPython 的 GIL 机制下，不会出现经典的锁顺序死锁问题，但仍建议上层应用保持调用顺序一致以避免潜在死锁风险。
