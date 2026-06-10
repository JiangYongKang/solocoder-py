from __future__ import annotations

from typing import Any

from .exceptions import InvalidPathError
from .parser import JSONPathParser, Segment, SegmentType


class JSONPathQuery:
    def __init__(self, data: Any) -> None:
        self._data = data

    def query(self, path: str) -> list[Any]:
        parser = JSONPathParser(path)
        segments = parser.parse()
        if not segments:
            return []

        results: list[Any] = [self._data]
        for segment in segments[1:]:
            results = self._apply_segment(results, segment)
            if not results:
                break

        return results

    def _apply_segment(self, current: list[Any], segment: Segment) -> list[Any]:
        if segment.seg_type == SegmentType.CHILD:
            return self._apply_child(current, segment.field)
        elif segment.seg_type == SegmentType.INDEX:
            return self._apply_index(current, segment.index)
        elif segment.seg_type == SegmentType.WILDCARD:
            return self._apply_wildcard(current)
        elif segment.seg_type == SegmentType.RECURSIVE:
            return self._apply_recursive(current, segment.field)
        else:
            return current

    def _apply_child(self, current: list[Any], field: str | None) -> list[Any]:
        if field is None:
            return []
        results: list[Any] = []
        for item in current:
            if isinstance(item, dict) and field in item:
                results.append(item[field])
        return results

    def _apply_index(self, current: list[Any], index: int | None) -> list[Any]:
        if index is None:
            return []
        results: list[Any] = []
        for item in current:
            if isinstance(item, list):
                if 0 <= index < len(item):
                    results.append(item[index])
                elif index < 0 and abs(index) <= len(item):
                    results.append(item[index])
        return results

    def _apply_wildcard(self, current: list[Any]) -> list[Any]:
        results: list[Any] = []
        for item in current:
            if isinstance(item, dict):
                for key in item:
                    results.append(item[key])
            elif isinstance(item, list):
                results.extend(item)
        return results

    def _apply_recursive(
        self, current: list[Any], field: str | None
    ) -> list[Any]:
        results: list[Any] = []
        for item in current:
            self._collect_recursive(item, field, results)
        return results

    def _collect_recursive(
        self, node: Any, field: str | None, results: list[Any]
    ) -> None:
        if isinstance(node, dict):
            if field is not None and field in node:
                results.append(node[field])
            for key in node:
                self._collect_recursive(node[key], field, results)
        elif isinstance(node, list):
            for element in node:
                self._collect_recursive(element, field, results)


def jsonpath(data: Any, path: str) -> list[Any]:
    return JSONPathQuery(data).query(path)
