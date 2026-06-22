from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class TreeNode:
    value: Any
    left: Optional[TreeNode] = None
    right: Optional[TreeNode] = None
