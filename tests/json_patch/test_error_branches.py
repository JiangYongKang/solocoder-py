import pytest

from solocoder_py.json_patch import (
    apply,
    apply_atomic,
    pointer_delete,
    pointer_get,
    pointer_parse,
    pointer_set_value,
    AddOutOfBoundsError,
    InvalidPointerError,
    PatchOperationError,
    PatchTestFailedError,
    PathNotFoundError,
    UnknownOperationError,
)


class TestTestFailureRollback:
    def test_atomic_rollback_on_test_failure(self):
        doc = {"foo": 1}
        ops = [
            {"op": "add", "path": "/bar", "value": 2},
            {"op": "test", "path": "/foo", "value": 999},
        ]
        result = apply_atomic(doc, ops)
        assert result == {"foo": 1}

    def test_atomic_rollback_preserves_original_on_multi_failure(self):
        doc = {"a": 1, "b": 2}
        ops = [
            {"op": "remove", "path": "/b"},
            {"op": "add", "path": "/c", "value": 3},
            {"op": "test", "path": "/a", "value": 999},
        ]
        result = apply_atomic(doc, ops)
        assert result == {"a": 1, "b": 2}

    def test_non_atomic_propagates_test_failure(self):
        doc = {"foo": 1}
        with pytest.raises(PatchTestFailedError):
            apply(doc, [{"op": "test", "path": "/foo", "value": 2}])

    def test_test_nonexistent_path_raises(self):
        doc = {"foo": 1}
        with pytest.raises(PatchTestFailedError):
            apply(doc, [{"op": "test", "path": "/missing", "value": 1}])

    def test_atomic_rollback_on_invalid_pointer(self):
        doc = {"foo": 1}
        ops = [
            {"op": "add", "path": "/bar", "value": 2},
            {"op": "add", "path": "badpointer", "value": 3},
        ]
        result = apply_atomic(doc, ops)
        assert result == {"foo": 1}

    def test_atomic_rollback_on_invalid_from_pointer(self):
        doc = {"foo": 1}
        ops = [
            {"op": "add", "path": "/bar", "value": 2},
            {"op": "copy", "from": "badfrom", "path": "/baz"},
        ]
        result = apply_atomic(doc, ops)
        assert result == {"foo": 1}


class TestRemoveNonexistentPath:
    def test_remove_missing_key(self):
        doc = {"foo": 1}
        with pytest.raises(PathNotFoundError):
            apply(doc, [{"op": "remove", "path": "/bar"}])

    def test_remove_array_index_out_of_range(self):
        doc = [1, 2]
        with pytest.raises(PathNotFoundError):
            apply(doc, [{"op": "remove", "path": "/5"}])

    def test_remove_from_nonexistent_parent(self):
        doc = {"foo": 1}
        with pytest.raises(PathNotFoundError):
            apply(doc, [{"op": "remove", "path": "/missing/key"}])


class TestReplaceNonexistentPath:
    def test_replace_missing_key(self):
        doc = {"foo": 1}
        with pytest.raises(PathNotFoundError):
            apply(doc, [{"op": "replace", "path": "/bar", "value": 2}])

    def test_replace_array_index_out_of_range(self):
        doc = [1, 2]
        with pytest.raises(PathNotFoundError):
            apply(doc, [{"op": "replace", "path": "/5", "value": 99}])


class TestInvalidPointerFormat:
    def test_pointer_without_leading_slash(self):
        with pytest.raises(InvalidPointerError):
            pointer_parse("foo")

    def test_pointer_with_no_slash(self):
        with pytest.raises(InvalidPointerError):
            pointer_parse("abc/def")

    def test_get_with_invalid_pointer(self):
        doc = {"foo": 1}
        with pytest.raises(InvalidPointerError):
            pointer_get(doc, "foo")

    def test_set_with_invalid_pointer(self):
        doc = {"foo": 1}
        with pytest.raises(InvalidPointerError):
            pointer_set_value(doc, "foo", 2)


class TestUnknownOperationType:
    def test_unknown_op(self):
        doc = {"foo": 1}
        with pytest.raises(UnknownOperationError):
            apply(doc, [{"op": "invalid", "path": "/foo"}])

    def test_missing_op_field(self):
        doc = {"foo": 1}
        with pytest.raises(UnknownOperationError):
            apply(doc, [{"path": "/foo"}])

    def test_missing_path_field(self):
        doc = {"foo": 1}
        with pytest.raises(PatchOperationError, match="Missing 'path'"):
            apply(doc, [{"op": "add", "value": 1}])


class TestCopyMoveFromNonexistent:
    def test_copy_from_nonexistent(self):
        doc = {"foo": 1}
        with pytest.raises(PathNotFoundError):
            apply(doc, [{"op": "copy", "from": "/missing", "path": "/bar"}])

    def test_move_from_nonexistent(self):
        doc = {"foo": 1}
        with pytest.raises(PathNotFoundError):
            apply(doc, [{"op": "move", "from": "/missing", "path": "/bar"}])

    def test_copy_missing_from_field(self):
        doc = {"foo": 1}
        with pytest.raises(PatchOperationError, match="Missing 'from'"):
            apply(doc, [{"op": "copy", "path": "/bar"}])

    def test_move_missing_from_field(self):
        doc = {"foo": 1}
        with pytest.raises(PatchOperationError, match="Missing 'from'"):
            apply(doc, [{"op": "move", "path": "/bar"}])


class TestAddArrayOutOfBounds:
    def test_add_at_index_beyond_length(self):
        doc = [1, 2]
        with pytest.raises(AddOutOfBoundsError):
            apply(doc, [{"op": "add", "path": "/5", "value": 99}])

    def test_add_negative_index(self):
        doc = [1, 2]
        with pytest.raises(AddOutOfBoundsError):
            apply(doc, [{"op": "add", "path": "/-1", "value": 99}])

    def test_add_at_exact_length_is_valid(self):
        doc = [1, 2]
        result = apply(doc, [{"op": "add", "path": "/2", "value": 3}])
        assert result == [1, 2, 3]


class TestDeleteRootError:
    def test_delete_root_raises(self):
        doc = {"foo": 1}
        with pytest.raises(PathNotFoundError, match="Cannot delete root"):
            pointer_delete(doc, "")


class TestGetDashIndexError:
    def test_get_dash_index_raises(self):
        doc = [1, 2, 3]
        with pytest.raises(PathNotFoundError, match="Cannot use '-'"):
            pointer_get(doc, "/-")


class TestTraverseIntoNonContainer:
    def test_get_into_scalar(self):
        doc = {"foo": 1}
        with pytest.raises(PathNotFoundError):
            pointer_get(doc, "/foo/bar")

    def test_set_into_scalar(self):
        doc = {"foo": 1}
        with pytest.raises(PathNotFoundError):
            pointer_set_value(doc, "/foo/bar", 2)
