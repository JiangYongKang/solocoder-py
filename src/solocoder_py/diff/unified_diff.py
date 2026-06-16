from __future__ import annotations

from typing import List, Tuple

from .exceptions import InvalidContextLinesError
from .models import DiffHunk, DiffOperation, DiffOperationType, DiffResult, DiffToken


def _count_equal_tokens(ops: List[DiffOperation]) -> int:
    count = 0
    for op in ops:
        if op.is_equal:
            count += len(op.tokens)
    return count


def build_hunks(
    operations: List[DiffOperation],
    context_lines: int = 3,
) -> List[DiffHunk]:
    if context_lines < 0:
        raise InvalidContextLinesError(context_lines)

    if not operations:
        return []

    change_regions: List[Tuple[int, int]] = []
    for i, op in enumerate(operations):
        if not op.is_equal:
            change_regions.append((i, i))

    if not change_regions:
        return []

    merged_regions: List[Tuple[int, int]] = []
    for start, end in change_regions:
        if not merged_regions:
            merged_regions.append((start, end))
            continue

        last_start, last_end = merged_regions[-1]
        gap_ops = operations[last_end + 1:start]
        equal_token_count = _count_equal_tokens(gap_ops)
        if equal_token_count <= 2 * context_lines:
            merged_regions[-1] = (last_start, end)
        else:
            merged_regions.append((start, end))

    hunks: List[DiffHunk] = []
    for region_start, region_end in merged_regions:
        context_before = 0
        i = region_start - 1
        while i >= 0 and context_before < context_lines:
            if operations[i].is_equal:
                tokens_count = len(operations[i].tokens)
                if context_before + tokens_count <= context_lines:
                    context_before += tokens_count
                    region_start = i
                else:
                    break
            else:
                break
            i -= 1

        context_after = 0
        j = region_end + 1
        while j < len(operations) and context_after < context_lines:
            if operations[j].is_equal:
                tokens_count = len(operations[j].tokens)
                if context_after + tokens_count <= context_lines:
                    context_after += tokens_count
                    region_end = j
                else:
                    break
            else:
                break
            j += 1

        hunk_ops = operations[region_start:region_end + 1]

        old_start = 0
        new_start = 0
        if hunk_ops:
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


def format_hunk_header(hunk: DiffHunk, granularity: str = "line") -> str:
    old_display_start = hunk.old_start + 1
    new_display_start = hunk.new_start + 1

    if granularity != "line":
        old_display_start = hunk.old_start
        new_display_start = hunk.new_start

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
        lines.append(format_hunk_header(hunk, diff_result.granularity.value))

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
