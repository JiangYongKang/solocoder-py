import time

import pytest

from solocoder_py.fuzzy_match import FuzzyMatcher, MatchResult, levenshtein_distance


class TestLevenshteinDistance:
    def test_identical_strings(self):
        assert levenshtein_distance("hello", "hello") == 0

    def test_empty_both(self):
        assert levenshtein_distance("", "") == 0

    def test_empty_vs_nonempty(self):
        assert levenshtein_distance("", "abc") == 3
        assert levenshtein_distance("abc", "") == 3

    def test_single_insertion(self):
        assert levenshtein_distance("cat", "cart") == 1

    def test_single_deletion(self):
        assert levenshtein_distance("cart", "cat") == 1

    def test_single_substitution(self):
        assert levenshtein_distance("cat", "bat") == 1

    def test_multiple_edits(self):
        assert levenshtein_distance("kitten", "sitting") == 3

    def test_completely_different(self):
        assert levenshtein_distance("abc", "xyz") == 3

    def test_single_character_strings(self):
        assert levenshtein_distance("a", "b") == 1
        assert levenshtein_distance("a", "a") == 0

    def test_unicode_strings(self):
        assert levenshtein_distance("你好", "你好世界") == 2
        assert levenshtein_distance("café", "cafe") == 1

    def test_longer_strings(self):
        s1 = "abcdefghij"
        s2 = "klmnopqrst"
        assert levenshtein_distance(s1, s2) == 10

    def test_prefix_match(self):
        assert levenshtein_distance("prefix", "prefixsuffix") == 6

    def test_suffix_match(self):
        assert levenshtein_distance("suffixprefix", "prefix") == 6


class TestFuzzyMatcherBasicMatching:
    def test_exact_match(self):
        matcher = FuzzyMatcher(["apple", "banana", "cherry"])
        results = matcher.match("apple", threshold=0)
        assert len(results) == 1
        assert results[0].candidate == "apple"
        assert results[0].distance == 0

    def test_no_match_with_zero_threshold(self):
        matcher = FuzzyMatcher(["apple", "banana", "cherry"])
        results = matcher.match("appla", threshold=0)
        assert len(results) == 0

    def test_fuzzy_match_with_threshold(self):
        matcher = FuzzyMatcher(["apple", "banana", "cherry"])
        results = matcher.match("appla", threshold=1)
        assert len(results) == 1
        assert results[0].candidate == "apple"
        assert results[0].distance == 1

    def test_multiple_matches_sorted_by_distance(self):
        matcher = FuzzyMatcher(["cat", "bat", "hat", "rat", "car"])
        results = matcher.match("cat", threshold=1)
        distances = [r.distance for r in results]
        assert distances == sorted(distances)
        exact = [r for r in results if r.candidate == "cat"]
        assert len(exact) == 1
        assert exact[0].distance == 0

    def test_tie_breaking_by_lexicographic_order(self):
        matcher = FuzzyMatcher(["bat", "cat", "hat", "rat"])
        results = matcher.match("zat", threshold=1)
        same_distance = [r.candidate for r in results if r.distance == 1]
        assert same_distance == sorted(same_distance)

    def test_max_results_limits_output(self):
        matcher = FuzzyMatcher(["cat", "bat", "hat", "rat", "mat"])
        results = matcher.match("cat", threshold=1, max_results=2)
        assert len(results) == 2

    def test_max_results_zero_returns_empty(self):
        matcher = FuzzyMatcher(["apple", "banana"])
        results = matcher.match("apple", threshold=1, max_results=0)
        assert len(results) == 0

    def test_default_threshold_is_zero(self):
        matcher = FuzzyMatcher(["hello"])
        results = matcher.match("hello")
        assert len(results) == 1
        results2 = matcher.match("helo")
        assert len(results2) == 0


class TestEmptyQueryAndCandidates:
    def test_empty_query_against_candidates(self):
        matcher = FuzzyMatcher(["a", "ab", "abc"])
        results = matcher.match("", threshold=1)
        assert len(results) == 1
        assert results[0].candidate == "a"
        assert results[0].distance == 1

    def test_empty_query_zero_threshold(self):
        matcher = FuzzyMatcher(["a", "ab"])
        results = matcher.match("", threshold=0)
        assert len(results) == 0

    def test_empty_candidate_set(self):
        matcher = FuzzyMatcher([])
        results = matcher.match("hello", threshold=5)
        assert len(results) == 0

    def test_empty_query_empty_candidates(self):
        matcher = FuzzyMatcher([])
        results = matcher.match("", threshold=0)
        assert len(results) == 0

    def test_query_equal_to_empty_candidate(self):
        matcher = FuzzyMatcher([""])
        results = matcher.match("", threshold=0)
        assert len(results) == 1
        assert results[0].distance == 0

    def test_nonempty_query_against_empty_candidate(self):
        matcher = FuzzyMatcher([""])
        results = matcher.match("abc", threshold=3)
        assert len(results) == 1
        assert results[0].candidate == ""
        assert results[0].distance == 3


class TestThresholdZero:
    def test_only_exact_matches(self):
        matcher = FuzzyMatcher(["abc", "abd", "ab"])
        results = matcher.match("abc", threshold=0)
        assert len(results) == 1
        assert results[0].candidate == "abc"

    def test_no_partial_matches(self):
        matcher = FuzzyMatcher(["abc", "abcd"])
        results = matcher.match("abc", threshold=0)
        assert len(results) == 1

    def test_duplicate_candidates(self):
        matcher = FuzzyMatcher(["abc", "abc"])
        results = matcher.match("abc", threshold=0)
        assert len(results) == 2


class TestQueryEqualsCandidate:
    def test_exact_match_with_large_threshold(self):
        matcher = FuzzyMatcher(["hello", "world"])
        results = matcher.match("hello", threshold=100)
        hello_results = [r for r in results if r.candidate == "hello"]
        assert len(hello_results) == 1
        assert hello_results[0].distance == 0

    def test_exact_match_distance_zero(self):
        matcher = FuzzyMatcher(["test"])
        results = matcher.match("test", threshold=0)
        assert results[0].distance == 0


class TestCandidateManagement:
    def test_add_candidate(self):
        matcher = FuzzyMatcher()
        matcher.add_candidate("apple")
        results = matcher.match("apple", threshold=0)
        assert len(results) == 1

    def test_add_multiple_candidates(self):
        matcher = FuzzyMatcher()
        matcher.add_candidate("a")
        matcher.add_candidate("b")
        matcher.add_candidate("c")
        assert matcher.candidate_count == 3

    def test_remove_candidate(self):
        matcher = FuzzyMatcher(["apple", "banana"])
        assert matcher.remove_candidate("apple") is True
        results = matcher.match("apple", threshold=0)
        assert len(results) == 0

    def test_remove_nonexistent_candidate(self):
        matcher = FuzzyMatcher(["apple"])
        assert matcher.remove_candidate("orange") is False

    def test_candidates_property_returns_copy(self):
        matcher = FuzzyMatcher(["a", "b"])
        cands = matcher.candidates
        cands.append("c")
        assert matcher.candidate_count == 2

    def test_candidate_count(self):
        matcher = FuzzyMatcher(["a", "b", "c"])
        assert matcher.candidate_count == 3
        matcher.add_candidate("d")
        assert matcher.candidate_count == 4
        matcher.remove_candidate("a")
        assert matcher.candidate_count == 3

    def test_init_with_none_candidates(self):
        matcher = FuzzyMatcher(None)
        assert matcher.candidate_count == 0


class TestLengthPruning:
    def test_length_filter_removes_far_candidates(self):
        candidates = ["a", "ab", "abc", "abcd", "abcde", "abcdefghij"]
        matcher = FuzzyMatcher(candidates)
        results = matcher.match("abc", threshold=2)
        for r in results:
            assert abs(len(r.candidate) - 3) <= 2

    def test_length_filter_with_threshold_one(self):
        candidates = ["a", "ab", "abc", "abcd", "abcde"]
        matcher = FuzzyMatcher(candidates)
        results = matcher.match("abc", threshold=1)
        result_lengths = [len(r.candidate) for r in results]
        for length in result_lengths:
            assert 2 <= length <= 4

    def test_length_pruning_efficiency(self):
        short = ["a" * i for i in range(1, 6)]
        long = ["a" * i for i in range(100, 200)]
        matcher = FuzzyMatcher(short + long)
        results = matcher.match("aaa", threshold=2)
        for r in results:
            assert len(r.candidate) <= 7

    def test_all_candidates_pruned_by_length(self):
        matcher = FuzzyMatcher(["a", "abcdefghij"])
        results = matcher.match("abc", threshold=1)
        for r in results:
            assert len(r.candidate) >= 2 and len(r.candidate) <= 4


class TestSorting:
    def test_sorted_by_distance_ascending(self):
        matcher = FuzzyMatcher(["abc", "abd", "abx", "xyz"])
        results = matcher.match("abc", threshold=3)
        distances = [r.distance for r in results]
        assert distances == sorted(distances)

    def test_same_distance_sorted_lexicographically(self):
        matcher = FuzzyMatcher(["cbb", "abb", "bbb"])
        results = matcher.match("abc", threshold=2)
        same_dist = [r.candidate for r in results if r.distance == results[0].distance]
        if len(same_dist) > 1:
            assert same_dist == sorted(same_dist)

    def test_max_results_respects_sort_order(self):
        matcher = FuzzyMatcher(["cat", "bat", "rat", "hat", "mat"])
        results = matcher.match("cat", threshold=1, max_results=1)
        assert len(results) == 1
        assert results[0].distance == 0
        assert results[0].candidate == "cat"


class TestInvalidInputs:
    def test_negative_threshold_raises(self):
        matcher = FuzzyMatcher(["test"])
        with pytest.raises(ValueError, match="threshold must be non-negative"):
            matcher.match("test", threshold=-1)

    def test_negative_max_results_raises(self):
        matcher = FuzzyMatcher(["test"])
        with pytest.raises(ValueError, match="max_results must be non-negative"):
            matcher.match("test", max_results=-1)

    def test_very_large_threshold(self):
        matcher = FuzzyMatcher(["a", "ab", "abc"])
        results = matcher.match("xyz", threshold=1000)
        assert len(results) == 3


class TestLargeCandidateSet:
    def test_large_candidate_set_performance(self):
        candidates = [f"candidate_{i:04d}" for i in range(10000)]
        matcher = FuzzyMatcher(candidates)
        start = time.time()
        results = matcher.match("candidate_0050", threshold=2)
        elapsed = time.time() - start
        assert elapsed < 2.0
        assert len(results) > 0
        exact = [r for r in results if r.distance == 0]
        assert len(exact) == 1

    def test_large_candidate_set_with_small_threshold(self):
        candidates = [f"c_{i:06d}" for i in range(50000)]
        matcher = FuzzyMatcher(candidates)
        start = time.time()
        results = matcher.match("c_000050", threshold=1)
        elapsed = time.time() - start
        assert elapsed < 5.0
        assert len(results) > 0

    def test_length_pruning_reduces_computation_for_large_set(self):
        short_candidates = [f"s{i}" for i in range(5000)]
        long_candidates = ["x" * 100 + f"{i}" for i in range(5000)]
        matcher = FuzzyMatcher(short_candidates + long_candidates)
        start = time.time()
        results = matcher.match("s0", threshold=1)
        elapsed = time.time() - start
        for r in results:
            assert len(r.candidate) <= 3


class TestMatchResultDataclass:
    def test_match_result_fields(self):
        r = MatchResult(candidate="test", distance=2)
        assert r.candidate == "test"
        assert r.distance == 2

    def test_match_result_equality(self):
        r1 = MatchResult(candidate="test", distance=1)
        r2 = MatchResult(candidate="test", distance=1)
        assert r1 == r2

    def test_match_result_inequality(self):
        r1 = MatchResult(candidate="a", distance=1)
        r2 = MatchResult(candidate="b", distance=1)
        assert r1 != r2


class TestBoundedLevenshteinInternal:
    def test_bounded_returns_same_as_unbounded_when_within_threshold(self):
        from solocoder_py.fuzzy_match.matcher import levenshtein_distance_bounded

        pairs = [
            ("kitten", "sitting"),
            ("saturday", "sunday"),
            ("", "abc"),
            ("abc", ""),
            ("hello", "hello"),
            ("a", "b"),
        ]
        for s1, s2 in pairs:
            full_dist = levenshtein_distance(s1, s2)
            bounded = levenshtein_distance_bounded(s1, s2, threshold=full_dist + 1)
            assert bounded == full_dist, f"Failed for ({s1}, {s2})"

    def test_bounded_returns_threshold_plus_one_when_exceeded(self):
        from solocoder_py.fuzzy_match.matcher import levenshtein_distance_bounded

        assert levenshtein_distance_bounded("abc", "xyz", threshold=1) == 2
        assert levenshtein_distance_bounded("a", "xyz", threshold=1) == 2

    def test_bounded_length_difference_exceeds_threshold(self):
        from solocoder_py.fuzzy_match.matcher import levenshtein_distance_bounded

        assert levenshtein_distance_bounded("a", "abcde", threshold=2) == 3


class TestBoundedRowMinEarlyTermination:
    def test_row_min_early_termination_completely_different_equal_length(self):
        from solocoder_py.fuzzy_match.matcher import levenshtein_distance_bounded

        s1 = "abcdefghij"
        s2 = "klmnopqrst"
        full = levenshtein_distance(s1, s2)
        assert full == 10
        bounded = levenshtein_distance_bounded(s1, s2, threshold=3)
        assert bounded == 4

    def test_row_min_early_termination_long_vs_short(self):
        from solocoder_py.fuzzy_match.matcher import levenshtein_distance_bounded

        s1 = "aaaaaaaaaa"
        s2 = "bbbbbb"
        full = levenshtein_distance(s1, s2)
        assert full == 10
        bounded = levenshtein_distance_bounded(s1, s2, threshold=2)
        assert bounded == 3

    def test_row_min_early_termination_short_vs_long(self):
        from solocoder_py.fuzzy_match.matcher import levenshtein_distance_bounded

        bounded = levenshtein_distance_bounded("abc", "xyzabcdefghij", threshold=2)
        assert bounded == 3

    def test_row_min_early_termination_at_row_one(self):
        from solocoder_py.fuzzy_match.matcher import levenshtein_distance_bounded

        bounded = levenshtein_distance_bounded("zzzzz", "aaaaa", threshold=0)
        assert bounded == 1

    def test_row_min_early_termination_mid_computation(self):
        from solocoder_py.fuzzy_match.matcher import levenshtein_distance_bounded

        s1 = "aabbb"
        s2 = "bbbaa"
        full = levenshtein_distance(s1, s2)
        assert full == 4
        bounded = levenshtein_distance_bounded(s1, s2, threshold=2)
        assert bounded == 3

    def test_row_min_early_termination_various_thresholds(self):
        from solocoder_py.fuzzy_match.matcher import levenshtein_distance_bounded

        s1 = "abcdef"
        s2 = "uvwxyz"
        full = levenshtein_distance(s1, s2)
        assert full == 6
        for t in range(6):
            bounded = levenshtein_distance_bounded(s1, s2, threshold=t)
            if full <= t:
                assert bounded == full
            else:
                assert bounded == t + 1

    def test_row_min_early_termination_with_partial_overlap(self):
        from solocoder_py.fuzzy_match.matcher import levenshtein_distance_bounded

        s1 = "aaabbb"
        s2 = "bbbccc"
        full = levenshtein_distance(s1, s2)
        bounded_tight = levenshtein_distance_bounded(s1, s2, threshold=full - 1)
        assert bounded_tight == full
        bounded_loose = levenshtein_distance_bounded(s1, s2, threshold=full)
        assert bounded_loose == full

    def test_row_min_termination_long_strings_tight_threshold(self):
        from solocoder_py.fuzzy_match.matcher import levenshtein_distance_bounded

        s1 = "a" * 50
        s2 = "b" * 50
        bounded = levenshtein_distance_bounded(s1, s2, threshold=1)
        assert bounded == 2


class TestBoundedWindowBoundary:
    def test_window_left_boundary_active(self):
        from solocoder_py.fuzzy_match.matcher import levenshtein_distance_bounded

        s1 = "abcdefghij"
        s2 = "abcx"
        full = levenshtein_distance(s1, s2)
        assert full == 7
        bounded = levenshtein_distance_bounded(s1, s2, threshold=1)
        assert bounded == 2

    def test_window_right_boundary_active(self):
        from solocoder_py.fuzzy_match.matcher import levenshtein_distance_bounded

        s1 = "abcx"
        s2 = "abcdefghij"
        full = levenshtein_distance(s1, s2)
        assert full == 7
        bounded = levenshtein_distance_bounded(s1, s2, threshold=1)
        assert bounded == 2

    def test_window_both_boundaries_active(self):
        from solocoder_py.fuzzy_match.matcher import levenshtein_distance_bounded

        s1 = "abcdefghij"
        s2 = "efghijklmn"
        bounded = levenshtein_distance_bounded(s1, s2, threshold=2)
        full = levenshtein_distance(s1, s2)
        if full <= 2:
            assert bounded == full
        else:
            assert bounded == 3

    def test_window_boundary_with_threshold_one(self):
        from solocoder_py.fuzzy_match.matcher import levenshtein_distance_bounded

        s1 = "abcde"
        s2 = "xabcde"
        full = levenshtein_distance(s1, s2)
        assert full == 1
        bounded = levenshtein_distance_bounded(s1, s2, threshold=1)
        assert bounded == 1

    def test_window_boundary_consistency_with_unbounded(self):
        from solocoder_py.fuzzy_match.matcher import levenshtein_distance_bounded

        pairs = [
            ("abcdef", "abcxef", 1),
            ("abcdef", "abqdef", 1),
            ("abcdef", "abwdef", 2),
            ("xabc", "abc", 1),
            ("abcx", "abc", 1),
            ("abcdef", "xbcdef", 1),
            ("abcdef", "abcde", 1),
        ]
        for s1, s2, t in pairs:
            full = levenshtein_distance(s1, s2)
            bounded = levenshtein_distance_bounded(s1, s2, threshold=t)
            if full <= t:
                assert bounded == full, f"Failed for ({s1}, {s2}, t={t})"
            else:
                assert bounded == t + 1, f"Failed for ({s1}, {s2}, t={t})"

    def test_window_truncation_with_unequal_lengths(self):
        from solocoder_py.fuzzy_match.matcher import levenshtein_distance_bounded

        s1 = "abcdefgh"
        s2 = "abc"
        full = levenshtein_distance(s1, s2)
        for t in range(full + 2):
            bounded = levenshtein_distance_bounded(s1, s2, threshold=t)
            if full <= t:
                assert bounded == full, f"Failed for t={t}"
            else:
                assert bounded == t + 1, f"Failed for t={t}"

    def test_window_truncation_swapped_unequal_lengths(self):
        from solocoder_py.fuzzy_match.matcher import levenshtein_distance_bounded

        s1 = "abc"
        s2 = "abcdefgh"
        full = levenshtein_distance(s1, s2)
        for t in range(full + 2):
            bounded = levenshtein_distance_bounded(s1, s2, threshold=t)
            if full <= t:
                assert bounded == full, f"Failed for t={t}"
            else:
                assert bounded == t + 1, f"Failed for t={t}"


class TestLengthPruningPerformance:
    def test_wide_length_distribution_does_not_degrade(self):
        candidates = []
        for length in range(1, 1001):
            candidates.append("a" * length)
        matcher = FuzzyMatcher(candidates)
        start = time.time()
        results = matcher.match("a" * 50, threshold=2)
        elapsed = time.time() - start
        assert elapsed < 1.0
        for r in results:
            assert 48 <= len(r.candidate) <= 52

    def test_sparse_length_keys_still_efficient(self):
        candidates = []
        for length in [1, 5, 10, 50, 100, 500, 1000, 5000, 10000]:
            for offset in range(10):
                candidates.append(chr(ord('a') + offset) * length)
        matcher = FuzzyMatcher(candidates)
        start = time.time()
        results = matcher.match("a" * 50, threshold=5)
        elapsed = time.time() - start
        assert elapsed < 1.0
        for r in results:
            assert 45 <= len(r.candidate) <= 55

    def test_many_length_categories_range_iteration(self):
        candidates = []
        for length in range(1, 2001):
            candidates.append("z" * length)
        matcher = FuzzyMatcher(candidates)
        start = time.time()
        for _ in range(100):
            matcher.match("a" * 100, threshold=3)
        elapsed = time.time() - start
        assert elapsed < 2.0
