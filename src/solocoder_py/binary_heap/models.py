from __future__ import annotations

from dataclasses import dataclass
from typing import Any, SupportsFloat


@dataclass(order=True)
class HeapEntry:
    priority: SupportsFloat
    element: Any
