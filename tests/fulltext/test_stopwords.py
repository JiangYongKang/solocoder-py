from __future__ import annotations

import pytest

from solocoder_py.fulltext import StopWords


class TestStopWordsNormalFlows:
    def test_default_english_stopwords(self):
        sw = StopWords()
        assert sw.is_stopword("the")
        assert sw.is_stopword("and")
        assert sw.is_stopword("is")
        assert sw.is_stopword("a")
        assert sw.is_stopword("an")
        assert sw.is_stopword("of")

    def test_default_chinese_stopwords(self):
        sw = StopWords()
        assert sw.is_stopword("的")
        assert sw.is_stopword("了")
        assert sw.is_stopword("和")
        assert sw.is_stopword("是")
        assert sw.is_stopword("在")

    def test_non_stopwords_not_detected(self):
        sw = StopWords()
        assert not sw.is_stopword("python")
        assert not sw.is_stopword("programming")
        assert not sw.is_stopword("计算机")
        assert not sw.is_stopword("编程")

    def test_case_insensitive_check(self):
        sw = StopWords()
        assert sw.is_stopword("The")
        assert sw.is_stopword("THE")
        assert sw.is_stopword("And")
        assert sw.is_stopword("AND")

    def test_filter_terms(self):
        sw = StopWords()
        terms = ["the", "quick", "brown", "fox", "jumps", "over", "a", "lazy", "dog"]
        filtered = sw.filter(terms)
        assert "the" not in filtered
        assert "a" not in filtered
        assert "over" not in filtered
        assert "quick" in filtered
        assert "brown" in filtered
        assert "fox" in filtered

    def test_filter_tokens(self):
        sw = StopWords()
        tokens = [
            ("the", 0),
            ("quick", 4),
            ("brown", 10),
            ("fox", 16),
            ("a", 20),
            ("dog", 22),
        ]
        filtered = sw.filter_tokens(tokens)
        filtered_terms = [t for t, _ in filtered]
        assert "the" not in filtered_terms
        assert "a" not in filtered_terms
        assert "quick" in filtered_terms
        positions = [p for _, p in filtered]
        assert 4 in positions
        assert 10 in positions

    def test_add_custom_stopword(self):
        sw = StopWords()
        assert not sw.is_stopword("custom")
        sw.add("custom")
        assert sw.is_stopword("custom")
        assert sw.is_stopword("CUSTOM")

    def test_remove_stopword(self):
        sw = StopWords()
        assert sw.is_stopword("the")
        sw.remove("the")
        assert not sw.is_stopword("the")

    def test_extra_stopwords_on_init(self):
        extra = {"custom1", "custom2", "测试词"}
        sw = StopWords(extra_stopwords=extra)
        assert sw.is_stopword("custom1")
        assert sw.is_stopword("custom2")
        assert sw.is_stopword("测试词")
        assert sw.is_stopword("the")


class TestStopWordsBoundaryConditions:
    def test_empty_extra_stopwords(self):
        sw = StopWords(extra_stopwords=set())
        assert sw.is_stopword("the")
        assert not sw.is_stopword("python")

    def test_remove_nonexistent_stopword_no_error(self):
        sw = StopWords()
        sw.remove("nonexistent_word_xyz")

    def test_filter_empty_list(self):
        sw = StopWords()
        assert sw.filter([]) == []
        assert sw.filter_tokens([]) == []

    def test_filter_all_stopwords(self):
        sw = StopWords()
        terms = ["the", "a", "an", "and", "is"]
        filtered = sw.filter(terms)
        assert filtered == []

    def test_stopwords_property(self):
        sw = StopWords()
        words = sw.stopwords
        assert "the" in words
        assert "的" in words
        sw.add("newword")
        assert "newword" in sw.stopwords


class TestStopWordsMultiCharChinese:
    def test_preprocess_text_multi_char_stopwords(self):
        sw = StopWords()
        processed = sw.preprocess_text("我们是一个测试")
        assert "我们" not in processed
        assert "一个" not in processed

    def test_preprocess_text_three_char_stopwords(self):
        sw = StopWords()
        processed = sw.preprocess_text("为什么这样")
        assert "为什么" not in processed

    def test_preprocess_text_combined_multi_char_stopwords(self):
        sw = StopWords()
        processed = sw.preprocess_text("我们为什么这个那个")
        assert "我们" not in processed
        assert "为什么" not in processed
        assert "这个" not in processed
        assert "那个" not in processed

    def test_preprocess_text_preserves_non_stopwords(self):
        sw = StopWords()
        processed = sw.preprocess_text("我们测试Python编程")
        assert "测试" in processed
        assert "编程" in processed
        assert "Python" in processed

    def test_preprocess_text_mixed_languages(self):
        sw = StopWords()
        processed = sw.preprocess_text("the 是我们")
        assert "the" not in processed
        assert "我们" not in processed

    def test_preprocess_text_empty(self):
        sw = StopWords()
        assert sw.preprocess_text("") == ""

    def test_preprocess_text_no_stopwords(self):
        sw = StopWords()
        result = sw.preprocess_text("Python 编程测试")
        assert "Python" in result
        assert "编程" in result
        assert "测试" in result

    def test_preprocess_text_longer_matches_first(self):
        sw = StopWords()
        processed = sw.preprocess_text("为什么")
        assert "为什么" not in processed

    def test_add_multi_char_custom_stopword_rebuilds_pattern(self):
        sw = StopWords()
        original = "这是测试词编程"
        processed_before = sw.preprocess_text(original)
        assert "测试词" in processed_before
        sw.add("测试词")
        processed_after = sw.preprocess_text(original)
        assert "测试词" not in processed_after

    def test_remove_multi_char_custom_stopword_rebuilds_pattern(self):
        sw = StopWords()
        sw.add("测试词")
        original = "这是测试词编程"
        processed_before = sw.preprocess_text(original)
        assert "测试词" not in processed_before
        sw.remove("测试词")
        processed_after = sw.preprocess_text(original)
        assert "测试词" in processed_after
