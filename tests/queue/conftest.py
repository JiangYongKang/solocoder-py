from datetime import timedelta

import pytest

from solocoder_py.queue import MessageQueue


@pytest.fixture
def queue() -> MessageQueue:
    return MessageQueue(
        default_visibility_timeout=timedelta(seconds=5),
        default_max_retry_count=3,
        default_dedup_window=timedelta(minutes=5),
    )
