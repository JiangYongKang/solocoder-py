from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CSVRow:
    fields: List[str]
    line_number: int


@dataclass
class ParseResult:
    header: Optional[List[str]]
    rows: List[CSVRow]
    field_mismatch_lines: List[int] = field(default_factory=list)

    @property
    def data(self) -> List[List[str]]:
        return [row.fields for row in self.rows]
