from __future__ import annotations

import pytest

from solocoder_py.tokenizer import (
    ScriptType,
    Token,
    UnicodeTokenizer,
    detect_script,
    tokenize,
    tokenize_to_strings,
)


class TestChineseTokenization:
    def test_pure_chinese_single_char_split(self, tokenizer, sample_chinese_text):
        result = tokenizer.tokenize(sample_chinese_text)

        assert len(result) == 7
        assert result.to_strings() == ["我", "爱", "北", "京", "天", "安", "门"]

        for token in result.tokens:
            assert token.script == ScriptType.CJK

    def test_chinese_with_punctuation(self, tokenizer):
        text = "你好，世界！"
        result = tokenizer.tokenize(text)
        strings = result.to_strings()

        assert "你" in strings
        assert "好" in strings
        assert "，" in strings
        assert "世" in strings
        assert "界" in strings
        assert "！" in strings

        punctuation_tokens = [t for t in result.tokens if t.script == ScriptType.PUNCTUATION]
        assert len(punctuation_tokens) == 2
        assert punctuation_tokens[0].text == "，"
        assert punctuation_tokens[1].text == "！"

    def test_chinese_token_positions(self, tokenizer):
        text = "我爱北京"
        result = tokenizer.tokenize(text)

        expected_positions = [
            (0, 1),
            (1, 2),
            (2, 3),
            (3, 4),
        ]

        for i, token in enumerate(result.tokens):
            assert token.start == expected_positions[i][0]
            assert token.end == expected_positions[i][1]


class TestEnglishTokenization:
    def test_pure_english_by_whitespace(self, tokenizer, sample_english_text):
        result = tokenizer.tokenize(sample_english_text)
        strings = result.to_strings()

        assert strings == ["Hello", "World", "from", "Unicode", "Tokenizer"]

        for token in result.tokens:
            assert token.script == ScriptType.LATIN

    def test_english_with_punctuation(self, tokenizer):
        text = "Hello, World!"
        result = tokenizer.tokenize(text)
        strings = result.to_strings()

        assert "Hello" in strings
        assert "," in strings
        assert "World" in strings
        assert "!" in strings

        word_tokens = [t for t in result.tokens if t.script == ScriptType.LATIN]
        assert len(word_tokens) == 2
        assert word_tokens[0].text == "Hello"
        assert word_tokens[1].text == "World"

    def test_english_numbers(self, tokenizer):
        text = "Test123Test"
        result = tokenizer.tokenize(text)
        strings = result.to_strings()

        assert strings == ["Test", "123", "Test"]

        number_tokens = [t for t in result.tokens if t.script == ScriptType.NUMBER]
        assert len(number_tokens) == 1
        assert number_tokens[0].text == "123"

    def test_contractions(self, tokenizer):
        text = "don't won't can't"
        result = tokenizer.tokenize(text)
        strings = result.to_strings()

        assert len(strings) == 9

        assert strings == ["don", "'", "t", "won", "'", "t", "can", "'", "t"]

        assert result.tokens[0].script == ScriptType.LATIN
        assert result.tokens[1].script == ScriptType.PUNCTUATION
        assert result.tokens[2].script == ScriptType.LATIN
        assert result.tokens[3].script == ScriptType.LATIN
        assert result.tokens[4].script == ScriptType.PUNCTUATION
        assert result.tokens[5].script == ScriptType.LATIN
        assert result.tokens[6].script == ScriptType.LATIN
        assert result.tokens[7].script == ScriptType.PUNCTUATION
        assert result.tokens[8].script == ScriptType.LATIN

        assert result.tokens[0].start == 0
        assert result.tokens[0].end == 3
        assert result.tokens[1].start == 3
        assert result.tokens[1].end == 4
        assert result.tokens[2].start == 4
        assert result.tokens[2].end == 5
        assert result.tokens[3].start == 6
        assert result.tokens[3].end == 9
        assert result.tokens[4].start == 9
        assert result.tokens[4].end == 10
        assert result.tokens[5].start == 10
        assert result.tokens[5].end == 11
        assert result.tokens[6].start == 12
        assert result.tokens[6].end == 15
        assert result.tokens[7].start == 15
        assert result.tokens[7].end == 16
        assert result.tokens[8].start == 16
        assert result.tokens[8].end == 17


class TestMixedTextTokenization:
    def test_chinese_english_mixed(self, tokenizer, sample_mixed_text):
        result = tokenizer.tokenize(sample_mixed_text)

        strings = result.to_strings()

        assert ScriptType.CJK in result.detected_scripts
        assert ScriptType.LATIN in result.detected_scripts
        assert ScriptType.PUNCTUATION in result.detected_scripts

        cjk_tokens = [t for t in result.tokens if t.script == ScriptType.CJK]
        latin_tokens = [t for t in result.tokens if t.script == ScriptType.LATIN]
        punct_tokens = [t for t in result.tokens if t.script == ScriptType.PUNCTUATION]

        assert len(cjk_tokens) == 10
        assert len(latin_tokens) == 2
        assert len(punct_tokens) == 5

    def test_code_switching(self, tokenizer):
        text = "你好Hello世界World"
        result = tokenizer.tokenize(text)
        strings = result.to_strings()

        assert strings == ["你", "好", "Hello", "世", "界", "World"]

    def test_mixed_with_numbers(self, tokenizer):
        text = "今天温度25度"
        result = tokenizer.tokenize(text)
        strings = result.to_strings()

        assert "今" in strings
        assert "天" in strings
        assert "温" in strings
        assert "度" in strings
        assert "25" in strings
        assert "度" in strings


class TestOtherScripts:
    def test_cyrillic(self, tokenizer):
        text = "Привет мир"
        result = tokenizer.tokenize(text)
        strings = result.to_strings()

        assert strings == ["Привет", "мир"]
        for token in result.tokens:
            assert token.script == ScriptType.CYRILLIC

    def test_arabic(self, tokenizer):
        text = "مرحبا بالعالم"
        result = tokenizer.tokenize(text)
        strings = result.to_strings()

        assert len(strings) == 2
        for token in result.tokens:
            assert token.script == ScriptType.ARABIC

    def test_japanese(self, tokenizer):
        text = "こんにちは世界"
        result = tokenizer.tokenize(text)
        strings = result.to_strings()

        assert len(strings) == 7
        hiragana_tokens = [t for t in result.tokens if t.script == ScriptType.HIRAGANA]
        cjk_tokens = [t for t in result.tokens if t.script == ScriptType.CJK]
        assert len(hiragana_tokens) == 5
        assert len(cjk_tokens) == 2

    def test_korean(self, tokenizer):
        text = "안녕하세요"
        result = tokenizer.tokenize(text)
        strings = result.to_strings()

        assert len(strings) == 5
        assert strings == ["안", "녕", "하", "세", "요"]
        for token in result.tokens:
            assert token.script == ScriptType.HANGUL

    def test_greek(self, tokenizer):
        text = "Γειά σου κόσμε"
        result = tokenizer.tokenize(text)
        strings = result.to_strings()

        assert strings == ["Γειά", "σου", "κόσμε"]
        for token in result.tokens:
            assert token.script == ScriptType.GREEK

    def test_hebrew(self, tokenizer):
        text = "שלום עולם"
        result = tokenizer.tokenize(text)
        strings = result.to_strings()

        assert len(strings) == 2
        for token in result.tokens:
            assert token.script == ScriptType.HEBREW

    def test_thai(self, tokenizer):
        text = "สวัสดีโลก"
        result = tokenizer.tokenize(text)
        strings = result.to_strings()

        assert len(strings) == 1
        assert result.tokens[0].script == ScriptType.THAI


class TestScriptDetection:
    def test_detect_script_chinese(self):
        assert detect_script("中") == ScriptType.CJK
        assert detect_script("文") == ScriptType.CJK

    def test_detect_script_english(self):
        assert detect_script("A") == ScriptType.LATIN
        assert detect_script("a") == ScriptType.LATIN

    def test_detect_script_punctuation(self):
        assert detect_script("，") == ScriptType.PUNCTUATION
        assert detect_script(",") == ScriptType.PUNCTUATION

    def test_detect_script_number(self):
        assert detect_script("1") == ScriptType.NUMBER
        assert detect_script("５") == ScriptType.NUMBER

    def test_detect_script_whitespace(self):
        assert detect_script(" ") == ScriptType.WHITESPACE
        assert detect_script("\n") == ScriptType.WHITESPACE
        assert detect_script("\t") == ScriptType.WHITESPACE

    def test_detect_script_emoji(self):
        assert detect_script("😀") == ScriptType.EMOJI
        assert detect_script("🎉") == ScriptType.EMOJI
        assert detect_script("\u2764") == ScriptType.EMOJI

    def test_detect_script_empty(self):
        assert detect_script("") == ScriptType.UNKNOWN


class TestConvenienceFunctions:
    def test_tokenize_function(self, sample_mixed_text):
        result = tokenize(sample_mixed_text)
        assert isinstance(result.tokens, list)
        assert len(result.tokens) > 0

    def test_tokenize_to_strings_function(self, sample_mixed_text):
        strings = tokenize_to_strings(sample_mixed_text)
        assert isinstance(strings, list)
        assert all(isinstance(s, str) for s in strings)

    def test_detect_dominant_script(self, tokenizer):
        assert tokenizer.detect_dominant_script("你好世界") == ScriptType.CJK
        assert tokenizer.detect_dominant_script("Hello World") == ScriptType.LATIN
        assert tokenizer.detect_dominant_script("") == ScriptType.UNKNOWN
        assert tokenizer.detect_dominant_script("1234") == ScriptType.UNKNOWN


class TestTokenProperties:
    def test_token_equality(self):
        t1 = Token(text="你", script=ScriptType.CJK, start=0, end=1)
        t2 = Token(text="你", script=ScriptType.CJK, start=0, end=1)
        t3 = Token(text="好", script=ScriptType.CJK, start=1, end=2)

        assert t1 == t2
        assert t1 != t3
        assert t1 != "你"

    def test_token_length(self):
        token = Token(text="Hello", script=ScriptType.LATIN, start=0, end=5)
        assert len(token) == 5

    def test_token_str_repr(self):
        token = Token(text="中", script=ScriptType.CJK, start=0, end=1)
        assert str(token) == "中"
        assert "CJK" in repr(token)
