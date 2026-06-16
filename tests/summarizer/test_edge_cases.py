from __future__ import annotations

import pytest

from solocoder_py.summarizer import TextSummarizer, SummarizerConfig


class TestFewerSentencesThanRequested:
    def test_returns_all_sentences_when_fewer_than_requested(self, default_summarizer):
        text = "First sentence. Second sentence."
        result = default_summarizer.summarize(text, num_sentences=5)
        assert len(result) == 2

    def test_returns_all_sentences_exact_match(self, default_summarizer):
        text = "One. Two. Three."
        result = default_summarizer.summarize(text, num_sentences=3)
        assert len(result) == 3

    def test_all_sentences_with_scores(self, default_summarizer):
        text = "First. Second."
        scores = default_summarizer.summarize_with_scores(text, num_sentences=10)
        assert len(scores) == 2


class TestSingleSentence:
    def test_single_sentence_returns_itself(self, default_summarizer):
        text = "This is a single sentence."
        result = default_summarizer.summarize(text, num_sentences=3)
        assert len(result) == 1
        assert result[0] == "This is a single sentence."

    def test_single_sentence_with_scores(self, default_summarizer):
        text = "Only one sentence here."
        scores = default_summarizer.summarize_with_scores(text, num_sentences=5)
        assert len(scores) == 1
        assert scores[0].index == 0


class TestHighStopwordRatio:
    def test_text_with_mostly_stopwords(self, default_summarizer):
        text = (
            "The is a of and. "
            "This that these those. "
            "Important keywords data analysis here. "
            "Is are was were be."
        )
        result = default_summarizer.summarize(text, num_sentences=1)
        assert len(result) == 1
        assert "Important keywords data analysis here" in result[0]

    def test_stopwords_only_text(self, default_summarizer):
        text = "The is a of and. This that these those. Is are was were be."
        result = default_summarizer.summarize(text, num_sentences=2)
        assert len(result) == 2

    def test_extra_stopwords_config(self):
        text = (
            "Customword appears here often. "
            "Important data machine learning. "
            "Another customword sentence here."
        )
        config = SummarizerConfig(
            extra_stopwords={"customword"},
        )
        summarizer = TextSummarizer(config)
        result = summarizer.summarize(text, num_sentences=1)
        assert len(result) == 1


class TestVariousTextFormats:
    def test_text_with_multiple_paragraphs(self, default_summarizer):
        text = """First paragraph starts here.
It has multiple sentences within it.

Second paragraph begins after a blank line.
This paragraph also contains several sentences.

Third paragraph concludes the document."""
        result = default_summarizer.summarize(text, num_sentences=2)
        assert len(result) == 2

    def test_text_with_various_punctuation(self, default_summarizer):
        text = "Hello! How are you? I am fine. This is great!"
        result = default_summarizer.summarize(text, num_sentences=2)
        assert len(result) == 2

    def test_chinese_with_punctuation(self, default_summarizer):
        text = "你好！你好吗？我很好。今天天气不错！"
        result = default_summarizer.summarize(text, num_sentences=2)
        assert len(result) == 2

    def test_mixed_language_text(self, default_summarizer):
        text = (
            "Machine learning is important. "
            "机器学习非常重要。 "
            "Both languages should work fine together."
        )
        result = default_summarizer.summarize(text, num_sentences=2)
        assert len(result) == 2

    def test_zero_sentences_requested(self, default_summarizer):
        text = "Some text with content. Another sentence here."
        result = default_summarizer.summarize(text, num_sentences=0)
        assert result == []

    def test_zero_sentences_with_scores(self, default_summarizer):
        text = "Some text here."
        result = default_summarizer.summarize_with_scores(text, num_sentences=0)
        assert result == []


class TestWhitespaceOnly:
    def test_whitespace_only_returns_empty(self, default_summarizer):
        text = "   \n\t   "
        result = default_summarizer.summarize(text, num_sentences=3)
        assert result == []

    def test_whitespace_with_scores(self, default_summarizer):
        text = "  \n  "
        scores = default_summarizer.summarize_with_scores(text, num_sentences=3)
        assert scores == []
