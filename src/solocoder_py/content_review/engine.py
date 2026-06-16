from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List, Optional

from .enums import ReviewAction, ReviewStatus
from .exceptions import (
    ContentNotFoundError,
    InvalidStateTransitionError,
    RejectionCommentRequiredError,
)
from .models import ContentItem, RejectionComment, ReviewRecord

_TRANSITIONS: Dict[ReviewStatus, Dict[ReviewAction, ReviewStatus]] = {
    ReviewStatus.DRAFT: {
        ReviewAction.SUBMIT: ReviewStatus.UNDER_REVIEW,
    },
    ReviewStatus.UNDER_REVIEW: {
        ReviewAction.APPROVE: ReviewStatus.APPROVED,
        ReviewAction.REJECT: ReviewStatus.DRAFT,
    },
    ReviewStatus.APPROVED: {
        ReviewAction.PUBLISH: ReviewStatus.PUBLISHED,
    },
    ReviewStatus.PUBLISHED: {
        ReviewAction.WITHDRAW: ReviewStatus.DRAFT,
    },
}


class ContentReviewService:
    def __init__(self) -> None:
        self._contents: Dict[str, ContentItem] = {}

    def create_content(
        self,
        title: str,
        body: str,
        author: str,
        content_id: Optional[str] = None,
    ) -> ContentItem:
        item = ContentItem(
            id=content_id or str(uuid.uuid4()),
            title=title,
            body=body,
            author=author,
            status=ReviewStatus.DRAFT,
        )
        self._contents[item.id] = item
        return item

    def submit_for_review(self, content_id: str) -> ContentItem:
        item = self._get_content(content_id)
        self._validate_transition(item.status, ReviewAction.SUBMIT)
        record = ReviewRecord(
            action=ReviewAction.SUBMIT,
            reviewer=item.author,
        )
        item.review_records.append(record)
        item.status = ReviewStatus.UNDER_REVIEW
        item.updated_at = datetime.now()
        return item

    def approve(self, content_id: str, reviewer: str) -> ContentItem:
        item = self._get_content(content_id)
        self._validate_transition(item.status, ReviewAction.APPROVE)
        record = ReviewRecord(
            action=ReviewAction.APPROVE,
            reviewer=reviewer,
        )
        item.review_records.append(record)
        item.status = ReviewStatus.APPROVED
        item.updated_at = datetime.now()
        return item

    def reject(
        self,
        content_id: str,
        reviewer: str,
        comment: str,
    ) -> ContentItem:
        item = self._get_content(content_id)
        self._validate_transition(item.status, ReviewAction.REJECT)
        if not comment or not comment.strip():
            raise RejectionCommentRequiredError()
        record = ReviewRecord(
            action=ReviewAction.REJECT,
            reviewer=reviewer,
            comment=comment,
        )
        item.review_records.append(record)
        item.status = ReviewStatus.DRAFT
        item.updated_at = datetime.now()
        return item

    def publish(self, content_id: str) -> ContentItem:
        item = self._get_content(content_id)
        self._validate_transition(item.status, ReviewAction.PUBLISH)
        record = ReviewRecord(
            action=ReviewAction.PUBLISH,
            reviewer=item.author,
        )
        item.review_records.append(record)
        item.status = ReviewStatus.PUBLISHED
        item.updated_at = datetime.now()
        return item

    def withdraw(self, content_id: str, reason: Optional[str] = None) -> ContentItem:
        item = self._get_content(content_id)
        self._validate_transition(item.status, ReviewAction.WITHDRAW)
        record = ReviewRecord(
            action=ReviewAction.WITHDRAW,
            reviewer=item.author,
            comment=reason,
        )
        item.review_records.append(record)
        item.status = ReviewStatus.DRAFT
        item.updated_at = datetime.now()
        return item

    def get_content(self, content_id: str) -> Optional[ContentItem]:
        return self._contents.get(content_id)

    def get_rejection_comments(self, content_id: str) -> List[RejectionComment]:
        item = self._get_content(content_id)
        return [
            RejectionComment(
                reviewer=r.reviewer,
                comment=r.comment,
                timestamp=r.timestamp,
            )
            for r in item.review_records
            if r.action == ReviewAction.REJECT
        ]

    def _get_content(self, content_id: str) -> ContentItem:
        item = self._contents.get(content_id)
        if item is None:
            raise ContentNotFoundError(content_id)
        return item

    @staticmethod
    def _validate_transition(
        current_status: ReviewStatus, action: ReviewAction
    ) -> None:
        allowed = _TRANSITIONS.get(current_status, {})
        if action not in allowed:
            raise InvalidStateTransitionError(current_status.value, action.value)
