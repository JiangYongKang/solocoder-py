from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from .enums import ReviewAction, ReviewStatus


@dataclass
class ReviewRecord:
    action: ReviewAction
    reviewer: str
    comment: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class RejectionComment:
    reviewer: str
    comment: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ContentItem:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    body: str = ""
    author: str = ""
    status: ReviewStatus = ReviewStatus.DRAFT
    review_records: List[ReviewRecord] = field(default_factory=list)
    rejection_comments: List[RejectionComment] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
