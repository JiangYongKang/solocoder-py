import pytest

from solocoder_py.dedup import (
    InvalidThresholdError,
    UnionFind,
    fuzzy_group,
    fuzzy_match_pairs,
    levenshtein_distance,
    similarity,
)


class TestLevenshteinDistance:
    def test_identical_strings(self):
        assert levenshtein_distance("hello", "hello") == 0

    def test_empty_strings(self):
        assert levenshtein_distance("", "") == 0
        assert levenshtein_distance("abc", "") == 3
        assert levenshtein_distance("", "abc") == 3

    def test_single_edit(self):
        assert levenshtein_distance("cat", "cart") == 1
        assert levenshtein_distance("cart", "cat") == 1
        assert levenshtein_distance("cat", "bat") == 1

    def test_multiple_edits(self):
        assert levenshtein_distance("kitten", "sitting") == 3
        assert levenshtein_distance("saturday", "sunday") == 3

    def test_completely_different(self):
        assert levenshtein_distance("abc", "xyz") == 3


class TestSimilarity:
    def test_identical_strings(self):
        assert similarity("hello", "hello") == 1.0

    def test_completely_different(self):
        assert similarity("abc", "xyz") == 0.0

    def test_empty_strings(self):
        assert similarity("", "") == 1.0
        assert similarity("", "abc") == 0.0
        assert similarity("abc", "") == 0.0

    def test_none_values(self):
        assert similarity(None, None) == 1.0
        assert similarity(None, "abc") == 0.0
        assert similarity("abc", None) == 0.0

    def test_partial_similarity(self):
        sim = similarity("hello", "hallo")
        assert 0.0 < sim < 1.0

    def test_single_character_diff(self):
        sim = similarity("cat", "bat")
        assert sim == pytest.approx(2 / 3)

    def test_non_string_values(self):
        sim = similarity(123, 124)
        assert 0.0 < sim < 1.0


class TestUnionFind:
    def test_initialization(self):
        uf = UnionFind(5)
        for i in range(5):
            assert uf.find(i) == i

    def test_union_and_find(self):
        uf = UnionFind(5)
        uf.union(0, 1)
        assert uf.find(0) == uf.find(1)
        assert uf.find(0) != uf.find(2)

    def test_multiple_unions(self):
        uf = UnionFind(5)
        uf.union(0, 1)
        uf.union(1, 2)
        uf.union(3, 4)
        assert uf.find(0) == uf.find(2)
        assert uf.find(3) == uf.find(4)
        assert uf.find(0) != uf.find(3)

    def test_transitivity(self):
        uf = UnionFind(4)
        uf.union(0, 1)
        uf.union(1, 2)
        uf.union(2, 3)
        assert uf.find(0) == uf.find(3)

    def test_get_groups(self):
        uf = UnionFind(5)
        uf.union(0, 1)
        uf.union(0, 2)
        uf.union(3, 4)
        groups = uf.get_groups()
        assert len(groups) == 2
        group_sizes = sorted([len(v) for v in groups.values()])
        assert group_sizes == [2, 3]

    def test_union_same_element(self):
        uf = UnionFind(3)
        result = uf.union(1, 1)
        assert result is False
        assert uf.find(1) == 1

    def test_path_compression(self):
        uf = UnionFind(4)
        uf.union(0, 1)
        uf.union(1, 2)
        uf.union(2, 3)
        root_before = uf.find(0)
        root_after = uf.find(0)
        assert root_before == root_after


class TestFuzzyMatchPairs:
    def test_empty_records(self):
        pairs = fuzzy_match_pairs([], fields=["name"], threshold=0.5)
        assert pairs == []

    def test_single_record(self):
        records = [{"name": "Alice"}]
        pairs = fuzzy_match_pairs(records, fields=["name"], threshold=0.5)
        assert pairs == []

    def test_identical_records(self):
        records = [
            {"name": "Alice"},
            {"name": "Alice"},
        ]
        pairs = fuzzy_match_pairs(records, fields=["name"], threshold=0.8)
        assert len(pairs) == 1
        assert pairs[0].score == 1.0

    def test_above_threshold(self):
        records = [
            {"name": "Alice"},
            {"name": "Alicia"},
        ]
        pairs = fuzzy_match_pairs(records, fields=["name"], threshold=0.5)
        assert len(pairs) == 1
        assert pairs[0].score >= 0.5

    def test_below_threshold(self):
        records = [
            {"name": "Alice"},
            {"name": "Bob"},
        ]
        pairs = fuzzy_match_pairs(records, fields=["name"], threshold=0.8)
        assert pairs == []

    def test_multiple_fields(self):
        records = [
            {"first": "John", "last": "Doe"},
            {"first": "Jon", "last": "Doe"},
        ]
        pairs = fuzzy_match_pairs(
            records, fields=["first", "last"], threshold=0.7
        )
        assert len(pairs) == 1
        assert "first" in pairs[0].matched_fields
        assert "last" in pairs[0].matched_fields

    def test_field_weights(self):
        records = [
            {"first": "John", "last": "Doe"},
            {"first": "Jon", "last": "Smith"},
        ]
        pairs = fuzzy_match_pairs(
            records,
            fields=["first", "last"],
            threshold=0.3,
            field_weights={"first": 10, "last": 1},
        )
        assert len(pairs) == 1

    def test_invalid_threshold_zero(self):
        with pytest.raises(InvalidThresholdError):
            fuzzy_match_pairs([{"n": "a"}], fields=["n"], threshold=0)

    def test_invalid_threshold_negative(self):
        with pytest.raises(InvalidThresholdError):
            fuzzy_match_pairs([{"n": "a"}], fields=["n"], threshold=-0.5)

    def test_invalid_threshold_over_one(self):
        with pytest.raises(InvalidThresholdError):
            fuzzy_match_pairs([{"n": "a"}], fields=["n"], threshold=1.5)

    def test_empty_fields(self):
        with pytest.raises(InvalidThresholdError):
            fuzzy_match_pairs([{"n": "a"}], fields=[], threshold=0.5)


class TestFuzzyGroup:
    def test_empty_records(self):
        groups = fuzzy_group([], fields=["name"], threshold=0.8)
        assert groups == []

    def test_single_record(self):
        records = [{"name": "Alice"}]
        groups = fuzzy_group(records, fields=["name"], threshold=0.8)
        assert len(groups) == 1
        assert len(groups[0].records) == 1
        assert groups[0].is_exact is False

    def test_all_identical(self):
        records = [
            {"name": "Alice"},
            {"name": "Alice"},
            {"name": "Alice"},
        ]
        groups = fuzzy_group(records, fields=["name"], threshold=0.8)
        assert len(groups) == 1
        assert len(groups[0].records) == 3

    def test_all_unique(self):
        records = [
            {"name": "Alice"},
            {"name": "Bob"},
            {"name": "Charlie"},
        ]
        groups = fuzzy_group(records, fields=["name"], threshold=0.8)
        assert len(groups) == 3

    def test_transitive_matching(self):
        records = [
            {"name": "abcde"},
            {"name": "abcdf"},
            {"name": "abcdg"},
        ]
        groups = fuzzy_group(records, fields=["name"], threshold=0.7)
        assert len(groups) == 1
        assert len(groups[0].records) == 3
        assert len(groups[0].fuzzy_pairs) >= 2

    def test_transitive_chain(self):
        records = [
            {"name": "aaaaa"},
            {"name": "aaaab"},
            {"name": "aaabb"},
            {"name": "aabbb"},
        ]
        groups = fuzzy_group(records, fields=["name"], threshold=0.6)
        assert len(groups) == 1
        assert len(groups[0].records) == 4

    def test_two_separate_groups(self):
        records = [
            {"name": "Alice"},
            {"name": "Alicia"},
            {"name": "Bob"},
            {"name": "Bobby"},
        ]
        groups = fuzzy_group(records, fields=["name"], threshold=0.6)
        assert len(groups) == 2

    def test_empty_field_values(self):
        records = [
            {"name": ""},
            {"name": ""},
            {"name": "Alice"},
        ]
        groups = fuzzy_group(records, fields=["name"], threshold=0.8)
        empty_group = [g for g in groups if g.records[0]["name"] == ""][0]
        assert len(empty_group.records) == 2

    def test_none_field_values(self):
        records = [
            {"name": None},
            {"name": None},
            {"name": "Alice"},
        ]
        groups = fuzzy_group(records, fields=["name"], threshold=0.8)
        none_group = [g for g in groups if g.records[0].get("name") is None][0]
        assert len(none_group.records) == 2

    def test_mixed_empty_and_none(self):
        records = [
            {"name": ""},
            {"name": None},
        ]
        groups = fuzzy_group(records, fields=["name"], threshold=0.8)
        assert len(groups) == 2

    def test_indices_tracking(self):
        records = [
            {"name": "Alice"},
            {"name": "Bob"},
            {"name": "Alicia"},
        ]
        groups = fuzzy_group(records, fields=["name"], threshold=0.5)
        alice_group = [g for g in groups if len(g.records) == 2][0]
        assert sorted(alice_group.indices) == [0, 2]

    def test_match_score(self):
        records = [
            {"name": "Alice"},
            {"name": "Alicia"},
        ]
        groups = fuzzy_group(records, fields=["name"], threshold=0.5)
        assert len(groups) == 1
        assert 0.0 < groups[0].match_score < 1.0
