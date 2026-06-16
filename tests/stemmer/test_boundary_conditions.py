from __future__ import annotations

import pytest

from solocoder_py.stemmer import (
    AggressivenessLevel,
    Stemmer,
    StemmerConfig,
)


class TestStemmerBoundaryConditions:
    def test_empty_string(self):
        stemmer = Stemmer()
        assert stemmer.stem("") == ""

    def test_single_character(self):
        stemmer = Stemmer()
        assert stemmer.stem("a") == "a"
        assert stemmer.stem("i") == "i"
        assert stemmer.stem("s") == "s"

    def test_two_characters_default_min_length(self):
        stemmer = Stemmer()
        assert stemmer.stem("be") == "be"
        assert stemmer.stem("to") == "to"
        assert stemmer.stem("no") == "no"

    def test_min_stem_length_boundary(self):
        config = StemmerConfig(min_stem_length=2)
        stemmer = Stemmer(config=config)
        assert stemmer.stem("cat") == "cat"
        assert stemmer.stem("cats") == "cat"
        assert len(stemmer.stem("cats")) >= 2

    def test_min_stem_length_custom(self):
        config = StemmerConfig(min_stem_length=4)
        stemmer = Stemmer(config=config)
        assert len(stemmer.stem("running")) >= 4

    def test_pure_numbers_unchanged(self):
        stemmer = Stemmer()
        assert stemmer.stem("123") == "123"
        assert stemmer.stem("456789") == "456789"

    def test_pure_punctuation_unchanged(self):
        stemmer = Stemmer()
        assert stemmer.stem("...") == "..."
        assert stemmer.stem("!!!") == "!!!"
        assert stemmer.stem("???") == "???"

    def test_mixed_alphanumeric_unchanged(self):
        stemmer = Stemmer()
        assert stemmer.stem("test123") == "test123"
        assert stemmer.stem("123test") == "123test"
        assert stemmer.stem("hello_world") == "hello_world"

    def test_non_english_characters_unchanged(self):
        stemmer = Stemmer()
        assert stemmer.stem("你好") == "你好"
        assert stemmer.stem("测试") == "测试"
        assert stemmer.stem("café") == "café"
        assert stemmer.stem("naïve") == "naïve"

    def test_already_stemmed_words(self):
        stemmer = Stemmer()
        assert stemmer.stem("cat") == "cat"
        assert stemmer.stem("dog") == "dog"
        assert stemmer.stem("run") == "run"
        assert stemmer.stem("walk") == "walk"
        assert stemmer.stem("talk") == "talk"

    def test_very_long_word(self):
        stemmer = Stemmer()
        long_word = "electroencephalographically"
        result = stemmer.stem(long_word)
        assert isinstance(result, str)
        assert len(result) <= len(long_word)

    def test_all_vowels(self):
        stemmer = Stemmer()
        assert stemmer.stem("aeiou") == "aeiou"

    def test_all_consonants(self):
        stemmer = Stemmer()
        assert stemmer.stem("bcdfg") == "bcdfg"

    def test_double_consonant_ending(self):
        stemmer = Stemmer()
        assert stemmer.stem("running") == "run"
        assert stemmer.stem("swimming") == "swim"
        assert stemmer.stem("hopping") == "hop"

    def test_y_as_vowel(self):
        stemmer = Stemmer()
        assert stemmer.stem("syzygy") == "syzygi"
        assert stemmer.stem("happy") == "happi"

    def test_words_ending_with_ss(self):
        stemmer = Stemmer()
        assert stemmer.stem("boss") == "boss"
        assert stemmer.stem("glass") == "glass"
        assert stemmer.stem("class") == "class"

    def test_words_ending_with_ing_without_vowel_in_stem(self):
        stemmer = Stemmer()
        assert stemmer.stem("sing") == "sing"
        assert stemmer.stem("ring") == "ring"
        assert stemmer.stem("bring") == "bring"

    def test_words_ending_with_ed_without_vowel_in_stem(self):
        stemmer = Stemmer()
        assert stemmer.stem("bled") == "bled"
        assert stemmer.stem("fed") == "fed"

    def test_min_stem_length_1(self):
        config = StemmerConfig(min_stem_length=1)
        stemmer = Stemmer(config=config)
        result = stemmer.stem("as")
        assert len(result) >= 1

    def test_single_letter_case_preservation(self):
        stemmer = Stemmer()
        assert stemmer.stem("A") == "A"
        assert stemmer.stem("I") == "I"

    def test_two_letter_case_preservation(self):
        stemmer = Stemmer()
        assert stemmer.stem("Be") == "Be"
        assert stemmer.stem("BE") == "BE"

    def test_word_exactly_min_length(self):
        config = StemmerConfig(min_stem_length=3)
        stemmer = Stemmer(config=config)
        assert stemmer.stem("cat") == "cat"

    def test_word_one_above_min_length(self):
        config = StemmerConfig(min_stem_length=3)
        stemmer = Stemmer(config=config)
        assert len(stemmer.stem("cats")) >= 3
