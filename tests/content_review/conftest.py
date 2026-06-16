from __future__ import annotations

import pytest

from solocoder_py.content_review import ContentReviewService


@pytest.fixture
def service() -> ContentReviewService:
    return ContentReviewService()


@pytest.fixture
def draft_content(service: ContentReviewService) -> str:
    item = service.create_content(
        title="Test Article",
        body="Hello world",
        author="author-1",
    )
    return item.id
