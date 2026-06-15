import pytest

from solocoder_py.dedup import (
    EmptyMatchKeysError,
    exact_group,
    keep_by_field,
    keep_first,
    keep_last,
    keep_most_complete,
)


class TestExactGroupBasic:
    def test_empty_records(self):
        result = exact_group([], match_keys=["id"])
        assert result == []

    def test_single_record(self):
        records = [{"id": 1, "name": "Alice"}]
        groups = exact_group(records, match_keys=["id"])
        assert len(groups) == 1
        assert len(groups[0].records) == 1
        assert groups[0].is_exact is True
        assert groups[0].match_score == 1.0

    def test_all_unique(self):
        records = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 3, "name": "Charlie"},
        ]
        groups = exact_group(records, match_keys=["id"])
        assert len(groups) == 3
        for g in groups:
            assert len(g.records) == 1

    def test_all_duplicates(self):
        records = [
            {"id": 1, "name": "Alice"},
            {"id": 1, "name": "Alice Smith"},
            {"id": 1, "name": "Alicia"},
        ]
        groups = exact_group(records, match_keys=["id"])
        assert len(groups) == 1
        assert len(groups[0].records) == 3

    def test_mixed_records(self):
        records = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 1, "name": "Alice Smith"},
            {"id": 3, "name": "Charlie"},
            {"id": 2, "name": "Bobby"},
        ]
        groups = exact_group(records, match_keys=["id"])
        assert len(groups) == 3
        group_sizes = sorted([len(g.records) for g in groups])
        assert group_sizes == [1, 2, 2]

    def test_indices_tracking(self):
        records = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 1, "name": "Alice Smith"},
        ]
        groups = exact_group(records, match_keys=["id"])
        id1_group = [g for g in groups if len(g.records) == 2][0]
        assert id1_group.indices == [0, 2]


class TestExactGroupMultipleKeys:
    def test_two_match_keys(self):
        records = [
            {"first_name": "John", "last_name": "Doe", "age": 30},
            {"first_name": "John", "last_name": "Smith", "age": 25},
            {"first_name": "John", "last_name": "Doe", "age": 31},
            {"first_name": "Jane", "last_name": "Doe", "age": 28},
        ]
        groups = exact_group(records, match_keys=["first_name", "last_name"])
        assert len(groups) == 3
        john_doe = [g for g in groups if g.records[0]["first_name"] == "John" and g.records[0]["last_name"] == "Doe"][0]
        assert len(john_doe.records) == 2

    def test_three_match_keys(self):
        records = [
            {"city": "NY", "dept": "IT", "level": "senior", "name": "Alice"},
            {"city": "NY", "dept": "IT", "level": "senior", "name": "Bob"},
            {"city": "NY", "dept": "HR", "level": "senior", "name": "Charlie"},
        ]
        groups = exact_group(records, match_keys=["city", "dept", "level"])
        assert len(groups) == 2
        it_senior = [g for g in groups if g.records[0]["dept"] == "IT"][0]
        assert len(it_senior.records) == 2


class TestExactGroupEdgeCases:
    def test_none_values(self):
        records = [
            {"id": None, "name": "Alice"},
            {"id": None, "name": "Bob"},
            {"id": 1, "name": "Charlie"},
        ]
        groups = exact_group(records, match_keys=["id"])
        assert len(groups) == 2
        none_group = [g for g in groups if g.records[0]["id"] is None][0]
        assert len(none_group.records) == 2

    def test_empty_string_values(self):
        records = [
            {"id": "", "name": "Alice"},
            {"id": "", "name": "Bob"},
            {"id": "1", "name": "Charlie"},
        ]
        groups = exact_group(records, match_keys=["id"])
        assert len(groups) == 2

    def test_missing_fields(self):
        records = [
            {"id": 1, "name": "Alice"},
            {"name": "Bob"},
            {"id": 1, "age": 30},
        ]
        groups = exact_group(records, match_keys=["id"])
        assert len(groups) == 2
        id1_group = [g for g in groups if g.records[0].get("id") == 1][0]
        assert len(id1_group.records) == 2

    def test_different_types_same_value(self):
        records = [
            {"id": 1, "name": "Alice"},
            {"id": "1", "name": "Bob"},
        ]
        groups = exact_group(records, match_keys=["id"])
        assert len(groups) == 2


class TestExactGroupEmptyKeys:
    def test_empty_match_keys_raises(self):
        with pytest.raises(EmptyMatchKeysError):
            exact_group([{"id": 1}], match_keys=[])


class TestKeepStrategies:
    def test_keep_first(self):
        from solocoder_py.dedup import DedupGroup
        group = DedupGroup(
            records=[{"v": 1}, {"v": 2}, {"v": 3}],
            indices=[0, 1, 2],
            is_exact=True,
        )
        result = keep_first(group)
        assert result["v"] == 1

    def test_keep_last(self):
        from solocoder_py.dedup import DedupGroup
        group = DedupGroup(
            records=[{"v": 1}, {"v": 2}, {"v": 3}],
            indices=[0, 1, 2],
            is_exact=True,
        )
        result = keep_last(group)
        assert result["v"] == 3

    def test_keep_most_complete(self):
        from solocoder_py.dedup import DedupGroup
        group = DedupGroup(
            records=[
                {"a": 1, "b": None, "c": ""},
                {"a": 1, "b": 2, "c": 3},
                {"a": 1},
            ],
            indices=[0, 1, 2],
            is_exact=True,
        )
        result = keep_most_complete(group)
        assert result["b"] == 2
        assert result["c"] == 3

    def test_keep_most_complete_with_empty_values(self):
        from solocoder_py.dedup import DedupGroup
        group = DedupGroup(
            records=[
                {"a": 1, "b": "", "c": []},
                {"a": 1, "b": "hello", "c": [1, 2]},
            ],
            indices=[0, 1],
            is_exact=True,
        )
        result = keep_most_complete(group)
        assert result["b"] == "hello"

    def test_keep_by_field_desc(self):
        from solocoder_py.dedup import DedupGroup
        group = DedupGroup(
            records=[{"id": 1, "score": 80}, {"id": 2, "score": 95}, {"id": 3, "score": 70}],
            indices=[0, 1, 2],
            is_exact=True,
        )
        result = keep_by_field(group, field="score", desc=True)
        assert result["score"] == 95

    def test_keep_by_field_asc(self):
        from solocoder_py.dedup import DedupGroup
        group = DedupGroup(
            records=[{"id": 1, "score": 80}, {"id": 2, "score": 95}, {"id": 3, "score": 70}],
            indices=[0, 1, 2],
            is_exact=True,
        )
        result = keep_by_field(group, field="score", desc=False)
        assert result["score"] == 70
