import pytest

from solocoder_py.dedup import (
    DedupGroup,
    MergeConflictError,
    UnknownStrategyError,
    merge_group,
    STRATEGY_FIRST,
    STRATEGY_LAST,
    STRATEGY_LONGEST_STRING,
    STRATEGY_MOST_COMMON,
    STRATEGY_FIRST_NON_EMPTY,
    STRATEGY_CUSTOM,
)


class TestMergeGroupBasic:
    def test_empty_group_raises(self):
        group = DedupGroup(records=[], indices=[], is_exact=True)
        with pytest.raises(MergeConflictError):
            merge_group(group)

    def test_single_record(self):
        group = DedupGroup(
            records=[{"name": "Alice", "age": 30}],
            indices=[0],
            is_exact=True,
        )
        result = merge_group(group)
        assert result.record == {"name": "Alice", "age": 30}
        assert result.conflict_fields == []
        assert result.merged_fields == []

    def test_identical_records(self):
        group = DedupGroup(
            records=[
                {"name": "Alice", "age": 30},
                {"name": "Alice", "age": 30},
            ],
            indices=[0, 1],
            is_exact=True,
        )
        result = merge_group(group)
        assert result.record == {"name": "Alice", "age": 30}
        assert result.conflict_fields == []
        assert result.merged_fields == []


class TestMergeStrategyFirst:
    def test_conflict_field_keeps_first(self):
        group = DedupGroup(
            records=[
                {"name": "Alice", "age": 30},
                {"name": "Alice Smith", "age": 31},
            ],
            indices=[0, 1],
            is_exact=True,
        )
        result = merge_group(group, strategy=STRATEGY_FIRST)
        assert result.record["name"] == "Alice"
        assert result.record["age"] == 30
        assert "name" in result.conflict_fields
        assert "age" in result.conflict_fields

    def test_three_records(self):
        group = DedupGroup(
            records=[
                {"val": 1},
                {"val": 2},
                {"val": 3},
            ],
            indices=[0, 1, 2],
            is_exact=True,
        )
        result = merge_group(group, strategy=STRATEGY_FIRST)
        assert result.record["val"] == 1


class TestMergeStrategyLast:
    def test_conflict_field_keeps_last(self):
        group = DedupGroup(
            records=[
                {"name": "Alice", "age": 30},
                {"name": "Alice Smith", "age": 31},
            ],
            indices=[0, 1],
            is_exact=True,
        )
        result = merge_group(group, strategy=STRATEGY_LAST)
        assert result.record["name"] == "Alice Smith"
        assert result.record["age"] == 31

    def test_three_records(self):
        group = DedupGroup(
            records=[
                {"val": 1},
                {"val": 2},
                {"val": 3},
            ],
            indices=[0, 1, 2],
            is_exact=True,
        )
        result = merge_group(group, strategy=STRATEGY_LAST)
        assert result.record["val"] == 3


class TestMergeStrategyLongestString:
    def test_longer_string_wins(self):
        group = DedupGroup(
            records=[
                {"name": "Al"},
                {"name": "Alice"},
                {"name": "Alicia"},
            ],
            indices=[0, 1, 2],
            is_exact=True,
        )
        result = merge_group(group, strategy=STRATEGY_LONGEST_STRING)
        assert result.record["name"] == "Alicia"

    def test_mixed_empty_and_strings(self):
        group = DedupGroup(
            records=[
                {"name": ""},
                {"name": "Alice"},
                {"name": None},
            ],
            indices=[0, 1, 2],
            is_exact=True,
        )
        result = merge_group(group, strategy=STRATEGY_LONGEST_STRING)
        assert result.record["name"] == "Alice"

    def test_numeric_values(self):
        group = DedupGroup(
            records=[
                {"val": 9},
                {"val": 100},
            ],
            indices=[0, 1],
            is_exact=True,
        )
        result = merge_group(group, strategy=STRATEGY_LONGEST_STRING)
        assert result.record["val"] == 100


class TestMergeStrategyMostCommon:
    def test_majority_value(self):
        group = DedupGroup(
            records=[
                {"color": "red"},
                {"color": "blue"},
                {"color": "red"},
                {"color": "green"},
                {"color": "red"},
            ],
            indices=[0, 1, 2, 3, 4],
            is_exact=True,
        )
        result = merge_group(group, strategy=STRATEGY_MOST_COMMON)
        assert result.record["color"] == "red"

    def test_tie_breaks_by_first(self):
        group = DedupGroup(
            records=[
                {"color": "red"},
                {"color": "blue"},
            ],
            indices=[0, 1],
            is_exact=True,
        )
        result = merge_group(group, strategy=STRATEGY_MOST_COMMON)
        assert result.record["color"] == "red"


class TestMergeStrategyFirstNonEmpty:
    def test_skips_empty_values(self):
        group = DedupGroup(
            records=[
                {"name": ""},
                {"name": None},
                {"name": "Alice"},
            ],
            indices=[0, 1, 2],
            is_exact=True,
        )
        result = merge_group(group, strategy=STRATEGY_FIRST_NON_EMPTY)
        assert result.record["name"] == "Alice"

    def test_all_empty_returns_first(self):
        group = DedupGroup(
            records=[
                {"name": ""},
                {"name": None},
                {"name": []},
            ],
            indices=[0, 1, 2],
            is_exact=True,
        )
        result = merge_group(group, strategy=STRATEGY_FIRST_NON_EMPTY)
        assert result.record["name"] == ""


class TestMergeStrategyCustom:
    def test_custom_merge_function(self):
        def sum_values(field: str, values: list):
            return sum(v for v in values if v is not None)

        group = DedupGroup(
            records=[
                {"amount": 100},
                {"amount": 200},
                {"amount": 300},
            ],
            indices=[0, 1, 2],
            is_exact=True,
        )
        result = merge_group(
            group,
            strategy=STRATEGY_CUSTOM,
            custom_merge=sum_values,
        )
        assert result.record["amount"] == 600

    def test_custom_without_function_raises(self):
        group = DedupGroup(
            records=[{"val": 1}, {"val": 2}],
            indices=[0, 1],
            is_exact=True,
        )
        with pytest.raises(UnknownStrategyError):
            merge_group(group, strategy=STRATEGY_CUSTOM)


class TestFieldSpecificStrategies:
    def test_different_strategies_per_field(self):
        group = DedupGroup(
            records=[
                {"name": "Al", "amount": 100, "note": ""},
                {"name": "Alice", "amount": 200, "note": None},
                {"name": "Alicia", "amount": 200, "note": "hello"},
            ],
            indices=[0, 1, 2],
            is_exact=True,
        )
        result = merge_group(
            group,
            strategy=STRATEGY_FIRST,
            field_strategies={
                "name": STRATEGY_LONGEST_STRING,
                "amount": STRATEGY_MOST_COMMON,
                "note": STRATEGY_FIRST_NON_EMPTY,
            },
        )
        assert result.record["name"] == "Alicia"
        assert result.record["amount"] == 200
        assert result.record["note"] == "hello"

    def test_unknown_field_falls_back_to_default(self):
        group = DedupGroup(
            records=[
                {"val": 1},
                {"val": 2},
            ],
            indices=[0, 1],
            is_exact=True,
        )
        result = merge_group(
            group,
            strategy=STRATEGY_LAST,
            field_strategies={},
        )
        assert result.record["val"] == 2


class TestFallbackStrategy:
    def test_custom_field_without_func_uses_fallback(self):
        group = DedupGroup(
            records=[
                {"name": "a", "val": 1},
                {"name": "b", "val": 2},
                {"name": "c", "val": 3},
            ],
            indices=[0, 1, 2],
            is_exact=True,
        )
        result = merge_group(
            group,
            strategy=STRATEGY_FIRST,
            custom_merge=None,
            field_strategies={"val": STRATEGY_CUSTOM},
            fallback_strategy=STRATEGY_LAST,
        )
        assert result.record["name"] == "a"
        assert result.record["val"] == 3


class TestUnknownStrategy:
    def test_unknown_strategy_raises(self):
        group = DedupGroup(
            records=[{"val": 1}],
            indices=[0],
            is_exact=True,
        )
        with pytest.raises(UnknownStrategyError):
            merge_group(group, strategy="invalid_strategy")


class TestMergedFieldsTracking:
    def test_merged_fields_list(self):
        group = DedupGroup(
            records=[
                {"a": 1, "b": 2, "c": 3},
                {"a": 1, "b": 20, "c": 30},
            ],
            indices=[0, 1],
            is_exact=True,
        )
        result = merge_group(group, strategy=STRATEGY_FIRST)
        assert set(result.conflict_fields) == {"b", "c"}
        assert set(result.merged_fields) == {"b", "c"}

    def test_no_conflicts(self):
        group = DedupGroup(
            records=[
                {"a": 1, "b": 2},
                {"a": 1, "b": 2},
            ],
            indices=[0, 1],
            is_exact=True,
        )
        result = merge_group(group)
        assert result.conflict_fields == []
        assert result.merged_fields == []
