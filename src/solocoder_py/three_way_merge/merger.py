from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from .exceptions import InvalidInputError
from .lcs import diff_hunks
from .models import (
    Block,
    BlockType,
    ChangeType,
    DiffHunk,
    MergeResult,
    TextLine,
)


CONFLICT_START = "<<<<<<<"
CONFLICT_SEPARATOR = "======="
CONFLICT_END = ">>>>>>>"
CONFLICT_LABEL_A = " A"
CONFLICT_LABEL_B = " B"


def _to_lines(text: str | Sequence[str]) -> List[TextLine]:
    if isinstance(text, str):
        raw_lines = text.split("\n") if text else []
    else:
        raw_lines = list(text)
    return [TextLine(content=line, line_number=i) for i, line in enumerate(raw_lines)]


def _lines_equal(
    lines_a: Sequence[TextLine], lines_b: Sequence[TextLine]
) -> bool:
    if len(lines_a) != len(lines_b):
        return False
    return all(la.content == lb.content for la, lb in zip(lines_a, lines_b))


def _is_insert_range(start: int, end: int) -> bool:
    return start > end


def _ranges_conflict(
    a_start: int, a_end: int, b_start: int, b_end: int
) -> bool:
    a_insert = _is_insert_range(a_start, a_end)
    b_insert = _is_insert_range(b_start, b_end)

    if a_insert and b_insert:
        return a_start == b_start

    if a_insert and not b_insert:
        return b_start <= a_start <= b_end

    if not a_insert and b_insert:
        return a_start <= b_start <= a_end

    return not (a_end < b_start or b_end < a_start)


def _combine_ranges(
    a_start: int, a_end: int, b_start: int, b_end: int
) -> Tuple[int, int]:
    a_insert = _is_insert_range(a_start, a_end)
    b_insert = _is_insert_range(b_start, b_end)
    if a_insert and b_insert:
        return (a_start, a_end)
    if a_insert:
        return (min(a_start, b_start), b_end)
    if b_insert:
        return (min(a_start, b_start), a_end)
    return (min(a_start, b_start), max(a_end, b_end))


@dataclass
class _Segment:
    base_start: int
    base_end: int
    hunk_a: Optional[DiffHunk]
    hunk_b: Optional[DiffHunk]


def _collect_segments(
    hunks_a: Sequence[DiffHunk], hunks_b: Sequence[DiffHunk]
) -> List[_Segment]:
    segments: List[_Segment] = []
    i = j = 0
    n_a, n_b = len(hunks_a), len(hunks_b)

    while i < n_a or j < n_b:
        if i < n_a and (j >= n_b or hunks_a[i].base_start <= hunks_b[j].base_start):
            current_a = hunks_a[i]
            cluster_start, cluster_end = current_a.base_range
            cluster_hunks_a: List[DiffHunk] = [current_a]
            cluster_hunks_b: List[DiffHunk] = []
            i += 1

            changed = True
            while changed:
                changed = False
                while j < n_b and _ranges_conflict(
                    cluster_start, cluster_end,
                    hunks_b[j].base_start, hunks_b[j].base_end
                ):
                    cluster_hunks_b.append(hunks_b[j])
                    cluster_start, cluster_end = _combine_ranges(
                        cluster_start, cluster_end,
                        hunks_b[j].base_start, hunks_b[j].base_end,
                    )
                    j += 1
                    changed = True
                while i < n_a and _ranges_conflict(
                    cluster_start, cluster_end,
                    hunks_a[i].base_start, hunks_a[i].base_end
                ):
                    cluster_hunks_a.append(hunks_a[i])
                    cluster_start, cluster_end = _combine_ranges(
                        cluster_start, cluster_end,
                        hunks_a[i].base_start, hunks_a[i].base_end,
                    )
                    i += 1
                    changed = True

            merged_a = _merge_hunks_in_range(cluster_hunks_a, cluster_start, cluster_end)
            merged_b = _merge_hunks_in_range(cluster_hunks_b, cluster_start, cluster_end)
            segments.append(_Segment(cluster_start, cluster_end, merged_a, merged_b))

        else:
            current_b = hunks_b[j]
            cluster_start, cluster_end = current_b.base_range
            cluster_hunks_a: List[DiffHunk] = []
            cluster_hunks_b: List[DiffHunk] = [current_b]
            j += 1

            changed = True
            while changed:
                changed = False
                while i < n_a and _ranges_conflict(
                    cluster_start, cluster_end,
                    hunks_a[i].base_start, hunks_a[i].base_end
                ):
                    cluster_hunks_a.append(hunks_a[i])
                    cluster_start, cluster_end = _combine_ranges(
                        cluster_start, cluster_end,
                        hunks_a[i].base_start, hunks_a[i].base_end,
                    )
                    i += 1
                    changed = True
                while j < n_b and _ranges_conflict(
                    cluster_start, cluster_end,
                    hunks_b[j].base_start, hunks_b[j].base_end
                ):
                    cluster_hunks_b.append(hunks_b[j])
                    cluster_start, cluster_end = _combine_ranges(
                        cluster_start, cluster_end,
                        hunks_b[j].base_start, hunks_b[j].base_end,
                    )
                    j += 1
                    changed = True

            merged_a = _merge_hunks_in_range(cluster_hunks_a, cluster_start, cluster_end)
            merged_b = _merge_hunks_in_range(cluster_hunks_b, cluster_start, cluster_end)
            segments.append(_Segment(cluster_start, cluster_end, merged_a, merged_b))

    return segments


def _merge_hunks_in_range(
    hunks: Sequence[DiffHunk], range_start: int, range_end: int
) -> Optional[DiffHunk]:
    if not hunks:
        return None

    sorted_hunks = sorted(hunks, key=lambda h: h.base_start)

    all_lines: List[TextLine] = []
    first_other_start = None
    last_other_end = None

    for h in sorted_hunks:
        other_lines = h.lines
        if first_other_start is None:
            first_other_start = h.other_start
        last_other_end = h.other_end
        all_lines.extend(other_lines)

    if first_other_start is None:
        first_other_start = 0
    if last_other_end is None:
        last_other_end = -1

    return DiffHunk(
        base_start=range_start,
        base_end=range_end,
        other_start=first_other_start,
        other_end=last_other_end,
        change_type=ChangeType.MODIFIED,
        lines=all_lines,
    )


def _segment_to_block(
    segment: _Segment,
    base: Sequence[TextLine],
    a: Sequence[TextLine],
    b: Sequence[TextLine],
) -> Block:
    base_slice = list(base[segment.base_start : segment.base_end + 1]) if segment.base_start <= segment.base_end else []

    if segment.hunk_a is None and segment.hunk_b is None:
        return Block(
            block_type=BlockType.COMMON,
            base_lines=base_slice,
            a_lines=base_slice,
            b_lines=base_slice,
        )

    if segment.hunk_a is not None and segment.hunk_b is None:
        a_lines = segment.hunk_a.lines
        return Block(
            block_type=BlockType.CHANGE_A,
            base_lines=base_slice,
            a_lines=a_lines,
            b_lines=base_slice,
        )

    if segment.hunk_a is None and segment.hunk_b is not None:
        b_lines = segment.hunk_b.lines
        return Block(
            block_type=BlockType.CHANGE_B,
            base_lines=base_slice,
            a_lines=base_slice,
            b_lines=b_lines,
        )

    assert segment.hunk_a is not None and segment.hunk_b is not None

    a_lines = segment.hunk_a.lines
    b_lines = segment.hunk_b.lines

    if _lines_equal(a_lines, b_lines):
        return Block(
            block_type=BlockType.CHANGE_A,
            base_lines=base_slice,
            a_lines=a_lines,
            b_lines=b_lines,
        )

    a_same_as_base = _lines_equal(a_lines, base_slice)
    b_same_as_base = _lines_equal(b_lines, base_slice)

    if a_same_as_base and not b_same_as_base:
        return Block(
            block_type=BlockType.CHANGE_B,
            base_lines=base_slice,
            a_lines=a_lines,
            b_lines=b_lines,
        )
    if b_same_as_base and not a_same_as_base:
        return Block(
            block_type=BlockType.CHANGE_A,
            base_lines=base_slice,
            a_lines=a_lines,
            b_lines=b_lines,
        )

    return Block(
        block_type=BlockType.CONFLICT,
        base_lines=base_slice,
        a_lines=a_lines,
        b_lines=b_lines,
    )


def _build_blocks_from_segments(
    base: Sequence[TextLine],
    a: Sequence[TextLine],
    b: Sequence[TextLine],
    segments: Sequence[_Segment],
) -> List[Block]:
    blocks: List[Block] = []
    cursor = 0

    for seg in segments:
        if seg.base_start > cursor:
            common = list(base[cursor : seg.base_start])
            if common:
                blocks.append(Block(
                    block_type=BlockType.COMMON,
                    base_lines=common,
                    a_lines=common,
                    b_lines=common,
                ))
        block = _segment_to_block(seg, base, a, b)
        blocks.append(block)
        cursor = seg.base_end + 1

    if cursor < len(base):
        common = list(base[cursor:])
        if common:
            blocks.append(Block(
                block_type=BlockType.COMMON,
                base_lines=common,
                a_lines=common,
                b_lines=common,
            ))

    return _merge_adjacent_common(blocks)


def _merge_adjacent_common(blocks: Sequence[Block]) -> List[Block]:
    if not blocks:
        return []

    merged: List[Block] = []
    current = Block(
        block_type=blocks[0].block_type,
        base_lines=list(blocks[0].base_lines),
        a_lines=list(blocks[0].a_lines),
        b_lines=list(blocks[0].b_lines),
    )

    for blk in blocks[1:]:
        if blk.block_type == BlockType.COMMON and current.block_type == BlockType.COMMON:
            current.base_lines.extend(blk.base_lines)
            current.a_lines.extend(blk.a_lines)
            current.b_lines.extend(blk.b_lines)
        else:
            merged.append(current)
            current = Block(
                block_type=blk.block_type,
                base_lines=list(blk.base_lines),
                a_lines=list(blk.a_lines),
                b_lines=list(blk.b_lines),
            )
    merged.append(current)
    return merged


class ThreeWayMerger:
    CONFLICT_START = CONFLICT_START
    CONFLICT_SEPARATOR = CONFLICT_SEPARATOR
    CONFLICT_END = CONFLICT_END
    CONFLICT_LABEL_A = CONFLICT_LABEL_A
    CONFLICT_LABEL_B = CONFLICT_LABEL_B

    def __init__(
        self,
        conflict_start: str = CONFLICT_START,
        conflict_separator: str = CONFLICT_SEPARATOR,
        conflict_end: str = CONFLICT_END,
        label_a: str = " A",
        label_b: str = " B",
    ) -> None:
        self.conflict_start = conflict_start
        self.conflict_separator = conflict_separator
        self.conflict_end = conflict_end
        self.label_a = label_a
        self.label_b = label_b

    def _format_conflict_block(self, block: Block) -> List[str]:
        result: List[str] = [self.conflict_start + self.label_a]
        result.extend(line.content for line in block.a_lines)
        result.append(self.conflict_separator)
        result.extend(line.content for line in block.b_lines)
        result.append(self.conflict_end + self.label_b)
        return result

    def _format_block(self, block: Block) -> List[str]:
        if block.block_type == BlockType.COMMON:
            return [line.content for line in block.base_lines]
        elif block.block_type == BlockType.CHANGE_A:
            return [line.content for line in block.a_lines]
        elif block.block_type == BlockType.CHANGE_B:
            return [line.content for line in block.b_lines]
        elif block.block_type == BlockType.CONFLICT:
            return self._format_conflict_block(block)
        return []

    def merge(
        self,
        base: str | Sequence[str],
        a: str | Sequence[str],
        b: str | Sequence[str],
    ) -> MergeResult:
        base_lines = _to_lines(base)
        a_lines = _to_lines(a)
        b_lines = _to_lines(b)

        hunks_a = diff_hunks(base_lines, a_lines)
        hunks_b = diff_hunks(base_lines, b_lines)

        segments = _collect_segments(hunks_a, hunks_b)
        blocks = _build_blocks_from_segments(base_lines, a_lines, b_lines, segments)

        merged_lines: List[str] = []
        conflict_count = 0
        for block in blocks:
            merged_lines.extend(self._format_block(block))
            if block.block_type == BlockType.CONFLICT:
                conflict_count += 1

        return MergeResult(
            merged_lines=merged_lines,
            conflict_count=conflict_count,
            blocks=blocks,
        )


def merge_texts(
    base: str | Sequence[str],
    a: str | Sequence[str],
    b: str | Sequence[str],
) -> MergeResult:
    merger = ThreeWayMerger()
    return merger.merge(base, a, b)
