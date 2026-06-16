from __future__ import annotations

import pytest

from solocoder_py.tokenizer import (
    InvalidTextError,
    ScriptRuleSet,
    ScriptType,
    Token,
    UnicodeTokenizer,
    is_cjk,
    is_emoji,
    is_number,
    is_punctuation,
    is_surrogate,
    is_whitespace,
    tokenize,
    tokenize_to_strings,
)


class TestEmojiHandling:
    def test_emoji_single_char(self, tokenizer):
        text = "😀"
        result = tokenizer.tokenize(text)

        assert len(result) == 1
        assert result.tokens[0].text == "😀"
        assert result.tokens[0].script == ScriptType.EMOJI

    def test_emoji_with_text(self, tokenizer):
        text = "你好😀世界"
        result = tokenizer.tokenize(text)
        strings = result.to_strings()

        assert "😀" in strings
        assert strings.index("😀") == 2

        emoji_token = [t for t in result.tokens if t.script == ScriptType.EMOJI][0]
        assert emoji_token.text == "😀"

    def test_multiple_emojis(self, tokenizer):
        text = "😀🎉❤️"
        result = tokenizer.tokenize(text)

        assert len(result) == 3
        for token in result.tokens:
            assert token.script == ScriptType.EMOJI
        assert result.to_strings() == ["😀", "🎉", "❤"]

    def test_emoji_between_words(self, tokenizer):
        text = "Hello😀World"
        result = tokenizer.tokenize(text)
        strings = result.to_strings()

        assert strings == ["Hello", "😀", "World"]

    def test_emoji_does_not_break_tokenization(self, tokenizer):
        text = "你好😀世界Hello🎉World"
        result = tokenizer.tokenize(text)

        assert len(result) == 8

        cjk_tokens = [t for t in result.tokens if t.script == ScriptType.CJK]
        latin_tokens = [t for t in result.tokens if t.script == ScriptType.LATIN]
        emoji_tokens = [t for t in result.tokens if t.script == ScriptType.EMOJI]

        assert len(cjk_tokens) == 4
        assert len(latin_tokens) == 2
        assert len(emoji_tokens) == 2


class TestSurrogateHandling:
    def test_is_surrogate_function(self):
        high_surrogate = "\ud800"
        low_surrogate = "\udc00"
        normal_char = "A"

        assert is_surrogate(high_surrogate) is True
        assert is_surrogate(low_surrogate) is True
        assert is_surrogate(normal_char) is False
        assert is_surrogate("") is False

    def test_surrogate_in_text(self, tokenizer):
        text = "a\ud800\udc00b"
        result = tokenizer.tokenize(text)
        strings = result.to_strings()

        assert "a" in strings
        assert "b" in strings
        assert len(result) == 2

    def test_surrogate_does_not_cause_crash(self, tokenizer):
        text = "\ud800\udc00测试\ud801\udc01文本"
        result = tokenizer.tokenize(text)

        assert len(result) == 4
        cjk_tokens = [t for t in result.tokens if t.script == ScriptType.CJK]
        assert len(cjk_tokens) == 4


class TestUnknownScriptHandling:
    def test_unknown_script_detection(self, tokenizer):
        rare_char = "\uE000"
        result = tokenizer.tokenize(rare_char)

        assert len(result) == 1
        assert result.tokens[0].script == ScriptType.UNKNOWN

    def test_unknown_script_fallback(self, tokenizer):
        text = "\uE000\uE001\uE002"
        result = tokenizer.tokenize(text)

        assert len(result) == 1
        assert result.tokens[0].script == ScriptType.UNKNOWN
        assert result.tokens[0].text == "\uE000\uE001\uE002"

    def test_unknown_script_with_known(self, tokenizer):
        text = "Hello\uE000World"
        result = tokenizer.tokenize(text)
        strings = result.to_strings()

        assert "Hello" in strings
        assert "\uE000" in strings
        assert "World" in strings
        assert len(result) == 3


class TestConsecutivePunctuation:
    def test_consecutive_punctuation_are_separate(self, tokenizer):
        text = ",,,!!!"
        result = tokenizer.tokenize(text)

        assert len(result) == 6
        assert result.to_strings() == [",", ",", ",", "!", "!", "!"]

    def test_consecutive_mixed_punctuation(self, tokenizer):
        text = "，，，！！！"
        result = tokenizer.tokenize(text)

        assert len(result) == 6
        assert result.to_strings() == ["，", "，", "，", "！", "！", "！"]

    def test_punctuation_not_merged(self, tokenizer):
        text = "Hello,,,World!!!"
        result = tokenizer.tokenize(text)
        strings = result.to_strings()

        assert strings == ["Hello", ",", ",", ",", "World", "!", "!", "!"]

    def test_mixed_punctuation_types(self, tokenizer):
        text = "，、。！？、，。"
        result = tokenizer.tokenize(text)

        assert len(result) == 8
        for i, token in enumerate(result.tokens):
            assert token.script == ScriptType.PUNCTUATION
            assert len(token.text) == 1


class TestErrorConditions:
    def test_none_input_raises_error(self, tokenizer):
        with pytest.raises(InvalidTextError, match="cannot be None"):
            tokenizer.tokenize(None)

    def test_non_string_input_raises_error(self, tokenizer):
        with pytest.raises(InvalidTextError, match="must be a string"):
            tokenizer.tokenize(123)

        with pytest.raises(InvalidTextError, match="must be a string"):
            tokenizer.tokenize(["hello"])

    def test_convenience_function_none_input(self):
        with pytest.raises(InvalidTextError):
            tokenize(None)

        with pytest.raises(InvalidTextError):
            tokenize_to_strings(None)


class TestCustomRuleSet:
    def test_add_custom_rule_set(self, tokenizer):
        custom_rule = ScriptRuleSet(
            script=ScriptType.LATIN,
            split_by_single_char=True,
        )
        tokenizer.add_rule_set(custom_rule)

        result = tokenizer.tokenize("Hello")
        assert len(result) == 5
        assert result.to_strings() == ["H", "e", "l", "l", "o"]

    def test_get_rule_set(self, tokenizer):
        rule = tokenizer.get_rule_set(ScriptType.CJK)
        assert rule.script == ScriptType.CJK
        assert rule.split_by_single_char is True

        rule = tokenizer.get_rule_set(ScriptType.LATIN)
        assert rule.script == ScriptType.LATIN
        assert rule.split_by_single_char is False

    def test_unknown_script_uses_default(self, tokenizer):
        rule = tokenizer.get_rule_set(ScriptType.UNKNOWN)
        assert rule is not None
        assert rule.script == ScriptType.UNKNOWN


class TestIsFunctions:
    def test_is_cjk(self):
        assert is_cjk("中") is True
        assert is_cjk("A") is False
        assert is_cjk("") is False

    def test_is_punctuation(self):
        assert is_punctuation("，") is True
        assert is_punctuation(",") is True
        assert is_punctuation("A") is False
        assert is_punctuation("") is False

    def test_is_whitespace(self):
        assert is_whitespace(" ") is True
        assert is_whitespace("\n") is True
        assert is_whitespace("\t") is True
        assert is_whitespace("A") is False
        assert is_whitespace("") is False

    def test_is_number(self):
        assert is_number("1") is True
        assert is_number("５") is True
        assert is_number("A") is False
        assert is_number("") is False

    def test_is_emoji(self):
        assert is_emoji("😀") is True
        assert is_emoji("🎉") is True
        assert is_emoji("\u2764") is True
        assert is_emoji("A") is False
        assert is_emoji("") is False


class TestTokenizationResultMetadata:
    def test_token_metadata(self, tokenizer):
        text = "Hello世界"
        result = tokenizer.tokenize(text)

        assert len(result) == 3
        assert result.tokens[0].text == "Hello"
        assert result.tokens[0].metadata == {}

    def test_original_text_preserved(self, tokenizer, sample_mixed_text):
        result = tokenizer.tokenize(sample_mixed_text)
        assert result.original_text == sample_mixed_text

    def test_empty_result_original_text(self, tokenizer):
        result = tokenizer.tokenize("")
        assert result.original_text == ""


class TestComplexEdgeCases:
    def test_zero_width_joiners(self, tokenizer):
        text = "👨‍👩‍👧‍👦"
        result = tokenizer.tokenize(text)

        assert len(result) >= 1

    def test_variation_selectors(self, tokenizer):
        text = "☀️"
        result = tokenizer.tokenize(text)

        assert len(result) >= 1

    def test_combining_characters(self, tokenizer):
        text = "àéîõü"
        result = tokenizer.tokenize(text)

        assert len(result) == 1
        assert result.tokens[0].script == ScriptType.LATIN

    def test_right_to_left_text(self, tokenizer):
        text = "שלום Hello 世界"
        result = tokenizer.tokenize(text)

        hebrew_tokens = [t for t in result.tokens if t.script == ScriptType.HEBREW]
        latin_tokens = [t for t in result.tokens if t.script == ScriptType.LATIN]
        cjk_tokens = [t for t in result.tokens if t.script == ScriptType.CJK]

        assert len(hebrew_tokens) == 1
        assert len(latin_tokens) == 1
        assert len(cjk_tokens) == 2

    def test_all_script_types(self, tokenizer):
        text = "中 한 に हे Привет Hello Γειά σου שלום مرحبا"
        result = tokenizer.tokenize(text)

        scripts = {t.script for t in result.tokens}

        assert ScriptType.CJK in scripts
        assert ScriptType.HANGUL in scripts
        assert ScriptType.HIRAGANA in scripts
        assert ScriptType.DEVANAGARI in scripts
        assert ScriptType.CYRILLIC in scripts
        assert ScriptType.LATIN in scripts
        assert ScriptType.GREEK in scripts
        assert ScriptType.HEBREW in scripts
        assert ScriptType.ARABIC in scripts
