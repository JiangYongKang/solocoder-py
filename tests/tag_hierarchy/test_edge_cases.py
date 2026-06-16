import pytest

from solocoder_py.tag_hierarchy import (
    TagHierarchy,
)


class TestDeepNesting:
    def test_deep_nested_tag_ancestors(self, tag_hierarchy: TagHierarchy):
        depth = 20
        prev_id = None
        for i in range(depth):
            tag_id = f"level_{i}"
            tag_hierarchy.create_tag(tag_id, f"Level {i}", parent_id=prev_id)
            prev_id = tag_id

        deepest = f"level_{depth - 1}"
        ancestors = tag_hierarchy.get_ancestors(deepest)
        assert len(ancestors) == depth - 1

        ancestor_ids = [a.tag_id for a in ancestors]
        expected = [f"level_{i}" for i in range(depth - 2, -1, -1)]
        assert ancestor_ids == expected

    def test_deep_nested_tag_descendants(self, tag_hierarchy: TagHierarchy):
        depth = 15
        prev_id = None
        for i in range(depth):
            tag_id = f"level_{i}"
            tag_hierarchy.create_tag(tag_id, f"Level {i}", parent_id=prev_id)
            prev_id = tag_id

        descendants = tag_hierarchy.get_descendants("level_0")
        assert len(descendants) == depth - 1

    def test_deep_nested_inheritance(self, tag_hierarchy: TagHierarchy):
        depth = 10
        prev_id = None
        for i in range(depth):
            tag_id = f"level_{i}"
            tag_hierarchy.create_tag(tag_id, f"Level {i}", parent_id=prev_id)
            prev_id = tag_id

        deepest = f"level_{depth - 1}"
        tag_hierarchy.tag_object("obj:1", deepest)

        root_objects = tag_hierarchy.find_objects_by_tag("level_0")
        assert root_objects == {"obj:1"}

        all_tags = tag_hierarchy.get_object_tags("obj:1", include_inherited=True)
        assert len(all_tags) == depth


class TestRootTagInheritance:
    def test_root_tag_no_inheritance_up(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("root", "Root")
        tag_hierarchy.tag_object("obj:1", "root")

        tags = tag_hierarchy.get_object_tags("obj:1", include_inherited=True)
        assert tags == {"root"}

    def test_root_tag_query_returns_all_descendants_objects(
        self, tag_hierarchy: TagHierarchy
    ):
        tag_hierarchy.create_tag("root", "Root")
        tag_hierarchy.create_tag("child1", "Child 1", parent_id="root")
        tag_hierarchy.create_tag("child2", "Child 2", parent_id="root")
        tag_hierarchy.create_tag("grandchild", "Grandchild", parent_id="child1")

        tag_hierarchy.tag_object("obj:1", "root")
        tag_hierarchy.tag_object("obj:2", "child1")
        tag_hierarchy.tag_object("obj:3", "child2")
        tag_hierarchy.tag_object("obj:4", "grandchild")

        result = tag_hierarchy.find_objects_by_tag("root")
        assert result == {"obj:1", "obj:2", "obj:3", "obj:4"}

    def test_multiple_root_tags(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("root1", "Root 1")
        tag_hierarchy.create_tag("root2", "Root 2")
        tag_hierarchy.create_tag("child", "Child", parent_id="root1")

        roots = tag_hierarchy.get_root_tags()
        root_ids = {r.tag_id for r in roots}
        assert root_ids == {"root1", "root2"}


class TestEmptyIntersection:
    def test_empty_tag_list_intersection(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("tech", "Technology")
        tag_hierarchy.tag_object("obj:1", "tech")

        result = tag_hierarchy.find_objects_by_tags([])
        assert result == set()

    def test_no_objects_intersection(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("tech", "Technology")
        tag_hierarchy.create_tag("tutorial", "Tutorial")

        result = tag_hierarchy.find_objects_by_tags(["tech", "tutorial"])
        assert result == set()

    def test_partial_match_intersection(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("a", "Tag A")
        tag_hierarchy.create_tag("b", "Tag B")
        tag_hierarchy.create_tag("c", "Tag C")

        tag_hierarchy.tag_object("obj:1", "a")
        tag_hierarchy.tag_object("obj:1", "b")
        tag_hierarchy.tag_object("obj:2", "b")
        tag_hierarchy.tag_object("obj:2", "c")

        result = tag_hierarchy.find_objects_by_tags(["a", "b", "c"])
        assert result == set()

    def test_intersection_with_inherited_tags(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("tech", "Technology")
        tag_hierarchy.create_tag("python", "Python", parent_id="tech")
        tag_hierarchy.create_tag("web", "Web")
        tag_hierarchy.create_tag("frontend", "Frontend", parent_id="web")

        tag_hierarchy.tag_object("obj:1", "python")
        tag_hierarchy.tag_object("obj:1", "frontend")
        tag_hierarchy.tag_object("obj:2", "python")
        tag_hierarchy.tag_object("obj:3", "frontend")

        result = tag_hierarchy.find_objects_by_tags(["tech", "web"])
        assert result == {"obj:1"}


class TestBoundaryConditions:
    def test_tag_without_objects(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("empty", "Empty Tag")

        objects = tag_hierarchy.find_objects_by_tag("empty")
        assert objects == set()

    def test_untag_tag_not_on_object_returns_false(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("tech", "Technology")
        tag_hierarchy.create_tag("business", "Business")
        tag_hierarchy.tag_object("obj:1", "tech")

        result = tag_hierarchy.untag_object("obj:1", "business")
        assert result is False

    def test_move_to_root(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("root", "Root")
        tag_hierarchy.create_tag("child", "Child", parent_id="root")

        tag_hierarchy.move_tag("child", None)

        tag = tag_hierarchy.get_tag("child")
        assert tag.parent_id is None
        assert tag.is_root() is True
        assert tag.is_dangling is False

        roots = tag_hierarchy.get_root_tags()
        root_ids = {r.tag_id for r in roots}
        assert "child" in root_ids

    def test_move_within_same_parent_noop(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("root", "Root")
        tag_hierarchy.create_tag("child", "Child", parent_id="root")

        tag_hierarchy.move_tag("child", "root")

        tag = tag_hierarchy.get_tag("child")
        assert tag.parent_id == "root"

    def test_get_ancestors_of_root(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("root", "Root")

        ancestors = tag_hierarchy.get_ancestors("root")
        assert ancestors == []

    def test_get_descendants_of_leaf(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("root", "Root")
        tag_hierarchy.create_tag("leaf", "Leaf", parent_id="root")

        descendants = tag_hierarchy.get_descendants("leaf")
        assert descendants == []

    def test_has_tag_false(self, tag_hierarchy: TagHierarchy):
        assert tag_hierarchy.has_tag("nonexistent") is False

    def test_object_has_tag_false(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("tech", "Technology")
        assert tag_hierarchy.object_has_tag("nonexistent", "tech") is False

    def test_stats_empty(self, tag_hierarchy: TagHierarchy):
        stats = tag_hierarchy.get_stats()
        assert stats.tag_count == 0
        assert stats.root_tag_count == 0
        assert stats.dangling_tag_count == 0
        assert stats.object_count == 0

    def test_stats_with_tags_and_objects(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("tech", "Technology")
        tag_hierarchy.create_tag("python", "Python", parent_id="tech")
        tag_hierarchy.create_tag("business", "Business")
        tag_hierarchy.tag_object("obj:1", "python")
        tag_hierarchy.tag_object("obj:2", "business")

        stats = tag_hierarchy.get_stats()
        assert stats.tag_count == 3
        assert stats.root_tag_count == 2
        assert stats.dangling_tag_count == 0
        assert stats.object_count == 2
