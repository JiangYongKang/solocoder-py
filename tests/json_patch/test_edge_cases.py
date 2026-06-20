import pytest

from solocoder_py.json_patch import (
    apply,
    apply_atomic,
    pointer_add_value,
    pointer_delete,
    pointer_get,
    pointer_parse,
    pointer_set_value,
    AddOutOfBoundsError,
    PatchTestFailedError,
    PathNotFoundError,
)


class TestEmptyOperationList:
    def test_apply_empty_ops(self):
        doc = {"a": 1}
        result = apply(doc, [])
        assert result == {"a": 1}

    def test_apply_atomic_empty_ops(self):
        doc = {"a": 1}
        result = apply_atomic(doc, [])
        assert result == {"a": 1}


class TestRootPath:
    def test_add_at_root(self):
        doc = {"old": True}
        result = apply(doc, [{"op": "add", "path": "", "value": {"new": True}}])
        assert result == {"new": True}

    def test_set_at_root(self):
        doc = {"old": True}
        result = pointer_set_value(doc, "", {"new": True})
        assert result == {"new": True}

    def test_get_at_root(self):
        doc = {"x": 1}
        assert pointer_get(doc, "") == {"x": 1}

    def test_test_at_root(self):
        doc = {"x": 1}
        result = apply(doc, [{"op": "test", "path": "", "value": {"x": 1}}])
        assert result == {"x": 1}


class TestArrayDashAppend:
    def test_add_dash_appends_to_array(self):
        doc = [1, 2, 3]
        result = apply(doc, [{"op": "add", "path": "/-", "value": 4}])
        assert result == [1, 2, 3, 4]

    def test_add_dash_in_nested_array(self):
        doc = {"items": [1, 2]}
        result = apply(doc, [{"op": "add", "path": "/items/-", "value": 3}])
        assert result == {"items": [1, 2, 3]}


class TestDeepNesting:
    def test_deep_nested_add(self):
        doc = {"a": {"b": {"c": {"d": 1}}}}
        result = apply(doc, [{"op": "add", "path": "/a/b/c/e", "value": 2}])
        assert result == {"a": {"b": {"c": {"d": 1, "e": 2}}}}

    def test_deep_nested_get(self):
        doc = {"a": {"b": {"c": {"d": 42}}}}
        assert pointer_get(doc, "/a/b/c/d") == 42

    def test_deep_nested_delete(self):
        doc = {"a": {"b": {"c": {"d": 1, "e": 2}}}}
        result = pointer_delete(doc, "/a/b/c/d")
        assert result == {"a": {"b": {"c": {"e": 2}}}}


class TestTildeEscaping:
    def test_key_with_tilde(self):
        doc = {"a~b": 1}
        assert pointer_get(doc, "/a~0b") == 1

    def test_key_with_slash(self):
        doc = {"a/b": 1}
        assert pointer_get(doc, "/a~1b") == 1

    def test_key_with_tilde_and_slash(self):
        doc = {"a~/b": 1}
        assert pointer_get(doc, "/a~0~1b") == 1

    def test_roundtrip_escaping(self):
        doc = {"a~b/c": 42}
        assert pointer_get(doc, "/a~0b~1c") == 42

    def test_set_with_escaped_key(self):
        doc = {}
        result = pointer_set_value(doc, "/a~0b", 1)
        assert result == {"a~b": 1}

    def test_multiple_escape_sequences(self):
        doc = {"~0~1": "val"}
        assert pointer_get(doc, "/~00~01") == "val"


class TestArrayOutOfBoundsAdd:
    def test_add_at_exact_length(self):
        doc = [1, 2]
        result = pointer_add_value(doc, "/2", 3)
        assert result == [1, 2, 3]

    def test_add_beyond_length_raises(self):
        doc = [1, 2]
        with pytest.raises(AddOutOfBoundsError):
            pointer_add_value(doc, "/5", 99)

    def test_add_negative_index_raises(self):
        doc = [1, 2]
        with pytest.raises(AddOutOfBoundsError):
            pointer_add_value(doc, "/-1", 99)


class TestArrayRemoveShifts:
    def test_remove_shifts_indices(self):
        doc = [10, 20, 30, 40]
        result = apply(doc, [{"op": "remove", "path": "/1"}])
        assert result == [10, 30, 40]

    def test_remove_first_element(self):
        doc = [10, 20, 30]
        result = apply(doc, [{"op": "remove", "path": "/0"}])
        assert result == [20, 30]

    def test_remove_last_element(self):
        doc = [10, 20, 30]
        result = apply(doc, [{"op": "remove", "path": "/2"}])
        assert result == [10, 20]


class TestCopyMoveCrossPaths:
    def test_copy_to_new_nested_path(self):
        doc = {"src": {"a": 1}}
        result = apply(doc, [{"op": "copy", "from": "/src/a", "path": "/dst"}])
        assert result == {"src": {"a": 1}, "dst": 1}

    def test_move_between_siblings(self):
        doc = {"a": 1, "b": 2}
        result = apply(doc, [{"op": "move", "from": "/a", "path": "/c"}])
        assert result == {"b": 2, "c": 1}

    def test_move_within_array(self):
        doc = [0, 1, 2, 3]
        result = apply(doc, [{"op": "move", "from": "/3", "path": "/0"}])
        assert result == [3, 0, 1, 2]

    def test_copy_array_element_to_object(self):
        doc = {"arr": [10, 20]}
        result = apply(doc, [{"op": "copy", "from": "/arr/0", "path": "/val"}])
        assert result == {"arr": [10, 20], "val": 10}
