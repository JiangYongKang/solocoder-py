from __future__ import annotations

import uuid
from typing import List, Optional

from .models import CancelTokenInfo


class CancelToken:
    def __init__(
        self,
        token_id: Optional[str] = None,
        parent: Optional["CancelToken"] = None,
        initially_cancelled: bool = False,
    ) -> None:
        self._token_id = token_id or str(uuid.uuid4())
        self._parent = parent
        self._children: List["CancelToken"] = []
        self._is_cancelled = initially_cancelled
        if parent is not None:
            parent._children.append(self)

    @property
    def token_id(self) -> str:
        return self._token_id

    @property
    def parent(self) -> Optional["CancelToken"]:
        return self._parent

    @property
    def is_cancelled(self) -> bool:
        return self._is_cancelled

    @property
    def is_active(self) -> bool:
        return not self._is_cancelled

    @property
    def children(self) -> List["CancelToken"]:
        return list(self._children)

    @property
    def children_count(self) -> int:
        return len(self._children)

    def create_child(self, token_id: Optional[str] = None) -> "CancelToken":
        return CancelToken(
            token_id=token_id,
            parent=self,
            initially_cancelled=self._is_cancelled,
        )

    def cancel(self) -> None:
        if self._is_cancelled:
            return
        self._is_cancelled = True
        for child in self._children:
            child.cancel()

    def to_info(self) -> CancelTokenInfo:
        return CancelTokenInfo(
            token_id=self._token_id,
            is_cancelled=self._is_cancelled,
            is_active=self.is_active,
            parent_id=self._parent.token_id if self._parent else None,
            children_count=len(self._children),
        )
