import threading

import pytest

from solocoder_py.autocomplete import (
    Candidate,
    EmptyWordError,
    InvalidPrefixError,
    InvalidWeightError,
    TrieAutocomplete,
)
from solocoder_py.autocomplete.models import TrieNode


class TestBasicOperations:
    def test_insert_single_word(self, empty_trie):
        empty_trie.insert("hello", weight=5)
        assert empty_trie.size == 1
        assert empty_trie.contains("hello") is True
        assert empty_trie.get_weight("hello") == 5

    def test_insert_multiple_words(self, empty_trie):
        words = [("apple", 10), ("banana", 8), ("cherry", 12)]
        for word, weight in words:
            empty_trie.insert(word, weight)
        assert empty_trie.size == 3
        for word, weight in words:
            assert empty_trie.contains(word) is True
            assert empty_trie.get_weight(word) == weight

    def test_insert_duplicate_word_accumulates_weight(self, empty_trie):
        empty_trie.insert("test", weight=5)
        empty_trie.insert("test", weight=10)
        assert empty_trie.size == 1
        assert empty_trie.get_weight("test") == 15

    def test_contains_nonexistent_word(self, empty_trie):
        assert empty_trie.contains("nonexistent") is False

    def test_get_weight_nonexistent_word(self, empty_trie):
        assert empty_trie.get_weight("nonexistent") is None

    def test_size_empty_trie(self, empty_trie):
        assert empty_trie.size == 0

    def test_get_all_words(self, sample_trie):
        words = sample_trie.get_all_words()
        assert words == sorted(["apple", "app", "application", "banana", "ball", "cat", "car"])

    def test_clear(self, sample_trie):
        assert sample_trie.size == 7
        sample_trie.clear()
        assert sample_trie.size == 0
        assert sample_trie.contains("apple") is False
        results = sample_trie.search("a")
        assert results == []


class TestSearchOperations:
    def test_search_by_prefix(self, sample_trie):
        results = sample_trie.search("app")
        assert len(results) == 3
        assert results[0].word == "application"
        assert results[0].weight == 15
        assert results[1].word == "apple"
        assert results[1].weight == 10
        assert results[2].word == "app"
        assert results[2].weight == 8

    def test_search_single_char_prefix(self, sample_trie):
        results = sample_trie.search("a")
        assert len(results) == 3
        words = [r.word for r in results]
        assert "application" in words
        assert "apple" in words
        assert "app" in words

    def test_search_no_match_returns_empty(self, sample_trie):
        results = sample_trie.search("xyz", fuzzy=False)
        assert results == []

    def test_search_empty_prefix_returns_all(self, sample_trie):
        results = sample_trie.search("")
        assert len(results) == 7
        assert results[0].word == "application"
        assert results[0].weight == 15
        assert results[1].word == "banana"
        assert results[1].weight == 12

    def test_search_top_n_truncation(self, sample_trie):
        results = sample_trie.search("", top_n=3)
        assert len(results) == 3
        assert results[0].word == "application"
        assert results[1].word == "banana"
        assert results[2].word == "apple"

    def test_search_top_n_greater_than_candidates(self, sample_trie):
        results = sample_trie.search("app", top_n=10)
        assert len(results) == 3

    def test_search_top_n_zero_returns_all(self, sample_trie):
        results = sample_trie.search("app", top_n=0)
        assert len(results) == 3

    def test_search_top_n_negative_returns_all(self, sample_trie):
        results = sample_trie.search("app", top_n=-1)
        assert len(results) == 3

    def test_search_none_prefix_raises(self, empty_trie):
        with pytest.raises(TypeError, match="prefix cannot be None"):
            empty_trie.search(None)


class TestWeightSorting:
    def test_results_sorted_by_weight_descending(self, empty_trie):
        empty_trie.insert("a", weight=5)
        empty_trie.insert("b", weight=10)
        empty_trie.insert("c", weight=3)
        results = empty_trie.search("")
        assert results[0].weight == 10
        assert results[1].weight == 5
        assert results[2].weight == 3

    def test_equal_weight_sorted_lexicographically(self, empty_trie):
        empty_trie.insert("banana", weight=5)
        empty_trie.insert("apple", weight=5)
        empty_trie.insert("cherry", weight=5)
        results = empty_trie.search("")
        assert results[0].word == "apple"
        assert results[1].word == "banana"
        assert results[2].word == "cherry"

    def test_mixed_weight_and_lex_order(self, empty_trie):
        empty_trie.insert("zebra", weight=10)
        empty_trie.insert("apple", weight=10)
        empty_trie.insert("banana", weight=15)
        results = empty_trie.search("")
        assert results[0].word == "banana"
        assert results[0].weight == 15
        assert results[1].word == "apple"
        assert results[1].weight == 10
        assert results[2].word == "zebra"
        assert results[2].weight == 10


class TestWeightUpdate:
    def test_update_weight_override(self, sample_trie):
        assert sample_trie.get_weight("apple") == 10
        sample_trie.update_weight("apple", weight=20)
        assert sample_trie.get_weight("apple") == 20
        results = sample_trie.search("app")
        assert results[0].word == "apple"
        assert results[0].weight == 20

    def test_update_weight_accumulate(self, sample_trie):
        assert sample_trie.get_weight("apple") == 10
        sample_trie.update_weight("apple", weight=5, accumulate=True)
        assert sample_trie.get_weight("apple") == 15
        results = sample_trie.search("app")
        assert results[0].word == "apple"
        assert results[0].weight == 15
        assert results[1].word == "application"
        assert results[1].weight == 15

    def test_update_nonexistent_word_inserts(self, empty_trie):
        empty_trie.update_weight("new_word", weight=7)
        assert empty_trie.contains("new_word") is True
        assert empty_trie.get_weight("new_word") == 7

    def test_update_after_search_reflects_changes(self, empty_trie):
        empty_trie.insert("test1", weight=5)
        empty_trie.insert("test2", weight=10)
        results1 = empty_trie.search("test")
        assert results1[0].word == "test2"
        empty_trie.update_weight("test1", weight=15)
        results2 = empty_trie.search("test")
        assert results2[0].word == "test1"
        assert results2[0].weight == 15

    def test_multiple_updates_consistency(self, empty_trie):
        empty_trie.insert("word", weight=1)
        for i in range(100):
            empty_trie.update_weight("word", weight=1, accumulate=True)
        assert empty_trie.get_weight("word") == 101
        results = empty_trie.search("w")
        assert len(results) == 1
        assert results[0].weight == 101

    def test_frequent_updates_sort_consistency(self, empty_trie):
        words = ["a", "b", "c", "d", "e"]
        for word in words:
            empty_trie.insert(word, weight=1)

        for i in range(50):
            word = words[i % len(words)]
            empty_trie.update_weight(word, weight=1, accumulate=True)

        results = empty_trie.search("")
        for i in range(len(results) - 1):
            assert results[i].weight >= results[i + 1].weight
            if results[i].weight == results[i + 1].weight:
                assert results[i].word < results[i + 1].word


class TestDeleteOperations:
    def test_delete_existing_word(self, sample_trie):
        assert sample_trie.delete("apple") is True
        assert sample_trie.contains("apple") is False
        assert sample_trie.size == 6
        results = sample_trie.search("app")
        words = [r.word for r in results]
        assert "apple" not in words

    def test_delete_nonexistent_word(self, empty_trie):
        assert empty_trie.delete("nonexistent") is False

    def test_delete_updates_search_results(self, sample_trie):
        results_before = sample_trie.search("app")
        assert len(results_before) == 3
        sample_trie.delete("application")
        results_after = sample_trie.search("app")
        assert len(results_after) == 2
        words = [r.word for r in results_after]
        assert "application" not in words

    def test_delete_all_words(self, sample_trie):
        words = sample_trie.get_all_words()
        for word in words:
            assert sample_trie.delete(word) is True
        assert sample_trie.size == 0
        assert sample_trie.search("") == []

    def test_delete_then_reinsert(self, sample_trie):
        sample_trie.delete("apple")
        assert sample_trie.contains("apple") is False
        sample_trie.insert("apple", weight=20)
        assert sample_trie.contains("apple") is True
        assert sample_trie.get_weight("apple") == 20


class TestEdgeCases:
    def test_insert_single_character_word(self, empty_trie):
        empty_trie.insert("a", weight=5)
        assert empty_trie.size == 1
        assert empty_trie.contains("a") is True
        results = empty_trie.search("a")
        assert len(results) == 1
        assert results[0].word == "a"

    def test_insert_long_word(self, empty_trie):
        long_word = "a" * 100
        empty_trie.insert(long_word, weight=10)
        assert empty_trie.contains(long_word) is True
        results = empty_trie.search("a" * 50)
        assert len(results) == 1
        assert results[0].word == long_word

    def test_insert_unicode_words(self, empty_trie):
        empty_trie.insert("中文", weight=5)
        empty_trie.insert("日本語", weight=8)
        empty_trie.insert("한국어", weight=3)
        assert empty_trie.size == 3
        results = empty_trie.search("中")
        assert len(results) == 1
        assert results[0].word == "中文"

    def test_insert_words_with_common_prefixes(self, empty_trie):
        words = ["a", "ab", "abc", "abcd", "abcde"]
        for i, word in enumerate(words):
            empty_trie.insert(word, weight=i + 1)
        assert empty_trie.size == 5
        results = empty_trie.search("a")
        assert len(results) == 5
        assert results[0].word == "abcde"
        assert results[-1].word == "a"

    def test_search_partial_prefix(self, sample_trie):
        results = sample_trie.search("ap")
        assert len(results) == 3
        words = [r.word for r in results]
        assert all(w.startswith("ap") for w in words)

    def test_search_exact_word(self, sample_trie):
        results = sample_trie.search("apple")
        assert len(results) == 1
        assert results[0].word == "apple"

    def test_search_prefix_longer_than_all_words_returns_empty(self, empty_trie):
        empty_trie.insert("app", weight=5)
        results = empty_trie.search("application", fuzzy=False)
        assert results == []

    def test_zero_weight_word(self, empty_trie):
        empty_trie.insert("zero", weight=0)
        assert empty_trie.get_weight("zero") == 0
        results = empty_trie.search("z")
        assert len(results) == 1
        assert results[0].weight == 0

    def test_large_number_of_words(self, empty_trie):
        for i in range(1000):
            empty_trie.insert(f"word_{i:04d}", weight=i)
        assert empty_trie.size == 1000
        results = empty_trie.search("word_0", top_n=5)
        assert len(results) == 5
        assert results[0].weight > results[-1].weight


class TestErrorCases:
    def test_insert_empty_string_raises(self, empty_trie):
        with pytest.raises(EmptyWordError, match="word cannot be empty"):
            empty_trie.insert("", weight=5)

    def test_insert_negative_weight_raises(self, empty_trie):
        with pytest.raises(InvalidWeightError, match="weight must be non-negative"):
            empty_trie.insert("test", weight=-1)

    def test_update_empty_string_raises(self, empty_trie):
        with pytest.raises(EmptyWordError, match="word cannot be empty"):
            empty_trie.update_weight("", weight=5)

    def test_update_negative_weight_raises(self, empty_trie):
        with pytest.raises(InvalidWeightError, match="weight must be non-negative"):
            empty_trie.update_weight("test", weight=-1)

    def test_delete_empty_string_raises(self, empty_trie):
        with pytest.raises(EmptyWordError, match="word cannot be empty"):
            empty_trie.delete("")


class TestCandidateModel:
    def test_candidate_creation(self):
        c = Candidate(word="test", weight=10)
        assert c.word == "test"
        assert c.weight == 10

    def test_candidate_empty_word_raises(self):
        with pytest.raises(EmptyWordError):
            Candidate(word="", weight=5)

    def test_candidate_negative_weight_raises(self):
        with pytest.raises(InvalidWeightError):
            Candidate(word="test", weight=-1)

    def test_candidate_equality(self):
        c1 = Candidate(word="a", weight=10)
        c2 = Candidate(word="a", weight=10)
        c3 = Candidate(word="b", weight=10)
        c4 = Candidate(word="a", weight=20)
        assert c1 == c2
        assert c1 != c3
        assert c1 != c4

    def test_candidate_lt_weight_comparison(self):
        c_low = Candidate(word="a", weight=5)
        c_high = Candidate(word="b", weight=10)
        assert c_high < c_low
        assert not c_low < c_high

    def test_candidate_lt_equal_weight_lex_ascending(self):
        c_apple = Candidate(word="apple", weight=10)
        c_banana = Candidate(word="banana", weight=10)
        assert c_apple < c_banana
        assert not c_banana < c_apple

    def test_candidate_gt_weight_comparison(self):
        c_low = Candidate(word="a", weight=5)
        c_high = Candidate(word="b", weight=10)
        assert c_low > c_high
        assert not c_high > c_low

    def test_candidate_gt_equal_weight_lex_ascending(self):
        c_apple = Candidate(word="apple", weight=10)
        c_banana = Candidate(word="banana", weight=10)
        assert c_banana > c_apple
        assert not c_apple > c_banana

    def test_candidate_ge_weight_comparison(self):
        c_low = Candidate(word="a", weight=5)
        c_high = Candidate(word="b", weight=10)
        c_high2 = Candidate(word="c", weight=10)
        assert c_low >= c_high
        assert not c_high >= c_high2
        assert c_high2 >= c_high
        assert not c_high >= c_low

    def test_candidate_ge_equal_weight_lex_ascending(self):
        c_apple = Candidate(word="apple", weight=10)
        c_banana = Candidate(word="banana", weight=10)
        c_apple2 = Candidate(word="apple", weight=10)
        assert c_banana >= c_apple
        assert c_apple >= c_apple2
        assert not c_apple >= c_banana

    def test_candidate_le_weight_comparison(self):
        c_low = Candidate(word="a", weight=5)
        c_high = Candidate(word="b", weight=10)
        c_low2 = Candidate(word="c", weight=5)
        assert c_high <= c_low
        assert c_low <= c_low2
        assert not c_low <= c_high

    def test_candidate_le_equal_weight_lex_ascending(self):
        c_apple = Candidate(word="apple", weight=10)
        c_banana = Candidate(word="banana", weight=10)
        c_apple2 = Candidate(word="apple", weight=10)
        assert c_apple <= c_banana
        assert c_apple <= c_apple2
        assert not c_banana <= c_apple

    def test_candidate_list_sort_weight_descending(self):
        c1 = Candidate(word="a", weight=5)
        c2 = Candidate(word="b", weight=10)
        c3 = Candidate(word="c", weight=3)
        candidates = [c1, c2, c3]
        candidates.sort()
        assert candidates[0].weight == 10
        assert candidates[1].weight == 5
        assert candidates[2].weight == 3

    def test_candidate_list_sort_equal_weight_lex_ascending(self):
        c_banana = Candidate(word="banana", weight=10)
        c_apple = Candidate(word="apple", weight=10)
        c_cherry = Candidate(word="cherry", weight=10)
        candidates = [c_banana, c_apple, c_cherry]
        candidates.sort()
        assert candidates[0].word == "apple"
        assert candidates[1].word == "banana"
        assert candidates[2].word == "cherry"

    def test_candidate_list_sort_mixed(self):
        c_zebra = Candidate(word="zebra", weight=10)
        c_apple = Candidate(word="apple", weight=10)
        c_banana = Candidate(word="banana", weight=15)
        c_cat = Candidate(word="cat", weight=10)
        candidates = [c_zebra, c_apple, c_banana, c_cat]
        candidates.sort()
        assert candidates[0].word == "banana"
        assert candidates[0].weight == 15
        assert candidates[1].word == "apple"
        assert candidates[1].weight == 10
        assert candidates[2].word == "cat"
        assert candidates[2].weight == 10
        assert candidates[3].word == "zebra"
        assert candidates[3].weight == 10


class TestFuzzySearch:
    def test_fuzzy_search_when_no_exact_match(self, sample_trie):
        results = sample_trie.search("appla", fuzzy=True)
        assert len(results) > 0
        for r in results:
            assert r.is_fuzzy is True
            assert r.edit_distance > 0

    def test_fuzzy_search_disabled_returns_empty(self, sample_trie):
        results = sample_trie.search("appla", fuzzy=False)
        assert results == []

    def test_fuzzy_threshold_zero_returns_empty(self, sample_trie):
        results = sample_trie.search("appla", fuzzy=True, fuzzy_threshold=0)
        assert results == []

    def test_fuzzy_edit_distance_at_threshold(self, empty_trie):
        empty_trie.insert("apple", weight=10)
        results = empty_trie.search("appla", fuzzy=True, fuzzy_threshold=1)
        assert len(results) == 1
        assert results[0].word == "apple"
        assert results[0].edit_distance == 1
        assert results[0].is_fuzzy is True

    def test_fuzzy_edit_distance_exceeds_threshold(self, empty_trie):
        empty_trie.insert("apple", weight=10)
        results = empty_trie.search("xyz", fuzzy=True, fuzzy_threshold=1)
        assert results == []

    def test_fuzzy_results_sorted_by_distance_then_weight(self, empty_trie):
        empty_trie.insert("apple", weight=10)
        empty_trie.insert("apply", weight=15)
        empty_trie.insert("apples", weight=8)
        results = empty_trie.search("appla", fuzzy=True, fuzzy_threshold=2)
        assert len(results) == 3
        assert results[0].word == "apply"
        assert results[0].edit_distance == 1
        assert results[0].weight == 15
        assert results[1].word == "apple"
        assert results[1].edit_distance == 1
        assert results[1].weight == 10

    def test_exact_match_takes_precedence_over_fuzzy(self, sample_trie):
        results = sample_trie.search("app", fuzzy=True)
        assert len(results) == 3
        for r in results:
            assert r.is_fuzzy is False

    def test_fuzzy_search_case_insensitive(self, empty_trie):
        empty_trie.insert("Apple", weight=10)
        results = empty_trie.search("appla", fuzzy=True, fuzzy_threshold=1)
        assert len(results) == 1
        assert results[0].word == "Apple"
        assert results[0].is_fuzzy is True

    def test_fuzzy_search_case_sensitive(self, empty_trie):
        trie = TrieAutocomplete(case_sensitive=True)
        trie.insert("Apple", weight=10)
        results = trie.search("Appla", fuzzy=True, fuzzy_threshold=1)
        assert len(results) == 1
        assert results[0].edit_distance == 1

    def test_fuzzy_mixed_with_exact_returns_exact_only(self, empty_trie):
        empty_trie.insert("apple", weight=10)
        empty_trie.insert("apply", weight=5)
        results = empty_trie.search("appl", fuzzy=True)
        assert len(results) == 2
        for r in results:
            assert r.is_fuzzy is False
            assert r.edit_distance == 0


class TestBoundaryConditions:
    def test_empty_corpus_returns_empty(self, empty_trie):
        results = empty_trie.search("test")
        assert results == []

    def test_top_n_zero_returns_all(self, sample_trie):
        results = sample_trie.search("app", top_n=0)
        assert len(results) == 3

    def test_top_n_negative_returns_all(self, sample_trie):
        results = sample_trie.search("app", top_n=-1)
        assert len(results) == 3

    def test_single_char_prefix(self, sample_trie):
        results = sample_trie.search("a", top_n=2)
        assert len(results) == 2
        assert results[0].weight >= results[1].weight

    def test_prefix_matches_all_corpus(self, empty_trie):
        for i in range(100):
            empty_trie.insert(f"w{i}", weight=i)
        results = empty_trie.search("w", top_n=10)
        assert len(results) == 10
        for i in range(9):
            assert results[i].weight > results[i + 1].weight

    def test_chinese_prefix_match(self, chinese_trie):
        results = chinese_trie.search("中国")
        assert len(results) == 3
        words = [r.word for r in results]
        assert "中国" in words
        assert "中国人" in words
        assert "中国话" in words

    def test_chinese_single_char_prefix(self, chinese_trie):
        results = chinese_trie.search("北")
        assert len(results) == 2
        words = [r.word for r in results]
        assert "北京" in words
        assert "北京大学" in words

    def test_mixed_chinese_english(self, empty_trie):
        empty_trie.insert("中国food", weight=10)
        empty_trie.insert("中国city", weight=8)
        empty_trie.insert("china", weight=5)
        results = empty_trie.search("中国")
        assert len(results) == 2
        assert results[0].weight == 10

    def test_case_insensitive_search(self, sample_trie):
        results = sample_trie.search("APP")
        assert len(results) == 3
        words = [r.word for r in results]
        assert "apple" in words
        assert "app" in words
        assert "application" in words

    def test_case_sensitive_search(self, case_sensitive_trie):
        results = case_sensitive_trie.search("APP")
        assert len(results) == 1
        assert results[0].word == "APP"

    def test_case_sensitive_different_cases(self, case_sensitive_trie):
        results_lower = case_sensitive_trie.search("app")
        results_upper = case_sensitive_trie.search("APP")
        results_mixed = case_sensitive_trie.search("App")
        assert results_lower[0].word == "apple"
        assert results_upper[0].word == "APP"
        assert results_mixed[0].word == "Apple"

    def test_blank_word_insertion_raises(self, empty_trie):
        with pytest.raises(EmptyWordError):
            empty_trie.insert("   ", weight=5)

    def test_blank_word_update_raises(self, empty_trie):
        with pytest.raises(EmptyWordError):
            empty_trie.update_weight("  \t  ", weight=5)

    def test_blank_word_delete_raises(self, empty_trie):
        with pytest.raises(EmptyWordError):
            empty_trie.delete("\n  ")

    def test_empty_prefix_search_returns_all(self, sample_trie):
        results = sample_trie.search("")
        assert len(results) == sample_trie.size

    def test_none_prefix_raises(self, empty_trie):
        with pytest.raises(TypeError):
            empty_trie.search(None)

    def test_fuzzy_threshold_negative_raises(self, sample_trie):
        with pytest.raises(InvalidWeightError):
            sample_trie.fuzzy_threshold = -1


class TestErrorBranches:
    def test_delete_nonexistent_returns_false(self, empty_trie):
        assert empty_trie.delete("nonexistent") is False

    def test_update_nonexistent_inserts(self, empty_trie):
        empty_trie.update_weight("new", weight=10)
        assert empty_trie.contains("new") is True
        assert empty_trie.get_weight("new") == 10

    def test_fuzzy_threshold_zero_no_suggestions(self, empty_trie):
        empty_trie.insert("apple", weight=10)
        results = empty_trie.search("appla", fuzzy=True, fuzzy_threshold=0)
        assert results == []

    def test_edit_distance_exactly_threshold(self, empty_trie):
        empty_trie.insert("test", weight=10)
        results = empty_trie.search("tesx", fuzzy=True, fuzzy_threshold=1)
        assert len(results) == 1
        assert results[0].edit_distance == 1
        assert results[0].is_fuzzy is True

    def test_exact_and_fuzzy_both_exist(self, empty_trie):
        empty_trie.insert("apple", weight=10)
        empty_trie.insert("apply", weight=5)
        results = empty_trie.search("appl", fuzzy=True)
        assert len(results) == 2
        for r in results:
            assert r.is_fuzzy is False

    def test_duplicate_insert_accumulates(self, empty_trie):
        empty_trie.insert("test", weight=5)
        empty_trie.insert("test", weight=3)
        empty_trie.insert("test", weight=2)
        assert empty_trie.get_weight("test") == 10

    def test_delete_updates_all_prefix_nodes(self, empty_trie):
        empty_trie.insert("apple", weight=10)
        empty_trie.insert("app", weight=5)
        results_before = empty_trie.search("ap")
        assert len(results_before) == 2
        empty_trie.delete("apple")
        results_after = empty_trie.search("ap")
        assert len(results_after) == 1
        assert results_after[0].word == "app"


class TestHeatUpdate:
    def test_search_increments_heat(self, empty_trie):
        empty_trie.insert("apple", weight=5)
        results = empty_trie.search("app")
        assert results[0].weight == 5
        empty_trie.update_weight("apple", weight=1, accumulate=True)
        results = empty_trie.search("app")
        assert results[0].weight == 6

    def test_multiple_searches_increment_heat(self, empty_trie):
        empty_trie.insert("test", weight=1)
        for _ in range(10):
            empty_trie.update_weight("test", weight=1, accumulate=True)
        assert empty_trie.get_weight("test") == 11

    def test_heat_affects_sorting(self, empty_trie):
        empty_trie.insert("a", weight=5)
        empty_trie.insert("b", weight=10)
        results1 = empty_trie.search("")
        assert results1[0].word == "b"
        empty_trie.update_weight("a", weight=10, accumulate=True)
        results2 = empty_trie.search("")
        assert results2[0].word == "a"

    def test_heat_same_value_lex_order(self, empty_trie):
        empty_trie.insert("banana", weight=5)
        empty_trie.insert("apple", weight=5)
        results = empty_trie.search("")
        assert results[0].word == "apple"
        assert results[1].word == "banana"


class TestTrieNode:
    def test_trie_node_initialization(self):
        node = TrieNode("a")
        assert node.char == "a"
        assert node.children == {}
        assert node.is_end_of_word is False
        assert node.weight == 0
        assert node.candidates == []

    def test_trie_node_add_candidate(self):
        node = TrieNode("a")
        node.add_candidate("apple", 10)
        assert len(node.candidates) == 1
        assert node.candidates[0].word == "apple"
        assert node.candidates[0].weight == 10

    def test_trie_node_update_candidate(self):
        node = TrieNode("a")
        node.add_candidate("apple", 10)
        node.add_candidate("apple", 20)
        assert len(node.candidates) == 1
        assert node.candidates[0].weight == 20

    def test_trie_node_remove_candidate(self):
        node = TrieNode("a")
        node.add_candidate("apple", 10)
        node.add_candidate("app", 5)
        node.remove_candidate("apple")
        assert len(node.candidates) == 1
        assert node.candidates[0].word == "app"

    def test_trie_node_get_top_candidates(self):
        node = TrieNode("a")
        node.add_candidate("a", 1)
        node.add_candidate("ab", 2)
        node.add_candidate("abc", 3)
        top2 = node.get_top_candidates(2)
        assert len(top2) == 2
        assert top2[0].weight == 3
        assert top2[1].weight == 2


class TestConcurrentAccess:
    def test_concurrent_inserts(self, empty_trie):
        errors = []
        num_threads = 10
        per_thread = 100

        def writer(start, count):
            try:
                for i in range(start, start + count):
                    empty_trie.insert(f"word_{i}", weight=i)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=writer, args=(i * per_thread, per_thread))
            for i in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert empty_trie.size == num_threads * per_thread

    def test_concurrent_reads_and_writes(self, empty_trie):
        errors = []

        def writer():
            for i in range(200):
                try:
                    empty_trie.insert(f"key_{i}", weight=i)
                except Exception as e:
                    errors.append(e)

        def reader():
            for i in range(200):
                try:
                    empty_trie.search(f"key_{i}")
                except Exception as e:
                    errors.append(e)

        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=writer))
            threads.append(threading.Thread(target=reader))
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_concurrent_updates(self, empty_trie):
        empty_trie.insert("counter", weight=0)
        errors = []

        def increment():
            try:
                for _ in range(100):
                    empty_trie.update_weight("counter", weight=1, accumulate=True)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=increment) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert empty_trie.get_weight("counter") == 1000


class TestCaseInsensitiveKeyNormalization:
    def test_insert_different_case_merges(self, empty_trie):
        empty_trie.insert("Apple", weight=10)
        empty_trie.insert("apple", weight=5)
        assert empty_trie.size == 1
        assert empty_trie.get_weight("Apple") == 15
        assert empty_trie.get_weight("apple") == 15
        assert empty_trie.get_weight("APPLE") == 15

    def test_contains_case_insensitive(self, empty_trie):
        empty_trie.insert("Hello", weight=10)
        assert empty_trie.contains("hello") is True
        assert empty_trie.contains("HELLO") is True
        assert empty_trie.contains("Hello") is True
        assert empty_trie.contains("HeLLo") is True

    def test_get_weight_case_insensitive(self, empty_trie):
        empty_trie.insert("Test", weight=20)
        assert empty_trie.get_weight("test") == 20
        assert empty_trie.get_weight("TEST") == 20
        assert empty_trie.get_weight("Test") == 20

    def test_update_weight_case_insensitive(self, empty_trie):
        empty_trie.insert("Test", weight=10)
        empty_trie.update_weight("test", weight=5, accumulate=True)
        assert empty_trie.get_weight("Test") == 15
        assert empty_trie.size == 1

    def test_update_weight_override_case_insensitive(self, empty_trie):
        empty_trie.insert("Test", weight=10)
        empty_trie.update_weight("TEST", weight=100)
        assert empty_trie.get_weight("test") == 100

    def test_update_weight_nonexistent_inserts(self, empty_trie):
        empty_trie.insert("Apple", weight=10)
        empty_trie.update_weight("banana", weight=5)
        assert empty_trie.size == 2
        assert empty_trie.get_weight("Banana") == 5

    def test_delete_case_insensitive(self, empty_trie):
        empty_trie.insert("Hello", weight=10)
        assert empty_trie.delete("hello") is True
        assert empty_trie.size == 0
        assert empty_trie.contains("Hello") is False

    def test_delete_case_insensitive_nonexistent(self, empty_trie):
        empty_trie.insert("Hello", weight=10)
        assert empty_trie.delete("world") is False
        assert empty_trie.size == 1

    def test_search_case_insensitive_returns_original(self, empty_trie):
        empty_trie.insert("ApplePie", weight=10)
        results = empty_trie.search("apple")
        assert len(results) == 1
        assert results[0].word == "ApplePie"

    def test_get_all_words_returns_original_case(self, empty_trie):
        empty_trie.insert("Apple", weight=10)
        empty_trie.insert("Banana", weight=5)
        words = empty_trie.get_all_words()
        assert "Apple" in words
        assert "Banana" in words

    def test_fuzzy_search_case_insensitive(self, empty_trie):
        empty_trie.insert("HelloWorld", weight=10)
        results = empty_trie.search("halloworld", fuzzy=True, fuzzy_threshold=1)
        assert len(results) == 1
        assert results[0].word == "HelloWorld"
        assert results[0].is_fuzzy is True

    def test_case_sensitive_mode_keeps_separate(self):
        trie = TrieAutocomplete(case_sensitive=True)
        trie.insert("Apple", weight=10)
        trie.insert("apple", weight=5)
        assert trie.size == 2
        assert trie.get_weight("Apple") == 10
        assert trie.get_weight("apple") == 5
        assert trie.contains("APPLE") is False

    def test_duplicate_insert_case_preserves_first_original(self, empty_trie):
        empty_trie.insert("Apple", weight=10)
        empty_trie.insert("apple", weight=5)
        assert empty_trie.get_original_word("apple") == "Apple"
        results = empty_trie.search("app")
        assert results[0].word == "Apple"

    def test_update_weight_preserves_original_case(self, empty_trie):
        empty_trie.insert("HelloWorld", weight=10)
        empty_trie.update_weight("helloworld", weight=20)
        assert empty_trie.get_original_word("HELLOWORLD") == "HelloWorld"
        results = empty_trie.search("hello")
        assert results[0].word == "HelloWorld"


class TestUpdateWord:
    def test_update_word_basic(self, empty_trie):
        empty_trie.insert("apple", weight=10)
        assert empty_trie.update_word("apple", "banana") is True
        assert empty_trie.contains("apple") is False
        assert empty_trie.contains("banana") is True
        assert empty_trie.get_weight("banana") == 10
        assert empty_trie.size == 1

    def test_update_word_preserves_weight(self, empty_trie):
        empty_trie.insert("test", weight=42)
        empty_trie.update_word("test", "new_test")
        assert empty_trie.get_weight("new_test") == 42

    def test_update_word_case_insensitive_old(self, empty_trie):
        empty_trie.insert("Apple", weight=10)
        assert empty_trie.update_word("apple", "banana") is True
        assert empty_trie.contains("Apple") is False
        assert empty_trie.contains("banana") is True

    def test_update_word_nonexistent_returns_false(self, empty_trie):
        assert empty_trie.update_word("nonexistent", "new") is False
        assert empty_trie.size == 0

    def test_update_word_search_results_reflect_change(self, empty_trie):
        empty_trie.insert("apple", weight=15)
        empty_trie.insert("application", weight=10)
        results_before = empty_trie.search("app")
        words_before = [r.word for r in results_before]
        assert "apple" in words_before

        empty_trie.update_word("apple", "banana")
        results_after = empty_trie.search("app")
        words_after = [r.word for r in results_after]
        assert "apple" not in words_after
        assert "banana" not in words_after

        banana_results = empty_trie.search("ban")
        assert len(banana_results) == 1
        assert banana_results[0].word == "banana"
        assert banana_results[0].weight == 15

    def test_update_word_same_normalized_updates_original(self, empty_trie):
        empty_trie.insert("apple", weight=10)
        assert empty_trie.update_word("apple", "Apple") is True
        assert empty_trie.size == 1
        assert empty_trie.get_original_word("apple") == "Apple"
        results = empty_trie.search("app")
        assert results[0].word == "Apple"
        assert results[0].weight == 10

    def test_update_word_same_word_noop(self, empty_trie):
        empty_trie.insert("test", weight=10)
        assert empty_trie.update_word("test", "test") is True
        assert empty_trie.size == 1
        assert empty_trie.get_weight("test") == 10

    def test_update_word_get_all_words_updated(self, empty_trie):
        empty_trie.insert("old", weight=5)
        empty_trie.update_word("old", "new")
        words = empty_trie.get_all_words()
        assert "old" not in words
        assert "new" in words

    def test_update_word_fuzzy_search_uses_new_word(self, empty_trie):
        empty_trie.insert("apple", weight=10)
        empty_trie.update_word("apple", "banana")
        results = empty_trie.search("banan", fuzzy=True, fuzzy_threshold=1)
        assert len(results) == 1
        assert results[0].word == "banana"

    def test_update_word_empty_old_raises(self, empty_trie):
        with pytest.raises(EmptyWordError):
            empty_trie.update_word("", "new")

    def test_update_word_empty_new_raises(self, empty_trie):
        empty_trie.insert("old", weight=5)
        with pytest.raises(EmptyWordError):
            empty_trie.update_word("old", "")

    def test_update_word_blank_old_raises(self, empty_trie):
        with pytest.raises(EmptyWordError):
            empty_trie.update_word("   ", "new")

    def test_update_word_blank_new_raises(self, empty_trie):
        empty_trie.insert("old", weight=5)
        with pytest.raises(EmptyWordError):
            empty_trie.update_word("old", "  \t  ")

    def test_update_word_chinese(self, empty_trie):
        empty_trie.insert("中国", weight=10)
        assert empty_trie.update_word("中国", "中华人民共和国") is True
        assert empty_trie.contains("中国") is False
        assert empty_trie.contains("中华人民共和国") is True
        assert empty_trie.get_weight("中华人民共和国") == 10
        results = empty_trie.search("中华")
        assert len(results) == 1
        assert results[0].word == "中华人民共和国"

    def test_update_word_case_sensitive_mode(self):
        trie = TrieAutocomplete(case_sensitive=True)
        trie.insert("Apple", weight=10)
        trie.insert("apple", weight=5)
        assert trie.update_word("Apple", "Banana") is True
        assert trie.size == 2
        assert trie.contains("Banana") is True
        assert trie.get_weight("Banana") == 10
        assert trie.contains("apple") is True
        assert trie.get_weight("apple") == 5

    def test_update_word_sorting_unchanged(self, empty_trie):
        empty_trie.insert("a", weight=5)
        empty_trie.insert("b", weight=20)
        empty_trie.insert("c", weight=10)
        results_before = empty_trie.search("")
        assert results_before[0].word == "b"

        empty_trie.update_word("b", "z")
        results_after = empty_trie.search("")
        assert results_after[0].word == "z"
        assert results_after[0].weight == 20
