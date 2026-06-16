from __future__ import annotations

import pytest

from solocoder_py.stemmer import (
    AggressivenessLevel,
    Stemmer,
    StemmerConfig,
)


class TestStemmerNormalFlows:
    def test_plural_nouns_standard(self):
        stemmer = Stemmer()
        assert stemmer.stem("cats") == "cat"
        assert stemmer.stem("dogs") == "dog"
        assert stemmer.stem("classes") == "class"
        assert stemmer.stem("kisses") == "kiss"
        assert stemmer.stem("boxes") == "box"

    def test_past_tense_standard(self):
        stemmer = Stemmer()
        assert stemmer.stem("walked") == "walk"
        assert stemmer.stem("started") == "start"
        assert stemmer.stem("ended") == "end"
        assert stemmer.stem("talked") == "talk"
        assert stemmer.stem("jumped") == "jump"

    def test_ing_form_standard(self):
        stemmer = Stemmer()
        assert stemmer.stem("walking") == "walk"
        assert stemmer.stem("running") == "run"
        assert stemmer.stem("swimming") == "swim"
        assert stemmer.stem("talking") == "talk"
        assert stemmer.stem("jumping") == "jump"

    def test_step2_suffixes(self):
        stemmer = Stemmer()
        assert stemmer.stem("relational") == "relat"
        assert stemmer.stem("conditional") == "condit"
        assert stemmer.stem("valence") == "valenc"
        assert stemmer.stem("hesitance") == "hesit"
        assert stemmer.stem("digitalizer") == "digit"

    def test_step3_suffixes(self):
        stemmer = Stemmer()
        assert stemmer.stem("triplicate") == "triplic"
        assert stemmer.stem("formative") == "form"
        assert stemmer.stem("formalize") == "formal"
        assert stemmer.stem("electrical") == "electr"
        assert stemmer.stem("goodness") == "good"

    def test_step4_suffixes(self):
        stemmer = Stemmer()
        assert stemmer.stem("revival") == "reviv"
        assert stemmer.stem("allowance") == "allow"
        assert stemmer.stem("inference") == "infer"
        assert stemmer.stem("airliner") == "airlin"
        assert stemmer.stem("magical") == "magic"

    def test_step5_e_removal(self):
        stemmer = Stemmer()
        assert stemmer.stem("probate") == "probat"
        assert stemmer.stem("rate") == "rate"
        assert stemmer.stem("cease") == "ceas"

    def test_irregular_words_exception_dict(self):
        stemmer = Stemmer()
        assert stemmer.stem("ran") == "run"
        assert stemmer.stem("mice") == "mouse"
        assert stemmer.stem("better") == "good"
        assert stemmer.stem("best") == "good"
        assert stemmer.stem("worse") == "bad"
        assert stemmer.stem("men") == "man"
        assert stemmer.stem("women") == "woman"
        assert stemmer.stem("children") == "child"
        assert stemmer.stem("teeth") == "tooth"
        assert stemmer.stem("feet") == "foot"

    def test_case_preservation_lower(self):
        stemmer = Stemmer()
        assert stemmer.stem("running") == "run"
        assert stemmer.stem("cats") == "cat"
        assert stemmer.stem("happiness") == "happi"

    def test_case_preservation_title(self):
        stemmer = Stemmer()
        assert stemmer.stem("Running") == "Run"
        assert stemmer.stem("Cats") == "Cat"
        assert stemmer.stem("Happiness") == "Happi"

    def test_case_preservation_upper(self):
        stemmer = Stemmer()
        assert stemmer.stem("RUNNING") == "RUN"
        assert stemmer.stem("CATS") == "CAT"
        assert stemmer.stem("HAPPINESS") == "HAPPI"

    def test_aggressiveness_conservative(self):
        config = StemmerConfig(level=AggressivenessLevel.CONSERVATIVE)
        stemmer = Stemmer(config=config)
        assert stemmer.stem("cats") == "cat"
        assert stemmer.stem("running") == "run"
        assert stemmer.stem("walked") == "walk"
        assert stemmer.stem("happiness") == "happiness"
        assert stemmer.stem("national") == "national"

    def test_aggressiveness_light(self):
        config = StemmerConfig(level=AggressivenessLevel.LIGHT)
        stemmer = Stemmer(config=config)
        assert stemmer.stem("cats") == "cat"
        assert stemmer.stem("running") == "run"
        assert stemmer.stem("happy") == "happi"
        assert stemmer.stem("operational") == "operate"

    def test_aggressiveness_standard(self):
        config = StemmerConfig(level=AggressivenessLevel.STANDARD)
        stemmer = Stemmer(config=config)
        assert stemmer.stem("cats") == "cat"
        assert stemmer.stem("running") == "run"
        assert stemmer.stem("happiness") == "happi"
        assert stemmer.stem("national") == "nation"

    def test_aggressiveness_aggressive(self):
        config = StemmerConfig(level=AggressivenessLevel.AGGRESSIVE)
        stemmer = Stemmer(config=config)
        standard_stemmer = Stemmer()
        agg_result = stemmer.stem("wonderful")
        std_result = standard_stemmer.stem("wonderful")
        assert len(agg_result) <= len(std_result)

    def test_different_aggressiveness_outputs_differ(self):
        word = "happiness"
        conservative = Stemmer(config=StemmerConfig(level=AggressivenessLevel.CONSERVATIVE))
        light = Stemmer(config=StemmerConfig(level=AggressivenessLevel.LIGHT))
        standard = Stemmer(config=StemmerConfig(level=AggressivenessLevel.STANDARD))

        conservative_result = conservative.stem(word)
        light_result = light.stem(word)
        standard_result = standard.stem(word)

        assert conservative_result != light_result or conservative_result != standard_result

    def test_stem_words_batch(self):
        stemmer = Stemmer()
        words = ["running", "cats", "happiness", "better"]
        results = stemmer.stem_words(words)
        assert results == ["run", "cat", "happi", "good"]

    def test_verb_forms_consistency(self):
        stemmer = Stemmer()
        assert stemmer.stem("walk") == stemmer.stem("walks")
        assert stemmer.stem("walk") == stemmer.stem("walking")
        assert stemmer.stem("walk") == stemmer.stem("walked")

    def test_add_exception(self):
        stemmer = Stemmer()
        assert stemmer.stem("foobar") == "foobar"
        stemmer.add_exception("foobar", "foo")
        assert stemmer.stem("foobar") == "foo"

    def test_remove_exception(self):
        stemmer = Stemmer()
        assert stemmer.stem("ran") == "run"
        result = stemmer.remove_exception("ran")
        assert result is True
        assert stemmer.stem("ran") != "run"

    def test_remove_nonexistent_exception(self):
        stemmer = Stemmer()
        result = stemmer.remove_exception("nonexistentword")
        assert result is False

    def test_get_exceptions(self):
        stemmer = Stemmer()
        exceptions = stemmer.get_exceptions()
        assert "ran" in exceptions
        assert "mice" in exceptions
        assert exceptions["ran"] == "run"
        stemmer.add_exception("testword", "test")
        exceptions2 = stemmer.get_exceptions()
        assert "testword" in exceptions2
        exceptions2["added_later"] = "later"
        assert "added_later" not in stemmer.get_exceptions()

    def test_aggressiveness_property(self):
        stemmer = Stemmer()
        assert stemmer.aggressiveness == AggressivenessLevel.STANDARD
        stemmer.aggressiveness = AggressivenessLevel.CONSERVATIVE
        assert stemmer.aggressiveness == AggressivenessLevel.CONSERVATIVE

    def test_stemmer_class_default_config(self):
        stemmer = Stemmer()
        assert stemmer.stem("cats") == "cat"
        assert stemmer.stem("running") == "run"
        assert stemmer.stem("happiness") == "happi"
