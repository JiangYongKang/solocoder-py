from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ConversionResult:
    html: str
    warnings: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        return self.html


@dataclass
class CodeBlock:
    language: str
    code: str
    line_number: int = 0


@dataclass
class TableRow:
    cells: List[str]


@dataclass
class TableData:
    header: TableRow
    rows: List[TableRow]
    alignments: Optional[List[str]] = None
