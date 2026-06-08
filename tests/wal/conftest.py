from __future__ import annotations

import pytest

from solocoder_py.wal import WriteAheadLog


@pytest.fixture
def wal() -> WriteAheadLog:
    return WriteAheadLog()
