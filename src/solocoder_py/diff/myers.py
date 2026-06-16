from __future__ import annotations

from typing import List, Sequence, Tuple

from .models import DiffOperation, DiffOperationType, DiffToken


class MyersDiff:
    def __init__(self) -> None:
        pass

    def diff(
        self, old_tokens: Sequence[DiffToken], new_tokens: Sequence[DiffToken]
    ) -> List[DiffOperation]:
        n = len(old_tokens)
        m = len(new_tokens)

        if n == 0 and m == 0:
            return []

        if n == 0:
            return [
                DiffOperation(
                    op_type=DiffOperationType.INSERT,
                    old_start=0,
                    old_end=0,
                    new_start=0,
                    new_end=m,
                    tokens=list(new_tokens),
                )
            ]

        if m == 0:
            return [
                DiffOperation(
                    op_type=DiffOperationType.DELETE,
                    old_start=0,
                    old_end=n,
                    new_start=0,
                    new_end=0,
                    tokens=list(old_tokens),
                )
            ]

        edits = self._myers_shortest_edit(old_tokens, new_tokens)
        return self._edits_to_operations(edits, old_tokens, new_tokens)

    def _myers_shortest_edit(
        self, a: Sequence[DiffToken], b: Sequence[DiffToken]
    ) -> List[Tuple[str, int, int]]:
        n = len(a)
        m = len(b)
        max_d = n + m
        v_size = 2 * max_d + 1
        offset = max_d

        trace: List[List[int]] = []
        v: List[int] = [0] * v_size
        v[1 + offset] = 0

        found = False
        for d in range(max_d + 1):
            v_copy = v.copy()
            trace.append(v_copy)

            for k in range(-d, d + 1, 2):
                if k == -d or (k != d and v[k - 1 + offset] < v[k + 1 + offset]):
                    x = v[k + 1 + offset]
                else:
                    x = v[k - 1 + offset] + 1
                y = x - k

                while x < n and y < m and a[x] == b[y]:
                    x += 1
                    y += 1

                v[k + offset] = x

                if x >= n and y >= m:
                    found = True
                    break

            if found:
                break

        edits: List[Tuple[str, int, int]] = []
        x = n
        y = m

        for d in range(len(trace) - 1, -1, -1):
            v_prev = trace[d]
            k = x - y

            if k == -d or (k != d and v_prev[k - 1 + offset] < v_prev[k + 1 + offset]):
                k_prev = k + 1
            else:
                k_prev = k - 1

            x_prev = v_prev[k_prev + offset]
            y_prev = x_prev - k_prev

            while x > x_prev and y > y_prev:
                edits.append(("equal", x - 1, y - 1))
                x -= 1
                y -= 1

            if d > 0:
                if x == x_prev:
                    edits.append(("insert", x_prev, y_prev))
                else:
                    edits.append(("delete", x_prev, y_prev))

            x = x_prev
            y = y_prev

        edits.reverse()
        return edits

    def _edits_to_operations(
        self,
        edits: List[Tuple[str, int, int]],
        old_tokens: Sequence[DiffToken],
        new_tokens: Sequence[DiffToken],
    ) -> List[DiffOperation]:
        operations: List[DiffOperation] = []

        if not edits:
            return operations

        i = 0
        while i < len(edits):
            edit_type, old_idx, new_idx = edits[i]

            if edit_type == "equal":
                start_old = old_idx
                start_new = new_idx
                j = i
                while j < len(edits) and edits[j][0] == "equal" and edits[j][1] == start_old + (j - i) and edits[j][2] == start_new + (j - i):
                    j += 1
                end_old = start_old + (j - i)
                end_new = start_new + (j - i)
                operations.append(
                    DiffOperation(
                        op_type=DiffOperationType.EQUAL,
                        old_start=start_old,
                        old_end=end_old,
                        new_start=start_new,
                        new_end=end_new,
                        tokens=list(old_tokens[start_old:end_old]),
                    )
                )
                i = j

            elif edit_type == "delete":
                start_old = old_idx
                j = i
                while j < len(edits) and edits[j][0] == "delete":
                    j += 1
                end_old = start_old + (j - i)
                operations.append(
                    DiffOperation(
                        op_type=DiffOperationType.DELETE,
                        old_start=start_old,
                        old_end=end_old,
                        new_start=new_idx,
                        new_end=new_idx,
                        tokens=list(old_tokens[start_old:end_old]),
                    )
                )
                i = j

            elif edit_type == "insert":
                start_new = new_idx
                j = i
                while j < len(edits) and edits[j][0] == "insert":
                    j += 1
                end_new = start_new + (j - i)
                operations.append(
                    DiffOperation(
                        op_type=DiffOperationType.INSERT,
                        old_start=old_idx,
                        old_end=old_idx,
                        new_start=start_new,
                        new_end=end_new,
                        tokens=list(new_tokens[start_new:end_new]),
                    )
                )
                i = j

        return operations
