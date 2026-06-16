from __future__ import annotations

import pytest

from solocoder_py.cursor_pagination import (
    CursorPaginationEngine,
    PaginationConfig,
    SortField,
    SortOrder,
)


@pytest.fixture
def sample_data_10():
    return [{"id": i, "name": f"user_{i}", "score": 100 - i * 3} for i in range(1, 11)]


@pytest.fixture
def sample_data_5():
    return [{"id": i, "name": f"item_{i}", "value": i * 10} for i in range(1, 6)]


@pytest.fixture
def sample_data_large():
    return [
        {"id": i, "name": f"record_{i}", "category": (i % 5) + 1, "rank": i * 2}
        for i in range(1, 101)
    ]


@pytest.fixture
def empty_data():
    return []


@pytest.fixture
def basic_engine(sample_data_10):
    return CursorPaginationEngine(
        data=sample_data_10,
        sort_fields=[SortField("id", SortOrder.ASC)],
    )


@pytest.fixture
def engine_with_score_desc(sample_data_10):
    return CursorPaginationEngine(
        data=sample_data_10,
        sort_fields=[SortField("score", SortOrder.DESC), SortField("id", SortOrder.ASC)],
    )


@pytest.fixture
def engine_with_max_page_size(sample_data_large):
    config = PaginationConfig(max_page_size=10, default_page_size=5)
    return CursorPaginationEngine(
        data=sample_data_large,
        sort_fields=[SortField("id", SortOrder.ASC)],
        config=config,
    )


@pytest.fixture
def engine_with_ttl(sample_data_5):
    config = PaginationConfig(cursor_ttl_seconds=3600, cursor_secret="test-secret")
    return CursorPaginationEngine(
        data=sample_data_5,
        sort_fields=[SortField("id", SortOrder.ASC)],
        config=config,
    )
