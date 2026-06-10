# Fuzzy Match 模块

本模块提供基于编辑距离的模糊字符串匹配功能，使用内存数据结构模拟数据源，
支持阈值过滤、候选剪枝和按相似度排序。

## 模块功能

- **编辑距离计算**：支持计算两字符串之间的 Levenshtein 距离（允许插入、删除、替换）
- **阈值过滤**：给定编辑距离阈值，快速过滤掉距离超过阈值的候选
- **候选剪枝**：使用长度过滤与带界 DP 提前终止策略减少不必要的计算
- **相似度排序**：将过滤后的候选按编辑距离升序排列，距离相同则按字典序排列

## 核心类与函数

### `levenshtein_distance(s1: str, s2: str) -> int`

计算两字符串之间的 Levenshtein 编辑距离。使用经典的双行 DP 算法，
空间复杂度 O(min(len(s1), len(s2)))。

### `MatchResult`

匹配结果数据类，包含两个字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `candidate` | `str` | 候选字符串 |
| `distance` | `int` | 与查询串的编辑距离 |

### `FuzzyMatcher`

模糊匹配器主类，提供以下核心方法：

| 方法 | 说明 |
|------|------|
| `match(query, threshold=0, max_results=None)` | 对查询串执行模糊匹配，返回排序后的结果列表 |
| `add_candidate(candidate)` | 添加候选字符串 |
| `remove_candidate(candidate)` | 移除候选字符串，返回是否成功移除 |
| `candidates` | 当前候选列表（属性，返回副本） |
| `candidate_count` | 当前候选数量（属性） |

构造参数：

- `candidates`：初始候选字符串列表，默认为 `None`（空集）

`match` 方法参数：

- `query`：查询字符串
- `threshold`：编辑距离阈值，仅返回距离 ≤ 阈值的候选，默认 0（仅精确匹配）
- `max_results`：返回结果数量上限，默认 `None`（不限制）

## 编辑距离算法

### 标准算法（`levenshtein_distance`）

使用 Levenshtein 距离的经典动态规划算法，支持三种单字符编辑操作：
- **插入**：在字符串中插入一个字符
- **删除**：从字符串中删除一个字符
- **替换**：将一个字符替换为另一个字符

递推公式：

```
dp[i][j] = min(
    dp[i-1][j] + 1,       # 删除
    dp[i][j-1] + 1,       # 插入
    dp[i-1][j-1] + cost   # 替换（相同字符 cost=0，否则 cost=1）
)
```

实现采用双行优化，仅保留前一行和当前行的 DP 值，将空间复杂度从 O(m×n) 降至
O(min(m, n))。始终将较短字符串作为列维度，进一步节省空间。

### 带界算法（`levenshtein_distance_bounded`，内部使用）

在标准 DP 基础上增加两项优化，当距离超过给定阈值时提前返回：

1. **长度差快速判断**：若 |len(s1) - len(s2)| > threshold，直接返回 threshold + 1，
   因为至少需要 |len(s1) - len(s2)| 次插入/删除操作。
2. **行最小值提前终止**：计算每一行时追踪当前行最小值，若最小值超过 threshold，
   说明最终距离必然超过阈值，立即终止计算。
3. **窗口化 DP 计算**：对每行仅在 [i - threshold, i + threshold] 窗口内计算 DP 值，
   窗口外的值设为 threshold + 1，减少计算量。

## 剪枝优化策略

匹配流程采用两级剪枝，在候选集较大时显著减少完整的编辑距离计算次数：

### 第一级：长度过滤

基于编辑距离的下界性质：两字符串的编辑距离 ≥ |len(s1) - len(s2)|。
因此，若候选字符串长度与查询串长度之差已超过阈值，可直接跳过该候选。

实现上，`FuzzyMatcher` 在内部维护一个按字符串长度索引的哈希表
`_length_index: dict[int, list[str]]`，`match` 时仅遍历长度在
`[query_len - threshold, query_len + threshold]` 范围内的候选桶，
将不满足长度条件的候选在 DP 计算前全部排除。

### 第二级：带界 DP 提前终止

对通过长度过滤的候选，使用 `levenshtein_distance_bounded` 进行计算。
该函数在 DP 过程中一旦确定距离必然超过阈值就立即返回，避免完成整个
O(m×n) 的计算。

## 使用示例

```python
from solocoder_py.fuzzy_match import FuzzyMatcher, levenshtein_distance

# 计算编辑距离
dist = levenshtein_distance("kitten", "sitting")  # 3

# 基本模糊匹配
matcher = FuzzyMatcher(["apple", "banana", "cherry", "grape"])
results = matcher.match("aple", threshold=2)
for r in results:
    print(f"{r.candidate}: distance={r.distance}")
# apple: distance=1

# 仅精确匹配
results = matcher.match("apple", threshold=0)

# 限制返回数量
results = matcher.match("aple", threshold=2, max_results=1)

# 动态管理候选
matcher.add_candidate("apricot")
matcher.remove_candidate("banana")

# 查看候选数量
print(matcher.candidate_count)
```
