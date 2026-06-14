from __future__ import annotations

import pytest

from solocoder_py.fulltext import Stemmer, stem_word


class TestStemmerNormalFlows:
    def test_plural_nouns(self):
        assert stem_word("cats") == "cat"
        assert stem_word("dogs") == "dog"
        assert stem_word("boxes") == "box"
        assert stem_word("classes") == "class"
        assert stem_word("kisses") == "kiss"
        assert stem_word("churches") == "church"

    def test_past_tense(self):
        assert stem_word("walked") == "walk"
        assert stem_word("started") == "start"
        assert stem_word("ended") == "end"
        assert stem_word("talked") == "talk"
        assert stem_word("jumped") == "jump"

    def test_ing_form(self):
        assert stem_word("walking") == "walk"
        assert stem_word("running") == "run"
        assert stem_word("swimming") == "swim"
        assert stem_word("talking") == "talk"
        assert stem_word("jumping") == "jump"

    def test_adjectives(self):
        assert stem_word("happy") == "happi"
        assert stem_word("easily") == "easili"

    def test_common_variations(self):
        assert stem_word("connect") == "connect"
        assert stem_word("connected") == "connect"
        assert stem_word("connecting") == "connect"
        assert stem_word("connection") == "connect"

    def test_stemmer_class(self):
        stemmer = Stemmer()
        assert stemmer.stem("cats") == "cat"
        assert stemmer.stem("running") == "run"

    def test_stem_terms(self):
        stemmer = Stemmer()
        terms = ["cats", "dogs", "running", "walked"]
        stemmed = stemmer.stem_terms(terms)
        assert stemmed[0] == "cat"
        assert stemmed[1] == "dog"
        assert stemmed[2] == "run"
        assert stemmed[3] == "walk"

    def test_stem_tokens(self):
        stemmer = Stemmer()
        tokens = [("cats", 0), ("running", 5)]
        stemmed = stemmer.stem_tokens(tokens)
        assert stemmed[0][0] == "cat"
        assert stemmed[0][1] == 0
        assert stemmed[1][0] == "run"
        assert stemmed[1][1] == 5


class TestStemmerBoundaryConditions:
    def test_empty_string(self):
        assert stem_word("") == ""

    def test_single_character(self):
        assert stem_word("a") == "a"
        assert stem_word("I") == "i"

    def test_two_characters(self):
        assert stem_word("be") == "be"
        assert stem_word("to") == "to"
        assert stem_word("is") == "is"

    def test_chinese_unchanged(self):
        assert stem_word("你好") == "你好"
        assert stem_word("测试") == "测试"
        assert stem_word("编") == "编"

    def test_already_stemmed(self):
        assert stem_word("cat") == "cat"
        assert stem_word("dog") == "dog"
        assert stem_word("run") == "run"
        assert stem_word("walk") == "walk"
        assert stem_word("talk") == "talk"

    def test_case_insensitive(self):
        assert stem_word("Running") == "run"
        assert stem_word("WALKED") == "walk"
        assert stem_word("Cats") == "cat"

    def test_non_english_unchanged(self):
        assert stem_word("123") == "123"
        assert stem_word("test123") == "test123"


class TestStemmerConsistency:
    def test_plural_nouns_consistency(self):
        assert stem_word("cat") == stem_word("cats")
        assert stem_word("dog") == stem_word("dogs")
        assert stem_word("box") == stem_word("boxes")
        assert stem_word("class") == stem_word("classes")

    def test_verb_forms_consistency(self):
        assert stem_word("walk") == stem_word("walks") == stem_word("walking") == stem_word("walked")
        assert stem_word("talk") == stem_word("talks") == stem_word("talking") == stem_word("talked")
        assert stem_word("jump") == stem_word("jumps") == stem_word("jumping") == stem_word("jumped")

    def test_ing_and_ed_consistency(self):
        assert stem_word("running") == stem_word("run")
        assert stem_word("swimming") == stem_word("swim")

    def test_connect_variations_consistency(self):
        words = ["connect", "connects", "connecting", "connected", "connection"]
        stems = {stem_word(w) for w in words}
        assert len(stems) == 1

    def test_program_variations_consistency(self):
        words = ["program", "programs", "programming", "programmed"]
        stems = {stem_word(w) for w in words}
        assert len(stems) == 1

    def test_play_variations_consistency(self):
        words = ["play", "plays", "playing", "played"]
        stems = {stem_word(w) for w in words}
        assert len(stems) == 1
