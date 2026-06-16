from __future__ import annotations


class ContentReviewError(Exception):
    pass


class InvalidStateTransitionError(ContentReviewError):
    def __init__(self, current: str, action: str) -> None:
        self.current = current
        self.action = action
        super().__init__(
            f"Cannot perform '{action}' on content in state '{current}'"
        )


class RejectionCommentRequiredError(ContentReviewError):
    def __init__(self) -> None:
        super().__init__("Rejection comment is required when rejecting content")


class ContentNotFoundError(ContentReviewError):
    def __init__(self, content_id: str) -> None:
        self.content_id = content_id
        super().__init__(f"Content not found: {content_id}")


class InvalidOperationError(ContentReviewError):
    pass
