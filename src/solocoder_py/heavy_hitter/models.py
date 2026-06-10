from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class HeavyHitter:
    item: Any
    count: int

    def __lt__(self, other: "HeavyHitter") -> bool:
        return self.count < other.count

    def __le__(self, other: "HeavyHitter") -> bool:
        return self.count <= other.count

    def __gt__(self, other: "HeavyHitter") -> bool:
        return self.count > other.count

    def __ge__(self, other: "HeavyHitter") -> bool:
        return self.count >= other.count
