# Autocomplete 模块

本模块提供了一个基于前缀树（Trie）的自动补全功能实现，使用内存数据结构模拟数据源，
支持高效的前缀查询、权重排序、Top-N 截断和动态词频更新等特性。

## 模块功能

- **前缀树基本结构：支持逐字符插入词汇，每个节点维护以当前前缀为开头的所有词汇的汇总信息，支持按前缀高效查询候选词
- **按权重排序候选：每个词汇关联一个权重值，输入前缀查询时返回的候选列表按权重降序排列，权重相同的情况下按字典序**升序**排列
- **Top-N 截断：查询时可指定返回候选数量的上限 N，仅返回权重最高的前 N 个候选词，N 值不设上限时返回全部匹配的候选
- **动态词频更新：已存在的词汇可通过权重累加或覆盖方式更新其权重值，更新后立即影响后续查询结果的排序，新增词汇可动态插入而不需要重建整棵树
- **并发安全：使用可重入锁保护共享状态，支持多线程安全读写
- **词汇删除与清空：支持删除指定词汇或清空所有数据

## 核心类

### TrieAutocomplete

基于前缀树的自动补全引擎，提供以下核心方法：

| 方法 | 说明 |
|------|------|
| `insert(word, weight=1)` | 插入词汇及其权重，重复插入忽略 |
| `update_weight(word, weight, *, accumulate=False)` | 更新词汇权重，支持覆盖或累加模式，词汇不存在则自动插入 |
| `search(prefix, *, top_n=None)` | 按前缀查询候选词，返回按权重排序的候选列表，前缀不存在时抛出 `InvalidPrefixError` |
| `get_weight(word)` | 获取词汇的权重，不存在返回 `None` |
| `contains(word)` | 判断词汇是否存在 |
| `delete(word)` | 删除指定词汇，返回是否成功删除 |
| `clear()` | 清空所有词汇 |
| `get_all_words()` | 返回所有词汇的排序列表 |
| `size` | 当前词汇总数（属性） |

### Candidate

候选词数据类，包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `word` | `str` | 词汇文本 |
| `weight` | `int` | 词汇权重 |

### TrieNode

前缀树节点类，内部使用，包含：

- `char`：当前节点字符
- `children`：子节点映射（字符 → 节点）
- `is_end_of_word`：是否为词汇结束节点
- `weight`：词汇权重（仅结束节点有效）
- `candidates`：以当前前缀开头的候选词列表（已排序）

## 前缀树结构与 Top-N 截断逻辑

### 前缀树结构

前缀树（Trie）是一种树形数据结构，用于高效存储和检索字符串集合。每个节点代表一个字符，
从根节点到某个节点的路径代表一个前缀或完整词汇。

核心设计特点：

1. **逐字符插入：插入词汇时，从根节点开始，逐字符遍历词汇，不存在的节点则创建
2. **候选列表维护：每个节点维护一个已排序的候选词列表，包含所有以当前前缀开头的词汇
3. **排序策略：候选词按权重降序排列，权重相同则按字典序升序排列

### 排序策略说明

**排序规则：**
- **主要关键字：** 权重（weight），降序排列（权重高的候选词排在前面）
- **次要关键字：** 词汇（word），升序排列（等权重时字典序小的排在前面）

**设计理由：**
- 权重降序符合自动补全的使用场景：热门/高频词汇应该优先展示
- 等权重时字典序升序保证排序的稳定性和可预测性：相同权重的词汇按照字母顺序排列，结果确定性强
- 显式排序 key 便于代码阅读：`sort(key=lambda c: (-c.weight, c.word))` 直观表达排序意图，无需追溯 `__lt__` 方法

**实现方式：**
- `TrieNode.add_candidate` 使用插入排序维护有序列表，单次插入复杂度 O(k)（k 为候选词数量）
- 空前缀查询 `_get_all_candidates` 使用显式 key 的 `sort()`，复杂度 O(n log n)
- `Candidate` 类的比较运算符（`__lt__`、`__gt__` 等）同样遵循该排序策略，保证外部代码直接排序时行为一致

### 节点候选列表维护

每个前缀节点都维护一个完整的候选词列表，这样查询时只需定位到前缀节点，
即可直接返回已排序的候选列表，时间复杂度为 O(L)，其中 L 为前缀长度。

- **插入时更新：插入词汇时，沿途所有前缀节点都将该词汇加入候选列表并保持排序
- **更新时重排：更新词汇权重时，沿途所有前缀节点都重新排序该词汇的位置
- **删除时移除：删除词汇时，沿途所有前缀节点都移除该词汇

### Top-N 截断逻辑

查询时的截断策略：

1. **无限制（top_n=None 或 top_n ≤ 0）：返回所有匹配的候选词
2. **有上限（top_n > 0）：返回前 top_n 个权重最高的候选词
3. **候选不足：当实际候选数小于 top_n 时，返回全部候选
4. **空前缀查询：空前缀返回所有词汇，同样支持 Top-N 截断

## 使用示例

```python
from solocoder_py.autocomplete import TrieAutocomplete

# 创建自动补全实例
autocomplete = TrieAutocomplete()

# 插入词汇
autocomplete.insert("apple", weight=10)
autocomplete.insert("app", weight=8)
autocomplete.insert("application", weight=15)
autocomplete.insert("banana", weight=12)

# 按前缀查询
results = autocomplete.search("app")
for candidate in results:
    print(f"{candidate.word}: {candidate.weight}")
# application: 15
# apple: 10
# app: 8

# Top-N 查询
top2 = autocomplete.search("app", top_n=2)
assert len(top2) == 2

# 更新权重（覆盖模式）
autocomplete.update_weight("apple", weight=20)
results = autocomplete.search("app")
assert results[0].word == "apple"
assert results[0].weight == 20

# 更新权重（累加模式）
autocomplete.update_weight("app", weight=5, accumulate=True)
assert autocomplete.get_weight("app") == 13

# 空前缀查询（返回所有）
all_results = autocomplete.search("")
assert len(all_results) == 4

# 删除词汇
autocomplete.delete("banana")
assert autocomplete.contains("banana") is False

# 动态插入
autocomplete.insert("cat", weight=7)
results = autocomplete.search("c")
assert results[0].word == "cat"
```
