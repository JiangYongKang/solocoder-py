from __future__ import annotations

from enum import Enum
from typing import TypeVar, Generic, Optional, Tuple, List


T = TypeVar("T")


class WriteMode(str, Enum):
    OVERWRITE = "overwrite"
    NO_OVERWRITE = "no_overwrite"


class RingBufferError(Exception):
    pass


class InvalidCapacityError(RingBufferError):
    pass


class TimeoutError(RingBufferError):
    pass
