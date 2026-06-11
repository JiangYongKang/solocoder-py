from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class ChangeType(str, Enum):
    UNCHANGED = "unchanged"
    INSERTED = "inserted"
    DELETED = "deleted"
    MODIFIED = "modified"


class BlockType(str, Enum):
    COMMON = "common"
    CHANGE_A = "change_a"
    CHANGE_B = "change_b"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class TextLine:
    content: str
    line_number: int = 0

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TextLine):
            return NotImplemented
        return self.content == other.content

    def __hash__(self) -> int:
        return hash(self.content)


@dataclass
class DiffHunk:
    base_start: int
    base_end: int
    other_start: int
    other_end: int
    change_type: ChangeType
    lines: List[TextLine] = field(default_factory=list)

    @property
    def base_range(self) -> tuple[int, int]:
        return (self.base_start, self.base_end)

    @property
    def other_range(self) -> tuple[int, int]:
        return (self.other_start, self.other_end)

    @property
    def is_empty(self) -> bool:
        return len(self.lines) == 0


@dataclass
class Block:
    block_type: BlockType
    base_lines: List[TextLine] = field(default_factory=list)
    a_lines: List[TextLine] = field(default_factory=list)
    b_lines: List[TextLine] = field(default_factory=list)

    @property
    def is_conflict(self) -> bool:
        return self.block_type == BlockType.CONFLICT


@dataclass
class MergeResult:
    merged_lines: List[str] = field(default_factory=list)
    conflict_count: int = 0
    blocks: List[Block] = field(default_factory=list)

    @property
    def has_conflicts(self) -> bool:
        return self.conflict_count > 0

    def get_merged_text(self, separator: str = "\n") -> str:
        return separator.join(self.merged_lines)

    @property
    def conflict_blocks(self) -> List[Block]:
        return [b for b in self.blocks if b.is_conflict]
