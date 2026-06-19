from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(order=True)
class HuffmanNode:
    frequency: int = field(compare=True)
    symbol: Optional[Any] = field(default=None, compare=False)
    left: Optional["HuffmanNode"] = field(default=None, compare=False)
    right: Optional["HuffmanNode"] = field(default=None, compare=False)
    order: int = field(default=0, compare=True)

    @property
    def is_leaf(self) -> bool:
        return self.symbol is not None and self.left is None and self.right is None


@dataclass
class CodeInfo:
    symbol: Any
    code_length: int
    frequency: int
    code: str = ""


@dataclass
class FrequencyTable:
    frequencies: dict[Any, int]

    def items(self):
        return self.frequencies.items()

    def __getitem__(self, symbol: Any) -> int:
        return self.frequencies[symbol]

    def __contains__(self, symbol: Any) -> bool:
        return symbol in self.frequencies

    def __len__(self) -> int:
        return len(self.frequencies)

    def symbols(self) -> list[Any]:
        return list(self.frequencies.keys())

    def total(self) -> int:
        return sum(self.frequencies.values())


@dataclass
class CodeLengthTable:
    lengths: dict[Any, int]

    def __getitem__(self, symbol: Any) -> int:
        return self.lengths[symbol]

    def __contains__(self, symbol: Any) -> bool:
        return symbol in self.lengths

    def __len__(self) -> int:
        return len(self.lengths)

    def items(self):
        return self.lengths.items()

    def symbols(self) -> list[Any]:
        return list(self.lengths.keys())

    def max_length(self) -> int:
        return max(self.lengths.values()) if self.lengths else 0

    def min_length(self) -> int:
        return min(self.lengths.values()) if self.lengths else 0


@dataclass
class CodeTable:
    codes: dict[Any, CodeInfo]

    def __getitem__(self, symbol: Any) -> CodeInfo:
        return self.codes[symbol]

    def __contains__(self, symbol: Any) -> bool:
        return symbol in self.codes

    def __len__(self) -> int:
        return len(self.codes)

    def items(self):
        return self.codes.items()

    def symbols(self) -> list[Any]:
        return list(self.codes.keys())

    def get_code(self, symbol: Any) -> str:
        return self.codes[symbol].code

    def get_code_length(self, symbol: Any) -> int:
        return self.codes[symbol].code_length

    def max_length(self) -> int:
        return max((info.code_length for info in self.codes.values()), default=0)

    def min_length(self) -> int:
        return min((info.code_length for info in self.codes.values()), default=0)


@dataclass
class EncodedData:
    bit_string: str
    code_table: CodeTable
    original_length: int
