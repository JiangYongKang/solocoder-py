from __future__ import annotations

import threading
from typing import Any, Dict, Iterable, List, Optional, Set

from .exceptions import (
    CircularReferenceError,
    InvalidTagError,
    ObjectNotFoundError,
    TagAlreadyExistsError,
    TagHierarchyError,
    TagNotFoundError,
)
from .models import TagHierarchyStats, TagNode


class TagHierarchy:
    def __init__(self) -> None:
        self._tags: Dict[Any, TagNode] = {}
        self._object_direct_tags: Dict[Any, Set[Any]] = {}
        self._object_effective_tags: Dict[Any, Set[Any]] = {}
        self._tag_direct_objects: Dict[Any, Set[Any]] = {}
        self._lock = threading.Lock()

    def get_stats(self) -> TagHierarchyStats:
        with self._lock:
            root_count = sum(
                1 for tag in self._tags.values() if tag.is_root() and not tag.is_dangling
            )
            dangling_count = sum(
                1 for tag in self._tags.values() if tag.is_dangling
            )
            return TagHierarchyStats(
                tag_count=len(self._tags),
                root_tag_count=root_count,
                dangling_tag_count=dangling_count,
                object_count=len(self._object_direct_tags),
            )

    def create_tag(
        self,
        tag_id: Any,
        name: str,
        parent_id: Optional[Any] = None,
    ) -> TagNode:
        if tag_id is None:
            raise InvalidTagError("Tag ID cannot be None")
        if not name:
            raise InvalidTagError("Tag name cannot be empty")

        with self._lock:
            if tag_id in self._tags:
                raise TagAlreadyExistsError(f"Tag {tag_id!r} already exists")

            if parent_id is not None and parent_id not in self._tags:
                raise TagNotFoundError(f"Parent tag {parent_id!r} not found")

            tag_node = TagNode(
                tag_id=tag_id,
                name=name,
                parent_id=parent_id,
            )
            self._tags[tag_id] = tag_node
            self._tag_direct_objects[tag_id] = set()

            if parent_id is not None:
                self._tags[parent_id].children_ids.add(tag_id)

            return TagNode(
                tag_id=tag_node.tag_id,
                name=tag_node.name,
                parent_id=tag_node.parent_id,
                children_ids=tag_node.children_ids.copy(),
                is_dangling=tag_node.is_dangling,
            )

    def delete_tag(self, tag_id: Any) -> bool:
        if tag_id is None:
            raise InvalidTagError("Tag ID cannot be None")

        with self._lock:
            if tag_id not in self._tags:
                raise TagNotFoundError(f"Tag {tag_id!r} not found")

            self._delete_tag_internal(tag_id)
            return True

    def move_tag(self, tag_id: Any, new_parent_id: Optional[Any]) -> None:
        if tag_id is None:
            raise InvalidTagError("Tag ID cannot be None")

        with self._lock:
            if tag_id not in self._tags:
                raise TagNotFoundError(f"Tag {tag_id!r} not found")

            if new_parent_id is not None and new_parent_id not in self._tags:
                raise TagNotFoundError(f"New parent tag {new_parent_id!r} not found")

            if tag_id == new_parent_id:
                raise CircularReferenceError(
                    "Cannot move tag to be its own parent"
                )

            if new_parent_id is not None:
                descendants = self._get_descendants_internal(tag_id)
                if new_parent_id in descendants:
                    raise CircularReferenceError(
                        f"Cannot move tag {tag_id!r} under its descendant {new_parent_id!r}"
                    )

            tag_node = self._tags[tag_id]
            old_parent_id = tag_node.parent_id

            if old_parent_id == new_parent_id:
                return

            if old_parent_id is not None and old_parent_id in self._tags:
                self._tags[old_parent_id].children_ids.discard(tag_id)

            tag_node.parent_id = new_parent_id
            tag_node.is_dangling = False

            if new_parent_id is not None:
                self._tags[new_parent_id].children_ids.add(tag_id)

            self._recalc_descendants_effective_tags(tag_id)

    def get_tag(self, tag_id: Any) -> TagNode:
        if tag_id is None:
            raise InvalidTagError("Tag ID cannot be None")

        with self._lock:
            if tag_id not in self._tags:
                raise TagNotFoundError(f"Tag {tag_id!r} not found")

            tag_node = self._tags[tag_id]
            return TagNode(
                tag_id=tag_node.tag_id,
                name=tag_node.name,
                parent_id=tag_node.parent_id,
                children_ids=tag_node.children_ids.copy(),
                is_dangling=tag_node.is_dangling,
            )

    def has_tag(self, tag_id: Any) -> bool:
        if tag_id is None:
            raise InvalidTagError("Tag ID cannot be None")

        with self._lock:
            return tag_id in self._tags

    def get_children(self, tag_id: Any) -> List[TagNode]:
        if tag_id is None:
            raise InvalidTagError("Tag ID cannot be None")

        with self._lock:
            if tag_id not in self._tags:
                raise TagNotFoundError(f"Tag {tag_id!r} not found")

            children = []
            for child_id in self._tags[tag_id].children_ids:
                if child_id in self._tags:
                    child = self._tags[child_id]
                    children.append(TagNode(
                        tag_id=child.tag_id,
                        name=child.name,
                        parent_id=child.parent_id,
                        children_ids=child.children_ids.copy(),
                        is_dangling=child.is_dangling,
                    ))
            return children

    def get_ancestors(self, tag_id: Any) -> List[TagNode]:
        if tag_id is None:
            raise InvalidTagError("Tag ID cannot be None")

        with self._lock:
            if tag_id not in self._tags:
                raise TagNotFoundError(f"Tag {tag_id!r} not found")

            ancestors = []
            current_id = self._tags[tag_id].parent_id
            while current_id is not None and current_id in self._tags:
                ancestor = self._tags[current_id]
                ancestors.append(TagNode(
                    tag_id=ancestor.tag_id,
                    name=ancestor.name,
                    parent_id=ancestor.parent_id,
                    children_ids=ancestor.children_ids.copy(),
                    is_dangling=ancestor.is_dangling,
                ))
                current_id = ancestor.parent_id
            return ancestors

    def get_descendants(self, tag_id: Any) -> List[TagNode]:
        if tag_id is None:
            raise InvalidTagError("Tag ID cannot be None")

        with self._lock:
            if tag_id not in self._tags:
                raise TagNotFoundError(f"Tag {tag_id!r} not found")

            descendant_ids = self._get_descendants_internal(tag_id)
            descendants = []
            for desc_id in descendant_ids:
                if desc_id in self._tags:
                    desc = self._tags[desc_id]
                    descendants.append(TagNode(
                        tag_id=desc.tag_id,
                        name=desc.name,
                        parent_id=desc.parent_id,
                        children_ids=desc.children_ids.copy(),
                        is_dangling=desc.is_dangling,
                    ))
            return descendants

    def get_root_tags(self) -> List[TagNode]:
        with self._lock:
            roots = []
            for tag in self._tags.values():
                if tag.is_root() and not tag.is_dangling:
                    roots.append(TagNode(
                        tag_id=tag.tag_id,
                        name=tag.name,
                        parent_id=tag.parent_id,
                        children_ids=tag.children_ids.copy(),
                        is_dangling=tag.is_dangling,
                    ))
            return roots

    def tag_object(self, obj_id: Any, tag_id: Any) -> bool:
        if tag_id is None:
            raise InvalidTagError("Tag ID cannot be None")
        if obj_id is None:
            raise InvalidTagError("Object ID cannot be None")

        with self._lock:
            if tag_id not in self._tags:
                raise TagNotFoundError(f"Tag {tag_id!r} not found")

            if obj_id not in self._object_direct_tags:
                self._object_direct_tags[obj_id] = set()
                self._object_effective_tags[obj_id] = set()

            if tag_id in self._object_direct_tags[obj_id]:
                return False

            self._object_direct_tags[obj_id].add(tag_id)
            self._tag_direct_objects[tag_id].add(obj_id)

            ancestor_ids = self._get_ancestor_ids_internal(tag_id)
            self._object_effective_tags[obj_id].add(tag_id)
            self._object_effective_tags[obj_id].update(ancestor_ids)

            return True

    def untag_object(self, obj_id: Any, tag_id: Any) -> bool:
        if tag_id is None:
            raise InvalidTagError("Tag ID cannot be None")
        if obj_id is None:
            raise InvalidTagError("Object ID cannot be None")

        with self._lock:
            if tag_id not in self._tags:
                raise TagNotFoundError(f"Tag {tag_id!r} not found")

            if obj_id not in self._object_direct_tags:
                raise ObjectNotFoundError(f"Object {obj_id!r} not found")

            if tag_id not in self._object_direct_tags[obj_id]:
                return False

            self._object_direct_tags[obj_id].discard(tag_id)
            self._tag_direct_objects[tag_id].discard(obj_id)

            if not self._object_direct_tags[obj_id]:
                del self._object_direct_tags[obj_id]
                del self._object_effective_tags[obj_id]
            else:
                self._recalc_object_effective_tags(obj_id)

            return True

    def get_object_tags(
        self,
        obj_id: Any,
        include_inherited: bool = True,
    ) -> Set[Any]:
        if obj_id is None:
            raise InvalidTagError("Object ID cannot be None")

        with self._lock:
            if obj_id not in self._object_direct_tags:
                raise ObjectNotFoundError(f"Object {obj_id!r} not found")

            if not include_inherited:
                return self._object_direct_tags[obj_id].copy()

            return self._object_effective_tags[obj_id].copy()

    def object_has_tag(
        self,
        obj_id: Any,
        tag_id: Any,
        include_inherited: bool = True,
    ) -> bool:
        if tag_id is None:
            raise InvalidTagError("Tag ID cannot be None")
        if obj_id is None:
            raise InvalidTagError("Object ID cannot be None")

        with self._lock:
            if tag_id not in self._tags:
                raise TagNotFoundError(f"Tag {tag_id!r} not found")

            if obj_id not in self._object_direct_tags:
                return False

            if not include_inherited:
                return tag_id in self._object_direct_tags[obj_id]

            return tag_id in self._object_effective_tags[obj_id]

    def find_objects_by_tag(self, tag_id: Any) -> Set[Any]:
        if tag_id is None:
            raise InvalidTagError("Tag ID cannot be None")

        with self._lock:
            if tag_id not in self._tags:
                raise TagNotFoundError(f"Tag {tag_id!r} not found")

            return self._find_objects_by_tag_internal(tag_id)

    def find_objects_by_tags(self, tag_ids: Iterable[Any]) -> Set[Any]:
        tag_list = list(tag_ids)

        for tag_id in tag_list:
            if tag_id is None:
                raise InvalidTagError("Tag ID cannot be None")

        if not tag_list:
            return set()

        with self._lock:
            for tag_id in tag_list:
                if tag_id not in self._tags:
                    raise TagNotFoundError(f"Tag {tag_id!r} not found")

            smallest_tag_id = None
            smallest_count = None
            for tag_id in tag_list:
                count = self._count_objects_by_tag_internal(tag_id)
                if smallest_count is None or count < smallest_count:
                    smallest_count = count
                    smallest_tag_id = tag_id

            if smallest_tag_id is None or smallest_count == 0:
                return set()

            candidate_objects = self._find_objects_by_tag_internal(smallest_tag_id)

            other_tag_ids = [t for t in tag_list if t != smallest_tag_id]

            result: Set[Any] = set()
            for obj_id in candidate_objects:
                effective_tags = self._object_effective_tags.get(obj_id, set())
                if all(t in effective_tags for t in other_tag_ids):
                    result.add(obj_id)

            return result

    def find_dangling_tags(self) -> Set[Any]:
        with self._lock:
            return self._find_dangling_tags_internal()

    def cleanup_dangling_tags(self) -> int:
        with self._lock:
            dangling = self._find_dangling_tags_internal()
            for tag_id in dangling:
                self._delete_tag_internal(tag_id)
            return len(dangling)

    def _get_descendants_internal(self, tag_id: Any) -> Set[Any]:
        descendants: Set[Any] = set()
        stack = list(self._tags[tag_id].children_ids)
        while stack:
            child_id = stack.pop()
            if child_id not in descendants and child_id in self._tags:
                descendants.add(child_id)
                stack.extend(self._tags[child_id].children_ids)
        return descendants

    def _get_ancestor_ids_internal(self, tag_id: Any) -> Set[Any]:
        ancestors: Set[Any] = set()
        current_id = self._tags[tag_id].parent_id if tag_id in self._tags else None
        while current_id is not None and current_id in self._tags:
            ancestors.add(current_id)
            current_id = self._tags[current_id].parent_id
        return ancestors

    def _find_objects_by_tag_internal(self, tag_id: Any) -> Set[Any]:
        result: Set[Any] = set()
        tag_and_descendants = {tag_id} | self._get_descendants_internal(tag_id)
        for t_id in tag_and_descendants:
            if t_id in self._tag_direct_objects:
                result.update(self._tag_direct_objects[t_id])
        return result

    def _count_objects_by_tag_internal(self, tag_id: Any) -> int:
        count = 0
        tag_and_descendants = {tag_id} | self._get_descendants_internal(tag_id)
        for t_id in tag_and_descendants:
            if t_id in self._tag_direct_objects:
                count += len(self._tag_direct_objects[t_id])
        return count

    def _find_dangling_tags_internal(self) -> Set[Any]:
        return {
            tag_id for tag_id, tag in self._tags.items() if tag.is_dangling
        }

    def _delete_tag_internal(self, tag_id: Any) -> None:
        if tag_id not in self._tags:
            return

        tag_node = self._tags[tag_id]

        if tag_node.parent_id is not None:
            parent = self._tags.get(tag_node.parent_id)
            if parent is not None:
                parent.children_ids.discard(tag_id)

        descendant_ids = self._get_descendants_internal(tag_id)

        child_ids = list(tag_node.children_ids)
        for child_id in child_ids:
            if child_id in self._tags:
                child = self._tags[child_id]
                child.parent_id = None
                child.is_dangling = True

        if tag_id in self._tag_direct_objects:
            for obj_id in self._tag_direct_objects[tag_id]:
                if obj_id in self._object_direct_tags:
                    self._object_direct_tags[obj_id].discard(tag_id)
                    if not self._object_direct_tags[obj_id]:
                        del self._object_direct_tags[obj_id]
                        if obj_id in self._object_effective_tags:
                            del self._object_effective_tags[obj_id]
                    else:
                        self._recalc_object_effective_tags(obj_id)
            del self._tag_direct_objects[tag_id]

        del self._tags[tag_id]

        for desc_id in descendant_ids:
            if desc_id in self._tag_direct_objects:
                for obj_id in list(self._tag_direct_objects[desc_id]):
                    if obj_id in self._object_direct_tags:
                        self._recalc_object_effective_tags(obj_id)

    def _recalc_object_effective_tags(self, obj_id: Any) -> None:
        if obj_id not in self._object_direct_tags:
            if obj_id in self._object_effective_tags:
                del self._object_effective_tags[obj_id]
            return

        effective_tags: Set[Any] = set()
        for direct_tag_id in self._object_direct_tags[obj_id]:
            effective_tags.add(direct_tag_id)
            effective_tags.update(self._get_ancestor_ids_internal(direct_tag_id))

        self._object_effective_tags[obj_id] = effective_tags

    def _recalc_descendants_effective_tags(self, tag_id: Any) -> None:
        tag_and_descendants = {tag_id} | self._get_descendants_internal(tag_id)

        affected_objects: Set[Any] = set()
        for t_id in tag_and_descendants:
            if t_id in self._tag_direct_objects:
                affected_objects.update(self._tag_direct_objects[t_id])

        for obj_id in affected_objects:
            self._recalc_object_effective_tags(obj_id)
