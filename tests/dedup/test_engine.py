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
