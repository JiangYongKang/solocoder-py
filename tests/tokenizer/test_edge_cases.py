from __future__ import annotations

import pytest

from solocoder_py.tokenizer import (
    ScriptType,
    UnicodeTokenizer,
    tokenize,
    tokenize_to_strings,
)


class TestEmptyInput:
    def test_empty_string_returns_empty_list(self, tokenizer):
        result = tokenizer.tokenize("")

        assert len(result) == 0
        assert result.tokens == []
        assert result.to_strings() == []
        assert result.detected_scripts == set()
        assert result.original_text == ""

    def test_empty_string_convenience_function(self):
        strings = tokenize_to_strings("")
        assert strings == []

        result = tokenize("")
        assert len(result) == 0


class TestWhitespaceOnly:
    def test_only_spaces(self, tokenizer):
        text = "     "
        result = tokenizer.tokenize(text)

        assert len(result) == 0
        assert result.to_strings() == []

    def test_only_newlines(self, tokenizer):
        text = "\n\n\n"
        result = tokenizer.tokenize(text)

        assert len(result) == 0

    def test_only_tabs(self, tokenizer):
        text = "\t\t\t"
        result = tokenizer.tokenize(text)

        assert len(result) == 0

    def test_mixed_whitespace(self, tokenizer):
        text = " \t\n \t\n"
        result = tokenizer.tokenize(text)

        assert len(result) == 0

    def test_include_whitespace(self, tokenizer_with_whitespace):
        text = "a b"
        result = tokenizer_with_whitespace.tokenize(text)
        strings = result.to_strings()

        assert " " in strings
        assert strings.index(" ") == 1


class TestPunctuationOnly:
    def test_only_punctuation(self, tokenizer, sample_punctuation_text):
        result = tokenizer.tokenize(sample_punctuation_text)

        assert len(result) > 0
        for token in result.tokens:
            assert token.script == ScriptType.PUNCTUATION

    def test_each_punctuation_is_separate(self, tokenizer):
        text = ",,,"
        result = tokenizer.tokenize(text)

        assert len(result) == 3
        assert result.to_strings() == [",", ",", ","]

    def test_mixed_punctuation(self, tokenizer):
        text = "，。！？"
        result = tokenizer.tokenize(text)

        assert len(result) == 4
        assert result.to_strings() == ["，", "。", "！", "？"]

    def test_mixed_chinese_english_punctuation(self, tokenizer):
        text = "，,。.！!"
        result = tokenizer.tokenize(text)

        assert len(result) == 6
        expected = ["，", ",", "。", ".", "！", "!"]
        assert result.to_strings() == expected

    def test_no_punctuation_mode(self, tokenizer_no_punctuation):
        text = "你好，世界！"
        result = tokenizer_no_punctuation.tokenize(text)
        strings = result.to_strings()

        assert "，" not in strings
        assert "！" not in strings
        assert "你" in strings
        assert "好" in strings
        assert "世" in strings
        assert "界" in strings


class TestLongText:
    def test_very_long_cjk(self, tokenizer, long_cjk_text):
        result = tokenizer.tokenize(long_cjk_text)

        assert len(result) == 1000
        for token in result.tokens:
            assert token.text == "中"
            assert token.script == ScriptType.CJK

    def test_long_mixed_text(self, tokenizer):
        text = "你好World" * 100
        result = tokenizer.tokenize(text)

        assert len(result) == 300
        cjk_count = sum(1 for t in result.tokens if t.script == ScriptType.CJK)
        latin_count = sum(1 for t in result.tokens if t.script == ScriptType.LATIN)

        assert cjk_count == 200
        assert latin_count == 100

    def test_long_english_text(self, tokenizer):
        text = "Hello " * 1000
        result = tokenizer.tokenize(text)

        assert len(result) == 1000
        for token in result.tokens:
            assert token.text == "Hello"
            assert token.script == ScriptType.LATIN

    def test_tokenization_duration(self, tokenizer, long_cjk_text):
        result = tokenizer.tokenize(long_cjk_text)

        assert result.duration_ms is not None
        assert result.duration_ms >= 0


class TestUnicodeEdgeCases:
    def test_fullwidth_letters(self, tokenizer):
        text = "Ｈｅｌｌｏ Ｗｏｒｌｄ"
        result = tokenizer.tokenize(text)
        strings = result.to_strings()

        assert len(strings) == 2
        assert strings[0] == "Ｈｅｌｌｏ"
        assert strings[1] == "Ｗｏｒｌｄ"
        assert result.tokens[0].script == ScriptType.LATIN

    def test_fullwidth_numbers(self, tokenizer):
        text = "１２３ ４５６"
        result = tokenizer.tokenize(text)
        strings = result.to_strings()

        assert len(strings) == 2
        assert strings[0] == "１２３"
        assert strings[1] == "４５６"
        assert result.tokens[0].script == ScriptType.NUMBER

    def test_cjk_extension_a(self, tokenizer):
        char = "\u3400"
        text = f"{char}测试"
        result = tokenizer.tokenize(text)

        assert len(result) == 3
        assert result.tokens[0].script == ScriptType.CJK
        assert result.tokens[0].text == char

    def test_cjk_compatibility(self, tokenizer):
        char = "\uF900"
        text = f"{char}测试"
        result = tokenizer.tokenize(text)

        assert len(result) == 3
        assert result.tokens[0].script == ScriptType.CJK


class TestResultIteration:
    def test_iterate_over_tokens(self, tokenizer, sample_chinese_text):
        result = tokenizer.tokenize(sample_chinese_text)

        texts = []
        for token in result:
            texts.append(token.text)

        assert texts == ["我", "爱", "北", "京", "天", "安", "门"]

    def test_index_access(self, tokenizer, sample_chinese_text):
        result = tokenizer.tokenize(sample_chinese_text)

        assert result[0].text == "我"
        assert result[-1].text == "门"

    def test_slice_access(self, tokenizer, sample_chinese_text):
        result = tokenizer.tokenize(sample_chinese_text)

        slice_tokens = result[1:4]
        assert len(slice_tokens) == 3
        assert slice_tokens[0].text == "爱"


class TestDetectedScripts:
    def test_mixed_scripts_detected(self, tokenizer):
        text = "你好HelloПривет"
        result = tokenizer.tokenize(text)

        assert ScriptType.CJK in result.detected_scripts
        assert ScriptType.LATIN in result.detected_scripts
        assert ScriptType.CYRILLIC in result.detected_scripts

    def test_only_cjk(self, tokenizer, sample_chinese_text):
        result = tokenizer.tokenize(sample_chinese_text)

        assert result.detected_scripts == {ScriptType.CJK}

    def test_only_latin(self, tokenizer, sample_english_text):
        result = tokenizer.tokenize(sample_english_text)

        assert ScriptType.LATIN in result.detected_scripts

    def test_punctuation_in_detected_scripts(self, tokenizer):
        text = "你好，"
        result = tokenizer.tokenize(text)

        assert ScriptType.PUNCTUATION in result.detected_scripts
