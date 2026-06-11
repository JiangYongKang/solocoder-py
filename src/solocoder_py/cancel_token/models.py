from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class CancelTokenInfo:
    token_id: str
    is_cancelled: bool
    is_active: bool
    parent_id: Optional[str] = None
    children_count: int = 0
