from __future__ import annotations

from typing import List, Tuple

from .exceptions import InvalidContextLinesError
from .models import DiffHunk, DiffOperation, DiffOperationType, DiffResult, DiffToken


def _slice_equal_op(
    op: DiffOperation,
    start_offset: int = 0,
    end_offset: int = 0,
) -> DiffOperation:
    old_tokens = op.tokens[start_offset:len(op.tokens) - end_offset] if end_offset > 0 else op.tokens[start_offset:]
    return DiffOperation(
        op_type=DiffOperationType.EQUAL,
        old_start=op.old_start + start_offset,
        old_end=op.old_start + start_offset + len(old_tokens),
        new_start=op.new_start + start_offset,
        new_end=op.new_start + start_offset + len(old_tokens),
        tokens=old_tokens,
    )


def build_hunks(
    operations: List[DiffOperation],
    context_lines: int = 3,
) -> List[DiffHunk]:
    if context_lines < 0:
        raise InvalidContextLinesError(context_lines)

    if not operations:
        return []

    change_indices: List[int] = []
    for i, op in enumerate(operations):
        if not op.is_equal:
            change_indices.append(i)

    if not change_indices:
        return []

    merged_regions: List[Tuple[int, int]] = []
    for idx in change_indices:
        if not merged_regions:
            merged_regions.append((idx, idx))
            continue

        last_start, last_end = merged_regions[-1]

        equal_between = 0
        for op in operations[last_end + 1:idx]:
            if op.is_equal:
                equal_between += len(op.tokens)

        if equal_between <= 2 * context_lines:
            merged_regions[-1] = (last_start, idx)
        else:
            merged_regions.append((idx, idx))

    hunks: List[DiffHunk] = []

    for region_start_op_idx, region_end_op_idx in merged_regions:
        context_before_needed = context_lines
        start_op_idx = region_start_op_idx
        prefix_skip = 0

        i = region_start_op_idx - 1
        while i >= 0 and context_before_needed > 0:
            op = operations[i]
            if op.is_equal:
                n = len(op.tokens)
                if n <= context_before_needed:
                    context_before_needed -= n
                    start_op_idx = i
                else:
                    prefix_skip = n - context_before_needed
                    start_op_idx = i
                    context_before_needed = 0
                i -= 1
            else:
                break

        context_after_needed = context_lines
        end_op_idx = region_end_op_idx
        suffix_take = 0

        j = region_end_op_idx + 1
        while j < len(operations) and context_after_needed > 0:
            op = operations[j]
            if op.is_equal:
                n = len(op.tokens)
                if n <= context_after_needed:
                    context_after_needed -= n
                    end_op_idx = j
                else:
                    suffix_take = context_after_needed
                    end_op_idx = j
                    context_after_needed = 0
                j += 1
            else:
                break

        hunk_ops: List[DiffOperation] = []
        for k in range(start_op_idx, end_op_idx + 1):
            op = operations[k]
            op_copy = DiffOperation(
                op_type=op.op_type,
                old_start=op.old_start,
                old_end=op.old_end,
                new_start=op.new_start,
                new_end=op.new_end,
                tokens=list(op.tokens),
            )

            is_first = (k == start_op_idx)
            is_last = (k == end_op_idx)

            if is_first and is_last and op.is_equal and prefix_skip > 0 and suffix_take > 0:
                end_skip = len(op.tokens) - (prefix_skip + suffix_take)
                op_copy = _slice_equal_op(op, prefix_skip, end_skip)
            elif is_first and op.is_equal and prefix_skip > 0:
                op_copy = _slice_equal_op(op, prefix_skip, 0)
            elif is_last and op.is_equal and suffix_take > 0:
                end_skip = len(op.tokens) - suffix_take
                op_copy = _slice_equal_op(op, 0, end_skip)

            hunk_ops.append(op_copy)

        old_start = hunk_ops[0].old_start
        new_start = hunk_ops[0].new_start

        old_count = 0
        new_count = 0
        for op in hunk_ops:
            if op.is_equal or op.is_delete:
                old_count += op.old_end - op.old_start
            if op.is_equal or op.is_insert:
                new_count += op.new_end - op.new_start

        hunks.append(DiffHunk(
            old_start=old_start,
            old_count=old_count,
            new_start=new_start,
            new_count=new_count,
            operations=hunk_ops,
        ))

    return hunks


def format_hunk_header(hunk: DiffHunk) -> str:
    old_display_start = hunk.old_start + 1
    new_display_start = hunk.new_start + 1

    if hunk.old_count == 1:
        old_part = f"-{old_display_start}"
    else:
        old_part = f"-{old_display_start},{hunk.old_count}"

    if hunk.new_count == 1:
        new_part = f"+{new_display_start}"
    else:
        new_part = f"+{new_display_start},{hunk.new_count}"

    return f"@@ {old_part} {new_part} @@"


def format_unified_diff(
    diff_result: DiffResult,
    context_lines: int = 3,
    old_filename: str = "old",
    new_filename: str = "new",
) -> str:
    lines: List[str] = []

    if diff_result.hunks:
        lines.append(f"--- {old_filename}")
        lines.append(f"+++ {new_filename}")

    for hunk in diff_result.hunks:
        lines.append(format_hunk_header(hunk))

        for op in hunk.operations:
            if op.is_equal:
                for token in op.tokens:
                    lines.append(f" {token.content}")
            elif op.is_delete:
                for token in op.tokens:
                    lines.append(f"-{token.content}")
            elif op.is_insert:
                for token in op.tokens:
                    lines.append(f"+{token.content}")

    return "\n".join(lines)
