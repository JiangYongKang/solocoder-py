# FullText 全文检索引擎模块

本模块提供基于内存数据结构的全文检索引擎实现，支持中英文混合文本的分词、倒排索引构建、
停用词过滤、词干提取以及 BM25 相关度评分排序。

## 模块功能

- **分词与索引构建**：支持中英文混合文本的基本分词（英文按空格和标点切分，中文按单字切分），
  对分词结果建立倒排索引，记录每个词出现在哪些文档中以及在该文档中的出现频次和位置信息，
  支持增量添加、更新和删除文档
- **停用词过滤**：内置中英文常用停用词表，在索引构建和查询时自动忽略高频低信息量的词，
  支持用户自定义扩展停用词
- **词干提取**：采用 Porter 词干提取算法对英文单词进行词干归一化，将不同形态的词
  （如复数、过去式、进行时）映射到同一个索引词条，索引构建和查询时一致应用
- **BM25 相关度评分**：查询时使用 BM25 算法对匹配文档进行相关度评分，考虑词频（TF）、
  逆文档频率（IDF）、文档长度等因素，提供可调节参数 `k1` 和 `b`
- **多词查询评分合并**：多个查询词时，对每个查询词分别计算 BM25 分数，再将各词的得分
  按文档维度求和作为最终得分，结果按分数降序排列

## 核心类

### FullTextIndex

全文检索索引的核心实现类，提供以下方法与属性：

| 方法 / 属性 | 说明 |
|------------|------|
| `add_document(doc)` | 添加或更新文档，对内容分词后更新倒排索引 |
| `add_documents(docs)` | 批量添加文档 |
| `remove_document(doc_id)` | 删除指定文档，同步清理索引 |
| `search(query, top_k)` | 检索并返回按 BM25 分数排序的结果 |
| `get_document(doc_id)` | 获取指定文档 |
| `contains_document(doc_id)` | 判断文档是否存在 |
| `get_term_frequency(term, doc_id)` | 获取指定词在文档中的词频 |
| `get_term_positions(term, doc_id)` | 获取指定词在文档中的位置列表 |
| `get_document_frequency(term)` | 获取包含指定词的文档数量 |
| `clear()` | 清空索引 |
| `k1` | BM25 词频饱和度参数（属性） |
| `b` | BM25 文档长度归一化参数（属性） |
| `total_docs` | 索引中的文档总数（属性） |
| `avg_doc_length` | 索引中文档的平均长度（属性） |
| `stopwords` | 停用词管理器（属性） |

构造参数：

- `k1`：词频饱和度参数，默认 `1.5`，控制词频对评分的影响程度
- `b`：文档长度归一化参数，默认 `0.75`，控制文档长度对评分的影响程度
- `extra_stopwords`：额外的停用词集合，用于扩展内置停用词表

### Tokenizer

分词器，提供中英文混合文本的分词功能：

| 方法 | 说明 |
|------|------|
| `tokenize(text)` | 对文本进行分词，返回 (词, 位置) 元组列表 |
| `tokenize_terms(text)` | 对文本进行分词，仅返回词列表 |

分词策略：
- 英文：按空格和标点切分，保留缩写形式（如 don't, it's），统一转为小写
- 中文：按单字切分
- 数字：连续数字作为一个词
- 标点符号：过滤掉标点符号

### StopWords

停用词管理器，提供停用词过滤功能：

| 方法 | 说明 |
|------|------|
| `is_stopword(term)` | 判断一个词是否是停用词 |
| `add(term)` | 添加一个停用词 |
| `remove(term)` | 移除一个停用词 |
| `filter(terms)` | 过滤词列表，返回非停用词列表 |
| `filter_tokens(tokens)` | 过滤 (词, 位置) 元组列表 |

内置停用词表包含常用的英文和中文停用词，支持大小写不敏感匹配。

### Stemmer

词干提取器，基于 Porter 词干提取算法实现：

| 方法 | 说明 |
|------|------|
| `stem(word)` | 对单个单词进行词干提取 |
| `stem_terms(terms)` | 对词列表进行词干提取 |
| `stem_tokens(tokens)` | 对 (词, 位置) 元组列表进行词干提取 |

词干提取策略：
- 仅对纯英文单词进行词干提取
- 非英文单词（如中文、数字、混合字符）保持不变
- 大小写不敏感，返回结果为小写形式

### 数据模型

#### Document

文档数据类，包含文档 ID、内容和元数据。

| 字段 | 说明 |
|------|------|
| `doc_id` | 文档唯一标识 |
| `content` | 文档内容 |
| `metadata` | 文档元数据（可选） |

#### TermInfo

词项信息数据类，记录词在某文档中的出现信息。

| 字段 | 说明 |
|------|------|
| `term` | 词项 |
| `doc_id` | 文档 ID |
| `frequency` | 词频 |
| `positions` | 词在文档中的位置列表 |

#### SearchResult

搜索结果数据类。

| 字段 | 说明 |
|------|------|
| `doc_id` | 文档 ID |
| `score` | BM25 相关度评分 |
| `matched_terms` | 匹配的查询词列表 |
| `metadata` | 文档元数据 |

## BM25 评分公式

BM25（Best Match 25）是一种常用的信息检索相关度评分算法，它是 TF-IDF 的改进版本。

### 评分公式

对于查询 Q，包含查询词 q₁, q₂, ..., qₙ，文档 D 的 BM25 得分为：

```
score(D, Q) = Σᵢ₌₁ⁿ IDF(qᵢ) × (f(qᵢ, D) × (k₁ + 1)) / (f(qᵢ, D) + k₁ × (1 - b + b × |D| / avgdl))
```

其中：

- `f(qᵢ, D)`：查询词 qᵢ 在文档 D 中的词频（Term Frequency）
- `|D|`：文档 D 的长度（词数）
- `avgdl`：所有文档的平均长度
- `k₁`：词频饱和度参数
- `b`：文档长度归一化参数

### IDF（逆文档频率）

本模块使用的 IDF 公式为：

```
IDF(qᵢ) = ln((N - n(qᵢ) + 0.5) / (n(qᵢ) + 0.5) + 1)
```

其中：
- `N`：文档总数
- `n(qᵢ)`：包含查询词 qᵢ 的文档数

### 参数含义

#### k₁ 参数（词频饱和度）

- 默认值：`1.5`
- 控制词频对评分的影响程度
- `k₁` 越大，词频对评分的影响越大，高分词的优势越明显
- `k₁ = 0` 时，词频不影响评分，所有匹配文档的 TF 部分贡献相同
- 典型取值范围：`[1.2, 2.0]`

#### b 参数（文档长度归一化）

- 默认值：`0.75`
- 控制文档长度对评分的归一化程度
- `b = 1` 时，完全按文档长度归一化，长文档和短文档在相同词频下评分相近
- `b = 0` 时，完全不考虑文档长度，词频高的文档得分更高
- 典型取值范围：`[0.5, 1.0]`

## 词干提取策略

### Porter 词干算法

本模块使用 Porter 词干提取算法对英文单词进行归一化。Porter 算法是最经典的词干提取算法之一，
通过一系列规则逐步移除单词的后缀，将单词映射到其词干形式。

### 算法特点

- **启发式规则**：基于英语词法规则，通过多步后缀移除实现词干提取
- **速度快**：算法复杂度低，适合大规模文本处理
- **一致性好**：同一词的规则变形通常映射到相同的词干

### 能力范围

Porter 算法基于后缀移除规则，仅处理**规则变形**，不支持不规则动词和特殊词形：

- **支持的规则变形**：
  - 名词复数：`cats` → `cat`，`boxes` → `box`
  - 动词第三人称单数：`runs` → `run`，`goes` → `goe`
  - 动词进行时：`running` → `run`，`playing` → `playi`
  - 动词过去式（规则）：`walked` → `walk`，`played` → `plai`
  - 形容词后缀：`happy` → `happi`，`easily` → `easili`

- **不支持的变形**：
  - 不规则动词：`ran` ≠ `run`，`went` ≠ `go`，`did` ≠ `do`，`seen` ≠ `see`
  - 词根本身变化的词形：`men` ≠ `man`，`children` ≠ `child`

### 注意事项

- 词干不一定是正确的英文单词（如 "playing" → "playi"）
- 关键是**一致性**：同一词的规则变形映射到同一个词干
- 中文和非英文单词不进行词干提取

## 停用词过滤策略

### 什么是停用词

停用词是指在文本中频繁出现但信息量很低的词，如英文的 "the", "a", "is"，
中文的 "的", "了", "是" 等。这些词对检索结果的区分度很低，过滤后可以：

- 减少索引大小，节省内存
- 提高检索效率
- 避免停用词对评分的干扰

### 粒度约定与过滤机制

由于中文分词采用单字切分策略，而停用词表中同时包含单字和多字词条，
本模块采用**两阶段过滤**机制确保所有停用词都被正确处理：

1. **文本预处理阶段**（多字符停用词过滤）：
   - 在分词前，对原始文本进行扫描
   - 将所有长度 ≥ 2 的停用词（如 "我们"、"一个"、"为什么"）替换为等长空格
   - 按停用词长度从长到短依次匹配，避免短词先匹配影响长词
   - 此阶段确保多字符停用词不会被拆成单字进入索引

2. **Token 过滤阶段**（单字停用词过滤）：
   - 分词后，对每个 token 进行单字停用词检查
   - 过滤掉长度 = 1 的停用词（如 "的"、"了"、"是"、"我"）

这种两阶段机制保证了：
- 多字符中文停用词（如 "我们"、"一个"、"为什么"）被正确过滤
- 单字中文停用词（如 "的"、"了"、"是"）也被正确过滤
- 英文停用词（无论是单字如 "a" 还是多字符如 "the"）同样适用

### 内置停用词表

- **英文停用词**：包含常用的冠词、介词、连词、代词、助动词等约 150 个词
- **中文停用词**：
  - 单字停用词："的"、"了"、"和"、"是"、"在"、"我" 等约 80 个
  - 多字停用词："我们"、"一个"、"为什么"、"这个"、"那个" 等约 20 个

### 自定义扩展

用户可以通过以下方式自定义停用词：

- 构造 `FullTextIndex` 时通过 `extra_stopwords` 参数添加额外停用词
- 通过 `stopwords.add(term)` 动态添加停用词（自动适配单字或多字）
- 通过 `stopwords.remove(term)` 动态移除停用词

注意：动态添加/移除停用词只影响后续的索引和查询，已索引的文档不会自动重新索引。

## 使用示例

### 基本使用

```python
from solocoder_py.fulltext import FullTextIndex, Document

# 创建索引
index = FullTextIndex()

# 添加文档
docs = [
    Document(doc_id="doc1", content="Python is a great programming language"),
    Document(doc_id="doc2", content="Java is another popular programming language"),
    Document(doc_id="doc3", content="Python and Java are both widely used"),
]
index.add_documents(docs)

# 搜索
results = index.search("programming language")
for result in results:
    print(f"doc_id: {result.doc_id}, score: {result.score:.4f}")
```

### 中文搜索

```python
from solocoder_py.fulltext import FullTextIndex, Document

index = FullTextIndex()

index.add_document(Document(doc_id="doc1", content="Python 是一种很棒的编程语言"))
index.add_document(Document(doc_id="doc2", content="Java 是另一种流行的编程语言"))

results = index.search("编程语言")
for result in results:
    print(f"doc_id: {result.doc_id}, score: {result.score:.4f}")
```

### 自定义 BM25 参数

```python
from solocoder_py.fulltext import FullTextIndex

# 调整 BM25 参数
index = FullTextIndex(k1=2.0, b=0.5)
```

### 自定义停用词

```python
from solocoder_py.fulltext import FullTextIndex

# 构造时添加额外停用词
index = FullTextIndex(extra_stopwords={"custom1", "custom2"})

# 动态添加停用词
index.stopwords.add("apple")

# 动态移除停用词
index.stopwords.remove("the")
```

### 文档管理

```python
from solocoder_py.fulltext import FullTextIndex, Document

index = FullTextIndex()

# 添加文档
index.add_document(Document(doc_id="doc1", content="hello world"))

# 更新文档（相同 doc_id 会覆盖）
index.add_document(Document(doc_id="doc1", content="hello python"))

# 删除文档
index.remove_document("doc1")

# 清空索引
index.clear()
```

### 获取索引信息

```python
from solocoder_py.fulltext import FullTextIndex, Document

index = FullTextIndex()
index.add_document(Document(doc_id="doc1", content="hello world hello"))

# 获取词频
print(index.get_term_frequency("hello", "doc1"))  # 2

# 获取词位置
print(index.get_term_positions("hello", "doc1"))  # [0, 2]

# 获取文档频率
print(index.get_document_frequency("hello"))  # 1

# 文档总数
print(index.total_docs)  # 1

# 平均文档长度
print(index.avg_doc_length)
```
