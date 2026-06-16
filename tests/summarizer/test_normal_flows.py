from __future__ import annotations

import pytest

from solocoder_py.summarizer import (
    PositionDecayType,
    SimilarityMetric,
    SummarizerConfig,
    TextSummarizer,
    summarize_text,
)


MULTI_PARAGRAPH_TEXT = """Artificial intelligence is transforming industries worldwide.
Machine learning models analyze vast datasets to identify patterns.
Deep learning neural networks achieve state-of-the-art results.
Natural language processing enables human-computer communication.
Computer vision systems interpret visual information from images.
Robotics combines AI with physical hardware for automation.
Reinforcement learning agents learn through trial and error.
Generative AI creates new content from learned patterns.
The ethical implications of AI require careful consideration.
Future AI systems may surpass human cognitive capabilities."""


CN_MULTI_PARAGRAPH_TEXT = """人工智能正在全球范围内改变各个行业。
机器学习模型分析海量数据集以识别模式。
深度学习神经网络实现了最先进的结果。
自然语言处理实现了人机交流。
计算机视觉系统从图像中解释视觉信息。
机器人技术将人工智能与物理硬件结合实现自动化。
强化学习智能体通过试错进行学习。
生成式人工智能从学习到的模式中创建新内容。
人工智能的伦理影响需要仔细考虑。
未来的人工智能系统可能会超越人类的认知能力。"""


class TestMultiParagraphSummary:
    def test_english_summary_returns_correct_count(self, default_summarizer):
        result = default_summarizer.summarize(MULTI_PARAGRAPH_TEXT, num_sentences=3)
        assert len(result) == 3

    def test_chinese_summary_returns_correct_count(self, default_summarizer):
        result = default_summarizer.summarize(CN_MULTI_PARAGRAPH_TEXT, num_sentences=3)
        assert len(result) == 3

    def test_summary_sentences_are_from_original(self, default_summarizer):
        sentences = [s.strip() for s in MULTI_PARAGRAPH_TEXT.split("\n") if s.strip()]
        result = default_summarizer.summarize(MULTI_PARAGRAPH_TEXT, num_sentences=3)
        for sentence in result:
            assert sentence in sentences

    def test_summary_preserves_original_order(self, default_summarizer):
        sentences = [s.strip() for s in MULTI_PARAGRAPH_TEXT.split("\n") if s.strip()]
        result = default_summarizer.summarize(MULTI_PARAGRAPH_TEXT, num_sentences=3)
        indices = [sentences.index(s) for s in result]
        assert indices == sorted(indices)

    def test_summarize_text_function_works(self):
        result = summarize_text(MULTI_PARAGRAPH_TEXT, num_sentences=2)
        assert len(result) == 2


class TestPositionWeighting:
    def test_first_sentence_gets_high_weight(self):
        text = (
            "The quick brown fox jumps over the lazy dog. "
            "This is a middle sentence with some content. "
            "Another middle sentence appears here. "
            "The final sentence wraps up the discussion."
        )
        config = SummarizerConfig(
            num_sentences=1,
            position_decay=PositionDecayType.LINEAR,
            position_weight_factor=0.5,
            redundancy_penalty=0.0,
        )
        summarizer = TextSummarizer(config)
        scores = summarizer.summarize_with_scores(text, num_sentences=4)
        first_pos_weight = scores[0].position_weight
        last_pos_weight = scores[-1].position_weight
        middle_pos_weight = scores[1].position_weight
        assert first_pos_weight >= middle_pos_weight
        assert last_pos_weight >= middle_pos_weight

    def test_exponential_decay_position_weight(self):
        text = (
            "First sentence with important keywords. "
            "Second sentence with some content. "
            "Third sentence with more text. "
            "Fourth sentence here too. "
            "Fifth sentence at the end."
        )
        config = SummarizerConfig(
            num_sentences=5,
            position_decay=PositionDecayType.EXPONENTIAL,
            position_weight_factor=0.2,
            exponential_decay_rate=1.0,
        )
        summarizer = TextSummarizer(config)
        scores = summarizer.summarize_with_scores(text, num_sentences=5)
        assert scores[0].position_weight > scores[2].position_weight
        assert scores[-1].position_weight > scores[2].position_weight

    def test_none_decay_returns_uniform_weight(self):
        text = (
            "First sentence. "
            "Second sentence. "
            "Third sentence. "
            "Fourth sentence."
        )
        config = SummarizerConfig(
            num_sentences=4,
            position_decay=PositionDecayType.NONE,
        )
        summarizer = TextSummarizer(config)
        scores = summarizer.summarize_with_scores(text, num_sentences=4)
        for s in scores:
            assert s.position_weight == 1.0


class TestRedundancyPenalty:
    def test_redundant_sentences_penalized(self):
        text = (
            "Machine learning algorithms process data efficiently. "
            "Machine learning algorithms process data efficiently. "
            "Natural language processing understands human speech. "
            "Computer vision recognizes objects in images."
        )
        config_high_penalty = SummarizerConfig(
            num_sentences=3,
            similarity_threshold=0.3,
            redundancy_penalty=0.9,
            position_decay=PositionDecayType.NONE,
        )
        config_no_penalty = SummarizerConfig(
            num_sentences=3,
            similarity_threshold=1.0,
            redundancy_penalty=0.0,
            position_decay=PositionDecayType.NONE,
        )
        summarizer_high = TextSummarizer(config_high_penalty)
        summarizer_no = TextSummarizer(config_no_penalty)

        result_high = summarizer_high.summarize(text, num_sentences=3)
        result_no = summarizer_no.summarize(text, num_sentences=3)

        duplicate_count_high = len(result_high) - len(set(result_high))
        duplicate_count_no = len(result_no) - len(set(result_no))
        assert duplicate_count_high <= duplicate_count_no

    def test_jaccard_similarity_metric(self):
        text = (
            "Deep learning neural networks process data. "
            "Neural networks deep learning process data. "
            "Reinforcement learning uses rewards and actions."
        )
        config = SummarizerConfig(
            num_sentences=2,
            similarity_metric=SimilarityMetric.JACCARD,
            similarity_threshold=0.5,
            redundancy_penalty=0.8,
            position_decay=PositionDecayType.NONE,
        )
        summarizer = TextSummarizer(config)
        result = summarizer.summarize(text, num_sentences=2)
        assert len(set(result)) >= 2

    def test_shared_ratio_similarity_metric(self):
        text = (
            "Deep learning neural networks process complex data. "
            "Neural networks deep learning. "
            "Reinforcement learning uses reward-based training."
        )
        config = SummarizerConfig(
            num_sentences=2,
            similarity_metric=SimilarityMetric.SHARED_RATIO,
            similarity_threshold=0.5,
            redundancy_penalty=0.8,
            position_decay=PositionDecayType.NONE,
        )
        summarizer = TextSummarizer(config)
        result = summarizer.summarize(text, num_sentences=2)
        assert len(set(result)) >= 2


class TestSentenceScores:
    def test_summarize_with_scores_returns_details(self, default_summarizer):
        text = (
            "First sentence with keywords. "
            "Second sentence appears here. "
            "Third sentence ends the text."
        )
        scores = default_summarizer.summarize_with_scores(text, num_sentences=2)
        assert len(scores) == 2
        for s in scores:
            assert hasattr(s, "index")
            assert hasattr(s, "text")
            assert hasattr(s, "frequency_score")
            assert hasattr(s, "position_weight")
            assert hasattr(s, "final_score")
            assert hasattr(s, "tokens")
            assert s.final_score == pytest.approx(
                s.frequency_score * s.position_weight
            )

    def test_frequency_score_normalized_by_length(self):
        text = (
            "Important keyword appears. "
            "This longer sentence contains the important keyword along with other less meaningful words that should not unfairly inflate the score."
        )
        config = SummarizerConfig(
            position_decay=PositionDecayType.NONE,
        )
        summarizer = TextSummarizer(config)
        scores = summarizer.summarize_with_scores(text, num_sentences=2)
        short_freq = scores[0].frequency_score
        long_freq = scores[1].frequency_score
        assert short_freq > 0
        assert long_freq > 0
