from __future__ import annotations

import random
import threading
from typing import Any, Optional

from .exceptions import (
    EmptySkipListError,
    InvalidRangeError,
    InvalidRankError,
    ScoreNotFoundError,
)
from .models import RangeQueryResult, SkipListNode

_DEFAULT_MAX_LEVEL = 32
_DEFAULT_P = 0.5


class SkipList:
    def __init__(self, max_level: int = _DEFAULT_MAX_LEVEL, p: float = _DEFAULT_P) -> None:
        if max_level < 1:
            raise ValueError("max_level must be at least 1")
        if not (0 < p < 1):
            raise ValueError("p must be between 0 and 1")

        self._max_level = max_level
        self._p = p
        self._lock = threading.RLock()
        self._size = 0
        self._insert_counter = 0

        self._header = SkipListNode(
            score=float("-inf"),
            value=None,
            level=max_level,
            forward=[None] * max_level,
            span=[0] * max_level,
        )

    @property
    def size(self) -> int:
        with self._lock:
            return self._size

    @property
    def is_empty(self) -> bool:
        with self._lock:
            return self._size == 0

    def insert(self, score: float, value: Any) -> None:
        with self._lock:
            self._insert_counter += 1
            insert_seq = self._insert_counter
            level = self._random_level()
            update: list[Optional[SkipListNode]] = [None] * self._max_level
            rank: list[int] = [0] * self._max_level

            current = self._header
            for i in range(self._max_level - 1, -1, -1):
                rank[i] = rank[i + 1] if i + 1 < self._max_level else 0
                while current.forward[i] is not None and (
                    current.forward[i].score < score
                    or (
                        current.forward[i].score == score
                        and current.forward[i].insert_seq < insert_seq
                    )
                ):
                    rank[i] += current.span[i]
                    current = current.forward[i]
                update[i] = current

            new_node = SkipListNode(
                score=score,
                value=value,
                level=level,
                forward=[None] * level,
                span=[0] * level,
                insert_seq=insert_seq,
            )

            for i in range(level):
                new_node.forward[i] = update[i].forward[i]
                update[i].forward[i] = new_node

                new_node.span[i] = update[i].span[i] - (rank[0] - rank[i])
                update[i].span[i] = rank[0] - rank[i] + 1

            for i in range(level, self._max_level):
                if update[i] is not None:
                    update[i].span[i] += 1

            self._size += 1

    def delete(self, score: float) -> bool:
        with self._lock:
            if self._size == 0:
                return False

            update: list[Optional[SkipListNode]] = [None] * self._max_level
            current = self._header
            found: Optional[SkipListNode] = None

            for i in range(self._max_level - 1, -1, -1):
                while current.forward[i] is not None and current.forward[i].score < score:
                    current = current.forward[i]
                update[i] = current

            candidate = current.forward[0]
            while candidate is not None and candidate.score == score:
                found = candidate
                break

            if found is None:
                return False

            for i in range(self._max_level):
                if update[i].forward[i] is found:
                    update[i].span[i] += found.span[i] - 1
                    update[i].forward[i] = found.forward[i]
                else:
                    if update[i].span[i] > 0:
                        update[i].span[i] -= 1

            self._size -= 1
            return True

    def range_query(
        self,
        min_score: Optional[float] = None,
        max_score: Optional[float] = None,
        min_inclusive: bool = True,
        max_inclusive: bool = True,
    ) -> list[RangeQueryResult]:
        with self._lock:
            if self._size == 0:
                return []

            if min_score is not None and max_score is not None and min_score > max_score:
                raise InvalidRangeError("min_score cannot be greater than max_score")

            results: list[RangeQueryResult] = []

            current = self._header
            if min_score is not None:
                for i in range(self._max_level - 1, -1, -1):
                    while current.forward[i] is not None and current.forward[i].score < min_score:
                        current = current.forward[i]
                current = current.forward[0]

                if not min_inclusive:
                    while current is not None and current.score <= min_score:
                        current = current.forward[0]
            else:
                current = self._header.forward[0]

            while current is not None:
                if max_score is not None:
                    if max_inclusive:
                        if current.score > max_score:
                            break
                    else:
                        if current.score >= max_score:
                            break

                results.append(RangeQueryResult(score=current.score, value=current.value))
                current = current.forward[0]

            return results

    def get_rank(self, score: float) -> int:
        with self._lock:
            if self._size == 0:
                raise EmptySkipListError("Skip list is empty")

            rank = 0
            current = self._header
            for i in range(self._max_level - 1, -1, -1):
                while current.forward[i] is not None and current.forward[i].score < score:
                    rank += current.span[i]
                    current = current.forward[i]

            found = False
            check = current.forward[0]
            while check is not None and check.score == score:
                found = True
                break

            if not found:
                raise ScoreNotFoundError(f"Score {score} not found in skip list")

            return rank

    def get_by_rank(self, rank: int) -> RangeQueryResult:
        with self._lock:
            if self._size == 0:
                raise EmptySkipListError("Skip list is empty")
            if rank < 1 or rank > self._size:
                raise InvalidRankError(
                    f"Rank must be between 1 and {self._size}, got {rank}"
                )

            traversed = 0
            current = self._header
            for i in range(self._max_level - 1, -1, -1):
                while current.forward[i] is not None and traversed + current.span[i] <= rank:
                    traversed += current.span[i]
                    current = current.forward[i]

            return RangeQueryResult(score=current.score, value=current.value)

    def _random_level(self) -> int:
        level = 1
        while random.random() < self._p and level < self._max_level:
            level += 1
        return level
