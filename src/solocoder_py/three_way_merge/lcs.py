from __future__ import annotations

from typing import List, Sequence, Tuple

from .models import ChangeType, DiffHunk, TextLine


def lcs_table(a: Sequence[TextLine], b: Sequence[TextLine]) -> List[List[int]]:
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp


def backtrack_lcs(
    dp: List[List[int]], a: Sequence[TextLine], b: Sequence[TextLine]
) -> List[Tuple[int, int]]:
    matches: List[Tuple[int, int]] = []
    i, j = len(a), len(b)
    while i > 0 and j > 0:
        if a[i - 1] == b[j - 1]:
            matches.append((i - 1, j - 1))
            i -= 1
            j -= 1
        elif dp[i - 1][j] >= dp[i][j - 1]:
            i -= 1
        else:
            j -= 1
    matches.reverse()
    return matches


def diff_hunks(
    base: Sequence[TextLine], other: Sequence[TextLine]
) -> List[DiffHunk]:
    if not base and not other:
        return []

    dp = lcs_table(base, other)
    matches = backtrack_lcs(dp, base, other)

    hunks: List[DiffHunk] = []
    prev_b, prev_o = -1, -1

    for b_idx, o_idx in matches:
        if b_idx > prev_b + 1 or o_idx > prev_o + 1:
            del_start = prev_b + 1
            del_end = b_idx - 1
            ins_start = prev_o + 1
            ins_end = o_idx - 1

            if del_start <= del_end and ins_start <= ins_end:
                lines = list(other[ins_start : ins_end + 1])
                hunks.append(
                    DiffHunk(
                        base_start=del_start,
                        base_end=del_end,
                        other_start=ins_start,
                        other_end=ins_end,
                        change_type=ChangeType.MODIFIED,
                        lines=lines,
                    )
                )
            elif del_start <= del_end:
                hunks.append(
                    DiffHunk(
                        base_start=del_start,
                        base_end=del_end,
                        other_start=ins_start,
                        other_end=ins_end,
                        change_type=ChangeType.DELETED,
                        lines=[],
                    )
                )
            elif ins_start <= ins_end:
                lines = list(other[ins_start : ins_end + 1])
                hunks.append(
                    DiffHunk(
                        base_start=del_start,
                        base_end=del_end,
                        other_start=ins_start,
                        other_end=ins_end,
                        change_type=ChangeType.INSERTED,
                        lines=lines,
                    )
                )
        prev_b, prev_o = b_idx, o_idx

    n_base, n_other = len(base), len(other)
    if prev_b + 1 < n_base or prev_o + 1 < n_other:
        del_start = prev_b + 1
        del_end = n_base - 1
        ins_start = prev_o + 1
        ins_end = n_other - 1

        if del_start <= del_end and ins_start <= ins_end:
            lines = list(other[ins_start : ins_end + 1])
            hunks.append(
                DiffHunk(
                    base_start=del_start,
                    base_end=del_end,
                    other_start=ins_start,
                    other_end=ins_end,
                    change_type=ChangeType.MODIFIED,
                    lines=lines,
                )
            )
        elif del_start <= del_end:
            hunks.append(
                DiffHunk(
                    base_start=del_start,
                    base_end=del_end,
                    other_start=ins_start,
                    other_end=ins_end,
                    change_type=ChangeType.DELETED,
                    lines=[],
                )
            )
        elif ins_start <= ins_end:
            lines = list(other[ins_start : ins_end + 1])
            hunks.append(
                DiffHunk(
                    base_start=del_start,
                    base_end=del_end,
                    other_start=ins_start,
                    other_end=ins_end,
                    change_type=ChangeType.INSERTED,
                    lines=lines,
                )
            )

    return hunks
