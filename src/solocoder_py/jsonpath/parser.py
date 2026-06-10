from __future__ import annotations

from enum import Enum
from typing import Union

from .exceptions import InvalidPathError, UnexpectedTokenError


class SegmentType(Enum):
    ROOT = "root"
    CHILD = "child"
    INDEX = "index"
    WILDCARD = "wildcard"
    RECURSIVE = "recursive"


class Segment:
    def __init__(
        self,
        seg_type: SegmentType,
        field: str | None = None,
        index: int | None = None,
    ) -> None:
        self.seg_type = seg_type
        self.field = field
        self.index = index

    def __repr__(self) -> str:
        parts = [f"SegmentType.{self.seg_type.name}"]
        if self.field is not None:
            parts.append(f"field={self.field!r}")
        if self.index is not None:
            parts.append(f"index={self.index}")
        return f"Segment({', '.join(parts)})"


class JSONPathParser:
    def __init__(self, path: str) -> None:
        self._path = path
        self._pos = 0
        self._length = len(path)

    def parse(self) -> list[Segment]:
        if not self._path or not self._path.strip():
            raise InvalidPathError("Path cannot be empty")

        segments: list[Segment] = []
        self._skip_whitespace()

        if self._pos < self._length and self._path[self._pos] == "$":
            segments.append(Segment(seg_type=SegmentType.ROOT))
            self._pos += 1
        else:
            segments.append(Segment(seg_type=SegmentType.ROOT))

        while self._pos < self._length:
            self._skip_whitespace()
            if self._pos >= self._length:
                break

            ch = self._path[self._pos]

            if ch == ".":
                self._pos += 1
                if self._pos < self._length and self._path[self._pos] == ".":
                    self._pos += 1
                    self._skip_whitespace()
                    field = self._read_field_name()
                    if field is None:
                        raise InvalidPathError(
                            f"Expected field name after '..' at position {self._pos}"
                        )
                    segments.append(
                        Segment(seg_type=SegmentType.RECURSIVE, field=field)
                    )
                else:
                    self._skip_whitespace()
                    if self._pos < self._length and self._path[self._pos] == "*":
                        self._pos += 1
                        segments.append(Segment(seg_type=SegmentType.WILDCARD))
                    else:
                        field = self._read_field_name()
                        if field is None:
                            raise InvalidPathError(
                                f"Expected field name after '.' at position {self._pos}"
                            )
                        segments.append(
                            Segment(seg_type=SegmentType.CHILD, field=field)
                        )
            elif ch == "[":
                self._pos += 1
                self._skip_whitespace()
                if self._pos < self._length and self._path[self._pos] == "*":
                    self._pos += 1
                    self._skip_whitespace()
                    self._expect("]")
                    segments.append(Segment(seg_type=SegmentType.WILDCARD))
                elif self._pos < self._length and self._path[self._pos] == "'":
                    field = self._read_quoted_field()
                    self._skip_whitespace()
                    self._expect("]")
                    segments.append(
                        Segment(seg_type=SegmentType.CHILD, field=field)
                    )
                elif self._pos < self._length and self._path[self._pos] == '"':
                    field = self._read_double_quoted_field()
                    self._skip_whitespace()
                    self._expect("]")
                    segments.append(
                        Segment(seg_type=SegmentType.CHILD, field=field)
                    )
                else:
                    index = self._read_index()
                    self._skip_whitespace()
                    self._expect("]")
                    segments.append(
                        Segment(seg_type=SegmentType.INDEX, index=index)
                    )
            else:
                raise InvalidPathError(
                    f"Unexpected character '{ch}' at position {self._pos}. "
                    f"Expected '.' or '[' to start a new path segment."
                )

        return segments

    def _skip_whitespace(self) -> None:
        while self._pos < self._length and self._path[self._pos] in " \t":
            self._pos += 1

    def _expect(self, ch: str) -> None:
        if self._pos >= self._length or self._path[self._pos] != ch:
            actual = self._path[self._pos] if self._pos < self._length else "EOF"
            raise UnexpectedTokenError(
                f"Expected '{ch}' but got '{actual}' at position {self._pos}"
            )
        self._pos += 1

    def _read_field_name(self) -> str | None:
        self._skip_whitespace()
        start = self._pos
        while self._pos < self._length:
            ch = self._path[self._pos]
            if ch.isalnum() or ch == "_":
                self._pos += 1
            else:
                break
        if self._pos == start:
            return None
        return self._path[start : self._pos]

    def _read_quoted_field(self) -> str:
        self._expect("'")
        chars: list[str] = []
        while self._pos < self._length:
            ch = self._path[self._pos]
            if ch == "'":
                self._pos += 1
                return "".join(chars)
            elif ch == "\\" and self._pos + 1 < self._length:
                self._pos += 1
                chars.append(self._path[self._pos])
                self._pos += 1
            else:
                chars.append(ch)
                self._pos += 1
        raise InvalidPathError("Unclosed single quote in field name")

    def _read_double_quoted_field(self) -> str:
        self._expect('"')
        chars: list[str] = []
        while self._pos < self._length:
            ch = self._path[self._pos]
            if ch == '"':
                self._pos += 1
                return "".join(chars)
            elif ch == "\\" and self._pos + 1 < self._length:
                self._pos += 1
                chars.append(self._path[self._pos])
                self._pos += 1
            else:
                chars.append(ch)
                self._pos += 1
        raise InvalidPathError("Unclosed double quote in field name")

    def _read_index(self) -> int:
        start = self._pos
        if self._pos < self._length and self._path[self._pos] == "-":
            self._pos += 1
        while self._pos < self._length and self._path[self._pos].isdigit():
            self._pos += 1
        if self._pos == start:
            raise InvalidPathError(
                f"Expected index inside brackets at position {self._pos}"
            )
        text = self._path[start : self._pos]
        try:
            return int(text)
        except ValueError:
            raise InvalidPathError(f"Invalid index '{text}' at position {start}")
