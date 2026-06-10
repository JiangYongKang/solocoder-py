# InvertedIndex 倒排索引检索域模块

本模块提供了一个基于内存数据结构的倒排索引检索实现，支持增量构建索引、多词求交检索、
TF-IDF 相关度打分排序以及分页游标机制。

## 模块功能

- **倒排索引构建**：将文档按词切分后建立词到文档 ID 的倒排映射，每个词条记录包含该词的文档列表及词频信息，支持增量添加文档
- **多词求交检索**：输入多个查询词时取各词对应文档 ID 列表的交集，返回同时包含所有查询词的文档；单查询词时直接返回该词的文档列表
- **TF-IDF 相关度打分**：基于词频（TF）和逆文档频率（IDF）计算检索结果中每个文档的相关度分数，按分数降序排列返回
- **分页游标**：检索结果支持分页返回，每页大小可配置，使用基于排序值 + 文档 ID 的游标机制保证翻页过程中索引不因新增文档而错位或漏返

## 核心类

### InvertedIndex

倒排索引的核心实现类，提供以下方法与属性：

| 方法 / 属性 | 说明 |
|------------|------|
| `add_document(doc_id, content)` | 增量添加文档，对内容分词后更新倒排索引 |
| `search(query_terms, page_size, cursor)` | 检索并返回分页结果，支持多词求交与游标翻页 |
| `get_postings(term)` | 获取指定词条的倒排记录列表（Posting 列表） |
| `document_count` | 当前索引中的文档总数（属性） |
| `vocabulary_size` | 当前索引中的词条总数（属性） |

### Posting

倒排记录数据结构：

- `doc_id`：文档标识
- `term_freq`：该词在文档中的出现频次

### SearchResult

检索结果数据结构：

- `doc_id`：文档标识
- `score`：该文档的相关度分数

### SearchResponse

检索响应数据结构：

- `results`：当前页的检索结果列表（`list[SearchResult]`）
- `next_cursor`：下一页的游标，若无更多结果则为 `None`
- `total_count`：符合检索条件的文档总数

## 倒排索引结构

倒排索引的核心数据结构为 `dict[str, dict[str, int]]`：

- **外层键**：词条（term），经分词后的小写形式
- **内层键**：文档 ID（doc_id）
- **内层值**：该词在对应文档中的出现频次（term frequency）

此外还维护：
- `_documents`：文档 ID 到原文的映射，用于防止重复添加
- `_doc_term_counts`：文档 ID 到该文档总词数的映射

分词规则：使用正则 `\w+` 提取词元，统一转为小写，忽略标点符号。

### 查询词规范化规则

查询词与文档内容使用**完全一致**的规范化管道，保证查询键能与索引键正确匹配：

1. **分词**：对每个查询词字符串使用与文档相同的正则 `\w+` 提取词元（自动剥离标点符号），如 `"hello!"` → `"hello"`、`"foo-bar"` → `["foo", "bar"]`
2. **小写化**：所有词元统一转为小写
3. **去重**：对规范化后的查询词列表去重（保持首次出现顺序），避免重复词导致 TF-IDF 分数被重复累加

因此以下查询在语义上完全等价，返回相同的得分：
- `["hello"]` 与 `["hello", "hello"]` 与 `["hello!"]`

## 打分公式

采用 TF-IDF 变体（平滑 IDF）计算相关度分数：

```
TF(t, d) = term frequency of t in document d（原始词频）

IDF(t) = log((1 + N) / (1 + df(t))) + 1

Score(d, Q) = Σ_{t ∈ Q} TF(t, d) × IDF(t)
```

其中：
- `N`：索引中的文档总数
- `df(t)`：包含词条 t 的文档数量
- `Q`：查询词列表
- 平滑项 `+1` 避免 df 为 0 时除零，末尾 `+1` 确保常见词仍保留基础权重

多词查询的文档分数为各查询词 TF-IDF 值之和（查询词已去重，同一词不会重复计分）。结果按分数降序排列，分数相同时按文档 ID 升序排列（保证确定性排序）。

性能优化：IDF 仅与词条的文档频率和文档总数相关，不依赖具体文档，因此在 `_score_documents` 中对每个查询词预计算一次 IDF 值并缓存，避免在文档循环中重复计算对数。

## 分页游标机制

### 设计目标

在检索结果可能动态变化（如新增文档）的场景下，传统的 offset 分页会导致：
- 新增文档后 offset 偏移错位，出现重复或遗漏
- 大 offset 场景下性能较差

游标机制通过记录排序位置而非偏移量来解决上述问题。

### 游标编码

游标基于 Base64 编码，内容格式为 `{score}:{doc_id}`：

```
cursor = base64(f"{last_result_score}:{last_result_doc_id}")
```

### 翻页逻辑

1. 检索匹配文档并按 `(-score, doc_id)` 排序
2. 首次请求（无游标）：从排序结果的起始位置返回
3. 后续请求（携带游标）：解码游标得到 `(cursor_score, cursor_doc_id)`，定位到排序结果中该位置之后继续返回
4. 定位规则：跳过所有 `score > cursor_score` 或 `(score == cursor_score 且 doc_id <= cursor_doc_id)` 的结果

### 稳定性保证

由于游标基于 `(score, doc_id)` 定位，新增文档不会改变已有文档的相对排序位置：
- 若新文档分数高于游标分数，它出现在游标之前，不影响后续页面
- 若新文档分数低于游标分数，它出现在游标之后，会在后续页面中被正常检索到

注意：游标仅在相同查询条件下有效，不同查询不应复用游标。

## 异常类

| 异常类 | 说明 | 触发场景 |
|--------|------|----------|
| `InvertedIndexError` | 倒排索引操作的基类异常 | — |
| `EmptyQueryError` | 查询词列表为空时抛出 | 传入空列表或全空白词 |
| `DocumentExistsError` | 添加重复文档 ID 时抛出 | `add_document` 使用已存在的 doc_id |
| `InvalidCursorError` | 游标解码失败时抛出 | 传入格式错误的游标字符串 |

## 使用示例

```python
from solocoder_py.inverted_index import InvertedIndex

# 创建倒排索引
idx = InvertedIndex()

# 增量添加文档
idx.add_document("doc1", "the quick brown fox jumps over the lazy dog")
idx.add_document("doc2", "the quick blue hare jumps over the sleepy cat")
idx.add_document("doc3", "a fast brown fox leaps across the lazy dog")

# 单词检索
resp = idx.search(["fox"])
print(f"匹配文档数: {resp.total_count}")
for r in resp.results:
    print(f"  {r.doc_id}: score={r.score:.4f}")

# 多词求交检索
resp = idx.search(["fox", "lazy"])
# 仅返回同时包含 "fox" 和 "lazy" 的文档

# 带分页的检索
resp = idx.search(["the"], page_size=2)
print(f"第1页: {[r.doc_id for r in resp.results]}")
if resp.next_cursor:
    resp2 = idx.search(["the"], page_size=2, cursor=resp.next_cursor)
    print(f"第2页: {[r.doc_id for r in resp2.results]}")

# 查看词条倒排记录
postings = idx.get_postings("fox")
for p in postings:
    print(f"  文档 {p.doc_id}: 词频={p.term_freq}")

# 添加重复文档会抛出异常
from solocoder_py.inverted_index import DocumentExistsError
try:
    idx.add_document("doc1", "duplicate")
except DocumentExistsError:
    print("文档已存在")

# 空查询词列表会抛出异常
from solocoder_py.inverted_index import EmptyQueryError
try:
    idx.search([])
except EmptyQueryError:
    print("查询词不能为空")
```
