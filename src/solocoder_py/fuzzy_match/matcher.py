from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MatchResult:
    candidate: str
    distance: int


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


def levenshtein_distance_bounded(s1: str, s2: str, threshold: int) -> int:
    len1 = len(s1)
    len2 = len(s2)
    if abs(len1 - len2) > threshold:
        return threshold + 1

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
        row_min = curr_row[0]
        start = max(1, i - threshold)
        end = min(len2, i + threshold)

        if start > 1:
            curr_row[start - 1] = threshold + 1

        for j in range(start, end + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            curr_row[j] = min(
                curr_row[j - 1] + 1,
                prev_row[j] + 1,
                prev_row[j - 1] + cost,
            )
            if curr_row[j] < row_min:
                row_min = curr_row[j]

        if end < len2:
            curr_row[end + 1] = threshold + 1

        if row_min > threshold:
            return threshold + 1

        prev_row, curr_row = curr_row, prev_row

    result = prev_row[len2]
    return result if result <= threshold else threshold + 1


class FuzzyMatcher:
    def __init__(self, candidates: list[str] | None = None) -> None:
        self._candidates: list[str] = []
        self._length_index: dict[int, list[str]] = {}
        if candidates:
            for c in candidates:
                self._add_internal(c)

    def add_candidate(self, candidate: str) -> None:
        self._add_internal(candidate)

    def remove_candidate(self, candidate: str) -> bool:
        if candidate not in self._candidates:
            return False
        self._candidates.remove(candidate)
        length = len(candidate)
        if length in self._length_index:
            bucket = self._length_index[length]
            if candidate in bucket:
                bucket.remove(candidate)
            if not bucket:
                del self._length_index[length]
        return True

    def match(
        self,
        query: str,
        threshold: int = 0,
        max_results: int | None = None,
    ) -> list[MatchResult]:
        if threshold < 0:
            raise ValueError("threshold must be non-negative")
        if max_results is not None and max_results < 0:
            raise ValueError("max_results must be non-negative")

        pruned = self._prune_by_length(query, threshold)

        results: list[MatchResult] = []
        for candidate in pruned:
            dist = levenshtein_distance_bounded(query, candidate, threshold)
            if dist <= threshold:
                results.append(MatchResult(candidate=candidate, distance=dist))

        results.sort(key=lambda r: (r.distance, r.candidate))

        if max_results is not None:
            results = results[:max_results]

        return results

    @property
    def candidates(self) -> list[str]:
        return list(self._candidates)

    @property
    def candidate_count(self) -> int:
        return len(self._candidates)

    def _add_internal(self, candidate: str) -> None:
        self._candidates.append(candidate)
        length = len(candidate)
        if length not in self._length_index:
            self._length_index[length] = []
        self._length_index[length].append(candidate)

    def _prune_by_length(self, query: str, threshold: int) -> list[str]:
        query_len = len(query)
        min_len = max(0, query_len - threshold)
        max_len = query_len + threshold

        range_size = max_len - min_len + 1
        bucket_count = len(self._length_index)

        result: list[str] = []

        if range_size <= bucket_count:
            for length in range(min_len, max_len + 1):
                bucket = self._length_index.get(length)
                if bucket is not None:
                    result.extend(bucket)
        else:
            for length, bucket in self._length_index.items():
                if min_len <= length <= max_len:
                    result.extend(bucket)

        return result
