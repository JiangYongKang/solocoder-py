from __future__ import annotations

import pytest

from solocoder_py.summarizer import (
    PositionDecayType,
    SimilarityMetric,
    SummarizerConfig,
    SummarizerInvalidInputError,
    SummarizerInvalidParameterError,
    TextSummarizer,
    summarize_text,
)


class TestNoneInput:
    def test_none_text_raises_error(self, default_summarizer):
        with pytest.raises(SummarizerInvalidInputError, match="cannot be None"):
            default_summarizer.summarize(None)

    def test_none_text_with_scores_raises_error(self, default_summarizer):
        with pytest.raises(SummarizerInvalidInputError, match="cannot be None"):
            default_summarizer.summarize_with_scores(None)

    def test_none_text_function_raises_error(self):
        with pytest.raises(SummarizerInvalidInputError):
            summarize_text(None)


class TestEmptyText:
    def test_empty_string_returns_empty_list(self, default_summarizer):
        result = default_summarizer.summarize("")
        assert result == []

    def test_empty_string_with_scores(self, default_summarizer):
        result = default_summarizer.summarize_with_scores("")
        assert result == []

    def test_empty_string_function(self):
        result = summarize_text("")
        assert result == []


class TestNegativeNumSentences:
    def test_negative_num_sentences_in_summarize_raises(self, default_summarizer):
        with pytest.raises(
            SummarizerInvalidParameterError, match="non-negative"
        ):
            default_summarizer.summarize("Some text.", num_sentences=-1)

    def test_negative_num_sentences_in_with_scores_raises(self, default_summarizer):
        with pytest.raises(
            SummarizerInvalidParameterError, match="non-negative"
        ):
            default_summarizer.summarize_with_scores("Text.", num_sentences=-5)

    def test_negative_num_sentences_function_raises(self):
        with pytest.raises(SummarizerInvalidParameterError):
            summarize_text("Some text.", num_sentences=-3)


class TestInvalidConfigParameters:
    def test_invalid_num_sentences_in_config(self):
        with pytest.raises(SummarizerInvalidParameterError):
            config = SummarizerConfig(num_sentences=-1)
            TextSummarizer(config)

    def test_invalid_similarity_threshold_too_high(self):
        with pytest.raises(SummarizerInvalidParameterError):
            config = SummarizerConfig(similarity_threshold=1.5)
            TextSummarizer(config)

    def test_invalid_similarity_threshold_negative(self):
        with pytest.raises(SummarizerInvalidParameterError):
            config = SummarizerConfig(similarity_threshold=-0.1)
            TextSummarizer(config)

    def test_invalid_redundancy_penalty_too_high(self):
        with pytest.raises(SummarizerInvalidParameterError):
            config = SummarizerConfig(redundancy_penalty=1.1)
            TextSummarizer(config)

    def test_invalid_redundancy_penalty_negative(self):
        with pytest.raises(SummarizerInvalidParameterError):
            config = SummarizerConfig(redundancy_penalty=-0.5)
            TextSummarizer(config)

    def test_invalid_position_weight_factor_too_high(self):
        with pytest.raises(SummarizerInvalidParameterError):
            config = SummarizerConfig(position_weight_factor=1.5)
            TextSummarizer(config)

    def test_invalid_position_weight_factor_negative(self):
        with pytest.raises(SummarizerInvalidParameterError):
            config = SummarizerConfig(position_weight_factor=-0.3)
            TextSummarizer(config)

    def test_invalid_exponential_decay_rate_zero(self):
        with pytest.raises(SummarizerInvalidParameterError):
            config = SummarizerConfig(exponential_decay_rate=0)
            TextSummarizer(config)

    def test_invalid_exponential_decay_rate_negative(self):
        with pytest.raises(SummarizerInvalidParameterError):
            config = SummarizerConfig(exponential_decay_rate=-0.5)
            TextSummarizer(config)


class TestAllStopwordsText:
    def test_all_stopwords_returns_all_sentences(self, default_summarizer):
        text = "The is a of. And but or if. This that these those."
        result = default_summarizer.summarize(text, num_sentences=2)
        assert len(result) == 2

    def test_all_stopwords_with_scores_returns_zero_freq(self, default_summarizer):
        text = "The is a of. And but or if."
        scores = default_summarizer.summarize_with_scores(text, num_sentences=2)
        assert len(scores) == 2
        for s in scores:
            assert s.frequency_score == 0.0
            assert s.final_score == 0.0


class TestConfigProperty:
    def test_config_property_returns_copy(self):
        config = SummarizerConfig(
            num_sentences=5,
            position_decay=PositionDecayType.EXPONENTIAL,
        )
        summarizer = TextSummarizer(config)
        returned_config = summarizer.config
        assert returned_config.num_sentences == 5
        assert returned_config.position_decay == PositionDecayType.EXPONENTIAL
        returned_config.num_sentences = 999
        assert summarizer.config.num_sentences == 5
