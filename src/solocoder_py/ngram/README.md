# N-Gram 索引模块

本模块提供基于 N-Gram（字符 n 元语法）的内存文本索引与子串搜索实现，
支持增量构建索引、亚线性子串搜索、命中位置回溯以及命中片段高亮提取。

## 模块功能

- **N-Gram 索引构建**：将输入文本按可配置的 N 值切分为连续的字符片段（gram），
  建立每个 gram 到其所在文本及位置的倒排索引，支持增量添加、删除和更新文档
- **亚线性子串搜索**：查询时将查询串按相同 N 值切分为 gram 列表，通过索引快速
  定位候选文档（包含所有查询 gram 的文档），再对候选做精确子串匹配验证，
  搜索时间与 gram 命中数相关而非与文档总量线性相关
- **命中位置回溯**：查询成功后返回子串在文档中的所有命中起始字符偏移量，
  位置信息通过合并相邻 gram 的位置序列得出
- **命中片段高亮提取**：对每个命中位置，提取命中点前后的上下文文本
  （上下文窗口大小可配置），用特殊标记包裹命中子串，返回高亮后的片段
- **N 值可配置**：索引构建时可指定 N 值（如 N=2 的 bigram、N=3 的 trigram），
  不同 N 值对应不同的索引精度和空间开销

## 核心类

### NGramIndex

N-Gram 索引的核心实现类，提供以下方法与属性：

| 方法 / 属性 | 说明 |
|------------|------|
| `add_document(doc_id, content)` | 增量添加文档，对内容提取 gram 后更新倒排索引 |
| `remove_document(doc_id)` | 删除文档，同步清理索引中对应的 gram 记录（利用缓存避免重复提取 gram） |
| `update_document(doc_id, new_content)` | 更新文档内容，基于新旧 gram 差异增量更新索引 |
| `search(query, context_size, highlight_start, highlight_end)` | 子串搜索，返回匹配结果及高亮片段 |
| `get_gram_postings(gram)` | 获取指定 gram 的倒排记录列表（Posting 列表） |
| `n` | 索引的 N 值（属性） |
| `document_count` | 当前索引中的文档总数（属性） |
| `gram_count` | 当前索引中的 gram 总数（属性） |

构造参数：

- `n`：Gram 大小，默认 `2`（bigram）。N 值越大搜索越精确但索引空间越大；
  N 值越小索引空间越小但候选集越大，需要更多精确匹配验证。

`search` 方法参数：

- `query`：查询子串
- `context_size`：高亮片段前后上下文的字符数，默认 `10`
- `highlight_start`：高亮起始标记，默认 `"[["`
- `highlight_end`：高亮结束标记，默认 `"]]"`

### GramPosting

Gram 倒排记录数据结构：

- `doc_id`：文档标识
- `positions`：该 gram 在文档中出现的所有起始位置列表

### NGramSearchResult

单文档搜索结果数据结构：

- `doc_id`：文档标识
- `hit_positions`：所有命中位置的起始字符偏移量列表
- `fragments`：各命中位置对应的高亮片段列表（与 `hit_positions` 一一对应）

### NGramSearchResponse

搜索响应数据结构：

- `results`：搜索结果列表（`list[NGramSearchResult]`）
- `total_count`：匹配的文档总数

### HighlightedFragment

高亮片段数据结构：

- `text`：带高亮标记的片段文本
- `hit_start`：高亮子串在片段文本中的起始偏移（包含起始标记）
- `hit_end`：高亮子串在片段文本中的结束偏移（包含结束标记）

## N-Gram 索引结构

倒排索引的核心数据结构为 `dict[str, dict[str, list[int]]]`：

- **外层键**：Gram 字符串（如 bigram 的 `"he"`, `"el"`, `"ll"` 等）
- **内层键**：文档 ID（doc_id）
- **内层值**：该 gram 在对应文档中出现的所有起始位置列表

此外还维护：
- `_documents`：文档 ID 到原文内容的映射，用于精确匹配验证和高亮提取
- `_doc_grams`：文档 ID 到该文档 gram→位置列表映射的缓存，避免删除和更新时重复提取 gram

### 文档更新的增量策略

`update_document` 通过比较新旧内容的 gram 集合差异，增量更新索引：

1. **grams_to_remove**：仅存在于旧内容中的 gram，从索引中移除该文档的记录
2. **grams_to_add**：仅存在于新内容中的 gram，向索引中添加该文档的位置列表
3. **grams_to_update**：同时存在于新旧内容但位置列表有变化的 gram，更新索引中的记录

此策略避免了 `remove_document` + `add_document` 两步操作带来的完整重建开销。

### Gram 提取规则

对长度为 L 的文本，使用大小为 N 的滑动窗口提取 gram：

```
文本: "hello" (L=5), N=2
grams: "he"(0), "el"(1), "ll"(2), "lo"(3)
```

- 当文本长度 < N 时，不产生任何 gram
- 位置为 gram 首字符在原文本中的 0 基偏移量

## 子串搜索与位置回溯算法

### 搜索流程

1. **查询 gram 化**：将查询串按相同 N 值切分为 gram 列表，并记录每个 gram
   在查询串中的偏移量
2. **候选文档筛选**：取所有查询 gram 对应文档集合的交集，得到候选文档
   （即包含所有查询 gram 的文档）
   - 优化：按 gram 的文档频率从小到大求交，尽早缩小候选集
3. **位置回溯**：对每个候选文档，通过合并各 gram 的位置序列推算可能的
   命中起始位置
4. **精确验证**：对推算出的候选位置，在原文中做精确子串匹配验证，
   过滤掉 gram 位置重合但实际子串不匹配的假阳性
5. **结果排序**：按命中次数降序、文档 ID 升序排列

### 位置回溯算法

位置回溯的核心思想：若查询串 `Q` 在文档 `D` 的位置 `p` 处出现，则 Q 的
第 i 个 gram 必须出现在 D 的 `p + offset_i` 位置，其中 `offset_i` 是该 gram
在 Q 中的偏移量。

算法步骤：

1. 以第一个查询 gram 为基准，对其在文档中的每个出现位置 `doc_pos`，
   计算候选起始位置 `candidate = doc_pos - first_gram_offset`
2. 对剩余的每个查询 gram，检查所有候选位置是否满足：
   `candidate + gram_offset` 存在于该 gram 的文档位置列表中
3. 逐步淘汰不满足条件的候选，最终剩余的即为可能的命中位置
4. 对候选位置做精确字符串匹配验证

复杂度：与查询 gram 数和首个 gram 的命中数相关，远小于遍历全文。

### 短查询处理

当查询串长度 < N 时，查询无法产生任何 gram。此时退化为线性扫描所有文档，
使用 `str.find()` 进行精确匹配。虽然是线性扫描，但由于查询过短时索引
无法提供剪枝效果，这是 N-Gram 索引的固有特性。

## 高亮提取策略

对每个命中位置，提取前后各 `context_size` 个字符的上下文，并在命中子串
前后添加高亮标记。

### 边界安全处理

- 若命中位置靠近文本开头，则前置上下文截断到 0（不会越界）
- 若命中位置靠近文本结尾，则后置上下文截断到文本末尾（不会越界）
- `context_size = 0` 时，仅返回被高亮标记包裹的命中子串本身

### 偏移计算

`HighlightedFragment` 中的 `hit_start` 和 `hit_end` 是相对于高亮后
片段文本的偏移量，包含高亮标记本身的长度，便于调用方定位高亮区域。

## 异常类

| 异常类 | 说明 | 触发场景 |
|--------|------|----------|
| `NGramError` | N-Gram 操作的基类异常 | — |
| `InvalidNValueError` | N 值无效时抛出 | `n < 1` |
| `DocumentExistsError` | 添加重复文档 ID 时抛出 | `add_document` 使用已存在的 doc_id |
| `DocumentNotFoundError` | 删除不存在的文档时抛出 | `remove_document` 使用不存在的 doc_id |
| `EmptyQueryError` | 查询串为空时抛出 | `search("")` |
| `InvalidContextSizeError` | 上下文大小无效时抛出 | `context_size < 0` |

## 使用示例

```python
from solocoder_py.ngram import NGramIndex

# 创建 bigram 索引（默认 N=2）
idx = NGramIndex(n=2)

# 增量添加文档
idx.add_document("doc1", "the quick brown fox jumps over the lazy dog")
idx.add_document("doc2", "the quick blue hare jumps over the sleepy cat")
idx.add_document("doc3", "a fast brown fox leaps across the lazy dog")

# 子串搜索
resp = idx.search("quick")
print(f"匹配文档数: {resp.total_count}")
for r in resp.results:
    print(f"  {r.doc_id}: 命中位置 {r.hit_positions}")
    for frag in r.fragments:
        print(f"    片段: {frag.text}")

# 自定义上下文大小和高亮标记
resp = idx.search(
    "fox",
    context_size=5,
    highlight_start="<b>",
    highlight_end="</b>",
)

# 多命中搜索
idx.add_document("doc4", "apple pie and apple juice and apple sauce")
resp = idx.search("apple")
print(f"命中次数: {len(resp.results[0].hit_positions)}")  # 3

# 删除文档
idx.remove_document("doc3")
resp = idx.search("fast")
print(resp.total_count)  # 0

# 更新文档内容（增量更新索引，避免完整重建）
idx.update_document("doc2", "the quick blue fox jumps over the sleepy cat")
resp_hare = idx.search("hare")
print(resp_hare.total_count)  # 0
resp_fox = idx.search("fox")
print(resp_fox.total_count)  # 2 (doc1 和 doc2)

# trigram 索引（N=3）
idx3 = NGramIndex(n=3)
idx3.add_document("doc1", "hello world")
resp = idx3.search("world")

# 查看 gram 倒排记录
from solocoder_py.ngram import GramPosting
postings = idx.get_gram_postings("th")
for p in postings:
    print(f"文档 {p.doc_id}: 位置 {p.positions}")

# 异常处理
from solocoder_py.ngram import (
    DocumentExistsError,
    DocumentNotFoundError,
    EmptyQueryError,
    InvalidNValueError,
)

try:
    NGramIndex(n=0)
except InvalidNValueError:
    print("N 值必须 >= 1")

try:
    idx.search("")
except EmptyQueryError:
    print("查询串不能为空")

try:
    idx.update_document("nonexistent", "new content")
except DocumentNotFoundError:
    print("文档不存在")
```
