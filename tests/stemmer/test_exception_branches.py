from __future__ import annotations

import pytest

from solocoder_py.stemmer import (
    AggressivenessLevel,
    Stemmer,
    StemmerConfig,
)


class TestStemmerExceptionBranches:
    def test_exception_dict_overrides_rules(self):
        stemmer = Stemmer()
        assert stemmer.stem("ran") == "run"

    def test_exception_dict_with_case_preservation(self):
        stemmer = Stemmer()
        assert stemmer.stem("Ran") == "Run"
        assert stemmer.stem("RAN") == "RUN"
        assert stemmer.stem("ran") == "run"

    def test_custom_exceptions_override_default(self):
        custom_exceptions = {"ran": "ran_custom", "mice": "mouse_custom"}
        stemmer = Stemmer(exceptions=custom_exceptions)
        assert stemmer.stem("ran") == "ran_custom"
        assert stemmer.stem("mice") == "mouse_custom"

    def test_empty_exceptions_dict(self):
        stemmer = Stemmer(exceptions={})
        default_stemmer = Stemmer()
        assert default_stemmer.stem("ran") == "run"
        assert stemmer.stem("ran") != "run"

    def test_none_exceptions_uses_default(self):
        stemmer = Stemmer(exceptions=None)
        assert stemmer.stem("ran") == "run"
        assert stemmer.stem("better") == "good"

    def test_add_exception_case_insensitive(self):
        stemmer = Stemmer()
        stemmer.add_exception("Testcase", "test")
        assert stemmer.stem("testcase") == "test"
        assert stemmer.stem("Testcase") == "Test"
        assert stemmer.stem("TESTCASE") == "TEST"

    def test_remove_exception_case_insensitive(self):
        stemmer = Stemmer()
        assert stemmer.stem("ran") == "run"
        stemmer.remove_exception("RAN")
        assert stemmer.stem("ran") != "run"

    def test_empty_string_returns_empty(self):
        stemmer = Stemmer()
        assert stemmer.stem("") == ""

    def test_whitespace_not_processed(self):
        stemmer = Stemmer()
        assert stemmer.stem(" ") == " "
        assert stemmer.stem("   ") == "   "

    def test_words_with_uncommon_suffixes_not_stripped(self):
        stemmer = Stemmer()
        assert stemmer.stem("xyz") == "xyz"
        assert stemmer.stem("abcd") == "abcd"

    def test_suffix_conditions_not_met(self):
        config = StemmerConfig(level=AggressivenessLevel.STANDARD)
        stemmer = Stemmer(config=config)
        assert stemmer.stem("sky") == "sky"
        assert stemmer.stem("skies") == "ski"

    def test_measure_zero_no_stripping(self):
        stemmer = Stemmer()
        assert stemmer.stem("s") == "s"
        assert stemmer.stem("ss") == "ss"

    def test_ion_suffix_requires_s_or_t(self):
        stemmer = Stemmer()
        assert stemmer.stem("election") == "elect"
        assert stemmer.stem("vision") == "vision"

    def test_step1b_eed_measure_gt_0(self):
        stemmer = Stemmer()
        assert stemmer.stem("agreed") == "agre"
        assert stemmer.stem("feed") == "feed"

    def test_step5a_e_removal_conditions(self):
        stemmer = Stemmer()
        assert stemmer.stem("rate") == "rate"
        assert stemmer.stem("cease") == "ceas"

    def test_preserve_case_false(self):
        config = StemmerConfig(preserve_case=False)
        stemmer = Stemmer(config=config)
        assert stemmer.stem("Running") == "run"
        assert stemmer.stem("CATS") == "cat"
        assert stemmer.stem("Happy") == "happi"

    def test_preserve_case_false_with_exceptions(self):
        config = StemmerConfig(preserve_case=False)
        stemmer = Stemmer(config=config)
        assert stemmer.stem("Ran") == "run"
        assert stemmer.stem("BETTER") == "good"

    def test_exception_and_rule_conflict_dict_priority(self):
        stemmer = Stemmer()
        normal_result = stemmer.stem("mice")
        assert normal_result == "mouse"
        stemmer.remove_exception("mice")
        rule_result = stemmer.stem("mice")
        assert rule_result != "mouse"
        assert normal_result != rule_result

    def test_stem_words_empty_list(self):
        stemmer = Stemmer()
        result = stemmer.stem_words([])
        assert result == []

    def test_stem_words_with_mixed_content(self):
        stemmer = Stemmer()
        words = ["running", "123", "cats", "你好", "better", ""]
        results = stemmer.stem_words(words)
        assert results[0] == "run"
        assert results[1] == "123"
        assert results[2] == "cat"
        assert results[3] == "你好"
        assert results[4] == "good"
        assert results[5] == ""

    def test_aggressive_mode_does_not_crash_on_short_words(self):
        config = StemmerConfig(level=AggressivenessLevel.AGGRESSIVE)
        stemmer = Stemmer(config=config)
        assert stemmer.stem("a") == "a"
        assert stemmer.stem("ab") == "ab"
        assert stemmer.stem("abc") == "abc"

    def test_multiple_exception_additions(self):
        stemmer = Stemmer()
        stemmer.add_exception("apple", "appl")
        stemmer.add_exception("banana", "banan")
        stemmer.add_exception("cherry", "cherri")
        assert stemmer.stem("apple") == "appl"
        assert stemmer.stem("banana") == "banan"
        assert stemmer.stem("cherry") == "cherri"

    def test_exception_stem_shorter_than_min_length(self):
        config = StemmerConfig(min_stem_length=5)
        stemmer = Stemmer(config=config, exceptions={"testing": "test"})
        result = stemmer.stem("testing")
        assert len(result) >= 5 or result == "test"
