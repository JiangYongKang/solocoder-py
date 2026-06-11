import pytest

from solocoder_py.cancel_token import CancelToken, CancelTokenInfo
from solocoder_py.cancel_token.exceptions import CancelTokenError


class TestCancelTokenCreation:
    def test_create_root_token_default_id(self, make_root_token):
        token = make_root_token()
        assert token.token_id is not None
        assert isinstance(token.token_id, str)
        assert len(token.token_id) > 0

    def test_create_root_token_custom_id(self, make_root_token):
        token = make_root_token(token_id="my-token")
        assert token.token_id == "my-token"

    def test_new_token_is_active(self, make_root_token):
        token = make_root_token()
        assert token.is_active is True
        assert token.is_cancelled is False

    def test_new_token_has_no_parent(self, make_root_token):
        token = make_root_token()
        assert token.parent is None

    def test_new_token_has_no_children(self, make_root_token):
        token = make_root_token()
        assert token.children_count == 0
        assert len(token.children) == 0


class TestCancelTokenTreeStructure:
    def test_create_single_child(self, make_root_token):
        root = make_root_token(token_id="root")
        child = root.create_child(token_id="child")
        assert root.children_count == 1
        assert root.children[0] is child
        assert child.parent is root
        assert child.is_active is True

    def test_create_multiple_children(self, make_two_level_tree):
        root, children = make_two_level_tree()
        assert root.children_count == 3
        for i, child in enumerate(children):
            assert root.children[i] is child
            assert child.parent is root

    def test_create_grandchild(self, make_three_level_tree):
        root, level1, level2 = make_three_level_tree()
        assert level1[0].children_count == 2
        assert level1[1].children_count == 1
        assert level2[0].parent is level1[0]
        assert level2[1].parent is level1[0]
        assert level2[2].parent is level1[1]

    def test_children_returns_copy(self, make_root_token):
        root = make_root_token()
        child = root.create_child()
        children_list = root.children
        children_list.append("fake")
        assert root.children_count == 1
        assert "fake" not in root.children


class TestCascadeCancellation:
    def test_cancel_root_cancels_all_children(self, make_two_level_tree):
        root, children = make_two_level_tree()
        root.cancel()
        assert root.is_cancelled is True
        for child in children:
            assert child.is_cancelled is True
            assert child.is_active is False

    def test_cancel_root_cancels_all_descendants(self, make_three_level_tree):
        root, level1, level2 = make_three_level_tree()
        root.cancel()
        assert root.is_cancelled is True
        for token in level1 + level2:
            assert token.is_cancelled is True

    def test_deep_nested_cascade_cancellation(self, make_deep_nested_tree):
        root, chain = make_deep_nested_tree(depth=20)
        root.cancel()
        assert root.is_cancelled is True
        for token in chain:
            assert token.is_cancelled is True


class TestSingleBranchIsolation:
    def test_cancel_child_does_not_affect_parent(self, make_two_level_tree):
        root, children = make_two_level_tree()
        children[0].cancel()
        assert children[0].is_cancelled is True
        assert root.is_cancelled is False
        assert root.is_active is True

    def test_cancel_child_does_not_affect_siblings(self, make_two_level_tree):
        root, children = make_two_level_tree()
        children[0].cancel()
        assert children[0].is_cancelled is True
        assert children[1].is_active is True
        assert children[2].is_active is True

    def test_cancel_child_cancels_its_own_descendants_only(self, make_three_level_tree):
        root, level1, level2 = make_three_level_tree()
        level1[0].cancel()
        assert level1[0].is_cancelled is True
        assert level2[0].is_cancelled is True
        assert level2[1].is_cancelled is True
        assert level1[1].is_active is True
        assert level2[2].is_active is True
        assert root.is_active is True


class TestIdempotentOperations:
    def test_cancel_already_cancelled_token_is_noop(self, make_root_token):
        token = make_root_token()
        token.cancel()
        assert token.is_cancelled is True
        try:
            token.cancel()
        except Exception as e:
            pytest.fail(f"cancel() on cancelled token raised exception: {e}")
        assert token.is_cancelled is True

    def test_cancel_already_cancelled_token_multiple_times(self, make_root_token):
        token = make_root_token()
        for _ in range(5):
            token.cancel()
        assert token.is_cancelled is True

    def test_create_child_on_cancelled_token_returns_cancelled_child(self, make_root_token):
        root = make_root_token()
        root.cancel()
        child = root.create_child(token_id="child-of-cancelled")
        assert child.is_cancelled is True
        assert child.is_active is False
        assert child.parent is root

    def test_create_child_on_cancelled_token_chain(self, make_root_token):
        root = make_root_token()
        root.cancel()
        child1 = root.create_child()
        child2 = root.create_child()
        grandchild = child1.create_child()
        assert child1.is_cancelled is True
        assert child2.is_cancelled is True
        assert grandchild.is_cancelled is True

    def test_cancel_on_cancelled_branch_does_not_raise(self, make_three_level_tree):
        root, level1, level2 = make_three_level_tree()
        level1[0].cancel()
        try:
            level2[0].cancel()
            level1[0].cancel()
        except Exception as e:
            pytest.fail(f"cancel() on already cancelled branch raised exception: {e}")


class TestEdgeCases:
    def test_single_node_tree_cancel(self, make_root_token):
        token = make_root_token(token_id="single")
        assert token.children_count == 0
        token.cancel()
        assert token.is_cancelled is True
        assert token.children_count == 0

    def test_leaf_node_cancel(self, make_three_level_tree):
        root, level1, level2 = make_three_level_tree()
        level2[0].cancel()
        assert level2[0].is_cancelled is True
        for token in [root, level1[0], level1[1], level2[1], level2[2]]:
            assert token.is_active is True

    def test_empty_children_list_on_leaf(self, make_root_token):
        root = make_root_token()
        child = root.create_child()
        assert child.children_count == 0
        assert child.children == []

    def test_very_deep_nesting(self, make_deep_nested_tree):
        root, chain = make_deep_nested_tree(depth=100)
        assert len(chain) == 99
        assert chain[-1].parent is chain[-2]
        chain[50].cancel()
        for token in chain[:50]:
            assert token.is_active is True
        for token in chain[50:]:
            assert token.is_cancelled is True
        assert root.is_active is True


class TestCancelTokenInfo:
    def test_active_token_to_info(self, make_root_token):
        token = make_root_token(token_id="info-test")
        info = token.to_info()
        assert isinstance(info, CancelTokenInfo)
        assert info.token_id == "info-test"
        assert info.is_cancelled is False
        assert info.is_active is True
        assert info.parent_id is None
        assert info.children_count == 0

    def test_cancelled_token_to_info(self, make_root_token):
        token = make_root_token(token_id="cancelled-info")
        token.cancel()
        info = token.to_info()
        assert info.is_cancelled is True
        assert info.is_active is False

    def test_child_token_to_info(self, make_root_token):
        root = make_root_token(token_id="parent")
        child = root.create_child(token_id="child")
        root_info = root.to_info()
        child_info = child.to_info()
        assert root_info.children_count == 1
        assert child_info.parent_id == "parent"


class TestCancelTokenError:
    def test_cancel_token_error_is_exception(self):
        assert issubclass(CancelTokenError, Exception)

    def test_raise_cancel_token_error(self):
        with pytest.raises(CancelTokenError):
            raise CancelTokenError("test error")
