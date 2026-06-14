from __future__ import annotations

import pytest

from solocoder_py.fulltext import Tokenizer, tokenize


class TestTokenizerNormalFlows:
    def test_simple_english_sentence(self):
        text = "Hello world this is a test"
        result = tokenize(text)
        terms = [t for t, _ in result]
        assert "hello" in terms
        assert "world" in terms
        assert "test" in terms
        assert all(t == t.lower() for t in terms)

    def test_english_with_punctuation(self):
        text = "Hello, world! How are you?"
        result = tokenize(text)
        terms = [t for t, _ in result]
        assert "hello" in terms
        assert "world" in terms
        assert "how" in terms
        assert "are" in terms
        assert "you" in terms
        assert "," not in terms
        assert "!" not in terms

    def test_english_with_contractions(self):
        text = "don't won't can't it's"
        result = tokenize(text)
        terms = [t for t, _ in result]
        assert "don't" in terms
        assert "won't" in terms
        assert "can't" in terms
        assert "it's" in terms

    def test_chinese_text(self):
        text = "你好世界这是一个测试"
        result = tokenize(text)
        terms = [t for t, _ in result]
        assert len(terms) == 10
        assert "你" in terms
        assert "好" in terms
        assert "世" in terms
        assert "界" in terms
        assert "这" in terms
        assert "是" in terms
        assert "一" in terms
        assert "个" in terms
        assert "测" in terms
        assert "试" in terms

    def test_mixed_chinese_english(self):
        text = "你好 world 测试 Python"
        result = tokenize(text)
        terms = [t for t, _ in result]
        assert "你" in terms
        assert "好" in terms
        assert "world" in terms
        assert "测" in terms
        assert "试" in terms
        assert "python" in terms

    def test_mixed_with_punctuation(self):
        text = "Hello, 你好！World, 世界！"
        result = tokenize(text)
        terms = [t for t, _ in result]
        assert "hello" in terms
        assert "world" in terms
        assert "你" in terms
        assert "好" in terms
        assert "世" in terms
        assert "界" in terms

    def test_tokenizer_class(self):
        tokenizer = Tokenizer()
        text = "Hello world"
        result = tokenizer.tokenize(text)
        assert len(result) == 2
        terms = tokenizer.tokenize_terms(text)
        assert terms == ["hello", "world"]

    def test_digits(self):
        text = "There are 123 apples and 456 oranges"
        result = tokenize(text)
        terms = [t for t, _ in result]
        assert "123" in terms
        assert "456" in terms
        assert "apples" in terms

    def test_positions_recorded(self):
        text = "Hello world"
        result = tokenize(text)
        assert result[0][1] == 0
        assert result[1][1] == 6


class TestTokenizerBoundaryConditions:
    def test_empty_string(self):
        result = tokenize("")
        assert result == []

    def test_only_spaces(self):
        result = tokenize("     ")
        assert result == []

    def test_only_punctuation(self):
        result = tokenize("!!!???,,,")
        assert result == []

    def test_single_english_word(self):
        result = tokenize("Hello")
        assert len(result) == 1
        assert result[0][0] == "hello"

    def test_single_chinese_char(self):
        result = tokenize("好")
        assert len(result) == 1
        assert result[0][0] == "好"

    def test_mixed_spaces_and_punctuation(self):
        text = "  Hello,   world!  "
        result = tokenize(text)
        terms = [t for t, _ in result]
        assert terms == ["hello", "world"]

    def test_case_insensitive(self):
        text = "HELLO Hello hello"
        result = tokenize(text)
        terms = [t for t, _ in result]
        assert all(t == "hello" for t in terms)
