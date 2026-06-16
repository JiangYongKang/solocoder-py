from __future__ import annotations

from typing import List, Tuple, Union

from .exceptions import InvalidGranularityError
from .granularity import tokenize, validate_granularity
from .models import DiffGranularity, DiffOperation, DiffOperationType, DiffResult, DiffToken
from .myers import MyersDiff
from .unified_diff import build_hunks, format_unified_diff


def _is_composite_granularity(
    granularity: Union[str, DiffGranularity, Tuple[DiffGranularity, DiffGranularity]]
) -> bool:
    return isinstance(granularity, tuple) and len(granularity) == 2


def _normalize_granularity(
    granularity: Union[str, DiffGranularity, Tuple[DiffGranularity, DiffGranularity]]
) -> Union[DiffGranularity, Tuple[DiffGranularity, DiffGranularity]]:
    if isinstance(granularity, tuple):
        if len(granularity) != 2:
            raise InvalidGranularityError(str(granularity))
        coarse = validate_granularity(granularity[0].value if isinstance(granularity[0], DiffGranularity) else granularity[0])
        fine = validate_granularity(granularity[1].value if isinstance(granularity[1], DiffGranularity) else granularity[1])
        if coarse != DiffGranularity.LINE:
            raise InvalidGranularityError("Composite granularity must have LINE as coarse level")
        if fine not in (DiffGranularity.WORD, DiffGranularity.CHAR):
            raise InvalidGranularityError(f"Fine granularity must be WORD or CHAR, got {fine}")
        return (coarse, fine)

    if isinstance(granularity, str):
        return validate_granularity(granularity)

    return granularity


class TextDiffer:
    def __init__(self) -> None:
        self._myers = MyersDiff()

    def diff(
        self,
        old_text: Union[str, List[str]],
        new_text: Union[str, List[str]],
        granularity: Union[str, DiffGranularity, Tuple[DiffGranularity, DiffGranularity]] = DiffGranularity.LINE,
        context_lines: int = 3,
    ) -> DiffResult:
        norm_granularity = _normalize_granularity(granularity)

        if context_lines < 0:
            from .exceptions import InvalidContextLinesError
            raise InvalidContextLinesError(context_lines)

        if _is_composite_granularity(norm_granularity):
            return self._diff_composite(
                old_text, new_text, norm_granularity[0], norm_granularity[1], context_lines
            )

        old_tokens = tokenize(old_text, norm_granularity)
        new_tokens = tokenize(new_text, norm_granularity)

        operations = self._myers.diff(old_tokens, new_tokens)
        hunks = build_hunks(operations, context_lines)

        return DiffResult(
            old_tokens=old_tokens,
            new_tokens=new_tokens,
            operations=operations,
            hunks=hunks,
            granularity=norm_granularity,
        )

    def _diff_composite(
        self,
        old_text: Union[str, List[str]],
        new_text: Union[str, List[str]],
        coarse_granularity: DiffGranularity,
        fine_granularity: DiffGranularity,
        context_lines: int = 3,
    ) -> DiffResult:
        old_tokens = tokenize(old_text, coarse_granularity)
        new_tokens = tokenize(new_text, coarse_granularity)

        operations = self._myers.diff(old_tokens, new_tokens)

        refined_ops = self._refine_modified_lines(
            operations, old_tokens, new_tokens, fine_granularity
        )

        hunks = build_hunks(refined_ops, context_lines)

        return DiffResult(
            old_tokens=old_tokens,
            new_tokens=new_tokens,
            operations=refined_ops,
            hunks=hunks,
            granularity=(coarse_granularity, fine_granularity),
        )

    def _refine_modified_lines(
        self,
        operations: List[DiffOperation],
        old_tokens: List[DiffToken],
        new_tokens: List[DiffToken],
        fine_granularity: DiffGranularity,
    ) -> List[DiffOperation]:
        refined: List[DiffOperation] = []
        i = 0
        processed_indices: set[int] = set()

        while i < len(operations):
            if i in processed_indices:
                i += 1
                continue

            op = operations[i]
            pair_found = False

            if op.is_delete and i + 1 < len(operations) and operations[i + 1].is_insert:
                delete_op = op
                insert_op = operations[i + 1]
                pair_found = True
            elif op.is_insert and i + 1 < len(operations) and operations[i + 1].is_delete:
                insert_op = op
                delete_op = operations[i + 1]
                pair_found = True

            if pair_found:
                old_lines = [t.content for t in delete_op.tokens]
                new_lines = [t.content for t in insert_op.tokens]

                self._refine_line_pair(delete_op, insert_op, old_lines, new_lines, fine_granularity)

                if op.is_delete:
                    refined.append(delete_op)
                    refined.append(insert_op)
                else:
                    refined.append(insert_op)
                    refined.append(delete_op)

                processed_indices.add(i)
                processed_indices.add(i + 1)
                i += 2
            else:
                refined.append(op)
                i += 1

        return refined

    def _refine_line_pair(
        self,
        delete_op: DiffOperation,
        insert_op: DiffOperation,
        old_lines: List[str],
        new_lines: List[str],
        fine_granularity: DiffGranularity,
    ) -> None:
        old_lines_tokens = []
        for line in old_lines:
            old_lines_tokens.append(tokenize(line, fine_granularity))

        new_lines_tokens = []
        for line in new_lines:
            new_lines_tokens.append(tokenize(line, fine_granularity))

        m = len(old_lines)
        n = len(new_lines)
        min_len = min(m, n)

        all_sub_ops: List[DiffOperation] = []
        old_token_offset = 0
        new_token_offset = 0

        for k in range(min_len):
            fine_ops = self._myers.diff(old_lines_tokens[k], new_lines_tokens[k])
            for sub_op in fine_ops:
                shifted = DiffOperation(
                    op_type=sub_op.op_type,
                    old_start=sub_op.old_start + old_token_offset,
                    old_end=sub_op.old_end + old_token_offset,
                    new_start=sub_op.new_start + new_token_offset,
                    new_end=sub_op.new_end + new_token_offset,
                    tokens=list(sub_op.tokens),
                )
                all_sub_ops.append(shifted)
            old_token_offset += len(old_lines_tokens[k])
            new_token_offset += len(new_lines_tokens[k])

        if m > min_len:
            extra_old_tokens = []
            for k in range(min_len, m):
                extra_old_tokens.extend(old_lines_tokens[k])
            if extra_old_tokens:
                all_sub_ops.append(DiffOperation(
                    op_type=DiffOperationType.DELETE,
                    old_start=old_token_offset,
                    old_end=old_token_offset + len(extra_old_tokens),
                    new_start=new_token_offset,
                    new_end=new_token_offset,
                    tokens=extra_old_tokens,
                ))

        if n > min_len:
            extra_new_tokens = []
            for k in range(min_len, n):
                extra_new_tokens.extend(new_lines_tokens[k])
            if extra_new_tokens:
                all_sub_ops.append(DiffOperation(
                    op_type=DiffOperationType.INSERT,
                    old_start=old_token_offset,
                    old_end=old_token_offset,
                    new_start=new_token_offset,
                    new_end=new_token_offset + len(extra_new_tokens),
                    tokens=extra_new_tokens,
                ))

        delete_sub_ops: List[DiffOperation] = []
        insert_sub_ops: List[DiffOperation] = []

        for sub_op in all_sub_ops:
            if sub_op.is_insert:
                insert_sub_ops.append(DiffOperation(
                    op_type=sub_op.op_type,
                    old_start=sub_op.old_start,
                    old_end=sub_op.old_end,
                    new_start=sub_op.new_start,
                    new_end=sub_op.new_end,
                    tokens=list(sub_op.tokens),
                ))
            elif sub_op.is_delete:
                delete_sub_ops.append(DiffOperation(
                    op_type=sub_op.op_type,
                    old_start=sub_op.old_start,
                    old_end=sub_op.old_end,
                    new_start=sub_op.new_start,
                    new_end=sub_op.new_end,
                    tokens=list(sub_op.tokens),
                ))
            else:
                delete_sub_ops.append(DiffOperation(
                    op_type=sub_op.op_type,
                    old_start=sub_op.old_start,
                    old_end=sub_op.old_end,
                    new_start=sub_op.new_start,
                    new_end=sub_op.new_end,
                    tokens=list(sub_op.tokens),
                ))
                insert_sub_ops.append(DiffOperation(
                    op_type=sub_op.op_type,
                    old_start=sub_op.old_start,
                    old_end=sub_op.old_end,
                    new_start=sub_op.new_start,
                    new_end=sub_op.new_end,
                    tokens=list(sub_op.tokens),
                ))

        delete_op.sub_operations = delete_sub_ops
        insert_op.sub_operations = insert_sub_ops

    def unified_diff(
        self,
        old_text: Union[str, List[str]],
        new_text: Union[str, List[str]],
        granularity: Union[str, DiffGranularity, Tuple[DiffGranularity, DiffGranularity]] = DiffGranularity.LINE,
        context_lines: int = 3,
        old_filename: str = "old",
        new_filename: str = "new",
    ) -> str:
        result = self.diff(old_text, new_text, granularity, context_lines)
        return format_unified_diff(result, context_lines, old_filename, new_filename)

    def operations_list(
        self,
        old_text: Union[str, List[str]],
        new_text: Union[str, List[str]],
        granularity: Union[str, DiffGranularity, Tuple[DiffGranularity, DiffGranularity]] = DiffGranularity.LINE,
        include_sub: bool = False,
    ) -> List[dict]:
        result = self.diff(old_text, new_text, granularity)
        return result.get_operations_list(include_sub=include_sub)


def diff_texts(
    old_text: Union[str, List[str]],
    new_text: Union[str, List[str]],
    granularity: Union[str, DiffGranularity, Tuple[DiffGranularity, DiffGranularity]] = DiffGranularity.LINE,
    context_lines: int = 3,
) -> DiffResult:
    differ = TextDiffer()
    return differ.diff(old_text, new_text, granularity, context_lines)


def unified_diff_texts(
    old_text: Union[str, List[str]],
    new_text: Union[str, List[str]],
    granularity: Union[str, DiffGranularity, Tuple[DiffGranularity, DiffGranularity]] = DiffGranularity.LINE,
    context_lines: int = 3,
    old_filename: str = "old",
    new_filename: str = "new",
) -> str:
    differ = TextDiffer()
    return differ.unified_diff(
        old_text, new_text, granularity, context_lines, old_filename, new_filename
    )
