import pytest

from solocoder_py.dedup import (
    DedupEngine,
    DedupGroup,
    InvalidConfigError,
    MergeConflictError,
    STRATEGY_FIRST,
    STRATEGY_LAST,
    STRATEGY_LONGEST_STRING,
    STRATEGY_MOST_COMMON,
    STRATEGY_FIRST_NON_EMPTY,
    STRATEGY_CUSTOM,
    merge_group,
    fuzzy_group,
    exact_group,
)


class TestEdgeSingleRecord:
    def test_exact_single_record(self):
        engine = DedupEngine(exact_match_keys=["id"])
        engine.add_record({"id": 42, "name": "Solo"})
        result = engine.dedup()
        assert result.total_input == 1
        assert result.total_unique == 1
        assert result.total_duplicates == 0
        assert result.unique_records[0]["id"] == 42
        assert len(result.groups) == 1
        assert result.groups[0].is_exact is True

    def test_fuzzy_single_record(self):
        engine = DedupEngine(
            use_fuzzy=True,
            fuzzy_fields=["name"],
            fuzzy_threshold=0.8,
        )
        engine.add_record({"name": "Unique"})
        result = engine.dedup()
        assert result.total_input == 1
        assert result.total_unique == 1
        assert result.groups[0].is_exact is False

    def test_single_record_merge_strategies(self):
        group = DedupGroup(
            records=[{"a": 1, "b": "hello"}],
            indices=[0],
            is_exact=True,
        )
        for strategy in [
            STRATEGY_FIRST,
            STRATEGY_LAST,
            STRATEGY_LONGEST_STRING,
            STRATEGY_MOST_COMMON,
            STRATEGY_FIRST_NON_EMPTY,
        ]:
            result = merge_group(group, strategy=strategy)
            assert result.record == {"a": 1, "b": "hello"}
            assert result.conflict_fields == []


class TestEdgeAllDuplicates:
    def test_all_identical_exact(self):
        engine = DedupEngine(exact_match_keys=["order_id"])
        records = [
            {"order_id": "ORD-001", "amount": 99.99, "status": "pending"}
            for _ in range(50)
        ]
        engine.add_records(records)
        result = engine.dedup()
        assert result.total_input == 50
        assert result.total_unique == 1
        assert result.total_duplicates == 49
        assert len(result.groups) == 1
        assert len(result.groups[0].records) == 50

    def test_all_duplicates_fuzzy(self):
        engine = DedupEngine(
            use_fuzzy=True,
            fuzzy_fields=["name"],
            fuzzy_threshold=0.5,
        )
        names = ["Alice", "Alicia", "Alisha", "Alesha", "Alisia"]
        engine.add_records([{"name": n} for n in names])
        result = engine.dedup()
        assert result.total_unique <= 3


class TestEdgeEmptyFieldsFuzzy:
    def test_both_empty_strings(self):
        from solocoder_py.dedup import similarity
        assert similarity("", "") == 1.0

    def test_one_empty_one_not(self):
        from solocoder_py.dedup import similarity
        assert similarity("", "hello") == 0.0
        assert similarity("hello", "") == 0.0

    def test_both_none(self):
        from solocoder_py.dedup import similarity
        assert similarity(None, None) == 1.0

    def test_none_vs_empty(self):
        from solocoder_py.dedup import similarity
        assert similarity(None, "") == 0.0
        assert similarity("", None) == 0.0

    def test_empty_in_record_fuzzy_group(self):
        records = [
            {"name": "", "email": "a@b.com"},
            {"name": "", "email": "a@b.com"},
        ]
        groups = fuzzy_group(records, fields=["name"], threshold=0.8)
        assert len(groups) == 1
        assert len(groups[0].records) == 2

    def test_mixed_none_and_values(self):
        records = [
            {"name": None, "phone": "123"},
            {"name": "Alice", "phone": "123"},
            {"name": None, "phone": "456"},
        ]
        groups = fuzzy_group(records, fields=["name", "phone"], threshold=0.3)
        assert len(groups) >= 1


class TestEdgeTransitiveMatching:
    def test_chain_transitivity(self):
        records = [
            {"code": "AAAAA"},
            {"code": "AAAAB"},
            {"code": "AAABB"},
            {"code": "AABBB"},
            {"code": "ABBBB"},
        ]
        groups = fuzzy_group(records, fields=["code"], threshold=0.6)
        assert len(groups) == 1
        assert len(groups[0].records) == 5

    def test_star_transitivity(self):
        records = [
            {"name": "common_prefix_abc"},
            {"name": "common_prefix_def"},
            {"name": "common_prefix_ghi"},
        ]
        groups = fuzzy_group(records, fields=["name"], threshold=0.7)
        assert len(groups) == 1

    def test_disconnected_chains(self):
        records = [
            {"name": "aaa1"},
            {"name": "aaa2"},
            {"name": "aaa3"},
            {"name": "zzz1"},
            {"name": "zzz2"},
            {"name": "zzz3"},
        ]
        groups = fuzzy_group(records, fields=["name"], threshold=0.6)
        assert len(groups) == 2
        group_sizes = sorted([len(g.records) for g in groups])
        assert group_sizes == [3, 3]

    def test_transitive_with_bridge_record(self):
        records = [
            {"name": "abcde"},
            {"name": "abxde"},
            {"name": "xyzwv"},
        ]
        groups = fuzzy_group(records, fields=["name"], threshold=0.5)
        assert len(groups) >= 1

    def test_group_score_with_transitivity(self):
        records = [
            {"name": "aaaaa"},
            {"name": "aaaab"},
            {"name": "aaabb"},
        ]
        groups = fuzzy_group(records, fields=["name"], threshold=0.6)
        assert len(groups) == 1
        assert 0.0 < groups[0].match_score < 1.0


class TestEdgeMergeConflicts:
    def test_all_fields_conflict(self):
        group = DedupGroup(
            records=[
                {"a": 1, "b": 2, "c": 3},
                {"a": 10, "b": 20, "c": 30},
            ],
            indices=[0, 1],
            is_exact=True,
        )
        result = merge_group(group, strategy=STRATEGY_FIRST)
        assert set(result.conflict_fields) == {"a", "b", "c"}
        assert result.record == {"a": 1, "b": 2, "c": 3}

    def test_no_fields_conflict(self):
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

    def test_partial_conflict(self):
        group = DedupGroup(
            records=[
                {"id": 1, "name": "Alice", "age": 30},
                {"id": 1, "name": "Bob", "age": 30},
            ],
            indices=[0, 1],
            is_exact=True,
        )
        result = merge_group(group)
        assert "name" in result.conflict_fields
        assert "age" not in result.conflict_fields

    def test_nested_values_conflict(self):
        group = DedupGroup(
            records=[
                {"data": {"x": 1}},
                {"data": {"x": 2}},
            ],
            indices=[0, 1],
            is_exact=True,
        )
        result = merge_group(group, strategy=STRATEGY_LAST)
        assert result.record["data"]["x"] == 2

    def test_list_values_conflict(self):
        group = DedupGroup(
            records=[
                {"tags": ["a", "b"]},
                {"tags": ["c", "d"]},
            ],
            indices=[0, 1],
            is_exact=True,
        )
        result = merge_group(group, strategy=STRATEGY_FIRST)
        assert result.record["tags"] == ["a", "b"]


class TestEdgeCustomMergeFallback:
    def test_custom_raises_fallback(self):
        def bad_merge(field, values):
            raise ValueError("can't merge")

        group = DedupGroup(
            records=[
                {"val": "first"},
                {"val": "second"},
            ],
            indices=[0, 1],
            is_exact=True,
        )
        engine = DedupEngine(
            exact_match_keys=["id"],
            merge_strategy=STRATEGY_CUSTOM,
            custom_merge=bad_merge,
            fallback_merge_strategy=STRATEGY_LAST,
        )
        engine.add_record({"id": 1, "val": "first"})
        engine.add_record({"id": 1, "val": "second"})
        result = engine.dedup()
        assert result.unique_records[0]["val"] == "second"

    def test_per_field_custom_with_fallback(self):
        def merge_name(field, values):
            return " | ".join(str(v) for v in values if v)

        group = DedupGroup(
            records=[
                {"name": "A", "age": 20, "city": "NY"},
                {"name": "B", "age": 30, "city": "LA"},
            ],
            indices=[0, 1],
            is_exact=True,
        )
        result = merge_group(
            group,
            strategy=STRATEGY_FIRST,
            custom_merge=merge_name,
            field_strategies={
                "name": STRATEGY_CUSTOM,
                "age": STRATEGY_LAST,
            },
            fallback_strategy=STRATEGY_FIRST,
        )
        assert result.record["name"] == "A | B"
        assert result.record["age"] == 30
        assert result.record["city"] == "NY"


class TestEdgeEmptyAndNone:
    def test_none_vs_empty_in_exact(self):
        records = [
            {"key": None, "val": 1},
            {"key": "", "val": 2},
            {"key": None, "val": 3},
        ]
        groups = exact_group(records, match_keys=["key"])
        assert len(groups) == 2
        none_group = [g for g in groups if g.records[0]["key"] is None][0]
        assert len(none_group.records) == 2

    def test_zero_vs_none(self):
        records = [
            {"val": 0},
            {"val": None},
            {"val": 0},
        ]
        groups = exact_group(records, match_keys=["val"])
        assert len(groups) == 2

    def test_false_vs_none(self):
        records = [
            {"active": False},
            {"active": None},
        ]
        groups = exact_group(records, match_keys=["active"])
        assert len(groups) == 2

    def test_empty_list_vs_none(self):
        records = [
            {"items": []},
            {"items": None},
        ]
        groups = exact_group(records, match_keys=["items"])
        assert len(groups) == 2


class TestEdgeLargeRecords:
    def test_many_fields(self):
        engine = DedupEngine(exact_match_keys=["id"])
        record = {f"field_{i}": i for i in range(100)}
        record["id"] = 1
        engine.add_record(record)
        engine.add_record({**record, "field_99": "modified"})
        result = engine.dedup()
        assert result.total_unique == 1
        assert len(result.unique_records[0]) == 101

    def test_long_string_values(self):
        long_str = "a" * 10000
        engine = DedupEngine(
            use_fuzzy=True,
            fuzzy_fields=["desc"],
            fuzzy_threshold=0.9,
        )
        engine.add_record({"desc": long_str})
        engine.add_record({"desc": long_str[:-1] + "b"})
        result = engine.dedup()
        assert result.total_unique == 1


class TestEdgeMergeResultIntegrity:
    def test_conflict_and_merged_fields_match(self):
        group = DedupGroup(
            records=[
                {"a": 1, "b": 2, "c": 3, "d": 4},
                {"a": 1, "b": 20, "c": 30, "d": 4},
            ],
            indices=[0, 1],
            is_exact=True,
        )
        result = merge_group(group, strategy=STRATEGY_FIRST)
        assert set(result.conflict_fields) == set(result.merged_fields)
        assert "b" in result.conflict_fields
        assert "c" in result.conflict_fields

    def test_all_fields_present_after_merge(self):
        group = DedupGroup(
            records=[
                {"a": 1, "b": 2},
                {"b": 3, "c": 4},
                {"d": 5},
            ],
            indices=[0, 1, 2],
            is_exact=True,
        )
        result = merge_group(group, strategy=STRATEGY_LAST)
        assert set(result.record.keys()) == {"a", "b", "c", "d"}


class TestEdgeEngineConfigErrors:
    def test_neither_exact_nor_fuzzy(self):
        with pytest.raises(InvalidConfigError):
            DedupEngine()

    def test_exact_none_and_fuzzy_false(self):
        with pytest.raises(InvalidConfigError):
            DedupEngine(exact_match_keys=None, use_fuzzy=False)
