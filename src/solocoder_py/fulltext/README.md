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
| `tokenize(text)` | 将文本分词，返回 `(词, 位置)` 列表 |
| `tokenize_terms(text)` | 将文本分词，仅返回词列表 |

分词规则：
- 英文：按空格和标点切分，保留缩写形式（如 don't），自动转小写
- 中文：按单字切分（Unicode 范围 `\u4e00-\u9fff`）
- 数字：连续数字作为一个词元
- 标点符号：忽略

### StopWords

停用词管理器，内置中英文常用停用词表：

| 方法 | 说明 |
|------|------|
| `is_stopword(term)` | 判断词是否为停用词 |
| `add(term)` | 添加自定义停用词 |
| `remove(term)` | 移除停用词 |
| `filter(terms)` | 过滤词列表中的停用词 |
| `filter_tokens(tokens)` | 过滤带位置信息的词元列表 |
| `stopwords` | 返回当前停用词集合（属性） |

### Stemmer

词干提取器，基于 Porter 算法实现：

| 方法 | 说明 |
|------|------|
| `stem(word)` | 对单个词进行词干提取 |
| `stem_terms(terms)` | 对词列表进行词干提取 |
| `stem_tokens(tokens)` | 对带位置信息的词元列表进行词干提取 |

规则：
- 仅对纯英文字母组成的词执行词干提取
- 中文、数字及混合内容不做处理，原样返回
- 索引构建和查询时一致应用，确保查询词和索引词条的归一化

### 数据模型

| 类 | 说明 |
|----|------|
| `Document` | 文档，包含 `doc_id`、`content`、`metadata` |
| `TermInfo` | 词项信息，包含 `term`、`doc_id`、`frequency`、`positions` |
| `SearchResult` | 检索结果，包含 `doc_id`、`score`、`matched_terms`、`metadata` |

## BM25 评分公式与参数含义

BM25（Best Matching 25）是信息检索领域经典的相关度评分算法，本模块的实现公式如下：

### IDF（逆文档频率）

```
IDF(q) = ln((N - n(q) + 0.5) / (n(q) + 0.5) + 1)
```

- `N`：索引中的文档总数
- `n(q)`：包含查询词 q 的文档数量
- IDF 衡量词的区分度，越稀有的词 IDF 越高

### TF 组件（词频饱和函数）

```
TF(q, D) = (f(q, D) * (k1 + 1)) / (f(q, D) + k1 * (1 - b + b * |D| / avgdl))
```

- `f(q, D)`：查询词 q 在文档 D 中的出现频次
- `|D|`：文档 D 的长度（分词后的词元数量）
- `avgdl`：所有文档的平均长度

### BM25 单词评分

```
score(q, D) = IDF(q) * TF(q, D)
```

### 多词查询评分合并

```
score(Q, D) = Σ score(qi, D)   for each qi in Q
```

多个查询词的 BM25 分数按文档维度求和，作为该文档的最终得分。

### 参数含义

| 参数 | 默认值 | 含义 |
|------|--------|------|
| `k1` | 1.5 | **词频饱和度参数**。控制词频对评分的影响程度。值越大，词频增加带来的评分增益越大；值为 0 时，词频不影响评分，所有匹配文档得到相同的基础分 |
| `b` | 0.75 | **文档长度归一化参数**。控制文档长度对评分的惩罚程度。值为 0 时不考虑文档长度；值为 1 时完全按平均长度归一化，长文档受到更大惩罚 |

## 词干提取与停用词过滤策略

### 词干提取策略

采用 Porter Stemming Algorithm，按以下步骤依次执行：

1. **Step 1a**：处理复数后缀（sses → ss, ies → i, ss → ss, s → 去掉）
2. **Step 1b**：处理过去式/进行时后缀（eed → ee, ed → 去掉, ing → 去掉）
3. **Step 1c**：处理 y 结尾（元音后 y → i）
4. **Step 2**：处理派生后缀（ational → ate, tional → tion, 等）
5. **Step 3**：处理形容词/名词后缀（icate → ic, ative → 去掉, 等）
6. **Step 4**：处理词缀删除（al, ance, ence, er, ic, 等）
7. **Step 5a**：处理 e 结尾
8. **Step 5b**：处理双辅音 l 结尾

词干提取在索引构建和查询时一致应用，确保 `running`、`ran`、`runs` 等变体都映射到 `run`。

### 停用词过滤策略

- 内置英文停用词约 80 个，涵盖冠词、代词、介词、连词、助动词等高频低信息量词
- 内置中文停用词约 100 个，涵盖助词、代词、介词、连词、语气词等
- 在索引构建时过滤：停用词不进入倒排索引，不计入文档长度
- 在查询时过滤：停用词不参与 BM25 评分计算
- 支持运行时动态添加/移除停用词，修改后即时生效于后续查询

## 使用示例

### 基本用法

```python
from solocoder_py.fulltext import FullTextIndex, Document

# 创建索引（使用默认 BM25 参数）
index = FullTextIndex()

# 添加文档
index.add_document(Document(doc_id="1", content="Python is a programming language"))
index.add_document(Document(doc_id="2", content="Java is also a programming language"))
index.add_document(Document(doc_id="3", content="Python data analysis with pandas"))

# 搜索
results = index.search("Python programming")
for r in results:
    print(f"文档 {r.doc_id}: 分数={r.score:.4f}, 匹配词={r.matched_terms}")
```

### 自定义 BM25 参数

```python
# 降低词频影响，增强长度归一化
index = FullTextIndex(k1=1.2, b=0.9)

# 词频不影响评分（仅由 IDF 决定排序）
index = FullTextIndex(k1=0.0, b=0.75)

# 不考虑文档长度
index = FullTextIndex(k1=1.5, b=0.0)
```

### 自定义停用词

```python
# 初始化时添加额外停用词
index = FullTextIndex(extra_stopwords={"python", "java"})

# 运行时动态添加/移除
index.stopwords.add("custom_stopword")
index.stopwords.remove("the")
```

### 中英文混合检索

```python
index = FullTextIndex()
index.add_document(Document(doc_id="1", content="Python编程 语言学习"))
index.add_document(Document(doc_id="2", content="Java开发 Web应用"))

# 中文按单字检索
results = index.search("编程")
# 英文词干提取
results = index.search("programming")
# 混合查询
results = index.search("Python开发")
```

### 文档管理与增量操作

```python
# 更新文档（相同 doc_id 会自动替换）
index.add_document(Document(doc_id="1", content="new content"))

# 删除文档
index.remove_document("1")

# 查看词项信息
freq = index.get_term_frequency("python", "1")
positions = index.get_term_positions("python", "1")
doc_freq = index.get_document_frequency("python")
```

### 限定返回数量

```python
# 只返回前 5 条结果
results = index.search("test query", top_k=5)
```
