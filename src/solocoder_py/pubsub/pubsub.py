from __future__ import annotations

import logging
import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Deque, Dict, List, Optional, Set

from .models import (
    BackpressureStrategy,
    DeliveryRecord,
    DeliveryStatus,
    DuplicateSubscriptionError,
    Message,
    PubSubError,
    Subscriber,
    SubscriberHandler,
    SubscriberNotFoundError,
    TopicAlreadyExistsError,
    TopicNotFoundError,
    TopicStats,
)

logger = logging.getLogger(__name__)


@dataclass
class _SubscriberRuntime:
    subscriber: Subscriber
    buffer: Deque[Message] = field(default_factory=deque)
    buffer_lock: threading.Lock = field(default_factory=threading.Lock)
    dispatch_thread: Optional[threading.Thread] = None
    dispatch_event: threading.Event = field(default_factory=threading.Event)
    stopped: bool = False
    dropped_count: int = 0
    success_count: int = 0
    failed_count: int = 0


@dataclass
class _TopicRuntime:
    name: str
    created_at: datetime
    subscribers: Dict[str, _SubscriberRuntime] = field(default_factory=dict)
    message_count: int = 0
    lock: threading.RLock = field(default_factory=threading.RLock)


class PubSubBroker:
    def __init__(
        self,
        default_subscriber_buffer_size: int = 100,
        default_backpressure_strategy: BackpressureStrategy = BackpressureStrategy.DROP_OLDEST,
    ) -> None:
        if default_subscriber_buffer_size <= 0:
            raise ValueError("default_subscriber_buffer_size must be positive")

        self._default_buffer_size = default_subscriber_buffer_size
        self._default_strategy = default_backpressure_strategy
        self._topics: Dict[str, _TopicRuntime] = {}
        self._global_lock: threading.RLock = threading.RLock()
        self._delivery_records: List[DeliveryRecord] = []
        self._records_lock: threading.Lock = threading.Lock()

    def create_topic(self, topic_name: str) -> None:
        if not topic_name:
            raise ValueError("topic_name cannot be empty")
        with self._global_lock:
            if topic_name in self._topics:
                raise TopicAlreadyExistsError(f"Topic '{topic_name}' already exists")
            self._topics[topic_name] = _TopicRuntime(
                name=topic_name,
                created_at=datetime.now(),
            )

    def delete_topic(self, topic_name: str) -> None:
        with self._global_lock:
            if topic_name not in self._topics:
                raise TopicNotFoundError(f"Topic '{topic_name}' does not exist")
            topic = self._topics.pop(topic_name)
            for sub_rt in topic.subscribers.values():
                self._stop_subscriber_dispatch(sub_rt)

    def topic_exists(self, topic_name: str) -> bool:
        with self._global_lock:
            return topic_name in self._topics

    def list_topics(self) -> List[str]:
        with self._global_lock:
            return list(self._topics.keys())

    def get_topic_stats(self, topic_name: str) -> TopicStats:
        with self._global_lock:
            if topic_name not in self._topics:
                raise TopicNotFoundError(f"Topic '{topic_name}' does not exist")
            topic = self._topics[topic_name]
            return TopicStats(
                name=topic.name,
                subscriber_count=len(topic.subscribers),
                message_published_count=topic.message_count,
                created_at=topic.created_at,
            )

    def subscribe(
        self,
        topic_name: str,
        handler: SubscriberHandler,
        *,
        subscriber_id: Optional[str] = None,
        subscriber_name: Optional[str] = None,
        buffer_size: Optional[int] = None,
        backpressure_strategy: Optional[BackpressureStrategy] = None,
    ) -> Subscriber:
        if not handler:
            raise ValueError("handler cannot be None")

        sub_id = subscriber_id or str(uuid.uuid4())
        effective_buffer = buffer_size or self._default_buffer_size
        effective_strategy = backpressure_strategy or self._default_strategy

        subscriber = Subscriber(
            id=sub_id,
            handler=handler,
            name=subscriber_name,
            buffer_size=effective_buffer,
            backpressure_strategy=effective_strategy,
        )

        with self._global_lock:
            if topic_name not in self._topics:
                raise TopicNotFoundError(f"Topic '{topic_name}' does not exist")
            topic = self._topics[topic_name]
            with topic.lock:
                if sub_id in topic.subscribers:
                    raise DuplicateSubscriptionError(
                        f"Subscriber '{sub_id}' already subscribed to topic '{topic_name}'"
                    )
                sub_rt = _SubscriberRuntime(subscriber=subscriber)
                topic.subscribers[sub_id] = sub_rt
                self._start_subscriber_dispatch(sub_rt)
                return subscriber

    def unsubscribe(self, topic_name: str, subscriber_id: str) -> None:
        with self._global_lock:
            if topic_name not in self._topics:
                raise TopicNotFoundError(f"Topic '{topic_name}' does not exist")
            topic = self._topics[topic_name]
            with topic.lock:
                if subscriber_id not in topic.subscribers:
                    raise SubscriberNotFoundError(
                        f"Subscriber '{subscriber_id}' not found in topic '{topic_name}'"
                    )
                sub_rt = topic.subscribers.pop(subscriber_id)
                self._stop_subscriber_dispatch(sub_rt)

    def get_subscribers(self, topic_name: str) -> List[Subscriber]:
        with self._global_lock:
            if topic_name not in self._topics:
                raise TopicNotFoundError(f"Topic '{topic_name}' does not exist")
            topic = self._topics[topic_name]
            with topic.lock:
                return [rt.subscriber for rt in topic.subscribers.values()]

    def is_subscribed(self, topic_name: str, subscriber_id: str) -> bool:
        with self._global_lock:
            if topic_name not in self._topics:
                return False
            topic = self._topics[topic_name]
            with topic.lock:
                return subscriber_id in topic.subscribers

    def publish(
        self,
        topic_name: str,
        payload: Any,
        *,
        message_id: Optional[str] = None,
        publisher_id: Optional[str] = None,
    ) -> Message:
        msg_id = message_id or str(uuid.uuid4())
        message = Message(
            id=msg_id,
            topic=topic_name,
            payload=payload,
            publisher_id=publisher_id,
        )

        with self._global_lock:
            if topic_name not in self._topics:
                raise TopicNotFoundError(f"Topic '{topic_name}' does not exist")
            topic = self._topics[topic_name]
            topic.message_count += 1

            with topic.lock:
                subscriber_runtimes = list(topic.subscribers.values())

        for sub_rt in subscriber_runtimes:
            if not sub_rt.subscriber.active:
                self._record_delivery(
                    message_id=message.id,
                    subscriber_id=sub_rt.subscriber.id,
                    topic=topic_name,
                    status=DeliveryStatus.DROPPED,
                    error_message="Subscriber is inactive",
                )
                continue
            self._enqueue_for_subscriber(sub_rt, message, topic_name)

        return message

    def publish_batch(
        self,
        topic_name: str,
        payloads: List[Any],
        *,
        publisher_id: Optional[str] = None,
    ) -> List[Message]:
        messages: List[Message] = []
        for payload in payloads:
            msg = self.publish(topic_name, payload, publisher_id=publisher_id)
            messages.append(msg)
        return messages

    def set_subscriber_active(self, topic_name: str, subscriber_id: str, active: bool) -> None:
        with self._global_lock:
            if topic_name not in self._topics:
                raise TopicNotFoundError(f"Topic '{topic_name}' does not exist")
            topic = self._topics[topic_name]
            with topic.lock:
                if subscriber_id not in topic.subscribers:
                    raise SubscriberNotFoundError(
                        f"Subscriber '{subscriber_id}' not found in topic '{topic_name}'"
                    )
                topic.subscribers[subscriber_id].subscriber.active = active

    def get_delivery_records(
        self,
        *,
        topic_name: Optional[str] = None,
        subscriber_id: Optional[str] = None,
        message_id: Optional[str] = None,
    ) -> List[DeliveryRecord]:
        with self._records_lock:
            records = list(self._delivery_records)

        if topic_name is not None:
            records = [r for r in records if r.topic == topic_name]
        if subscriber_id is not None:
            records = [r for r in records if r.subscriber_id == subscriber_id]
        if message_id is not None:
            records = [r for r in records if r.message_id == message_id]

        return records

    def get_subscriber_buffer_size(self, topic_name: str, subscriber_id: str) -> int:
        with self._global_lock:
            if topic_name not in self._topics:
                raise TopicNotFoundError(f"Topic '{topic_name}' does not exist")
            topic = self._topics[topic_name]
            with topic.lock:
                if subscriber_id not in topic.subscribers:
                    raise SubscriberNotFoundError(
                        f"Subscriber '{subscriber_id}' not found in topic '{topic_name}'"
                    )
                sub_rt = topic.subscribers[subscriber_id]
                with sub_rt.buffer_lock:
                    return len(sub_rt.buffer)

    def clear(self) -> None:
        with self._global_lock:
            for topic in self._topics.values():
                for sub_rt in topic.subscribers.values():
                    self._stop_subscriber_dispatch(sub_rt)
            self._topics.clear()
        with self._records_lock:
            self._delivery_records.clear()

    def _start_subscriber_dispatch(self, sub_rt: _SubscriberRuntime) -> None:
        if sub_rt.dispatch_thread is not None and sub_rt.dispatch_thread.is_alive():
            return
        sub_rt.stopped = False
        sub_rt.dispatch_event.clear()
        thread = threading.Thread(
            target=self._dispatch_loop,
            args=(sub_rt,),
            daemon=True,
            name=f"pubsub-dispatch-{sub_rt.subscriber.id[:8]}",
        )
        sub_rt.dispatch_thread = thread
        thread.start()

    def _stop_subscriber_dispatch(self, sub_rt: _SubscriberRuntime) -> None:
        sub_rt.stopped = True
        sub_rt.dispatch_event.set()
        if sub_rt.dispatch_thread is not None:
            sub_rt.dispatch_thread.join(timeout=1.0)
            sub_rt.dispatch_thread = None

    def _dispatch_loop(self, sub_rt: _SubscriberRuntime) -> None:
        while not sub_rt.stopped:
            message: Optional[Message] = None
            with sub_rt.buffer_lock:
                if sub_rt.buffer:
                    message = sub_rt.buffer.popleft()

            if message is None:
                sub_rt.dispatch_event.wait(timeout=0.01)
                sub_rt.dispatch_event.clear()
                continue

            self._deliver_message(sub_rt, message)

    def _deliver_message(self, sub_rt: _SubscriberRuntime, message: Message) -> None:
        subscriber = sub_rt.subscriber
        try:
            subscriber.handler(message)
            sub_rt.success_count += 1
            self._record_delivery(
                message_id=message.id,
                subscriber_id=subscriber.id,
                topic=message.topic,
                status=DeliveryStatus.SUCCESS,
            )
        except Exception as e:
            sub_rt.failed_count += 1
            logger.exception(
                "Subscriber %s failed to handle message %s",
                subscriber.id,
                message.id,
            )
            self._record_delivery(
                message_id=message.id,
                subscriber_id=subscriber.id,
                topic=message.topic,
                status=DeliveryStatus.FAILED,
                error_message=str(e),
            )

    def _enqueue_for_subscriber(
        self,
        sub_rt: _SubscriberRuntime,
        message: Message,
        topic_name: str,
    ) -> None:
        subscriber = sub_rt.subscriber
        with sub_rt.buffer_lock:
            if len(sub_rt.buffer) >= subscriber.buffer_size:
                strategy = subscriber.backpressure_strategy
                if strategy == BackpressureStrategy.DROP_OLDEST:
                    sub_rt.buffer.popleft()
                    sub_rt.dropped_count += 1
                    self._record_delivery(
                        message_id=message.id,
                        subscriber_id=subscriber.id,
                        topic=topic_name,
                        status=DeliveryStatus.DROPPED,
                        error_message="Buffer full: dropped oldest message",
                    )
                elif strategy == BackpressureStrategy.DROP_NEWEST:
                    sub_rt.dropped_count += 1
                    self._record_delivery(
                        message_id=message.id,
                        subscriber_id=subscriber.id,
                        topic=topic_name,
                        status=DeliveryStatus.DROPPED,
                        error_message="Buffer full: dropped newest message",
                    )
                    return
                elif strategy == BackpressureStrategy.BLOCK:
                    pass
                else:
                    sub_rt.dropped_count += 1
                    self._record_delivery(
                        message_id=message.id,
                        subscriber_id=subscriber.id,
                        topic=topic_name,
                        status=DeliveryStatus.DROPPED,
                        error_message=f"Unknown strategy: {strategy}",
                    )
                    return

            sub_rt.buffer.append(message)
            sub_rt.dispatch_event.set()

    def _record_delivery(
        self,
        *,
        message_id: str,
        subscriber_id: str,
        topic: str,
        status: DeliveryStatus,
        error_message: Optional[str] = None,
    ) -> None:
        record = DeliveryRecord(
            message_id=message_id,
            subscriber_id=subscriber_id,
            topic=topic,
            status=status,
            error_message=error_message,
        )
        if status != DeliveryStatus.PENDING:
            record.completed_at = datetime.now()
        with self._records_lock:
            self._delivery_records.append(record)
