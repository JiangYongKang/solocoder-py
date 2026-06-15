from __future__ import annotations

from typing import Any

from .exceptions import InvalidThresholdError
from .models import DedupGroup, FuzzyMatchPair, Record


def levenshtein_distance(s1: str, s2: str) -> int:
    len1 = len(s1)
    len2 = len(s2)
    if len1 == 0:
        return len2
    if len2 == 0:
        return len1

    if len1 < len2:
        s1, s2 = s2, s1
        len1, len2 = len2, len1

    prev_row = list(range(len2 + 1))
    curr_row = [0] * (len2 + 1)

    for i in range(1, len1 + 1):
        curr_row[0] = i
        for j in range(1, len2 + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            curr_row[j] = min(
                curr_row[j - 1] + 1,
                prev_row[j] + 1,
                prev_row[j - 1] + cost,
            )
        prev_row, curr_row = curr_row, prev_row

    return prev_row[len2]


def similarity(s1: str | None, s2: str | None) -> float:
    if s1 is None and s2 is None:
        return 1.0
    if s1 is None or s2 is None:
        return 0.0
    if not isinstance(s1, str):
        s1 = str(s1)
    if not isinstance(s2, str):
        s2 = str(s2)
    if s1 == "" and s2 == "":
        return 1.0
    if s1 == "" or s2 == "":
        return 0.0

    dist = levenshtein_distance(s1, s2)
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 1.0
    return 1.0 - dist / max_len


class UnionFind:
    def __init__(self, size: int) -> None:
        self._parent: list[int] = list(range(size))
        self._rank: list[int] = [0] * size

    def find(self, x: int) -> int:
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x

    def union(self, x: int, y: int) -> bool:
        px = self.find(x)
        py = self.find(y)
        if px == py:
            return False
        if self._rank[px] < self._rank[py]:
            self._parent[px] = py
        elif self._rank[px] > self._rank[py]:
            self._parent[py] = px
        else:
            self._parent[py] = px
            self._rank[px] += 1
        return True

    def get_groups(self) -> dict[int, list[int]]:
        groups: dict[int, list[int]] = {}
        for i in range(len(self._parent)):
            root = self.find(i)
            if root not in groups:
                groups[root] = []
            groups[root].append(i)
        return groups


def fuzzy_match_pairs(
    records: list[Record],
    fields: list[str],
    threshold: float = 0.8,
    field_weights: dict[str, float] | None = None,
) -> list[FuzzyMatchPair]:
    if not fields:
        raise InvalidThresholdError("fields cannot be empty")
    if threshold <= 0 or threshold > 1:
        raise InvalidThresholdError("threshold must be in (0, 1]")

    weights = field_weights or {}
    total_weight = sum(weights.get(f, 1.0) for f in fields)
    norm_weights = {f: weights.get(f, 1.0) / total_weight for f in fields}

    pairs: list[FuzzyMatchPair] = []
    n = len(records)

    for i in range(n):
        for j in range(i + 1, n):
            field_scores: dict[str, float] = {}
            total_score = 0.0
            for field in fields:
                val_i = records[i].get(field)
                val_j = records[j].get(field)
                sim = similarity(val_i, val_j)
                field_scores[field] = sim
                total_score += sim * norm_weights[field]

            if total_score >= threshold:
                pairs.append(
                    FuzzyMatchPair(
                        index_a=i,
                        index_b=j,
                        score=total_score,
                        matched_fields=field_scores,
                    )
                )

    return pairs


def fuzzy_group(
    records: list[Record],
    fields: list[str],
    threshold: float = 0.8,
    field_weights: dict[str, float] | None = None,
) -> list[DedupGroup]:
    pairs = fuzzy_match_pairs(records, fields, threshold, field_weights)
    n = len(records)

    if n == 0:
        return []

    uf = UnionFind(n)
    pair_lookup: dict[tuple[int, int], FuzzyMatchPair] = {}

    for pair in pairs:
        uf.union(pair.index_a, pair.index_b)
        a, b = min(pair.index_a, pair.index_b), max(pair.index_a, pair.index_b)
        pair_lookup[(a, b)] = pair

    raw_groups = uf.get_groups()

    groups: list[DedupGroup] = []
    for root, indices in raw_groups.items():
        indices_sorted = sorted(indices)
        group_records = [records[i] for i in indices_sorted]

        group_pairs: list[FuzzyMatchPair] = []
        for i in range(len(indices_sorted)):
            for j in range(i + 1, len(indices_sorted)):
                a, b = indices_sorted[i], indices_sorted[j]
                key = (min(a, b), max(a, b))
                if key in pair_lookup:
                    group_pairs.append(pair_lookup[key])

        is_singleton = len(indices_sorted) == 1
        avg_score = 1.0
        if group_pairs:
            avg_score = sum(p.score for p in group_pairs) / len(group_pairs)

        groups.append(
            DedupGroup(
                records=group_records,
                indices=indices_sorted,
                is_exact=False,
                match_score=avg_score if not is_singleton else 1.0,
                fuzzy_pairs=group_pairs,
            )
        )

    return groups
