from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional


class DeliveryStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    DROPPED = "dropped"
    TIMEOUT = "timeout"


class BackpressureStrategy(str, Enum):
    DROP_OLDEST = "drop_oldest"
    DROP_NEWEST = "drop_newest"
    BLOCK = "block"


class PubSubError(Exception):
    pass


class TopicNotFoundError(PubSubError):
    pass


class TopicAlreadyExistsError(PubSubError):
    pass


class SubscriberNotFoundError(PubSubError):
    pass


class DuplicateSubscriptionError(PubSubError):
    pass


SubscriberHandler = Callable[["Message"], None]


@dataclass(frozen=True)
class Message:
    id: str
    topic: str
    payload: Any
    publisher_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Message id cannot be empty")
        if not self.topic:
            raise ValueError("Message topic cannot be empty")


@dataclass
class Subscriber:
    id: str
    handler: SubscriberHandler
    name: Optional[str] = None
    buffer_size: int = 100
    backpressure_strategy: BackpressureStrategy = BackpressureStrategy.DROP_OLDEST
    active: bool = True
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Subscriber id cannot be empty")
        if self.buffer_size <= 0:
            raise ValueError("buffer_size must be positive")


@dataclass
class DeliveryRecord:
    message_id: str
    subscriber_id: str
    topic: str
    status: DeliveryStatus
    error_message: Optional[str] = None
    attempted_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


@dataclass
class TopicStats:
    name: str
    subscriber_count: int
    message_published_count: int
    created_at: datetime
