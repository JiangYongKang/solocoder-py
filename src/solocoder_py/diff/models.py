from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class DiffGranularity(str, Enum):
    LINE = "line"
    WORD = "word"
    CHAR = "char"


class DiffOperationType(str, Enum):
    EQUAL = "equal"
    DELETE = "delete"
    INSERT = "insert"


@dataclass(frozen=True)
class DiffToken:
    content: str
    index: int = 0

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DiffToken):
            return NotImplemented
        return self.content == other.content

    def __hash__(self) -> int:
        return hash(self.content)


@dataclass
class DiffOperation:
    op_type: DiffOperationType
    old_start: int
    old_end: int
    new_start: int
    new_end: int
    tokens: List[DiffToken] = field(default_factory=list)
    sub_operations: List[DiffOperation] = field(default_factory=list)

    @property
    def is_equal(self) -> bool:
        return self.op_type == DiffOperationType.EQUAL

    @property
    def is_delete(self) -> bool:
        return self.op_type == DiffOperationType.DELETE

    @property
    def is_insert(self) -> bool:
        return self.op_type == DiffOperationType.INSERT

    @property
    def has_sub_operations(self) -> bool:
        return len(self.sub_operations) > 0


@dataclass
class DiffHunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    operations: List[DiffOperation] = field(default_factory=list)


@dataclass
class DiffResult:
    old_tokens: List[DiffToken]
    new_tokens: List[DiffToken]
    operations: List[DiffOperation] = field(default_factory=list)
    hunks: List[DiffHunk] = field(default_factory=list)
    granularity: DiffGranularity = DiffGranularity.LINE

    def get_operations_list(self, include_sub: bool = False) -> List[dict]:
        result = []
        for op in self.operations:
            item = {
                "type": op.op_type.value,
                "old_start": op.old_start,
                "old_end": op.old_end,
                "new_start": op.new_start,
                "new_end": op.new_end,
                "content": [t.content for t in op.tokens],
            }
            if include_sub and op.has_sub_operations:
                item["sub_operations"] = [
                    {
                        "type": sub_op.op_type.value,
                        "old_start": sub_op.old_start,
                        "old_end": sub_op.old_end,
                        "new_start": sub_op.new_start,
                        "new_end": sub_op.new_end,
                        "content": [t.content for t in sub_op.tokens],
                    }
                    for sub_op in op.sub_operations
                ]
            result.append(item)
        return result
