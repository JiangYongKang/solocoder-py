import pytest

from solocoder_py.dedup import (
    DedupEngine,
    EmptyMatchKeysError,
    InvalidConfigError,
    InvalidThresholdError,
    STRATEGY_FIRST,
    STRATEGY_LAST,
    STRATEGY_LONGEST_STRING,
    STRATEGY_CUSTOM,
    KEEP_FIRST,
    KEEP_LAST,
    KEEP_MOST_COMPLETE,
    KEEP_BY_FIELD,
    KEEP_MERGE,
    UnknownStrategyError,
)


class TestEngineInitialization:
    def test_exact_match_only(self):
        engine = DedupEngine(exact_match_keys=["id"])
        assert engine.exact_match_keys == ["id"]
        assert engine.use_fuzzy is False

    def test_fuzzy_match_only(self):
        engine = DedupEngine(
            use_fuzzy=True,
            fuzzy_fields=["name"],
            fuzzy_threshold=0.8,
        )
        assert engine.use_fuzzy is True
        assert engine.fuzzy_fields == ["name"]

    def test_hybrid_mode(self):
        engine = DedupEngine(
            exact_match_keys=["dept"],
            use_fuzzy=True,
            fuzzy_fields=["name"],
            fuzzy_threshold=0.7,
        )
        assert engine.exact_match_keys == ["dept"]
        assert engine.use_fuzzy is True

    def test_no_config_raises(self):
        with pytest.raises(InvalidConfigError):
            DedupEngine()

    def test_empty_exact_keys_raises(self):
        with pytest.raises(EmptyMatchKeysError):
            DedupEngine(exact_match_keys=[])

    def test_fuzzy_without_fields_raises(self):
        with pytest.raises(InvalidConfigError):
            DedupEngine(use_fuzzy=True)

    def test_invalid_fuzzy_threshold_raises(self):
        with pytest.raises(InvalidThresholdError):
            DedupEngine(
                use_fuzzy=True,
                fuzzy_fields=["name"],
                fuzzy_threshold=0,
            )
        with pytest.raises(InvalidThresholdError):
            DedupEngine(
                use_fuzzy=True,
                fuzzy_fields=["name"],
                fuzzy_threshold=1.5,
            )


class TestEngineRecordManagement:
    def test_add_single_record(self):
        engine = DedupEngine(exact_match_keys=["id"])
        engine.add_record({"id": 1, "name": "Alice"})
        assert engine.record_count == 1

    def test_add_multiple_records(self):
        engine = DedupEngine(exact_match_keys=["id"])
        engine.add_records([
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ])
        assert engine.record_count == 2

    def test_clear_records(self):
        engine = DedupEngine(exact_match_keys=["id"])
        engine.add_records([{"id": 1}, {"id": 2}])
        engine.clear()
        assert engine.record_count == 0


class TestEngineExactDedup:
    def test_empty_input(self):
        engine = DedupEngine(exact_match_keys=["id"])
        result = engine.dedup()
        assert result.total_input == 0
        assert result.total_unique == 0
        assert result.total_duplicates == 0
        assert result.unique_records == []
        assert result.groups == []

    def test_single_record(self):
        engine = DedupEngine(exact_match_keys=["id"])
        engine.add_record({"id": 1, "name": "Alice"})
        result = engine.dedup()
        assert result.total_input == 1
        assert result.total_unique == 1
        assert result.total_duplicates == 0
        assert len(result.groups) == 1

    def test_all_unique(self):
        engine = DedupEngine(exact_match_keys=["id"])
        engine.add_records([
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 3, "name": "Charlie"},
        ])
        result = engine.dedup()
        assert result.total_input == 3
        assert result.total_unique == 3
        assert result.total_duplicates == 0

    def test_all_duplicates(self):
        engine = DedupEngine(exact_match_keys=["id"])
        engine.add_records([
            {"id": 1, "name": "Alice"},
            {"id": 1, "name": "Alicia"},
            {"id": 1, "name": "Al"},
        ])
        result = engine.dedup()
        assert result.total_input == 3
        assert result.total_unique == 1
        assert result.total_duplicates == 2

    def test_mixed_records(self):
        engine = DedupEngine(exact_match_keys=["id"])
        engine.add_records([
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 1, "name": "Alicia"},
            {"id": 3, "name": "Charlie"},
            {"id": 2, "name": "Bobby"},
        ])
        result = engine.dedup()
        assert result.total_input == 5
        assert result.total_unique == 3
        assert result.total_duplicates == 2

    def test_default_merge_strategy_is_first(self):
        engine = DedupEngine(exact_match_keys=["id"])
        engine.add_records([
            {"id": 1, "name": "Alice"},
            {"id": 1, "name": "Bob"},
        ])
        result = engine.dedup()
        assert result.unique_records[0]["name"] == "Alice"

    def test_custom_merge_strategy(self):
        engine = DedupEngine(
            exact_match_keys=["id"],
            merge_strategy=STRATEGY_LAST,
        )
        engine.add_records([
            {"id": 1, "name": "Alice"},
            {"id": 1, "name": "Bob"},
        ])
        result = engine.dedup()
        assert result.unique_records[0]["name"] == "Bob"


class TestEngineFuzzyDedup:
    def test_empty_input(self):
        engine = DedupEngine(
            use_fuzzy=True,
            fuzzy_fields=["name"],
            fuzzy_threshold=0.8,
        )
        result = engine.dedup()
        assert result.total_input == 0
        assert result.total_unique == 0

    def test_single_record(self):
        engine = DedupEngine(
            use_fuzzy=True,
            fuzzy_fields=["name"],
            fuzzy_threshold=0.8,
        )
        engine.add_record({"name": "Alice"})
        result = engine.dedup()
        assert result.total_input == 1
        assert result.total_unique == 1

    def test_transitive_matching_abc(self):
        engine = DedupEngine(
            use_fuzzy=True,
            fuzzy_fields=["name"],
            fuzzy_threshold=0.6,
        )
        engine.add_records([
            {"name": "aaaaa"},
            {"name": "aaaab"},
            {"name": "aaabb"},
        ])
        result = engine.dedup()
        assert result.total_unique == 1

    def test_two_separate_groups(self):
        engine = DedupEngine(
            use_fuzzy=True,
            fuzzy_fields=["name"],
            fuzzy_threshold=0.6,
        )
        engine.add_records([
            {"name": "Alice"},
            {"name": "Alicia"},
            {"name": "Robert"},
            {"name": "Roberto"},
        ])
        result = engine.dedup()
        assert result.total_unique == 2

    def test_merge_with_longest_string(self):
        engine = DedupEngine(
            use_fuzzy=True,
            fuzzy_fields=["name"],
            fuzzy_threshold=0.6,
            merge_strategy=STRATEGY_LONGEST_STRING,
        )
        engine.add_records([
            {"name": "Alice"},
            {"name": "Alicia"},
            {"name": "Alisha"},
        ])
        result = engine.dedup()
        assert result.total_unique == 1
        merged_names = [r["name"] for r in result.unique_records]
        assert "Alicia" in merged_names or "Alisha" in merged_names


class TestEngineHybridDedup:
    def test_exact_then_fuzzy(self):
        engine = DedupEngine(
            exact_match_keys=["dept"],
            use_fuzzy=True,
            fuzzy_fields=["name"],
            fuzzy_threshold=0.6,
        )
        engine.add_records([
            {"dept": "IT", "name": "John"},
            {"dept": "IT", "name": "Jon"},
            {"dept": "HR", "name": "John"},
            {"dept": "HR", "name": "Johnny"},
        ])
        result = engine.dedup()
        assert result.total_unique == 2

    def test_fuzzy_only_within_exact_groups(self):
        engine = DedupEngine(
            exact_match_keys=["dept"],
            use_fuzzy=True,
            fuzzy_fields=["name"],
            fuzzy_threshold=0.8,
        )
        engine.add_records([
            {"dept": "IT", "name": "Alice"},
            {"dept": "HR", "name": "Alicia"},
        ])
        result = engine.dedup()
        assert result.total_unique == 2


class TestEngineCustomMerge:
    def test_custom_merge_function(self):
        def sum_amount(field, values):
            if field == "amount":
                return sum(v for v in values if v is not None)
            return values[0]

        engine = DedupEngine(
            exact_match_keys=["order_id"],
            merge_strategy=STRATEGY_CUSTOM,
            custom_merge=sum_amount,
        )
        engine.add_records([
            {"order_id": "ORD001", "amount": 100},
            {"order_id": "ORD001", "amount": 50},
            {"order_id": "ORD001", "amount": 75},
        ])
        result = engine.dedup()
        assert result.unique_records[0]["amount"] == 225


class TestEngineEdgeCases:
    def test_all_records_same(self):
        engine = DedupEngine(exact_match_keys=["id"])
        records = [{"id": 1, "val": i} for i in range(100)]
        engine.add_records(records)
        result = engine.dedup()
        assert result.total_input == 100
        assert result.total_unique == 1

    def test_no_duplicates_large(self):
        engine = DedupEngine(exact_match_keys=["id"])
        records = [{"id": i, "val": i * 10} for i in range(100)]
        engine.add_records(records)
        result = engine.dedup()
        assert result.total_input == 100
        assert result.total_unique == 100

    def test_empty_field_values_fuzzy(self):
        engine = DedupEngine(
            use_fuzzy=True,
            fuzzy_fields=["name", "email"],
            fuzzy_threshold=0.5,
        )
        engine.add_records([
            {"name": "", "email": "a@b.com"},
            {"name": None, "email": "a@b.com"},
            {"name": "Alice", "email": ""},
        ])
        result = engine.dedup()
        assert result.total_input == 3

    def test_field_merge_strategies(self):
        engine = DedupEngine(
            exact_match_keys=["id"],
            merge_strategy=STRATEGY_FIRST,
            field_merge_strategies={
                "name": STRATEGY_LONGEST_STRING,
                "desc": STRATEGY_LAST,
            },
        )
        engine.add_records([
            {"id": 1, "name": "Al", "desc": "first", "val": 1},
            {"id": 1, "name": "Alice", "desc": "second", "val": 2},
        ])
        result = engine.dedup()
        record = result.unique_records[0]
        assert record["name"] == "Alice"
        assert record["desc"] == "second"
        assert record["val"] == 1

    def test_fallback_strategy(self):
        def broken_merge(field, values):
            raise RuntimeError("merge failed")

        engine = DedupEngine(
            exact_match_keys=["id"],
            merge_strategy=STRATEGY_FIRST,
            field_merge_strategies={"name": STRATEGY_CUSTOM},
            custom_merge=broken_merge,
            fallback_merge_strategy=STRATEGY_LAST,
        )
        engine.add_records([
            {"id": 1, "name": "first"},
            {"id": 1, "name": "last"},
        ])
        result = engine.dedup()
        assert result.unique_records[0]["name"] == "last"


class TestEngineGroups:
    def test_groups_are_correct(self):
        engine = DedupEngine(exact_match_keys=["id"])
        engine.add_records([
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 1, "name": "Alicia"},
        ])
        result = engine.dedup()
        assert len(result.groups) == 2
        group_sizes = sorted([len(g.records) for g in result.groups])
        assert group_sizes == [1, 2]

    def test_groups_have_indices(self):
        engine = DedupEngine(exact_match_keys=["id"])
        engine.add_records([
            {"id": 1},
            {"id": 2},
            {"id": 1},
        ])
        result = engine.dedup()
        id1_group = [g for g in result.groups if len(g.records) == 2][0]
        assert id1_group.indices == [0, 2]

    def test_fuzzy_groups_have_pairs(self):
        engine = DedupEngine(
            use_fuzzy=True,
            fuzzy_fields=["name"],
            fuzzy_threshold=0.5,
        )
        engine.add_records([
            {"name": "Alice"},
            {"name": "Alicia"},
            {"name": "Bob"},
        ])
        result = engine.dedup()
        fuzzy_groups = [g for g in result.groups if len(g.records) > 1]
        assert len(fuzzy_groups) == 1
        assert len(fuzzy_groups[0].fuzzy_pairs) >= 1


class TestEngineRecordSelectionStrategy:
    def test_keep_first_strategy(self):
        engine = DedupEngine(
            exact_match_keys=["id"],
            record_selection_strategy=KEEP_FIRST,
        )
        engine.add_records([
            {"id": 1, "name": "Alice", "age": 30},
            {"id": 1, "name": "Bob", "age": 25},
            {"id": 1, "name": "Charlie", "age": 35},
        ])
        result = engine.dedup()
        assert result.total_unique == 1
        assert result.unique_records[0]["name"] == "Alice"
        assert result.unique_records[0]["age"] == 30

    def test_keep_last_strategy(self):
        engine = DedupEngine(
            exact_match_keys=["id"],
            record_selection_strategy=KEEP_LAST,
        )
        engine.add_records([
            {"id": 1, "name": "Alice", "age": 30},
            {"id": 1, "name": "Bob", "age": 25},
            {"id": 1, "name": "Charlie", "age": 35},
        ])
        result = engine.dedup()
        assert result.total_unique == 1
        assert result.unique_records[0]["name"] == "Charlie"
        assert result.unique_records[0]["age"] == 35

    def test_keep_most_complete_strategy(self):
        engine = DedupEngine(
            exact_match_keys=["id"],
            record_selection_strategy=KEEP_MOST_COMPLETE,
        )
        engine.add_records([
            {"id": 1, "name": "Alice"},
            {"id": 1, "name": "Bob", "age": 25, "email": "bob@test.com"},
            {"id": 1, "name": "Charlie", "age": None},
        ])
        result = engine.dedup()
        assert result.total_unique == 1
        assert result.unique_records[0]["name"] == "Bob"
        assert result.unique_records[0]["age"] == 25
        assert result.unique_records[0]["email"] == "bob@test.com"

    def test_keep_by_field_desc_strategy(self):
        engine = DedupEngine(
            exact_match_keys=["user_id"],
            record_selection_strategy=KEEP_BY_FIELD,
            record_selection_field="updated_at",
            record_selection_desc=True,
        )
        engine.add_records([
            {"user_id": "u1", "updated_at": 100, "data": "old"},
            {"user_id": "u1", "updated_at": 300, "data": "newest"},
            {"user_id": "u1", "updated_at": 200, "data": "middle"},
        ])
        result = engine.dedup()
        assert result.total_unique == 1
        assert result.unique_records[0]["updated_at"] == 300
        assert result.unique_records[0]["data"] == "newest"

    def test_keep_by_field_asc_strategy(self):
        engine = DedupEngine(
            exact_match_keys=["user_id"],
            record_selection_strategy=KEEP_BY_FIELD,
            record_selection_field="score",
            record_selection_desc=False,
        )
        engine.add_records([
            {"user_id": "u1", "score": 95, "name": "Charlie"},
            {"user_id": "u1", "score": 80, "name": "Alice"},
            {"user_id": "u1", "score": 90, "name": "Bob"},
        ])
        result = engine.dedup()
        assert result.total_unique == 1
        assert result.unique_records[0]["score"] == 80
        assert result.unique_records[0]["name"] == "Alice"

    def test_keep_merge_strategy_default(self):
        engine = DedupEngine(
            exact_match_keys=["id"],
            record_selection_strategy=KEEP_MERGE,
            merge_strategy=STRATEGY_LAST,
        )
        engine.add_records([
            {"id": 1, "name": "Alice", "age": 30},
            {"id": 1, "name": "Bob", "age": 25},
        ])
        result = engine.dedup()
        assert result.total_unique == 1
        assert result.unique_records[0]["name"] == "Bob"
        assert result.unique_records[0]["age"] == 25

    def test_invalid_record_selection_strategy_raises(self):
        with pytest.raises(UnknownStrategyError):
            DedupEngine(
                exact_match_keys=["id"],
                record_selection_strategy="invalid_strategy",
            )

    def test_keep_by_field_without_field_raises(self):
        with pytest.raises(InvalidConfigError):
            DedupEngine(
                exact_match_keys=["id"],
                record_selection_strategy=KEEP_BY_FIELD,
            )

    def test_keep_strategy_with_multiple_groups(self):
        engine = DedupEngine(
            exact_match_keys=["id"],
            record_selection_strategy=KEEP_FIRST,
        )
        engine.add_records([
            {"id": 1, "name": "A1"},
            {"id": 1, "name": "A2"},
            {"id": 2, "name": "B1"},
            {"id": 2, "name": "B2"},
            {"id": 3, "name": "C1"},
        ])
        result = engine.dedup()
        assert result.total_unique == 3
        names = [r["name"] for r in result.unique_records]
        assert sorted(names) == sorted(["A1", "B1", "C1"])

    def test_keep_strategy_single_record_groups_unchanged(self):
        engine = DedupEngine(
            exact_match_keys=["id"],
            record_selection_strategy=KEEP_LAST,
        )
        engine.add_records([
            {"id": 1, "name": "Only"},
            {"id": 2, "name": "First"},
            {"id": 2, "name": "Last"},
        ])
        result = engine.dedup()
        assert result.total_unique == 2
        records_by_id = {r["id"]: r for r in result.unique_records}
        assert records_by_id[1]["name"] == "Only"
        assert records_by_id[2]["name"] == "Last"

    def test_keep_most_complete_with_tie_prefers_first(self):
        engine = DedupEngine(
            exact_match_keys=["id"],
            record_selection_strategy=KEEP_MOST_COMPLETE,
        )
        engine.add_records([
            {"id": 1, "a": 1, "b": 2},
            {"id": 1, "x": 10, "y": 20},
        ])
        result = engine.dedup()
        assert result.total_unique == 1
        assert "a" in result.unique_records[0]
        assert result.unique_records[0]["a"] == 1


class TestEngineFallbackFieldsPropagation:
    def test_fallback_fields_empty_when_no_fallback(self):
        engine = DedupEngine(
            exact_match_keys=["id"],
            merge_strategy=STRATEGY_FIRST,
        )
        engine.add_records([
            {"id": 1, "name": "Alice", "age": 30},
            {"id": 1, "name": "Bob", "age": 25},
        ])
        result = engine.dedup()
        assert result.fallback_fields == {}

    def test_fallback_fields_propagated_from_merge_group(self):
        def bad_merge(field, values):
            raise RuntimeError("merge failed")

        engine = DedupEngine(
            exact_match_keys=["id"],
            merge_strategy=STRATEGY_CUSTOM,
            custom_merge=bad_merge,
            fallback_merge_strategy=STRATEGY_LAST,
        )
        engine.add_records([
            {"id": 1, "name": "Alice", "age": 30},
            {"id": 1, "name": "Bob", "age": 25},
        ])
        result = engine.dedup()
        assert result.total_unique == 1
        assert 0 in result.fallback_fields
        assert set(result.fallback_fields[0]) == {"name", "age"}
        assert result.unique_records[0]["name"] == "Bob"
        assert result.unique_records[0]["age"] == 25

    def test_fallback_fields_multiple_groups(self):
        def bad_merge(field, values):
            if field == "name":
                raise RuntimeError("name merge failed")
            return values[0]

        engine = DedupEngine(
            exact_match_keys=["id"],
            merge_strategy=STRATEGY_CUSTOM,
            custom_merge=bad_merge,
            fallback_merge_strategy=STRATEGY_LAST,
        )
        engine.add_records([
            {"id": 1, "name": "A1", "age": 30},
            {"id": 1, "name": "A2", "age": 25},
            {"id": 2, "name": "B1", "age": 40},
            {"id": 2, "name": "B2", "age": 45},
        ])
        result = engine.dedup()
        assert result.total_unique == 2
        assert 0 in result.fallback_fields
        assert result.fallback_fields[0] == ["name"]
        assert 1 in result.fallback_fields
        assert result.fallback_fields[1] == ["name"]
        assert result.unique_records[0]["name"] == "A2"
        assert result.unique_records[1]["name"] == "B2"

    def test_fallback_fields_empty_for_single_record_groups(self):
        def bad_merge(field, values):
            raise RuntimeError("failed")

        engine = DedupEngine(
            exact_match_keys=["id"],
            merge_strategy=STRATEGY_CUSTOM,
            custom_merge=bad_merge,
            fallback_merge_strategy=STRATEGY_LAST,
        )
        engine.add_records([
            {"id": 1, "name": "Only"},
            {"id": 2, "name": "First"},
            {"id": 2, "name": "Last"},
        ])
        result = engine.dedup()
        assert 0 not in result.fallback_fields
        assert 1 in result.fallback_fields
        assert result.fallback_fields[1] == ["name"]
        assert result.unique_records[1]["name"] == "Last"

    def test_keep_strategies_have_empty_fallback_fields(self):
        for strategy in [KEEP_FIRST, KEEP_LAST, KEEP_MOST_COMPLETE]:
            engine = DedupEngine(
                exact_match_keys=["id"],
                record_selection_strategy=strategy,
            )
            engine.add_records([
                {"id": 1, "name": "A", "age": 30},
                {"id": 1, "name": "B", "age": 25},
            ])
            result = engine.dedup()
            assert result.fallback_fields == {}

    def test_keep_by_field_has_empty_fallback_fields(self):
        engine = DedupEngine(
            exact_match_keys=["id"],
            record_selection_strategy=KEEP_BY_FIELD,
            record_selection_field="age",
            record_selection_desc=True,
        )
        engine.add_records([
            {"id": 1, "name": "A", "age": 30},
            {"id": 1, "name": "B", "age": 25},
        ])
        result = engine.dedup()
        assert result.fallback_fields == {}

    def test_fallback_fields_not_present_when_no_conflicts(self):
        engine = DedupEngine(
            exact_match_keys=["id"],
            merge_strategy=STRATEGY_CUSTOM,
            custom_merge=lambda f, v: "should not be called",
        )
        engine.add_records([
            {"id": 1, "name": "Alice"},
            {"id": 1, "name": "Alice"},
        ])
        result = engine.dedup()
        assert result.fallback_fields == {}

    def test_fallback_fields_with_field_specific_custom_strategy(self):
        def bad_merge(field, values):
            raise RuntimeError("failed")

        engine = DedupEngine(
            exact_match_keys=["id"],
            merge_strategy=STRATEGY_FIRST,
            custom_merge=bad_merge,
            field_merge_strategies={
                "name": STRATEGY_CUSTOM,
            },
            fallback_merge_strategy=STRATEGY_LAST,
        )
        engine.add_records([
            {"id": 1, "name": "First", "age": 30},
            {"id": 1, "name": "Last", "age": 25},
        ])
        result = engine.dedup()
        assert 0 in result.fallback_fields
        assert result.fallback_fields[0] == ["name"]
        assert result.unique_records[0]["name"] == "Last"
        assert result.unique_records[0]["age"] == 30

    def test_dedupresult_fallback_fields_default_empty(self):
        from solocoder_py.dedup import DedupResult

        result = DedupResult(
            unique_records=[],
            groups=[],
            total_input=0,
            total_unique=0,
            total_duplicates=0,
        )
        assert result.fallback_fields == {}
