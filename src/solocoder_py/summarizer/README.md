# Text Summarizer

基于词频和句子打分的抽取式文本摘要器。

## 功能概述

该模块实现了一个简单但有效的抽取式文本摘要系统，通过以下核心策略从原文中选取最重要的句子组成摘要：

1. **基于词频的句子打分**：统计文本中各单词的出现频率，过滤停用词后，为每个句子计算基础得分。
2. **位置加权**：根据句子在原文中的位置给予加权，开头和结尾的句子权重更高。
3. **冗余度惩罚**：在选取摘要句子时，对与已选句子内容重复度高的候选句子进行惩罚，避免摘要内容冗余。

## 核心类职责

### `TextSummarizer`
摘要器主类，负责执行完整的摘要流程。可通过配置对象或构造参数自定义各阶段的行为。

主要方法：
- `summarize(text, num_sentences=None) -> list[str]`：生成文本摘要，返回选中的句子列表（按原文顺序）。
- `summarize_with_scores(text, num_sentences=None) -> list[SentenceScore]`：生成摘要并返回每个句子的详细打分信息。

### `Summarizer`
便捷函数，无需创建实例直接调用。

## 句子打分策略

### 1. 词频打分
- 将输入文本按句子分割（支持中英文标点符号）。
- 使用 Tokenizer 对每个句子进行分词。
- 过滤停用词（英文和中文停用词，支持自定义额外停用词）。
- 统计全文单词词频。
- 每个句子的词频得分 = 句子内所有有效单词的词频之和 / 句子有效单词数。
  - 除以句子长度的目的是避免长句子因包含更多单词而天然获得高分。

### 2. 位置加权
位置权重根据句子在原文中的位置计算，衰减方式可配置：

- **`PositionDecayType.LINEAR**（默认）：线性衰减
  - 句子越靠近中间，权重越低；两端权重最高。
  - `position_weight_factor` 控制最低权重（默认 1.0 表示无衰减）。

- **`PositionDecayType.EXPONENTIAL**：指数衰减
  - 使用指数函数进行衰减，中间部分衰减更快。
  - `exponential_decay_rate` 控制衰减速率。

- **`PositionDecayType.NONE**：不进行位置加权。

最终句子得分 = 词频得分 × 位置权重。

## 冗余度惩罚机制

在按得分从高到低选取句子时，每选中一个句子后：

1. 对剩余候选句子计算与已选句子集合的相似度。
2. 相似度计算方式（可配置）：
   - **`SimilarityMetric.JACCARD**（默认）：Jaccard 相似度 = |A ∩ B| / |A ∪ B|
   - **`SimilarityMetric.SHARED_RATIO**：共享词比例 = |A ∩ B| / min(|A|, |B|)
3. 如果相似度超过 `similarity_threshold`（默认 0.5），则对该候选句得分乘以 `(1 - redundancy_penalty)` 进行惩罚。
4. 重新排序后继续选取下一句，直到选够指定数量。

## 使用示例

### 基本用法

```python
from solocoder_py.summarizer import summarize_text

text = """Artificial intelligence is transforming the way we work and live.
Machine learning algorithms can process vast amounts of data quickly.
Deep learning has achieved remarkable results in image recognition.
Natural language processing enables computers to understand human language.
The future of AI holds great promise for solving complex problems."""

summary = summarize_text(text, num_sentences=2)
# 返回最重要的 2 个句子
```

### 使用 TextSummarizer 类

```python
from solocoder_py.summarizer import (
    TextSummarizer,
    SummarizerConfig,
    PositionDecayType,
    SimilarityMetric,
)

config = SummarizerConfig(
    num_sentences=3,
    position_decay=PositionDecayType.EXPONENTIAL,
    position_weight_factor=0.3,
    exponential_decay_rate=0.8,
    similarity_metric=SimilarityMetric.JACCARD,
    similarity_threshold=0.4,
    redundancy_penalty=0.6,
)

summarizer = TextSummarizer(config)
summary = summarizer.summarize(text)
```

### 获取详细打分信息

```python
from solocoder_py.summarizer import TextSummarizer

summarizer = TextSummarizer()
scores = summarizer.summarize_with_scores(text, num_sentences=3)
for s in scores:
    print(f"句子 {s.index}: {s.text}")
    print(f"  词频得分: {s.frequency_score:.4f}")
    print(f"  位置权重: {s.position_weight:.4f}")
    print(f"  最终得分: {s.final_score:.4f}")
```

### 中文文本摘要

```python
from solocoder_py.summarizer import summarize_text

cn_text = """人工智能正在改变我们的工作和生活方式。
机器学习算法能够快速处理大量数据。
深度学习在图像识别方面取得了显著成果。
自然语言处理使计算机能够理解人类语言。
人工智能的未来对于解决复杂问题具有广阔前景。"""

summary = summarize_text(cn_text, num_sentences=2)
```
