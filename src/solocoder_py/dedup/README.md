# Dedup 记录去重引擎

本模块提供基于内存数据结构的记录去重引擎，支持精确匹配去重、模糊匹配去重以及冲突字段合并，
适用于数据清洗、记录整合等场景。

## 模块功能

- **精确匹配去重**：支持配置一个或多个字段作为匹配键，按键值分组识别重复记录
- **模糊匹配去重**：基于编辑距离的相似度计算，支持多字段加权和阈值配置
- **传递性分组**：使用并查集（Union-Find）算法处理 A-B、B-C 的传递性重复问题
- **冲突合并策略**：提供多种字段冲突解决策略，支持按字段定制策略
- **混合模式**：支持精确匹配与模糊匹配组合使用，先按精确键分组再在组内模糊匹配

## 核心类与模块

### `DedupEngine`

去重引擎主类，整合精确匹配、模糊匹配和冲突合并功能。

主要方法：
- `add_record(record)`：添加单条记录
- `add_records(records)`：批量添加记录
- `clear()`：清空所有记录
- `dedup()`：执行去重，返回 `DedupResult`

主要配置参数：

| 参数 | 类型 | 说明 |
|------|------|------|
| `exact_match_keys` | `list[str] \| None` | 精确匹配的字段列表 |
| `use_fuzzy` | `bool` | 是否启用模糊匹配 |
| `fuzzy_fields` | `list[str] \| None` | 参与模糊匹配的字段 |
| `fuzzy_threshold` | `float` | 模糊匹配相似度阈值 (0, 1]，默认 0.8 |
| `fuzzy_field_weights` | `dict[str, float] \| None` | 各字段的权重 |
| `merge_strategy` | `str` | 默认合并策略，默认 `first` |
| `custom_merge` | `MergeFunction \| None` | 自定义合并函数 |
| `field_merge_strategies` | `dict[str, str] \| None` | 按字段指定合并策略 |
| `fallback_merge_strategy` | `str` | 兜底合并策略，默认 `last` |
| `record_selection_strategy` | `str` | 记录级保留策略，默认 `merge` |
| `record_selection_field` | `str \| None` | 按字段保留时的参考字段 |
| `record_selection_desc` | `bool` | 按字段保留时是否降序，默认 `True` |

### 记录级保留策略

当去重组内存在多条重复记录时，除了字段级冲突合并（`merge`）外，还可以选择直接保留组内某一条完整记录：

| 策略常量 | 说明 |
|----------|------|
| `KEEP_MERGE` | 字段级冲突合并（默认） |
| `KEEP_FIRST` | 保留组内最早出现的记录 |
| `KEEP_LAST` | 保留组内最后出现的记录 |
| `KEEP_MOST_COMPLETE` | 保留非空字段最多的记录 |
| `KEEP_BY_FIELD` | 按指定字段排序后保留首条（需配合 `record_selection_field` 使用） |

**示例：保留字段最完整的一条**

```python
from solocoder_py.dedup import DedupEngine, KEEP_MOST_COMPLETE

engine = DedupEngine(
    exact_match_keys=["id"],
    record_selection_strategy=KEEP_MOST_COMPLETE,
)
```

**示例：按更新时间保留最新一条**

```python
from solocoder_py.dedup import DedupEngine, KEEP_BY_FIELD

engine = DedupEngine(
    exact_match_keys=["user_id"],
    record_selection_strategy=KEEP_BY_FIELD,
    record_selection_field="updated_at",
    record_selection_desc=True,
)
```

### 数据模型

- `Record`：记录类型，别名 `dict[str, Any]`
- `DedupGroup`：去重分组，包含记录列表、原始索引、匹配得分等
- `DedupResult`：去重结果，包含唯一记录、分组、统计信息、兜底字段信息
  - `unique_records`：去重后的唯一记录列表
  - `groups`：所有分组列表
  - `total_input` / `total_unique` / `total_duplicates`：统计信息
  - `fallback_fields`：字典，key 为组索引，value 为该组使用兜底策略的字段列表
- `MergeResult`：合并结果，包含合并后的记录、冲突字段列表、成功合并字段列表、兜底字段列表
  - `record`：合并后的记录
  - `conflict_fields`：存在冲突的字段列表
  - `merged_fields`：成功应用合并策略的字段列表
  - `fallback_fields`：使用兜底策略的字段列表（调用方可感知哪些字段走了兜底）

### 子模块

- `exact_matcher`：精确匹配分组与保留策略
- `fuzzy_matcher`：模糊匹配、相似度计算、并查集算法
- `merge_strategies`：冲突合并策略实现
- `exceptions`：异常类定义

## 精确匹配与模糊匹配的协作方式

引擎支持三种工作模式：

### 1. 仅精确匹配

配置 `exact_match_keys` 即可。引擎按指定字段的组合键将记录分组，
同一组内的记录视为精确重复。

```python
engine = DedupEngine(exact_match_keys=["order_id"])
```

### 2. 仅模糊匹配

设置 `use_fuzzy=True` 并配置 `fuzzy_fields`。引擎对所有记录两两计算相似度，
超过阈值的记录对通过并查集算法聚合成组。

```python
engine = DedupEngine(
    use_fuzzy=True,
    fuzzy_fields=["name", "email"],
    fuzzy_threshold=0.8,
)
```

### 3. 混合模式

同时配置精确匹配键和模糊匹配。引擎先按精确键进行粗分组，
然后在每个精确组内部执行模糊匹配，进行更细粒度的去重。

```python
engine = DedupEngine(
    exact_match_keys=["city"],
    use_fuzzy=True,
    fuzzy_fields=["name"],
    fuzzy_threshold=0.7,
)
```

**协作流程**：
1. 先用 `exact_match_keys` 将记录分成若干精确组
2. 对每个精确组内的记录执行模糊匹配
3. 不同精确组之间的记录不会被模糊匹配到一起

这种模式适用于需要先按某个维度分区，再在分区内进行模糊去重的场景。

## 传递性分组策略

模糊匹配采用并查集（Union-Find）算法处理传递性问题：

- 若 A 匹配 B（相似度 ≥ 阈值），且 B 匹配 C，则 A、B、C 被分到同一组
- 即使 A 和 C 的相似度低于阈值，只要存在传递链，它们仍属同一组
- 每组的 `match_score` 为组内所有匹配对得分的平均值
- `fuzzy_pairs` 字段记录组内所有直接匹配的记录对

## 冲突合并策略

### 可用策略

| 策略名 | 说明 |
|--------|------|
| `first` | 保留组内第一条记录的值（默认） |
| `last` | 保留组内最后一条记录的值 |
| `longest_string` | 保留最长的字符串值 |
| `most_common` | 保留出现次数最多的值 |
| `first_non_empty` | 保留第一个非空（非 None/空字符串/空容器）的值 |
| `custom` | 使用自定义合并函数 |

### 策略优先级

冲突字段的合并策略按以下优先级确定：

1. **字段级策略**：`field_merge_strategies` 中为该字段指定的策略（最高优先级）
2. **全局默认策略**：`merge_strategy` 参数指定的默认策略
3. **兜底策略**：`fallback_merge_strategy`，当指定策略不可用时的回退方案

### 兜底策略与可观测性

当以下情况发生时，合并会自动回退到 `fallback_merge_strategy`：
- 指定 `custom` 策略但 `custom_merge` 函数抛出异常
- 指定 `custom` 策略但 `custom_merge` 为 `None`
- 指定的策略名称不存在
- 策略 resolver 执行时抛出异常

使用兜底策略的字段会被记录在 `MergeResult.fallback_fields` 列表中，调用方可通过该字段感知哪些字段走了兜底逻辑。

```python
from solocoder_py.dedup import DedupGroup, merge_group, STRATEGY_CUSTOM

def bad_merge(field, values):
    raise ValueError("oops")

group = DedupGroup(
    records=[{"id": 1, "name": "A"}, {"id": 1, "name": "B"}],
    indices=[0, 1],
    is_exact=True,
)
result = merge_group(group, strategy=STRATEGY_CUSTOM, custom_merge=bad_merge)
print(result.fallback_fields)  # ["id", "name"]
```

### 自定义合并函数

自定义函数签名：`(field_name: str, values: list[Any]) -> Any`

```python
def sum_amount(field, values):
    if field == "amount":
        return sum(v for v in values if v is not None)
    return values[0]

engine = DedupEngine(
    exact_match_keys=["order_id"],
    merge_strategy="custom",
    custom_merge=sum_amount,
)
```

## 使用示例

### 基本精确去重

```python
from solocoder_py.dedup import DedupEngine

engine = DedupEngine(exact_match_keys=["name", "phone"])
engine.add_records([
    {"name": "张三", "phone": "13800138000", "email": "zhang@a.com"},
    {"name": "张三", "phone": "13800138000", "email": "zhang@b.com"},
    {"name": "李四", "phone": "13900139000", "email": "li@c.com"},
])

result = engine.dedup()
print(f"输入: {result.total_input}, 唯一: {result.total_unique}, 重复: {result.total_duplicates}")
```

### 模糊去重

```python
from solocoder_py.dedup import DedupEngine, STRATEGY_LONGEST_STRING

engine = DedupEngine(
    use_fuzzy=True,
    fuzzy_fields=["name", "address"],
    fuzzy_threshold=0.75,
    fuzzy_field_weights={"name": 2, "address": 1},
    merge_strategy=STRATEGY_LONGEST_STRING,
)

engine.add_records([
    {"name": "阿里巴巴", "address": "杭州市文一西路"},
    {"name": "阿里吧吧", "address": "杭州市文一西路969号"},
    {"name": "腾讯", "address": "深圳市科技园"},
])

result = engine.dedup()
for group in result.groups:
    if len(group.records) > 1:
        print(f"发现模糊重复组，匹配度: {group.match_score:.2f}")
        for r in group.records:
            print(f"  - {r['name']}")
```

### 混合模式 + 字段级策略

```python
from solocoder_py.dedup import (
    DedupEngine,
    STRATEGY_LAST,
    STRATEGY_LONGEST_STRING,
    STRATEGY_MOST_COMMON,
)

engine = DedupEngine(
    exact_match_keys=["dept"],
    use_fuzzy=True,
    fuzzy_fields=["name"],
    fuzzy_threshold=0.6,
    merge_strategy=STRATEGY_LAST,
    field_merge_strategies={
        "name": STRATEGY_LONGEST_STRING,
        "title": STRATEGY_MOST_COMMON,
    },
)
```

### 自定义合并

```python
from solocoder_py.dedup import DedupEngine, STRATEGY_CUSTOM

def merge_tags(field, values):
    if field == "tags":
        merged = set()
        for v in values:
            if isinstance(v, list):
                merged.update(v)
        return sorted(merged)
    return values[0]

engine = DedupEngine(
    exact_match_keys=["user_id"],
    merge_strategy=STRATEGY_CUSTOM,
    custom_merge=merge_tags,
)
```

## MinHash + LSH 模糊文本去重

除了基于记录字段的去重引擎外，本模块还提供了基于 **MinHash** 和 **LSH (Locality Sensitive Hashing)** 算法的纯文本近似去重功能，适用于大规模文本数据的高效去重场景。

### 核心原理

#### 1. MinHash 签名计算

MinHash 是一种用于快速估计集合相似度（Jaccard 相似度）的概率数据结构：

- **N-Gram 分词**：将输入文本切分为 N 个字符的子串集合（如 3-Gram）
- **多个哈希函数**：使用 K 个独立的哈希函数对每个 N-Gram 进行哈希
- **最小哈希签名**：对每个哈希函数，取所有 N-Gram 哈希值中的最小值，组成长度为 K 的签名向量

MinHash 的核心性质：两个集合的 MinHash 签名中对应位置相等的概率，等于它们的 Jaccard 相似度。

#### 2. LSH 分桶

LSH (Locality Sensitive Hashing) 通过分桶策略大幅减少需要比较的文本对数量：

- **Band 切分**：将 MinHash 签名向量按行切分为 B 个 band，每个包含 R 行（K = B × R）
- **分桶哈希**：对每个 band 内的子向量独立计算哈希值，哈希到同一个桶的文本互为候选相似对
- **概率保证**：两条文本只要在任意一个 band 中被哈希到相同的桶，即被判定为候选相似对

通过调整 B 和 R 的比例，可以在召回率和精确率之间权衡：
- 更多 band → 更高召回率（更容易命中相似文本）
- 更多行/band → 更高精确率（减少误判）

#### 3. 相似度阈值筛选与规范代表选优

- **精确 Jaccard 计算**：对 LSH 产生的候选对，基于原始 N-Gram 集合计算精确的 Jaccard 相似度
- **阈值过滤**：仅保留相似度超过可配置阈值的配对
- **传递性聚类**：使用并查集算法将相似文本聚合成簇
- **规范代表选优**：在每组相似文本簇中自动选出一条文本作为规范代表

### 规范代表选优策略

| 策略常量 | 说明 |
|----------|------|
| `REP_STRATEGY_FIRST` | 选择最早出现的文本（默认） |
| `REP_STRATEGY_LONGEST` | 选择长度最长的文本 |
| `REP_STRATEGY_SHORTEST` | 选择长度最短的文本 |
| `REP_STRATEGY_MIDDLE_LENGTH` | 选择长度居中的文本 |
| `REP_STRATEGY_CUSTOM` | 使用用户提供的评分函数，选择得分最高的 |

### 核心类

#### `MinHash`

MinHash 签名计算器。

主要方法：
- `compute_signature(text)`：计算文本的 MinHash 签名
- `compute_signature_from_tokens(tokens)`：从 N-Gram 集合计算签名
- `jaccard_from_signatures(sig_a, sig_b)`：从签名估计 Jaccard 相似度

配置参数：
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `num_perm` | `int` | 128 | 哈希函数数量（签名长度） |
| `n` | `int` | 3 | N-Gram 的 N 值 |
| `seed` | `int` | 42 | 随机种子，保证可复现 |

#### `MinHashLSH`

LSH 分桶索引。

主要方法：
- `insert(idx, signature)`：插入一条文本的签名
- `query(signature)`：查询与给定签名相似的候选文本索引
- `get_candidate_pairs()`：获取所有候选相似对
- `clear()`：清空所有数据

配置参数：
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `num_perm` | `int` | 128 | MinHash 签名长度 |
| `num_bands` | `int \| None` | None | band 数量，与 threshold 二选一 |
| `threshold` | `float \| None` | 0.8 | 相似度阈值，用于自动计算 band 配置 |

#### `TextDedupEngine`

文本去重引擎主类，整合 MinHash + LSH + Jaccard 精确计算 + 规范代表选优。

主要方法：
- `add_text(text)`：添加单条文本，返回索引
- `add_texts(texts)`：批量添加文本，返回索引列表
- `dedup()`：执行去重，返回 `TextDedupResult`
- `clear()`：清空所有数据

配置参数：
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `num_perm` | `int` | 128 | MinHash 签名长度 |
| `n` | `int` | 3 | N-Gram 的 N 值 |
| `threshold` | `float` | 0.8 | Jaccard 相似度阈值 |
| `num_bands` | `int \| None` | None | LSH band 数量 |
| `representative_strategy` | `str` | `REP_STRATEGY_FIRST` | 规范代表选优策略 |
| `custom_score_fn` | `Callable[[str, int], float] \| None` | None | 自定义评分函数 |
| `seed` | `int` | 42 | 随机种子 |

### 数据模型

#### `TextDedupCluster`

相似文本簇。

| 字段 | 类型 | 说明 |
|------|------|------|
| `representative` | `str` | 规范代表文本 |
| `rep_index` | `int` | 规范代表的原始索引 |
| `members` | `list[str]` | 簇内所有成员文本 |
| `member_indices` | `list[int]` | 所有成员的原始索引 |
| `similarities` | `dict[tuple[int, int], float]` | 成员两两之间的精确相似度 |
| `avg_similarity` | `float` | 簇内平均相似度 |

#### `TextDedupResult`

文本去重结果。

| 字段 | 类型 | 说明 |
|------|------|------|
| `clusters` | `list[TextDedupCluster]` | 所有相似文本簇 |
| `total_input` | `int` | 输入文本总数 |
| `total_clusters` | `int` | 聚类后簇的数量 |
| `total_duplicates` | `int` | 重复文本数量 |
| `unique_texts` | `list[str]` | 去重后的唯一文本列表（各簇代表） |
| `unique_indices` | `list[int]` | 唯一文本的原始索引列表 |

### 使用示例

#### 基本文本去重

```python
from solocoder_py.dedup import TextDedupEngine

engine = TextDedupEngine(
    num_perm=128,
    n=3,
    threshold=0.8,
)

texts = [
    "这是一段测试文本，用于测试去重功能",
    "这是一段测试文本，用于测试去重功能！",  # 高度相似
    "这是另一段完全不同的文本内容",
    "这是一段测试文本，用于测试去重功能。",  # 高度相似
    "另外一个无关的句子",
]

engine.add_texts(texts)
result = engine.dedup()

print(f"输入: {result.total_input}")
print(f"去重后: {result.total_clusters}")
print(f"重复数: {result.total_duplicates}")

for i, cluster in enumerate(result.clusters):
    print(f"\n簇 {i}:")
    print(f"  代表: {cluster.representative}")
    print(f"  成员数: {len(cluster.members)}")
    print(f"  平均相似度: {cluster.avg_similarity:.2f}")
```

#### 使用自定义规范代表选优策略

```python
from solocoder_py.dedup import (
    TextDedupEngine,
    REP_STRATEGY_LONGEST,
    REP_STRATEGY_CUSTOM,
)

# 选择最长的文本作为代表
engine = TextDedupEngine(
    threshold=0.7,
    representative_strategy=REP_STRATEGY_LONGEST,
)

# 使用自定义评分函数
def score_text(text, idx):
    # 假设越早出现的文本质量越高，同时文本长度也有加成
    return -idx + len(text) * 0.01

engine2 = TextDedupEngine(
    threshold=0.7,
    representative_strategy=REP_STRATEGY_CUSTOM,
    custom_score_fn=score_text,
)
```

#### 直接使用 MinHash 和 LSH

```python
from solocoder_py.dedup import MinHash, MinHashLSH, jaccard_similarity, ngram_tokens

# N-Gram 分词
tokens = ngram_tokens("hello world", n=3)
print(tokens)  # {'hel', 'ell', 'llo', 'lo ', 'o w', ' wo', 'wor', 'orl', 'rld'}

# 计算 MinHash 签名
minhash = MinHash(num_perm=128, n=3)
sig1 = minhash.compute_signature("hello world")
sig2 = minhash.compute_signature("hello word")

# 从签名估计 Jaccard 相似度
est_sim = MinHash.jaccard_from_signatures(sig1, sig2)

# 精确 Jaccard 相似度
tokens1 = ngram_tokens("hello world", n=3)
tokens2 = ngram_tokens("hello word", n=3)
exact_sim = jaccard_similarity(tokens1, tokens2)

# 使用 LSH 索引
lsh = MinHashLSH(num_perm=128, threshold=0.8)
lsh.insert(0, sig1)
lsh.insert(1, sig2)

candidates = lsh.query(sig1)  # 查询与 sig1 相似的文本索引
pairs = lsh.get_candidate_pairs()  # 获取所有候选对
```

### 性能与精度权衡

- **签名长度 `num_perm`**：
  - 越大 → 相似度估计越精确，内存占用越高，计算越慢
  - 推荐值：64-256，默认 128

- **N-Gram 的 N 值**：
  - 越大 → 对细微差异更敏感，适合短文本
  - 越小 → 容错性更强，适合长文本
  - 推荐值：2-5，默认 3

- **相似度阈值 `threshold`**：
  - 越高 → 去重越严格，漏判越多（召回率低）
  - 越低 → 去重越宽松，误判越多（精确率低）
  - 根据业务需求调整，默认 0.8

### 子模块

- `min_hash`：MinHash 签名计算、N-Gram 分词、Jaccard 相似度
- `lsh`：LSH 分桶索引
- `text_dedup`：文本去重引擎，整合所有功能
- `exceptions`：异常类定义

## 异常说明

- `InvalidConfigError`：配置无效
- `EmptyMatchKeysError`：匹配键为空
- `InvalidThresholdError`：阈值无效
- `UnknownStrategyError`：未知的合并策略
- `MergeConflictError`：合并冲突错误
