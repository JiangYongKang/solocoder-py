from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Entry:
    key: Any
    value: Any
