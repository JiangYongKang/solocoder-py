from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Set


@dataclass
class TagNode:
    tag_id: Any
    name: str
    parent_id: Optional[Any] = None
    children_ids: Set[Any] = field(default_factory=set)
    is_dangling: bool = False

    def is_root(self) -> bool:
        return self.parent_id is None


@dataclass(frozen=True)
class TagHierarchyStats:
    tag_count: int = 0
    root_tag_count: int = 0
    dangling_tag_count: int = 0
    object_count: int = 0
