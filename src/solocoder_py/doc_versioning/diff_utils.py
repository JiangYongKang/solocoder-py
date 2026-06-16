from __future__ import annotations

from typing import List, Sequence

from ..three_way_merge import (
    ChangeType,
    DiffHunk,
    TextLine,
    diff_hunks,
)
from .exceptions import InvalidVersionError
from .models import DocumentDiff


def _to_lines(text: str) -> List[TextLine]:
    raw_lines = text.split("\n") if text else []
    return [TextLine(content=line, line_number=i) for i, line in enumerate(raw_lines)]


def _lines_to_text(lines: Sequence[str]) -> str:
    return "\n".join(lines)


def compute_diff(base_text: str, target_text: str,
                 base_version: int = 0, target_version: int = 0) -> DocumentDiff:
    base_lines = _to_lines(base_text)
    target_lines = _to_lines(target_text)

    hunks = diff_hunks(base_lines, target_lines)

    return DocumentDiff(
        base_version=base_version,
        target_version=target_version,
        hunks=list(hunks),
    )


def apply_diff(base_text: str, diff: DocumentDiff) -> str:
    base_lines = _to_lines(base_text)

    if diff.is_empty:
        return base_text

    result_lines: List[str] = []
    cursor = 0
    n_base = len(base_lines)

    for hunk in diff.hunks:
        if hunk.base_start > cursor:
            for i in range(cursor, hunk.base_start):
                result_lines.append(base_lines[i].content)

        for line in hunk.lines:
            result_lines.append(line.content)

        cursor = hunk.base_end + 1

    if cursor < n_base:
        for i in range(cursor, n_base):
            result_lines.append(base_lines[i].content)

    return _lines_to_text(result_lines)


def apply_diffs_sequential(baseline_text: str, diffs: Sequence[DocumentDiff]) -> str:
    current = baseline_text
    for diff in diffs:
        current = apply_diff(current, diff)
    return current


def validate_diff_chain(baseline: str, diffs: Sequence[DocumentDiff],
                        expected_final: str) -> bool:
    reconstructed = apply_diffs_sequential(baseline, diffs)
    return reconstructed == expected_final
