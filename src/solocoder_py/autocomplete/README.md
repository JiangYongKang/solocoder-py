# Autocomplete 模块

本模块提供了一个基于前缀树（Trie）的自动补全功能实现，使用内存数据结构模拟数据源，支持高效的前缀查询、热度加权排序、Top-N 截断、动态词频更新和拼写容错等特性。

## 模块功能

- **实时前缀匹配**：用户输入一个前缀字符串时，系统从已索引的候选词库中找出所有以该前缀开头的候选项。匹配支持中文和英文，大小写不敏感（可配置）。返回的候选项按热度排序后截取 Top-N 返回（N 可配置）。前缀匹配采用 Trie 数据结构，时间复杂度为 O(L)（L 为前缀长度），无需线性扫描全部候选词库。

- **热度加权排序**：每个候选项关联一个热度值（或搜索频次），热度越高的候选项排在越前面。热度值支持动态更新——每次候选项被选中或被搜索时可增加其热度值。相同前缀匹配的候选项中热度高的优先返回，热度相同时按字典序升序排列。

- **拼写容错候选建议**：当用户输入的前缀没有精确匹配的候选项时，系统尝试返回近似匹配的建议。容错策略采用编辑距离（Levenshtein 距离）在阈值范围内的候选项。容错建议按编辑距离、热度、字典序排序，且标记为"容错建议"（`is_fuzzy=True`）以区别于精确匹配。

- **候选词库管理**：支持向词库中添加新的候选项、删除已有候选项、更新候选项的热度或文本。词库中的候选项文本唯一，重复添加自动合并为更新热度。

- **并发安全**：使用可重入锁保护共享状态，支持多线程安全读写。

## 核心类

### TrieAutocomplete

基于前缀树的自动补全引擎，是模块的核心类。

**构造参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `case_sensitive` | `bool` | `False` | 是否大小写敏感 |
| `fuzzy_threshold` | `int` | `2` | 拼写容错的编辑距离阈值 |
| `default_top_n` | `Optional[int]` | `None` | 默认返回的候选数量上限 |

**核心方法：**

| 方法 | 说明 |
|------|------|
| `insert(word, weight=1)` | 插入词汇及其热度，重复插入累加热度 |
| `update_weight(word, weight, *, accumulate=False)` | 更新词汇热度，支持覆盖或累加模式，词汇不存在则自动插入 |
| `search(prefix, *, top_n=None, fuzzy=True, fuzzy_threshold=None)` | 按前缀查询候选词，返回按热度排序的 `SearchResult` 列表 |
| `get_weight(word)` | 获取词汇的热度，不存在返回 `None` |
| `contains(word)` | 判断词汇是否存在 |
| `delete(word)` | 删除指定词汇，返回是否成功删除 |
| `clear()` | 清空所有词汇 |
| `get_all_words()` | 返回所有词汇的排序列表 |

**属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `size` | `int` | 当前词汇总数（只读） |
| `case_sensitive` | `bool` | 是否大小写敏感（只读） |
| `fuzzy_threshold` | `int` | 拼写容错阈值（可读写） |

### Candidate

候选词数据类，包含词汇文本和热度值。

| 字段 | 类型 | 说明 |
|------|------|------|
| `word` | `str` | 词汇文本 |
| `weight` | `int` | 词汇热度（非负整数） |

### SearchResult

搜索结果数据类，包装候选词并提供匹配类型信息。

| 字段 | 类型 | 说明 |
|------|------|------|
| `candidate` | `Candidate` | 候选词对象 |
| `is_fuzzy` | `bool` | 是否为容错匹配结果 |
| `edit_distance` | `int` | 编辑距离（仅容错匹配有效） |

**便捷属性：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `word` | `str` | 候选词文本（代理 `candidate.word`） |
| `weight` | `int` | 候选词热度（代理 `candidate.weight`） |

### TrieNode

前缀树节点类，内部使用。

## 前缀匹配的数据结构与算法

### Trie 前缀树结构

前缀树（Trie）是一种树形数据结构，用于高效存储和检索字符串集合。每个节点代表一个字符，从根节点到某个节点的路径代表一个前缀或完整词汇。

**核心设计特点：**

1. **逐字符插入**：插入词汇时，从根节点开始，逐字符遍历词汇，不存在的节点则创建。
2. **候选列表维护**：每个节点维护一个已排序的候选词列表，包含所有以当前前缀开头的词汇。
3. **支持中英文**：由于 Python 字符串天然支持 Unicode，Trie 结构可以无缝处理中文、英文及混合文本。

### 前缀匹配算法

查询时只需定位到前缀对应的节点，即可直接返回该节点维护的已排序候选列表，时间复杂度为 O(L)，其中 L 为前缀长度。相比线性扫描 O(N) 的复杂度，在词库较大时优势明显。

**查询流程：**

1. 对输入前缀进行归一化处理（大小写转换）
2. 从根节点开始，逐字符遍历前缀
3. 如果中途字符不存在，说明没有精确匹配
4. 到达前缀末尾节点后，返回该节点的候选列表

### Top-N 截断逻辑

查询时的截断策略：

1. **无限制（`top_n=None` 或 `top_n <= 0`）**：返回所有匹配的候选词
2. **有上限（`top_n > 0`）**：返回前 `top_n` 个热度最高的候选词
3. **候选不足**：当实际候选数小于 `top_n` 时，返回全部候选
4. **空前缀查询**：空前缀返回所有词汇，同样支持 Top-N 截断

## 热度加权机制

### 热度排序策略

**排序规则（优先级从高到低）：**
1. **热度（weight）**：降序排列（热度高的候选词排在前面）
2. **词汇（word）**：升序排列（等热度时字典序小的排在前面）

**设计理由：**
- 热度降序符合自动补全的使用场景：热门/高频词汇应该优先展示
- 等热度时字典序升序保证排序的稳定性和可预测性

### 热度更新机制

热度支持两种更新模式：

1. **覆盖模式（`accumulate=False`）**：直接设置新的热度值
2. **累加模式（`accumulate=True`）**：在原有热度基础上增加指定值

**重复插入处理**：重复插入相同词汇时，热度自动累加。这模拟了实际搜索场景中，用户多次搜索同一个词时热度累积的效果。

### 节点候选列表维护

每个前缀节点都维护一个完整的候选词列表，这样查询时只需定位到前缀节点，即可直接返回已排序的候选列表。

- **插入时更新**：插入词汇时，沿途所有前缀节点都将该词汇加入候选列表并保持排序
- **更新时重排**：更新词汇热度时，沿途所有前缀节点都重新排序该词汇的位置
- **删除时移除**：删除词汇时，沿途所有前缀节点都移除该词汇

## 拼写容错策略

### 编辑距离算法

采用 Levenshtein 距离（编辑距离）衡量两个字符串的相似程度。编辑距离是指将一个字符串转换成另一个字符串所需的最少操作次数（插入、删除、替换一个字符）。

**算法实现优化：**
- 使用动态规划计算编辑距离
- 空间优化：只保留两行数据，空间复杂度从 O(M*N) 降低到 O(min(M,N))

### 容错查询流程

当精确前缀匹配没有结果时，触发容错查询：

1. 遍历词库中所有词汇
2. 计算查询词与每个词汇的编辑距离
3. 筛选出编辑距离在阈值范围内且大于 0 的词汇
4. 按编辑距离、热度、字典序排序
5. 返回 Top-N 结果

### 容错结果排序

容错结果的排序规则（优先级从高到低）：
1. **编辑距离**：升序排列（距离越小越相似，排在前面）
2. **热度**：降序排列（距离相同时热度高的排在前面）
3. **词汇**：升序排列（距离和热度都相同时字典序小的排在前面）

### 精确匹配优先

当存在精确匹配时，只返回精确匹配结果，不返回容错建议。这保证了精确匹配始终优先于容错建议。

### 容错配置

- `fuzzy_threshold`：编辑距离阈值，默认为 2。设置为 0 时完全禁用容错功能。
- `fuzzy` 参数：`search()` 方法可传入 `fuzzy=False` 临时禁用容错查询。

## 异常类

| 异常类 | 说明 |
|--------|------|
| `AutocompleteError` | 模块所有异常的基类 |
| `EmptyWordError` | 插入/更新/删除空字符串或纯空白词汇时抛出 |
| `InvalidWeightError` | 热度值为负数或容错阈值为负数时抛出 |
| `InvalidPrefixError` | 前缀无效时抛出（当前保留未使用） |

## 使用示例

### 基本使用

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
for result in results:
    print(f"{result.word}: {result.weight} (fuzzy: {result.is_fuzzy})")
# application: 15 (fuzzy: False)
# apple: 10 (fuzzy: False)
# app: 8 (fuzzy: False)

# Top-N 查询
top2 = autocomplete.search("app", top_n=2)
assert len(top2) == 2

# 更新热度（覆盖模式）
autocomplete.update_weight("apple", weight=20)
results = autocomplete.search("app")
assert results[0].word == "apple"
assert results[0].weight == 20

# 更新热度（累加模式）- 模拟用户选中该词
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

### 拼写容错示例

```python
from solocoder_py.autocomplete import TrieAutocomplete

autocomplete = TrieAutocomplete(fuzzy_threshold=2)

# 插入词汇
autocomplete.insert("apple", weight=10)
autocomplete.insert("apply", weight=15)
autocomplete.insert("apples", weight=8)

# 输入有拼写错误，触发容错建议
results = autocomplete.search("appla")
for result in results:
    print(f"{result.word}: distance={result.edit_distance}, weight={result.weight}, fuzzy={result.is_fuzzy}")
# apply: distance=1, weight=15, fuzzy=True
# apple: distance=1, weight=10, fuzzy=True
# apples: distance=2, weight=8, fuzzy=True

# 禁用容错
results = autocomplete.search("appla", fuzzy=False)
assert results == []

# 设置容错阈值为 0，完全禁用容错
autocomplete.fuzzy_threshold = 0
results = autocomplete.search("appla", fuzzy=True)
assert results == []
```

### 中文支持示例

```python
from solocoder_py.autocomplete import TrieAutocomplete

autocomplete = TrieAutocomplete()

# 插入中文词汇
autocomplete.insert("中国", weight=10)
autocomplete.insert("中国人", weight=15)
autocomplete.insert("中国话", weight=8)
autocomplete.insert("北京", weight=12)
autocomplete.insert("北京大学", weight=20)

# 中文前缀查询
results = autocomplete.search("中国")
for result in results:
    print(f"{result.word}: {result.weight}")
# 中国人: 15
# 中国: 10
# 中国话: 8

# 单字符前缀查询
results = autocomplete.search("北")
assert len(results) == 2
words = [r.word for r in results]
assert "北京大学" in words
assert "北京" in words

# 中英文混合
autocomplete.insert("中国food", weight=10)
autocomplete.insert("中国city", weight=8)
results = autocomplete.search("中国")
assert len(results) == 5
```

### 大小写敏感配置

```python
from solocoder_py.autocomplete import TrieAutocomplete

# 默认大小写不敏感
auto_ci = TrieAutocomplete()
auto_ci.insert("Apple", weight=10)
results = auto_ci.search("app")
assert len(results) == 1
assert results[0].word == "Apple"

# 大小写敏感
auto_cs = TrieAutocomplete(case_sensitive=True)
auto_cs.insert("Apple", weight=10)
auto_cs.insert("apple", weight=8)
auto_cs.insert("APP", weight=15)

results = auto_cs.search("app")
assert results[0].word == "apple"

results = auto_cs.search("APP")
assert results[0].word == "APP"

results = auto_cs.search("App")
assert results[0].word == "Apple"
```

### 并发安全示例

```python
import threading
from solocoder_py.autocomplete import TrieAutocomplete

autocomplete = TrieAutocomplete()
autocomplete.insert("counter", weight=0)

# 多线程累加热度
def increment():
    for _ in range(100):
        autocomplete.update_weight("counter", weight=1, accumulate=True)

threads = [threading.Thread(target=increment) for _ in range(10)]
for t in threads:
    t.start()
for t in threads:
    t.join()

assert autocomplete.get_weight("counter") == 1000
```

## 性能说明

- **前缀查询**：O(L)，L 为前缀长度
- **插入操作**：O(L * K)，L 为词汇长度，K 为节点候选列表平均长度（插入排序）
- **容错查询**：O(N * M)，N 为词库大小，M 为词汇平均长度（编辑距离计算）

对于大部分自动补全场景，前缀查询是主要操作，Trie 结构可以提供极佳的性能。容错查询作为备选方案，在词库较大时可能较慢，建议在业务层设置合理的超时或词库大小限制。
