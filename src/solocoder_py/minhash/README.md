# MinHash 模块

本模块实现了 **MinHash** 集合相似度估算算法，使用内存数据结构存储集合的 MinHash 签名。
MinHash 是一种**局部敏感哈希 (Locality Sensitive Hashing, LSH)** 技术，能够在亚线性时间内估算两个集合的 Jaccard 相似度，
特别适合大规模集合的去重、相似度搜索和聚类等场景。

---

## 模块功能

| 功能 | 描述 |
|------|------|
| **签名生成** | 从任意可哈希元素的集合生成长度为 `h` 的 MinHash 签名向量 |
| **增量更新** | 支持向签名中逐个添加元素，动态更新最小值 |
| **签名合并** | 合并两个签名，相当于求两个集合的并集的签名 |
| **Jaccard 估算** | 通过比较签名对应位置的最小值，估算原始集合的 Jaccard 相似度 |
| **兼容性检查** | 判断两个签名是否使用相同的哈希函数配置（相同的 `h` 和 `seed`） |

---

## 核心类职责

### MinHash

`MinHash` 类是模块的核心，封装了 MinHash 签名的生成、更新、合并和相似度估算功能。

**构造参数**：

| 参数 | 类型 | 默认值 | 描述 |
|------|------|:------:|------|
| `num_hash_functions` | `int` | `128` | 哈希函数的数量 `h`，越大精度越高，空间开销也越大 |
| `seed` | `int` | `42` | 随机种子，用于生成独立的哈希函数。相同 `seed` 和 `h` 的签名可以比较 |
| `elements` | `Optional[Iterable[Any]]` | `None` | 可选的初始元素集合，构造时一次性添加 |

**核心属性**：

| 属性 | 类型 | 描述 |
|------|------|------|
| `h` | `int` | 哈希函数的数量 `h`（只读） |
| `num_hash_functions` | `int` | `h` 的别名（只读） |
| `signature` | `list[int]` | 当前的 MinHash 签名向量（返回副本，防止外部修改） |

**核心方法**：

| 方法 | 描述 |
|------|------|
| `add(element)` | 向签名中添加一个元素，增量更新每个哈希函数的最小值 |
| `add_many(elements)` | 批量添加多个元素 |
| `update(elements)` | `add_many` 的别名，与 Python `set` 接口保持一致 |
| `from_set(elements, h, seed)` | 类方法：从集合一次性生成签名 |
| `is_compatible(other)` | 判断另一个 `MinHash` 是否与本签名兼容（相同 `h` 和 `seed`） |
| `jaccard(other)` | 估算与另一个签名的 Jaccard 相似度 |
| `merge(other)` / `__or__` | 合并两个签名，返回新的签名（相当于求并集） |
| `__ior__` | 原地合并签名 |

### 辅助函数

| 函数 | 描述 |
|------|------|
| `jaccard_similarity(set_a, set_b)` | 计算两个集合的真实 Jaccard 相似度（用于对比验证） |

---

## MinHash 算法数学原理

### 核心思想

MinHash 的核心洞察是：**对于两个集合 A 和 B，一个随机哈希函数作用于 A ∪ B 的最小哈希值
同时出现在 A 和 B 中的概率，恰好等于 A 和 B 的 Jaccard 相似度**。

### Jaccard 相似度定义

两个集合 A 和 B 的 Jaccard 相似度定义为：

```
J(A, B) = |A ∩ B| / |A ∪ B|
```

即交集大小除以并集大小，取值范围为 [0, 1]。

### 数学证明

设 `h` 是一个将全集 U 映射到整数的哈希函数，且 `h` 是**最小独立排列** (min-wise independent permutation)。
定义 `min_h(S)` 为集合 S 中所有元素的哈希值的最小值：

```
min_h(S) = min{ h(x) | x ∈ S }
```

**定理**：`P(min_h(A) = min_h(B)) = J(A, B)`

**证明**：
考虑并集 A ∪ B 中的元素，它们的哈希值构成一个随机排列。
最小值来自于 A ∩ B 的概率，等于 A ∩ B 的元素数除以 A ∪ B 的元素数，即 J(A, B)。
而最小值同时出现在 A 和 B 中，当且仅当最小值来自于 A ∩ B。因此：

```
P(min_h(A) = min_h(B)) = P(min_h(A ∪ B) ∈ A ∩ B) = |A ∩ B| / |A ∪ B| = J(A, B)
```

### 估计算法

使用 `h` 个独立的哈希函数 `h_1, h_2, ..., h_h`，对每个哈希函数计算最小值，得到签名向量：

```
sig(S) = [ min_{x∈S} h_1(x), min_{x∈S} h_2(x), ..., min_{x∈S} h_h(x) ]
```

对于两个签名向量 `sig(A)` 和 `sig(B)`，定义指示变量：

```
X_i = 1  如果 sig(A)[i] = sig(B)[i]，否则 0
```

则 Jaccard 相似度的无偏估计为：

```
Ĵ(A, B) = (X_1 + X_2 + ... + X_h) / h
```

---

## Jaccard 相似度估算公式与误差界

### 估算公式

```
Ĵ(A, B) = (1/h) * Σ_{i=1}^{h} I[sig(A)[i] = sig(B)[i]]
```

其中 `I[·]` 是指示函数，条件成立时为 1，否则为 0。

### 无偏性

由于每个 `X_i` 都是 J(A, B) 的无偏估计，因此整体估计也是无偏的：

```
E[Ĵ(A, B)] = (1/h) * Σ_{i=1}^{h} E[X_i] = (1/h) * Σ_{i=1}^{h} J(A, B) = J(A, B)
```

### 误差界（Chernoff 界）

由于 `X_i` 是独立的伯努利随机变量，根据 Chernoff 界，对于任意 ε > 0：

```
P(|Ĵ - J| ≥ ε * J) ≤ 2 * exp(-h * J * ε² / (2 + ε))
```

对于加法误差，我们有 Hoeffding 界：

```
P(|Ĵ - J| ≥ ε) ≤ 2 * exp(-2 * h * ε²)
```

**示例**：当 `h = 128`，要求误差 `ε = 0.1` 时：
```
P(|Ĵ - J| ≥ 0.1) ≤ 2 * exp(-2 * 128 * 0.01) = 2 * exp(-2.56) ≈ 0.155
```

当 `h = 256` 时：
```
P(|Ĵ - J| ≥ 0.1) ≤ 2 * exp(-2 * 256 * 0.01) = 2 * exp(-5.12) ≈ 0.012
```

可见，增大 `h` 可以显著降低误差概率。

---

## 签名生成与合并的语义

### 签名生成语义

签名向量的每个位置 `sig[i]` 存储的是第 `i` 个哈希函数对集合中所有元素计算出的最小值。
初始时所有位置设为最大值 `0xFFFFFFFFFFFFFFFF`（即 2^64 - 1）。

添加元素时，对每个哈希函数计算该元素的哈希值，如果小于当前签名位置的值则更新。

### 合并语义

两个签名的合并（merge）操作，对应于两个原始集合的**并集**的签名：

```
sig(A ∪ B)[i] = min(sig(A)[i], sig(B)[i]) = min{ h_i(x) | x ∈ A ∪ B }
```

这是因为：
```
min{ h_i(x) | x ∈ A ∪ B } = min( min{ h_i(x) | x ∈ A }, min{ h_i(x) | x ∈ B } )
```

合并操作具有以下性质：
- **交换律**：`A.merge(B) == B.merge(A)`
- **结合律**：`A.merge(B).merge(C) == A.merge(B.merge(C))`
- **幂等性**：`A.merge(A) == A`

---

## 使用示例

### 示例 1：基础用法

```python
from solocoder_py.minhash import MinHash

# 创建 MinHash 实例，使用 128 个哈希函数
mh = MinHash(num_hash_functions=128, seed=42)

# 添加元素
mh.add("apple")
mh.add("banana")
mh.add("cherry")

# 查看签名长度
print(f"签名长度 h = {mh.h}")  # 128
```

### 示例 2：Jaccard 相似度估算

```python
from solocoder_py.minhash import MinHash, jaccard_similarity

# 创建两个集合
set_a = {f"doc_{i}" for i in range(200)}
set_b = {f"doc_{i}" for i in range(100, 300)}

# 计算真实 Jaccard 相似度
true_j = jaccard_similarity(set_a, set_b)
print(f"真实 Jaccard 相似度: {true_j:.4f}")

# 使用 MinHash 估算
mh_a = MinHash.from_set(set_a, num_hash_functions=256, seed=42)
mh_b = MinHash.from_set(set_b, num_hash_functions=256, seed=42)

estimated_j = mh_a.jaccard(mh_b)
print(f"估算 Jaccard 相似度: {estimated_j:.4f}")
print(f"误差: {abs(estimated_j - true_j):.4f}")
```

### 示例 3：增量添加

```python
from solocoder_py.minhash import MinHash

elements = [f"item_{i}" for i in range(100)]

# 方式 1：一次性生成
mh_oneshot = MinHash.from_set(elements, num_hash_functions=128, seed=42)

# 方式 2：增量添加
mh_incremental = MinHash(num_hash_functions=128, seed=42)
for elem in elements:
    mh_incremental.add(elem)

# 两种方式结果相同
assert mh_oneshot.signature == mh_incremental.signature
assert mh_oneshot.jaccard(mh_incremental) == 1.0
```

### 示例 4：签名合并

```python
from solocoder_py.minhash import MinHash

# 创建两个 MinHash 实例（必须使用相同的 h 和 seed）
mh1 = MinHash(num_hash_functions=128, seed=42)
mh2 = MinHash(num_hash_functions=128, seed=42)

mh1.add("a")
mh1.add("b")
mh2.add("b")
mh2.add("c")

# 合并签名（相当于求并集）
merged = mh1.merge(mh2)
# 或者使用运算符
merged = mh1 | mh2

# 原地合并
mh1 |= mh2

# 合并后的签名与直接从并集生成的签名相同
union_set = {"a", "b", "c"}
mh_union = MinHash.from_set(union_set, num_hash_functions=128, seed=42)
assert merged.signature == mh_union.signature
```

### 示例 5：处理不同类型的元素

```python
from solocoder_py.minhash import MinHash

mh = MinHash(num_hash_functions=64, seed=42)

# 支持各种可哈希类型
mh.add("string")
mh.add(42)
mh.add(3.14159)
mh.add(True)
mh.add(None)
mh.add((1, 2, 3))
mh.add(frozenset([4, 5, 6]))
mh.add(b"bytes_data")
```

### 示例 6：错误处理

```python
from solocoder_py.minhash import (
    MinHash,
    InvalidConfigError,
    IncompatibleSignatureError,
    NonHashableElementError,
)

# h 必须为正整数
try:
    MinHash(num_hash_functions=0)
except InvalidConfigError as e:
    print(f"配置错误: {e}")

# 不兼容的签名不能比较
mh1 = MinHash(num_hash_functions=64, seed=42)
mh2 = MinHash(num_hash_functions=128, seed=42)
try:
    mh1.jaccard(mh2)
except IncompatibleSignatureError as e:
    print(f"签名不兼容: {e}")

# 非可哈希元素会报错
mh = MinHash(num_hash_functions=64, seed=42)
try:
    mh.add([1, 2, 3])  # list 不可哈希
except NonHashableElementError as e:
    print(f"元素不可哈希: {e}")
```

---

## 异常类型

| 异常类型 | 基类 | 触发场景 |
|---------|------|----------|
| `MinHashError` | `Exception` | 所有 MinHash 异常的基类 |
| `InvalidConfigError` | `MinHashError` | 无效的配置参数（如 `h ≤ 0`） |
| `IncompatibleSignatureError` | `MinHashError` | 比较或合并不兼容的签名（不同 `h` 或 `seed`） |
| `NonHashableElementError` | `MinHashError` | 添加不可哈希的元素（如 `list`、`dict`） |

---

## 性能建议

1. **选择合适的 `h`**：
   - `h = 64`：粗略估算，误差约 ±0.1
   - `h = 128`：平衡精度和性能，误差约 ±0.05
   - `h = 256`：较高精度，误差约 ±0.03
   - `h = 512`：高精度，误差约 ±0.02

2. **保持 `seed` 一致**：只有使用相同 `seed` 和 `h` 的签名才能进行比较和合并。

3. **优先使用 `from_set`**：一次性从集合生成签名比逐个 `add` 更高效，且结果相同。

4. **空间复杂度**：每个签名占用 `h * 8` 字节（每个哈希值为 64 位整数）。
   - `h = 128`：每个签名 1KB
   - `h = 1024`：每个签名 8KB

5. **时间复杂度**：
   - 添加元素：O(h)
   - 相似度估算：O(h)
   - 合并签名：O(h)
