import pytest

from solocoder_py.json_patch import (
    apply,
    apply_atomic,
    pointer_add_value,
    pointer_delete,
    pointer_get,
    pointer_parse,
    pointer_set_value,
    PatchTestFailedError,
    PathNotFoundError,
)


class TestJsonPointerParse:
    def test_empty_string_returns_empty_list(self):
        assert pointer_parse("") == []

    def test_root_pointer(self):
        assert pointer_parse("/") == [""]

    def test_simple_key(self):
        assert pointer_parse("/foo") == ["foo"]

    def test_nested_keys(self):
        assert pointer_parse("/foo/bar/baz") == ["foo", "bar", "baz"]

    def test_array_index(self):
        assert pointer_parse("/foo/0/bar") == ["foo", "0", "bar"]

    def test_unescape_tilde0(self):
        assert pointer_parse("/a~0b") == ["a~b"]

    def test_unescape_tilde1(self):
        assert pointer_parse("/a~1b") == ["a/b"]

    def test_unescape_both(self):
        assert pointer_parse("/a~0~1b") == ["a~/b"]


class TestJsonPointerGet:
    def test_get_from_object(self):
        doc = {"foo": "bar"}
        assert pointer_get(doc, "/foo") == "bar"

    def test_get_from_array(self):
        doc = {"items": [1, 2, 3]}
        assert pointer_get(doc, "/items/1") == 2

    def test_get_nested(self):
        doc = {"a": {"b": {"c": 42}}}
        assert pointer_get(doc, "/a/b/c") == 42

    def test_get_root(self):
        doc = {"x": 1}
        assert pointer_get(doc, "") == {"x": 1}

    def test_get_string_key_numeric(self):
        doc = {"0": "zero"}
        assert pointer_get(doc, "/0") == "zero"

    def test_get_from_array_in_object(self):
        doc = {"users": [{"name": "Alice"}, {"name": "Bob"}]}
        assert pointer_get(doc, "/users/1/name") == "Bob"


class TestJsonPointerSet:
    def test_set_in_object(self):
        doc = {"foo": "old"}
        result = pointer_set_value(doc, "/foo", "new")
        assert result == {"foo": "new"}
        assert doc == {"foo": "old"}

    def test_set_new_key_in_object(self):
        doc = {"foo": 1}
        result = pointer_set_value(doc, "/bar", 2)
        assert result == {"foo": 1, "bar": 2}

    def test_set_in_array(self):
        doc = [1, 2, 3]
        result = pointer_set_value(doc, "/1", 99)
        assert result == [1, 99, 3]

    def test_set_append_to_array(self):
        doc = [1, 2, 3]
        result = pointer_add_value(doc, "/-", 4)
        assert result == [1, 2, 3, 4]

    def test_set_insert_in_array(self):
        doc = [1, 2, 3]
        result = pointer_add_value(doc, "/1", 99)
        assert result == [1, 99, 2, 3]

    def test_set_nested(self):
        doc = {"a": {"b": 1}}
        result = pointer_set_value(doc, "/a/b", 2)
        assert result == {"a": {"b": 2}}

    def test_set_root(self):
        doc = {"old": True}
        result = pointer_set_value(doc, "", {"new": True})
        assert result == {"new": True}


class TestJsonPointerDelete:
    def test_delete_from_object(self):
        doc = {"foo": 1, "bar": 2}
        result = pointer_delete(doc, "/foo")
        assert result == {"bar": 2}

    def test_delete_from_array(self):
        doc = [1, 2, 3]
        result = pointer_delete(doc, "/1")
        assert result == [1, 3]

    def test_delete_nested(self):
        doc = {"a": {"b": 1, "c": 2}}
        result = pointer_delete(doc, "/a/b")
        assert result == {"a": {"c": 2}}


class TestOpAdd:
    def test_add_to_object(self):
        doc = {"foo": 1}
        result = apply(doc, [{"op": "add", "path": "/bar", "value": 2}])
        assert result == {"foo": 1, "bar": 2}

    def test_add_to_array_append(self):
        doc = {"items": [1, 2]}
        result = apply(doc, [{"op": "add", "path": "/items/-", "value": 3}])
        assert result == {"items": [1, 2, 3]}

    def test_add_to_array_insert(self):
        doc = {"items": [1, 3]}
        result = apply(doc, [{"op": "add", "path": "/items/1", "value": 2}])
        assert result == {"items": [1, 2, 3]}

    def test_add_overwrite_existing_key(self):
        doc = {"foo": "old"}
        result = apply(doc, [{"op": "add", "path": "/foo", "value": "new"}])
        assert result == {"foo": "new"}

    def test_add_new_key_to_object(self):
        doc = {"foo": 1}
        result = apply(doc, [{"op": "add", "path": "/bar", "value": 2}])
        assert result == {"foo": 1, "bar": 2}

    def test_add_nested_value(self):
        doc = {"a": {"b": 1}}
        result = apply(doc, [{"op": "add", "path": "/a/c", "value": 2}])
        assert result == {"a": {"b": 1, "c": 2}}


class TestOpRemove:
    def test_remove_from_object(self):
        doc = {"foo": 1, "bar": 2}
        result = apply(doc, [{"op": "remove", "path": "/bar"}])
        assert result == {"foo": 1}

    def test_remove_from_array(self):
        doc = [1, 2, 3]
        result = apply(doc, [{"op": "remove", "path": "/1"}])
        assert result == [1, 3]

    def test_remove_nested(self):
        doc = {"a": {"b": 1, "c": 2}}
        result = apply(doc, [{"op": "remove", "path": "/a/b"}])
        assert result == {"a": {"c": 2}}


class TestOpReplace:
    def test_replace_in_object(self):
        doc = {"foo": "old"}
        result = apply(doc, [{"op": "replace", "path": "/foo", "value": "new"}])
        assert result == {"foo": "new"}

    def test_replace_in_array(self):
        doc = [1, 2, 3]
        result = apply(doc, [{"op": "replace", "path": "/1", "value": 99}])
        assert result == [1, 99, 3]

    def test_replace_equivalent_to_remove_then_add(self):
        doc = {"foo": "old"}
        result = apply(doc, [{"op": "replace", "path": "/foo", "value": "new"}])
        result2 = apply(doc, [
            {"op": "remove", "path": "/foo"},
            {"op": "add", "path": "/foo", "value": "new"},
        ])
        assert result == result2


class TestOpCopy:
    def test_copy_value(self):
        doc = {"foo": {"x": 1}, "bar": None}
        result = apply(doc, [{"op": "copy", "from": "/foo", "path": "/bar"}])
        assert result == {"foo": {"x": 1}, "bar": {"x": 1}}

    def test_copy_is_deep(self):
        doc = {"src": [1, 2, 3]}
        result = apply(doc, [{"op": "copy", "from": "/src", "path": "/dst"}])
        result["src"].append(4)
        assert result["dst"] == [1, 2, 3]

    def test_copy_array_element(self):
        doc = {"items": [10, 20, 30]}
        result = apply(doc, [{"op": "copy", "from": "/items/1", "path": "/items/-"}])
        assert result == {"items": [10, 20, 30, 20]}


class TestOpMove:
    def test_move_value(self):
        doc = {"foo": 1, "bar": 2}
        result = apply(doc, [{"op": "move", "from": "/foo", "path": "/baz"}])
        assert result == {"bar": 2, "baz": 1}

    def test_move_equivalent_to_copy_then_remove(self):
        doc = {"foo": 1, "bar": 2}
        result = apply(doc, [{"op": "move", "from": "/foo", "path": "/baz"}])
        result2 = apply(doc, [
            {"op": "copy", "from": "/foo", "path": "/baz"},
            {"op": "remove", "path": "/foo"},
        ])
        assert result == result2

    def test_move_array_element(self):
        doc = {"items": [1, 2, 3]}
        result = apply(doc, [{"op": "move", "from": "/items/0", "path": "/items/-"}])
        assert result == {"items": [2, 3, 1]}


class TestOpTest:
    def test_test_passes(self):
        doc = {"foo": "bar"}
        result = apply(doc, [{"op": "test", "path": "/foo", "value": "bar"}])
        assert result == {"foo": "bar"}

    def test_test_fails_raises(self):
        doc = {"foo": "bar"}
        with pytest.raises(PatchTestFailedError):
            apply(doc, [{"op": "test", "path": "/foo", "value": "baz"}])

    def test_test_with_object(self):
        doc = {"foo": {"a": 1}}
        result = apply(doc, [{"op": "test", "path": "/foo", "value": {"a": 1}}])
        assert result == {"foo": {"a": 1}}

    def test_test_with_array(self):
        doc = {"items": [1, 2, 3]}
        result = apply(doc, [{"op": "test", "path": "/items", "value": [1, 2, 3]}])
        assert result == {"items": [1, 2, 3]}


class TestOperationSequence:
    def test_multiple_operations(self):
        doc = {"foo": 1}
        ops = [
            {"op": "add", "path": "/bar", "value": 2},
            {"op": "remove", "path": "/foo"},
            {"op": "add", "path": "/baz", "value": 3},
        ]
        result = apply(doc, ops)
        assert result == {"bar": 2, "baz": 3}

    def test_empty_operations(self):
        doc = {"foo": 1}
        result = apply(doc, [])
        assert result == {"foo": 1}

    def test_apply_atomic_success(self):
        doc = {"foo": 1}
        ops = [
            {"op": "add", "path": "/bar", "value": 2},
        ]
        result = apply_atomic(doc, ops)
        assert result == {"foo": 1, "bar": 2}

    def test_apply_atomic_rollback_on_test_failure(self):
        doc = {"foo": 1}
        ops = [
            {"op": "add", "path": "/bar", "value": 2},
            {"op": "test", "path": "/foo", "value": 999},
        ]
        result = apply_atomic(doc, ops)
        assert result == {"foo": 1}

    def test_original_doc_unchanged(self):
        doc = {"foo": [1, 2]}
        apply(doc, [{"op": "add", "path": "/foo/-", "value": 3}])
        assert doc == {"foo": [1, 2]}

    def test_complex_sequence(self):
        doc = {"users": [{"name": "Alice", "age": 30}]}
        ops = [
            {"op": "add", "path": "/users/-", "value": {"name": "Bob", "age": 25}},
            {"op": "replace", "path": "/users/0/age", "value": 31},
            {"op": "test", "path": "/users/1/name", "value": "Bob"},
        ]
        result = apply(doc, ops)
        assert result == {
            "users": [
                {"name": "Alice", "age": 31},
                {"name": "Bob", "age": 25},
            ]
        }
