import pytest

from solocoder_py.tag_hierarchy import (
    TagHierarchy,
    TagNode,
)


class TestTagCreationAndHierarchy:
    def test_create_root_tag(self, tag_hierarchy: TagHierarchy):
        tag = tag_hierarchy.create_tag("tech", "Technology")
        assert tag.tag_id == "tech"
        assert tag.name == "Technology"
        assert tag.parent_id is None
        assert tag.is_root() is True
        assert tag.is_dangling is False

    def test_create_child_tag(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("tech", "Technology")
        tag = tag_hierarchy.create_tag("python", "Python", parent_id="tech")
        assert tag.tag_id == "python"
        assert tag.parent_id == "tech"
        assert tag.is_root() is False

    def test_tag_children_relationship(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("tech", "Technology")
        tag_hierarchy.create_tag("python", "Python", parent_id="tech")
        tag_hierarchy.create_tag("java", "Java", parent_id="tech")

        children = tag_hierarchy.get_children("tech")
        child_ids = {child.tag_id for child in children}
        assert child_ids == {"python", "java"}

    def test_get_root_tags(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("tech", "Technology")
        tag_hierarchy.create_tag("business", "Business")
        tag_hierarchy.create_tag("python", "Python", parent_id="tech")

        roots = tag_hierarchy.get_root_tags()
        root_ids = {root.tag_id for root in roots}
        assert root_ids == {"tech", "business"}

    def test_move_tag(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("tech", "Technology")
        tag_hierarchy.create_tag("language", "Programming Language")
        tag_hierarchy.create_tag("python", "Python", parent_id="tech")

        tag_hierarchy.move_tag("python", "language")

        tag = tag_hierarchy.get_tag("python")
        assert tag.parent_id == "language"

        tech_children = tag_hierarchy.get_children("tech")
        assert len(tech_children) == 0

        lang_children = tag_hierarchy.get_children("language")
        assert len(lang_children) == 1
        assert lang_children[0].tag_id == "python"

    def test_move_tag_preserves_descendants(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("tech", "Technology")
        tag_hierarchy.create_tag("language", "Programming Language")
        tag_hierarchy.create_tag("python", "Python", parent_id="tech")
        tag_hierarchy.create_tag("django", "Django", parent_id="python")
        tag_hierarchy.create_tag("flask", "Flask", parent_id="python")

        tag_hierarchy.move_tag("python", "language")

        python_tag = tag_hierarchy.get_tag("python")
        assert python_tag.parent_id == "language"

        python_children = tag_hierarchy.get_children("python")
        child_ids = {child.tag_id for child in python_children}
        assert child_ids == {"django", "flask"}

    def test_delete_tag(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("tech", "Technology")
        assert tag_hierarchy.has_tag("tech") is True

        result = tag_hierarchy.delete_tag("tech")
        assert result is True
        assert tag_hierarchy.has_tag("tech") is False

    def test_get_ancestors(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("tech", "Technology")
        tag_hierarchy.create_tag("language", "Programming Language", parent_id="tech")
        tag_hierarchy.create_tag("python", "Python", parent_id="language")
        tag_hierarchy.create_tag("django", "Django", parent_id="python")

        ancestors = tag_hierarchy.get_ancestors("django")
        ancestor_ids = [a.tag_id for a in ancestors]
        assert ancestor_ids == ["python", "language", "tech"]

    def test_get_descendants(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("tech", "Technology")
        tag_hierarchy.create_tag("language", "Programming Language", parent_id="tech")
        tag_hierarchy.create_tag("python", "Python", parent_id="language")
        tag_hierarchy.create_tag("java", "Java", parent_id="language")
        tag_hierarchy.create_tag("django", "Django", parent_id="python")

        descendants = tag_hierarchy.get_descendants("tech")
        descendant_ids = {d.tag_id for d in descendants}
        assert descendant_ids == {"language", "python", "java", "django"}


class TestObjectTaggingAndInheritance:
    def test_tag_object(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("tech", "Technology")
        result = tag_hierarchy.tag_object("article:1", "tech")
        assert result is True

    def test_tag_object_idempotent(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("tech", "Technology")
        assert tag_hierarchy.tag_object("article:1", "tech") is True
        assert tag_hierarchy.tag_object("article:1", "tech") is False

    def test_untag_object(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("tech", "Technology")
        tag_hierarchy.tag_object("article:1", "tech")
        result = tag_hierarchy.untag_object("article:1", "tech")
        assert result is True

    def test_get_object_direct_tags(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("tech", "Technology")
        tag_hierarchy.create_tag("python", "Python", parent_id="tech")
        tag_hierarchy.create_tag("tutorial", "Tutorial")

        tag_hierarchy.tag_object("article:1", "python")
        tag_hierarchy.tag_object("article:1", "tutorial")

        direct_tags = tag_hierarchy.get_object_tags("article:1", include_inherited=False)
        assert direct_tags == {"python", "tutorial"}

    def test_get_object_tags_with_inheritance(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("tech", "Technology")
        tag_hierarchy.create_tag("language", "Programming Language", parent_id="tech")
        tag_hierarchy.create_tag("python", "Python", parent_id="language")

        tag_hierarchy.tag_object("article:1", "python")

        all_tags = tag_hierarchy.get_object_tags("article:1", include_inherited=True)
        assert all_tags == {"python", "language", "tech"}

    def test_object_has_tag_direct(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("python", "Python")
        tag_hierarchy.tag_object("article:1", "python")
        assert tag_hierarchy.object_has_tag("article:1", "python") is True

    def test_object_has_tag_inherited(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("tech", "Technology")
        tag_hierarchy.create_tag("python", "Python", parent_id="tech")

        tag_hierarchy.tag_object("article:1", "python")

        assert tag_hierarchy.object_has_tag("article:1", "tech") is True
        assert tag_hierarchy.object_has_tag("article:1", "tech", include_inherited=False) is False

    def test_find_objects_by_tag_direct(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("tech", "Technology")
        tag_hierarchy.tag_object("article:1", "tech")
        tag_hierarchy.tag_object("article:2", "tech")

        objects = tag_hierarchy.find_objects_by_tag("tech")
        assert objects == {"article:1", "article:2"}

    def test_find_objects_by_tag_with_inheritance(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("tech", "Technology")
        tag_hierarchy.create_tag("python", "Python", parent_id="tech")
        tag_hierarchy.create_tag("java", "Java", parent_id="tech")

        tag_hierarchy.tag_object("article:1", "python")
        tag_hierarchy.tag_object("article:2", "java")
        tag_hierarchy.tag_object("article:3", "tech")

        objects = tag_hierarchy.find_objects_by_tag("tech")
        assert objects == {"article:1", "article:2", "article:3"}

    def test_find_objects_by_child_tag(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("tech", "Technology")
        tag_hierarchy.create_tag("python", "Python", parent_id="tech")

        tag_hierarchy.tag_object("article:1", "python")
        tag_hierarchy.tag_object("article:2", "tech")

        objects = tag_hierarchy.find_objects_by_tag("python")
        assert objects == {"article:1"}


class TestIntersectionQuery:
    def test_find_objects_by_tags_single_tag(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("tech", "Technology")
        tag_hierarchy.tag_object("article:1", "tech")
        tag_hierarchy.tag_object("article:2", "tech")

        result = tag_hierarchy.find_objects_by_tags(["tech"])
        assert result == {"article:1", "article:2"}

    def test_find_objects_by_tags_intersection(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("tech", "Technology")
        tag_hierarchy.create_tag("tutorial", "Tutorial")
        tag_hierarchy.create_tag("python", "Python", parent_id="tech")

        tag_hierarchy.tag_object("article:1", "python")
        tag_hierarchy.tag_object("article:1", "tutorial")
        tag_hierarchy.tag_object("article:2", "python")
        tag_hierarchy.tag_object("article:3", "tutorial")

        result = tag_hierarchy.find_objects_by_tags(["tech", "tutorial"])
        assert result == {"article:1"}

    def test_find_objects_by_tags_with_inheritance(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("tech", "Technology")
        tag_hierarchy.create_tag("python", "Python", parent_id="tech")
        tag_hierarchy.create_tag("web", "Web Development")
        tag_hierarchy.create_tag("django", "Django", parent_id="web")

        tag_hierarchy.tag_object("article:1", "python")
        tag_hierarchy.tag_object("article:1", "django")
        tag_hierarchy.tag_object("article:2", "python")
        tag_hierarchy.tag_object("article:3", "django")

        result = tag_hierarchy.find_objects_by_tags(["tech", "web"])
        assert result == {"article:1"}

    def test_find_objects_by_tags_no_match(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("tech", "Technology")
        tag_hierarchy.create_tag("business", "Business")

        tag_hierarchy.tag_object("article:1", "tech")
        tag_hierarchy.tag_object("article:2", "business")

        result = tag_hierarchy.find_objects_by_tags(["tech", "business"])
        assert result == set()

    def test_find_objects_by_tags_multiple(self, tag_hierarchy: TagHierarchy):
        tag_hierarchy.create_tag("a", "Tag A")
        tag_hierarchy.create_tag("b", "Tag B")
        tag_hierarchy.create_tag("c", "Tag C")

        tag_hierarchy.tag_object("obj:1", "a")
        tag_hierarchy.tag_object("obj:1", "b")
        tag_hierarchy.tag_object("obj:1", "c")
        tag_hierarchy.tag_object("obj:2", "a")
        tag_hierarchy.tag_object("obj:2", "b")
        tag_hierarchy.tag_object("obj:3", "a")

        result = tag_hierarchy.find_objects_by_tags(["a", "b", "c"])
        assert result == {"obj:1"}
