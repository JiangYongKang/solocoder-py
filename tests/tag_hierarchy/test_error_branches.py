import pytest

from solocoder_py.tag_hierarchy import (
    CircularReferenceError,
    InvalidTagError,
    ObjectNotFoundError,
    TagAlreadyExistsError,
    TagHierarchy,
    TagNotFoundError,
)


class TestDanglingTagCleanup:
    def test_delete_parent_creates_dangling_children(
        self, tag_hierarchy: TagHierarchy
    ):
        tag_hierarchy.create_tag("parent", "Parent")
        tag_hierarchy.create_tag("child1", "Child 1", parent_id="parent")
        tag_hierarchy.create_tag("child2", "Child 2", parent_id="parent")
        tag_hierarchy.create_tag("grandchild", "Grandchild", parent_id="child1")

        tag_hierarchy.delete_tag("parent")

        dangling = tag_hierarchy.find_dangling_tags()
        assert dangling == {"child1", "child2"}

        child1 = tag_hierarchy.get_tag("child1")
        assert child1.parent_id is None
        assert child1.is_dangling is True

        grandchild = tag_hierarchy.get_tag("grandchild")
        assert grandchild.parent_id == "child1"
        assert grandchild.is_dangling is False

    def test_cleanup_dangling_tags(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("parent", "Parent")
        tag_hierarchy.create_tag("child1", "Child 1", parent_id="parent")
        tag_hierarchy.create_tag("child2", "Child 2", parent_id="parent")

        tag_hierarchy.delete_tag("parent")
        assert tag_hierarchy.find_dangling_tags() == {"child1", "child2"}

        cleaned = tag_hierarchy.cleanup_dangling_tags()
        assert cleaned == 2
        assert tag_hierarchy.find_dangling_tags() == set()
        assert tag_hierarchy.has_tag("child1") is False
        assert tag_hierarchy.has_tag("child2") is False

    def test_cleanup_dangling_with_grandchildren(
        self, tag_hierarchy: TagHierarchy
    ):
        tag_hierarchy.create_tag("root", "Root")
        tag_hierarchy.create_tag("level1", "Level 1", parent_id="root")
        tag_hierarchy.create_tag("level2", "Level 2", parent_id="level1")
        tag_hierarchy.create_tag("level3", "Level 3", parent_id="level2")

        tag_hierarchy.delete_tag("root")
        assert tag_hierarchy.find_dangling_tags() == {"level1"}

        tag_hierarchy.cleanup_dangling_tags()

        assert tag_hierarchy.has_tag("level2") is True
        assert tag_hierarchy.has_tag("level3") is True

        level2 = tag_hierarchy.get_tag("level2")
        assert level2.parent_id is None
        assert level2.is_dangling is True

    def test_dangling_tags_not_in_root_tags(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("parent", "Parent")
        tag_hierarchy.create_tag("child", "Child", parent_id="parent")

        tag_hierarchy.delete_tag("parent")

        roots = tag_hierarchy.get_root_tags()
        root_ids = {r.tag_id for r in roots}
        assert "child" not in root_ids

    def test_move_dangling_tag_removes_dangling_flag(
        self, tag_hierarchy: TagHierarchy
    ):
        tag_hierarchy.create_tag("parent", "Parent")
        tag_hierarchy.create_tag("child", "Child", parent_id="parent")
        tag_hierarchy.create_tag("new_parent", "New Parent")

        tag_hierarchy.delete_tag("parent")
        assert tag_hierarchy.get_tag("child").is_dangling is True

        tag_hierarchy.move_tag("child", "new_parent")
        child = tag_hierarchy.get_tag("child")
        assert child.is_dangling is False
        assert child.parent_id == "new_parent"

    def test_dangling_tag_with_objects(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("parent", "Parent")
        tag_hierarchy.create_tag("child", "Child", parent_id="parent")
        tag_hierarchy.tag_object("obj:1", "child")

        tag_hierarchy.delete_tag("parent")

        assert tag_hierarchy.find_dangling_tags() == {"child"}

        objects = tag_hierarchy.find_objects_by_tag("child")
        assert objects == {"obj:1"}

        tag_hierarchy.cleanup_dangling_tags()
        assert tag_hierarchy.has_tag("child") is False

    def test_delete_nonleaf_tag_invalidates_grandchild_object_cache(
        self, tag_hierarchy: TagHierarchy
    ):
        tag_hierarchy.create_tag("a", "A")
        tag_hierarchy.create_tag("b", "B", parent_id="a")
        tag_hierarchy.create_tag("c", "C", parent_id="b")

        tag_hierarchy.tag_object("obj:1", "c")

        tags_before = tag_hierarchy.get_object_tags("obj:1", include_inherited=True)
        assert tags_before == {"a", "b", "c"}

        tag_hierarchy.delete_tag("a")

        tags_after = tag_hierarchy.get_object_tags("obj:1", include_inherited=True)
        assert tags_after == {"b", "c"}
        assert "a" not in tags_after

    def test_delete_nonleaf_tag_invalidates_child_object_cache(
        self, tag_hierarchy: TagHierarchy
    ):
        tag_hierarchy.create_tag("a", "A")
        tag_hierarchy.create_tag("b", "B", parent_id="a")

        tag_hierarchy.tag_object("obj:1", "b")

        tags_before = tag_hierarchy.get_object_tags("obj:1", include_inherited=True)
        assert tags_before == {"a", "b"}

        tag_hierarchy.delete_tag("a")

        tags_after = tag_hierarchy.get_object_tags("obj:1", include_inherited=True)
        assert tags_after == {"b"}
        assert "a" not in tags_after

    def test_delete_nonleaf_tag_object_has_tag_no_longer_true(
        self, tag_hierarchy: TagHierarchy
    ):
        tag_hierarchy.create_tag("a", "A")
        tag_hierarchy.create_tag("b", "B", parent_id="a")

        tag_hierarchy.tag_object("obj:1", "b")
        assert tag_hierarchy.object_has_tag("obj:1", "a") is True

        tag_hierarchy.delete_tag("a")

        with pytest.raises(TagNotFoundError):
            tag_hierarchy.object_has_tag("obj:1", "a")

    def test_delete_nonleaf_tag_deep_chain_cache_invalidation(
        self, tag_hierarchy: TagHierarchy
    ):
        tag_hierarchy.create_tag("l0", "L0")
        tag_hierarchy.create_tag("l1", "L1", parent_id="l0")
        tag_hierarchy.create_tag("l2", "L2", parent_id="l1")
        tag_hierarchy.create_tag("l3", "L3", parent_id="l2")
        tag_hierarchy.create_tag("l4", "L4", parent_id="l3")

        tag_hierarchy.tag_object("obj:1", "l4")
        tag_hierarchy.tag_object("obj:2", "l2")

        tags1_before = tag_hierarchy.get_object_tags("obj:1", include_inherited=True)
        assert tags1_before == {"l0", "l1", "l2", "l3", "l4"}

        tags2_before = tag_hierarchy.get_object_tags("obj:2", include_inherited=True)
        assert tags2_before == {"l0", "l1", "l2"}

        tag_hierarchy.delete_tag("l1")

        tags1_after = tag_hierarchy.get_object_tags("obj:1", include_inherited=True)
        assert tags1_after == {"l2", "l3", "l4"}
        assert "l0" not in tags1_after
        assert "l1" not in tags1_after

        tags2_after = tag_hierarchy.get_object_tags("obj:2", include_inherited=True)
        assert tags2_after == {"l2"}
        assert "l0" not in tags2_after
        assert "l1" not in tags2_after

    def test_delete_nonleaf_tag_find_objects_by_tag_uses_correct_cache(
        self, tag_hierarchy: TagHierarchy
    ):
        tag_hierarchy.create_tag("a", "A")
        tag_hierarchy.create_tag("b", "B", parent_id="a")
        tag_hierarchy.create_tag("other_root", "Other Root")

        tag_hierarchy.tag_object("obj:1", "b")
        tag_hierarchy.tag_object("obj:2", "other_root")

        result_before = tag_hierarchy.find_objects_by_tags(["a", "other_root"])
        assert result_before == set()

        tag_hierarchy.delete_tag("a")

        result_after = tag_hierarchy.find_objects_by_tags(["b", "other_root"])
        assert result_after == set()


class TestCircularReference:
    def test_move_tag_to_itself_raises(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("tag", "Tag")

        with pytest.raises(CircularReferenceError, match="its own parent"):
            tag_hierarchy.move_tag("tag", "tag")

    def test_move_parent_to_child_raises(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("parent", "Parent")
        tag_hierarchy.create_tag("child", "Child", parent_id="parent")

        with pytest.raises(CircularReferenceError, match="descendant"):
            tag_hierarchy.move_tag("parent", "child")

    def test_move_ancestor_to_descendant_deep_raises(
        self, tag_hierarchy: TagHierarchy
    ):
        tag_hierarchy.create_tag("level0", "Level 0")
        tag_hierarchy.create_tag("level1", "Level 1", parent_id="level0")
        tag_hierarchy.create_tag("level2", "Level 2", parent_id="level1")
        tag_hierarchy.create_tag("level3", "Level 3", parent_id="level2")

        with pytest.raises(CircularReferenceError, match="descendant"):
            tag_hierarchy.move_tag("level0", "level3")

    def test_move_tag_to_sibling_is_ok(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("parent", "Parent")
        tag_hierarchy.create_tag("sibling1", "Sibling 1", parent_id="parent")
        tag_hierarchy.create_tag("sibling2", "Sibling 2", parent_id="parent")

        tag_hierarchy.move_tag("sibling1", "sibling2")

        tag = tag_hierarchy.get_tag("sibling1")
        assert tag.parent_id == "sibling2"

        children = tag_hierarchy.get_children("sibling2")
        assert len(children) == 1
        assert children[0].tag_id == "sibling1"


class TestTagNotFound:
    def test_get_nonexistent_tag_raises(self, tag_hierarchy: TagHierarchy):
        with pytest.raises(TagNotFoundError, match="not found"):
            tag_hierarchy.get_tag("nonexistent")

    def test_delete_nonexistent_tag_raises(self, tag_hierarchy: TagHierarchy):
        with pytest.raises(TagNotFoundError, match="not found"):
            tag_hierarchy.delete_tag("nonexistent")

    def test_move_nonexistent_tag_raises(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("target", "Target")
        with pytest.raises(TagNotFoundError, match="not found"):
            tag_hierarchy.move_tag("nonexistent", "target")

    def test_move_to_nonexistent_parent_raises(
        self, tag_hierarchy: TagHierarchy
    ):
        tag_hierarchy.create_tag("tag", "Tag")
        with pytest.raises(TagNotFoundError, match="not found"):
            tag_hierarchy.move_tag("tag", "nonexistent")

    def test_create_tag_with_nonexistent_parent_raises(
        self, tag_hierarchy: TagHierarchy
    ):
        with pytest.raises(TagNotFoundError, match="not found"):
            tag_hierarchy.create_tag("child", "Child", parent_id="nonexistent")

    def test_get_children_nonexistent_tag_raises(
        self, tag_hierarchy: TagHierarchy
    ):
        with pytest.raises(TagNotFoundError, match="not found"):
            tag_hierarchy.get_children("nonexistent")

    def test_get_ancestors_nonexistent_tag_raises(
        self, tag_hierarchy: TagHierarchy
    ):
        with pytest.raises(TagNotFoundError, match="not found"):
            tag_hierarchy.get_ancestors("nonexistent")

    def test_get_descendants_nonexistent_tag_raises(
        self, tag_hierarchy: TagHierarchy
    ):
        with pytest.raises(TagNotFoundError, match="not found"):
            tag_hierarchy.get_descendants("nonexistent")

    def test_find_objects_by_nonexistent_tag_raises(
        self, tag_hierarchy: TagHierarchy
    ):
        with pytest.raises(TagNotFoundError, match="not found"):
            tag_hierarchy.find_objects_by_tag("nonexistent")

    def test_find_objects_by_tags_with_nonexistent_raises(
        self, tag_hierarchy: TagHierarchy
    ):
        tag_hierarchy.create_tag("valid", "Valid")
        with pytest.raises(TagNotFoundError, match="not found"):
            tag_hierarchy.find_objects_by_tags(["valid", "nonexistent"])

    def test_object_has_tag_nonexistent_raises(
        self, tag_hierarchy: TagHierarchy
    ):
        with pytest.raises(TagNotFoundError, match="not found"):
            tag_hierarchy.object_has_tag("obj:1", "nonexistent")

    def test_tag_object_nonexistent_tag_raises(
        self, tag_hierarchy: TagHierarchy
    ):
        with pytest.raises(TagNotFoundError, match="not found"):
            tag_hierarchy.tag_object("obj:1", "nonexistent")

    def test_untag_object_nonexistent_tag_raises(
        self, tag_hierarchy: TagHierarchy
    ):
        tag_hierarchy.create_tag("tech", "Technology")
        tag_hierarchy.tag_object("obj:1", "tech")
        with pytest.raises(TagNotFoundError, match="not found"):
            tag_hierarchy.untag_object("obj:1", "nonexistent")


class TestInvalidTagError:
    def test_none_tag_id_raises(self, tag_hierarchy: TagHierarchy):
        with pytest.raises(InvalidTagError, match="cannot be None"):
            tag_hierarchy.create_tag(None, "Name")

    def test_empty_name_raises(self, tag_hierarchy: TagHierarchy):
        with pytest.raises(InvalidTagError, match="cannot be empty"):
            tag_hierarchy.create_tag("id", "")

    def test_has_tag_none_raises(self, tag_hierarchy: TagHierarchy):
        with pytest.raises(InvalidTagError, match="cannot be None"):
            tag_hierarchy.has_tag(None)

    def test_get_tag_none_raises(self, tag_hierarchy: TagHierarchy):
        with pytest.raises(InvalidTagError, match="cannot be None"):
            tag_hierarchy.get_tag(None)

    def test_delete_tag_none_raises(self, tag_hierarchy: TagHierarchy):
        with pytest.raises(InvalidTagError, match="cannot be None"):
            tag_hierarchy.delete_tag(None)

    def test_move_tag_none_raises(self, tag_hierarchy: TagHierarchy):
        with pytest.raises(InvalidTagError, match="cannot be None"):
            tag_hierarchy.move_tag(None, "parent")

    def test_tag_object_none_tag_raises(self, tag_hierarchy: TagHierarchy):
        with pytest.raises(InvalidTagError, match="cannot be None"):
            tag_hierarchy.tag_object("obj:1", None)

    def test_tag_object_none_obj_raises(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("tech", "Technology")
        with pytest.raises(InvalidTagError, match="cannot be None"):
            tag_hierarchy.tag_object(None, "tech")

    def test_find_objects_by_tag_none_raises(self, tag_hierarchy: TagHierarchy):
        with pytest.raises(InvalidTagError, match="cannot be None"):
            tag_hierarchy.find_objects_by_tag(None)

    def test_find_objects_by_tags_none_raises(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("tech", "Technology")
        with pytest.raises(InvalidTagError, match="cannot be None"):
            tag_hierarchy.find_objects_by_tags(["tech", None])


class TestObjectNotFound:
    def test_get_object_tags_nonexistent_raises(
        self, tag_hierarchy: TagHierarchy
    ):
        with pytest.raises(ObjectNotFoundError, match="not found"):
            tag_hierarchy.get_object_tags("nonexistent")

    def test_untag_nonexistent_object_raises(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("tech", "Technology")
        with pytest.raises(ObjectNotFoundError, match="not found"):
            tag_hierarchy.untag_object("nonexistent", "tech")


class TestTagAlreadyExists:
    def test_create_duplicate_tag_raises(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("tech", "Technology")
        with pytest.raises(TagAlreadyExistsError, match="already exists"):
            tag_hierarchy.create_tag("tech", "Tech 2")
