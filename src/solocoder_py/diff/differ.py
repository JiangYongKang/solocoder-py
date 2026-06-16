from __future__ import annotations

from typing import List, Union

from .exceptions import InvalidGranularityError
from .granularity import tokenize, validate_granularity
from .models import DiffGranularity, DiffOperation, DiffResult, DiffToken
from .myers import MyersDiff
from .unified_diff import build_hunks, format_unified_diff


class TextDiffer:
    def __init__(self) -> None:
        self._myers = MyersDiff()

    def diff(
        self,
        old_text: Union[str, List[str]],
        new_text: Union[str, List[str]],
        granularity: Union[str, DiffGranularity] = DiffGranularity.LINE,
        context_lines: int = 3,
    ) -> DiffResult:
        if isinstance(granularity, str):
            granularity = validate_granularity(granularity)

        if context_lines < 0:
            from .exceptions import InvalidContextLinesError
            raise InvalidContextLinesError(context_lines)

        old_tokens = tokenize(old_text, granularity)
        new_tokens = tokenize(new_text, granularity)

        operations = self._myers.diff(old_tokens, new_tokens)
        hunks = build_hunks(operations, context_lines)

        return DiffResult(
            old_tokens=old_tokens,
            new_tokens=new_tokens,
            operations=operations,
            hunks=hunks,
            granularity=granularity,
        )

    def unified_diff(
        self,
        old_text: Union[str, List[str]],
        new_text: Union[str, List[str]],
        granularity: Union[str, DiffGranularity] = DiffGranularity.LINE,
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
        granularity: Union[str, DiffGranularity] = DiffGranularity.LINE,
    ) -> List[dict]:
        result = self.diff(old_text, new_text, granularity)
        return result.get_operations_list()


def diff_texts(
    old_text: Union[str, List[str]],
    new_text: Union[str, List[str]],
    granularity: Union[str, DiffGranularity] = DiffGranularity.LINE,
    context_lines: int = 3,
) -> DiffResult:
    differ = TextDiffer()
    return differ.diff(old_text, new_text, granularity, context_lines)


def unified_diff_texts(
    old_text: Union[str, List[str]],
    new_text: Union[str, List[str]],
    granularity: Union[str, DiffGranularity] = DiffGranularity.LINE,
    context_lines: int = 3,
    old_filename: str = "old",
    new_filename: str = "new",
) -> str:
    differ = TextDiffer()
    return differ.unified_diff(
        old_text, new_text, granularity, context_lines, old_filename, new_filename
    )
