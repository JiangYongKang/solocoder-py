from __future__ import annotations

import pytest

from solocoder_py.jsonpath import (
    InvalidPathError,
    JSONPathQuery,
    UnexpectedTokenError,
    jsonpath,
)


_SAMPLE_DATA = {
    "store": {
        "book": [
            {
                "category": "reference",
                "author": "Nigel Rees",
                "title": "Sayings of the Century",
                "price": 8.95,
            },
            {
                "category": "fiction",
                "author": "Evelyn Waugh",
                "title": "Sword of Honour",
                "price": 12.99,
            },
            {
                "category": "fiction",
                "author": "Herman Melville",
                "title": "Moby Dick",
                "isbn": "0-553-21311-3",
                "price": 8.99,
            },
            {
                "category": "fiction",
                "author": "J.R.R. Tolkien",
                "title": "The Lord of the Rings",
                "isbn": "0-261-10353-7",
                "price": 22.99,
            },
        ],
        "bicycle": {
            "color": "red",
            "price": 19.95,
        },
    },
    "expensive": True,
}


class TestFieldSelection:
    def test_dot_notation_simple(self):
        result = jsonpath({"name": "Alice"}, "$.name")
        assert result == ["Alice"]

    def test_dot_notation_nested(self):
        result = jsonpath(_SAMPLE_DATA, "$.store.bicycle.color")
        assert result == ["red"]

    def test_bracket_notation_single_quote(self):
        result = jsonpath({"name": "Alice"}, "$['name']")
        assert result == ["Alice"]

    def test_bracket_notation_double_quote(self):
        result = jsonpath({"name": "Alice"}, '$["name"]')
        assert result == ["Alice"]

    def test_bracket_notation_nested(self):
        result = jsonpath(_SAMPLE_DATA, "$['store']['bicycle']['price']")
        assert result == [19.95]

    def test_mixed_dot_and_bracket(self):
        result = jsonpath(_SAMPLE_DATA, "$.store['bicycle'].color")
        assert result == ["red"]

    def test_field_not_found_returns_empty(self):
        result = jsonpath({"name": "Alice"}, "$.age")
        assert result == []

    def test_deeply_nested_field_not_found(self):
        result = jsonpath(_SAMPLE_DATA, "$.store.bicycle.wheels")
        assert result == []

    def test_field_with_underscore(self):
        result = jsonpath({"first_name": "Bob"}, "$.first_name")
        assert result == ["Bob"]

    def test_top_level_field_without_dollar(self):
        result = jsonpath({"name": "Alice"}, ".name")
        assert result == ["Alice"]

    def test_root_returns_entire_data(self):
        data = {"a": 1}
        result = jsonpath(data, "$")
        assert result == [data]

    def test_field_value_is_none(self):
        result = jsonpath({"name": None}, "$.name")
        assert result == [None]

    def test_field_value_is_false(self):
        result = jsonpath({"active": False}, "$.active")
        assert result == [False]

    def test_field_value_is_zero(self):
        result = jsonpath({"count": 0}, "$.count")
        assert result == [0]

    def test_field_value_is_empty_string(self):
        result = jsonpath({"name": ""}, "$.name")
        assert result == [""]


class TestArrayIndexSelection:
    def test_index_zero(self):
        result = jsonpath({"items": [10, 20, 30]}, "$.items[0]")
        assert result == [10]

    def test_index_one(self):
        result = jsonpath({"items": [10, 20, 30]}, "$.items[1]")
        assert result == [20]

    def test_index_last(self):
        result = jsonpath({"items": [10, 20, 30]}, "$.items[2]")
        assert result == [30]

    def test_negative_index(self):
        result = jsonpath({"items": [10, 20, 30]}, "$.items[-1]")
        assert result == [30]

    def test_negative_index_second_to_last(self):
        result = jsonpath({"items": [10, 20, 30]}, "$.items[-2]")
        assert result == [20]

    def test_index_out_of_bounds_returns_empty(self):
        result = jsonpath({"items": [10, 20]}, "$.items[5]")
        assert result == []

    def test_negative_index_out_of_bounds_returns_empty(self):
        result = jsonpath({"items": [10, 20]}, "$.items[-3]")
        assert result == []

    def test_empty_array_index_returns_empty(self):
        result = jsonpath({"items": []}, "$.items[0]")
        assert result == []

    def test_nested_array_access(self):
        result = jsonpath(
            {"matrix": [[1, 2], [3, 4]]}, "$.matrix[1][0]"
        )
        assert result == [3]

    def test_index_on_sample_data(self):
        result = jsonpath(_SAMPLE_DATA, "$.store.book[0].author")
        assert result == ["Nigel Rees"]

    def test_index_on_sample_data_last_book(self):
        result = jsonpath(_SAMPLE_DATA, "$.store.book[3].title")
        assert result == ["The Lord of the Rings"]


class TestWildcardSelection:
    def test_wildcard_on_object(self):
        data = {"a": 1, "b": 2, "c": 3}
        result = jsonpath(data, "$.*")
        assert result == [1, 2, 3]

    def test_wildcard_on_array(self):
        data = {"items": [10, 20, 30]}
        result = jsonpath(data, "$.items[*]")
        assert result == [10, 20, 30]

    def test_wildcard_on_nested_object(self):
        result = jsonpath(_SAMPLE_DATA, "$.store.bicycle.*")
        assert result == ["red", 19.95]

    def test_wildcard_on_books_array(self):
        result = jsonpath(_SAMPLE_DATA, "$.store.book[*].author")
        assert result == [
            "Nigel Rees",
            "Evelyn Waugh",
            "Herman Melville",
            "J.R.R. Tolkien",
        ]

    def test_wildcard_on_empty_object(self):
        result = jsonpath({}, "$.*")
        assert result == []

    def test_wildcard_on_empty_array(self):
        result = jsonpath({"items": []}, "$.items[*]")
        assert result == []

    def test_wildcard_preserves_document_order(self):
        data = {"x": 1, "a": 2, "m": 3}
        result = jsonpath(data, "$.*")
        assert result == [1, 2, 3]

    def test_double_wildcard(self):
        data = {"store": {"a": 1, "b": 2}}
        result = jsonpath(data, "$.store.*")
        assert result == [1, 2]

    def test_wildcard_on_array_of_objects(self):
        data = {"items": [{"id": 1}, {"id": 2}, {"id": 3}]}
        result = jsonpath(data, "$.items[*].id")
        assert result == [1, 2, 3]


class TestRecursiveDescent:
    def test_recursive_search_simple(self):
        data = {"a": {"b": {"c": "found"}}, "c": "top"}
        result = jsonpath(data, "$..c")
        assert result == ["top", "found"]

    def test_recursive_search_all_prices(self):
        result = jsonpath(_SAMPLE_DATA, "$..price")
        assert result == [8.95, 12.99, 8.99, 22.99, 19.95]

    def test_recursive_search_no_match(self):
        result = jsonpath({"a": 1, "b": 2}, "$..nonexistent")
        assert result == []

    def test_recursive_search_in_flat_object(self):
        data = {"x": 1, "y": 2}
        result = jsonpath(data, "$..x")
        assert result == [1]

    def test_recursive_search_array_values(self):
        data = {"items": [{"name": "a"}, {"name": "b"}]}
        result = jsonpath(data, "$..name")
        assert result == ["a", "b"]

    def test_recursive_search_deeply_nested(self):
        data = {"a": {"b": {"c": {"d": {"target": "deep"}}}}}
        result = jsonpath(data, "$..target")
        assert result == ["deep"]

    def test_recursive_search_multiple_occurrences(self):
        data = {
            "x": "level1",
            "child": {
                "x": "level2",
                "grandchild": {
                    "x": "level3",
                },
            },
        }
        result = jsonpath(data, "$..x")
        assert result == ["level1", "level2", "level3"]

    def test_recursive_search_across_arrays_and_objects(self):
        data = {
            "tags": [
                {"label": "a"},
                {"nested": {"label": "b"}},
            ],
            "label": "root",
        }
        result = jsonpath(data, "$..label")
        assert result == ["root", "a", "b"]

    def test_recursive_search_on_empty_data(self):
        result = jsonpath({}, "$..anything")
        assert result == []

    def test_recursive_search_on_primitive(self):
        result = jsonpath(42, "$..field")
        assert result == []


class TestMultiResultReturn:
    def test_wildcard_returns_multiple(self):
        data = {"a": 1, "b": 2, "c": 3}
        result = jsonpath(data, "$.*")
        assert len(result) == 3

    def test_recursive_returns_multiple(self):
        data = {"x": 1, "child": {"x": 2}}
        result = jsonpath(data, "$..x")
        assert len(result) == 2

    def test_single_result_still_in_list(self):
        result = jsonpath({"name": "Alice"}, "$.name")
        assert result == ["Alice"]
        assert isinstance(result, list)

    def test_order_preserved_for_array_wildcard(self):
        data = {"items": [3, 1, 4, 1, 5]}
        result = jsonpath(data, "$.items[*]")
        assert result == [3, 1, 4, 1, 5]

    def test_order_preserved_for_recursive(self):
        data = {"val": "first", "nested": {"val": "second", "deep": {"val": "third"}}}
        result = jsonpath(data, "$..val")
        assert result == ["first", "second", "third"]


class TestEdgeCases:
    def test_query_on_none_data(self):
        result = jsonpath(None, "$.field")
        assert result == []

    def test_query_on_integer_data(self):
        result = jsonpath(42, "$.field")
        assert result == []

    def test_query_on_string_data(self):
        result = jsonpath("hello", "$.field")
        assert result == []

    def test_index_on_non_array(self):
        result = jsonpath({"not_array": "string"}, "$.not_array[0]")
        assert result == []

    def test_wildcard_on_scalar(self):
        result = jsonpath(42, "$.*")
        assert result == []

    def test_deeply_nested_missing_intermediate(self):
        result = jsonpath({"a": 1}, "$.x.y.z")
        assert result == []

    def test_array_then_field_on_non_object(self):
        result = jsonpath({"items": [1, 2, 3]}, "$.items[0].name")
        assert result == []


class TestInvalidPathSyntax:
    def test_empty_path_raises(self):
        with pytest.raises(InvalidPathError, match="Path cannot be empty"):
            jsonpath({"a": 1}, "")

    def test_whitespace_only_path_raises(self):
        with pytest.raises(InvalidPathError, match="Path cannot be empty"):
            jsonpath({"a": 1}, "   ")

    def test_dot_without_field_raises(self):
        with pytest.raises(InvalidPathError, match="Expected field name"):
            jsonpath({"a": 1}, "$.")

    def test_double_dot_without_field_raises(self):
        with pytest.raises(InvalidPathError, match="Expected field name"):
            jsonpath({"a": 1}, "$..")

    def test_unclosed_bracket_raises(self):
        with pytest.raises(UnexpectedTokenError):
            jsonpath({"a": [1]}, "$.a[0")

    def test_unclosed_single_quote_raises(self):
        with pytest.raises(InvalidPathError, match="Unclosed"):
            jsonpath({"a": 1}, "$['a")

    def test_unclosed_double_quote_raises(self):
        with pytest.raises(InvalidPathError, match="Unclosed"):
            jsonpath({"a": 1}, '$["a')

    def test_invalid_character_in_path(self):
        with pytest.raises(InvalidPathError, match="Unexpected character"):
            jsonpath({"a": 1}, "$.a!b")

    def test_empty_brackets_raises(self):
        with pytest.raises(InvalidPathError, match="Expected index"):
            jsonpath({"a": [1]}, "$.a[]")

    def test_bracket_non_numeric_index_raises(self):
        with pytest.raises(InvalidPathError, match="Expected index"):
            jsonpath({"a": [1]}, "$.a[abc]")

    def test_bare_field_name_without_prefix_raises(self):
        with pytest.raises(InvalidPathError, match="Unexpected character"):
            jsonpath({"name": "Alice"}, "name")

    def test_bare_field_name_after_root_raises(self):
        with pytest.raises(InvalidPathError, match="Unexpected character"):
            jsonpath({"name": "Alice"}, "$name")


class TestJSONPathQueryClass:
    def test_query_reuse(self):
        data = {"a": {"b": 1}, "c": {"b": 2}}
        q = JSONPathQuery(data)
        assert q.query("$.a.b") == [1]
        assert q.query("$.c.b") == [2]

    def test_query_with_complex_data(self):
        q = JSONPathQuery(_SAMPLE_DATA)
        result = q.query("$.store.book[*].isbn")
        assert result == ["0-553-21311-3", "0-261-10353-7"]


class TestComplexPaths:
    def test_bracket_field_then_index(self):
        data = {"items": {"nested": [10, 20]}}
        result = jsonpath(data, "$['items']['nested'][0]")
        assert result == [10]

    def test_recursive_then_index(self):
        result = jsonpath(_SAMPLE_DATA, "$..book[2].title")
        assert result == ["Moby Dick"]

    def test_wildcard_then_recursive(self):
        data = {
            "group1": {"tag": "g1"},
            "group2": {"tag": "g2"},
        }
        result = jsonpath(data, "$.*..tag")
        assert result == ["g1", "g2"]

    def test_index_then_wildcard(self):
        data = {"matrix": [{"a": 1, "b": 2}, {"a": 3, "b": 4}]}
        result = jsonpath(data, "$.matrix[0].*")
        assert result == [1, 2]

    def test_recursive_on_top_level_field(self):
        data = {"name": "root", "child": {"name": "inner"}}
        result = jsonpath(data, "$..name")
        assert result == ["root", "inner"]

    def test_field_with_numeric_string_value(self):
        data = {"version": "1.0"}
        result = jsonpath(data, "$.version")
        assert result == ["1.0"]

    def test_bracket_field_with_special_chars(self):
        data = {"key with spaces": 42}
        result = jsonpath(data, "$['key with spaces']")
        assert result == [42]

    def test_bracket_field_with_dot(self):
        data = {"a.b": "dotted"}
        result = jsonpath(data, "$['a.b']")
        assert result == ["dotted"]
