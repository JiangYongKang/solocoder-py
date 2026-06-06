from __future__ import annotations

import heapq
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from .models import (
    DuplicateMessageError,
    Message,
    MessageNotFoundError,
    MessageStatus,
    QueueError,
)


@dataclass(order=True)
class _QueueEntry:
    sort_key: Tuple[int, float] = field(compare=True)
    message_id: str = field(compare=False)


@dataclass
class _DedupRecord:
    enqueued_at: datetime
    window: timedelta


class MessageQueue:
    def __init__(
        self,
        default_visibility_timeout: timedelta = timedelta(seconds=30),
        default_max_retry_count: int = 3,
        default_dedup_window: timedelta = timedelta(minutes=5),
    ) -> None:
        self._default_visibility_timeout = default_visibility_timeout
        self._default_max_retry_count = default_max_retry_count
        self._default_dedup_window = default_dedup_window

        self._messages: Dict[str, Dict[str, Message]] = {}
        self._queues: Dict[str, List[_QueueEntry]] = {}
        self._dead_letter_queues: Dict[str, List[str]] = {}
        self._dedup_records: Dict[str, Dict[str, _DedupRecord]] = {}
        self._in_flight: Dict[str, Set[str]] = {}
        self._counter: int = 0

    def _get_or_create_message_map(self, queue_name: str) -> Dict[str, Message]:
        if queue_name not in self._messages:
            self._messages[queue_name] = {}
        return self._messages[queue_name]

    def _get_or_create_queue(self, queue_name: str) -> List[_QueueEntry]:
        if queue_name not in self._queues:
            self._queues[queue_name] = []
        return self._queues[queue_name]

    def _get_or_create_dead_letter_queue(self, queue_name: str) -> List[str]:
        dlq_name = f"{queue_name}-dlq"
        if dlq_name not in self._dead_letter_queues:
            self._dead_letter_queues[dlq_name] = []
        return self._dead_letter_queues[dlq_name]

    def _get_or_create_dedup_map(self, queue_name: str) -> Dict[str, _DedupRecord]:
        if queue_name not in self._dedup_records:
            self._dedup_records[queue_name] = {}
        return self._dedup_records[queue_name]

    def _get_or_create_in_flight(self, queue_name: str) -> Set[str]:
        if queue_name not in self._in_flight:
            self._in_flight[queue_name] = set()
        return self._in_flight[queue_name]

    def _cleanup_expired_dedup(self, queue_name: str) -> None:
        dedup_map = self._get_or_create_dedup_map(queue_name)
        now = datetime.now()
        expired_ids = [
            msg_id for msg_id, rec in dedup_map.items()
            if now >= rec.enqueued_at + rec.window
        ]
        for msg_id in expired_ids:
            del dedup_map[msg_id]

    def _is_duplicate(self, queue_name: str, message_id: str) -> bool:
        self._cleanup_expired_dedup(queue_name)
        dedup_map = self._get_or_create_dedup_map(queue_name)
        return message_id in dedup_map

    def _record_dedup(self, queue_name: str, message_id: str, window: timedelta) -> None:
        dedup_map = self._get_or_create_dedup_map(queue_name)
        dedup_map[message_id] = _DedupRecord(
            enqueued_at=datetime.now(),
            window=window,
        )

    def _requeue_message(self, message: Message) -> None:
        heap = self._get_or_create_queue(message.queue_name)
        self._counter += 1
        entry = _QueueEntry(
            sort_key=(-message.priority, self._counter),
            message_id=message.id,
        )
        heapq.heappush(heap, entry)

    def _find_message(self, message_id: str) -> Optional[Message]:
        for queue_name, msg_map in self._messages.items():
            if message_id in msg_map:
                return msg_map[message_id]
        return None

    def _add_to_in_flight(self, message: Message) -> None:
        in_flight = self._get_or_create_in_flight(message.queue_name)
        in_flight.add(message.id)

    def _remove_from_in_flight(self, message: Message) -> None:
        if message.queue_name in self._in_flight:
            self._in_flight[message.queue_name].discard(message.id)

    def _process_expired_in_flight(self, queue_name: str) -> None:
        if queue_name not in self._in_flight:
            return
        msg_map = self._get_or_create_message_map(queue_name)
        in_flight = self._in_flight[queue_name]
        expired_ids: List[str] = []

        for msg_id in in_flight:
            if msg_id not in msg_map:
                expired_ids.append(msg_id)
                continue
            message = msg_map[msg_id]
            if message.is_visible:
                if message.is_dead:
                    message.mark_dead_letter()
                    dlq = self._get_or_create_dead_letter_queue(queue_name)
                    if message.id not in dlq:
                        dlq.append(message.id)
                else:
                    message.make_visible()
                    self._requeue_message(message)
                expired_ids.append(msg_id)

        for msg_id in expired_ids:
            in_flight.discard(msg_id)

    def _cleanup_stale_message(self, queue_name: str, msg_id: str) -> None:
        msg_map = self._get_or_create_message_map(queue_name)
        if msg_id in msg_map:
            self._remove_from_in_flight(msg_map[msg_id])
            del msg_map[msg_id]

        dlq_name = f"{queue_name}-dlq"
        if dlq_name in self._dead_letter_queues and msg_id in self._dead_letter_queues[dlq_name]:
            self._dead_letter_queues[dlq_name].remove(msg_id)

    def enqueue(
        self,
        queue_name: str,
        body: Any,
        *,
        message_id: Optional[str] = None,
        priority: int = 0,
        deliver_at: Optional[datetime] = None,
        visibility_timeout: Optional[timedelta] = None,
        max_retry_count: Optional[int] = None,
        dedup_window: Optional[timedelta] = None,
    ) -> Message:
        msg_id = message_id or str(uuid.uuid4())

        effective_window = dedup_window or self._default_dedup_window
        if self._is_duplicate(queue_name, msg_id):
            raise DuplicateMessageError(
                f"Message with id '{msg_id}' is still within dedup window for queue '{queue_name}'"
            )

        self._cleanup_stale_message(queue_name, msg_id)

        message = Message(
            id=msg_id,
            body=body,
            queue_name=queue_name,
            priority=priority,
            deliver_at=deliver_at,
            visibility_timeout=visibility_timeout or self._default_visibility_timeout,
            max_retry_count=max_retry_count if max_retry_count is not None else self._default_max_retry_count,
        )

        msg_map = self._get_or_create_message_map(queue_name)
        msg_map[msg_id] = message
        self._requeue_message(message)
        self._record_dedup(queue_name, msg_id, effective_window)

        return message

    def _check_dead_letter(self, message: Message) -> bool:
        if message.is_dead and message.status != MessageStatus.DEAD_LETTER:
            message.mark_dead_letter()
            dlq = self._get_or_create_dead_letter_queue(message.queue_name)
            if message.id not in dlq:
                dlq.append(message.id)
            self._remove_from_in_flight(message)
            return True
        return False

    def dequeue(
        self,
        queue_name: str,
        *,
        visibility_timeout: Optional[timedelta] = None,
    ) -> Optional[Message]:
        self._process_expired_in_flight(queue_name)

        if queue_name not in self._queues:
            return None

        heap = self._queues[queue_name]
        msg_map = self._get_or_create_message_map(queue_name)
        candidates: List[_QueueEntry] = []

        while heap:
            entry = heapq.heappop(heap)
            msg_id = entry.message_id

            if msg_id not in msg_map:
                continue

            message = msg_map[msg_id]

            if message.status == MessageStatus.DEAD_LETTER:
                continue

            if message.status == MessageStatus.IN_FLIGHT:
                candidates.append(entry)
                continue

            if self._check_dead_letter(message):
                continue

            if message.is_delayed:
                candidates.append(entry)
                continue

            if not message.is_visible:
                candidates.append(entry)
                continue

            for candidate in candidates:
                heapq.heappush(heap, candidate)

            message.mark_received(visibility_timeout)
            self._add_to_in_flight(message)

            if self._check_dead_letter(message):
                return None

            return message

        for candidate in candidates:
            heapq.heappush(heap, candidate)

        return None

    def acknowledge(self, message_id: str) -> None:
        message = self._find_message(message_id)
        if message is None:
            raise MessageNotFoundError(f"Message not found: {message_id}")

        self._remove_from_in_flight(message)

        queue_name = message.queue_name
        msg_map = self._get_or_create_message_map(queue_name)
        if message_id in msg_map:
            del msg_map[message_id]

        dlq_name = f"{queue_name}-dlq"
        if dlq_name in self._dead_letter_queues and message_id in self._dead_letter_queues[dlq_name]:
            self._dead_letter_queues[dlq_name].remove(message_id)

    def retry(self, message_id: str) -> None:
        message = self._find_message(message_id)
        if message is None:
            raise MessageNotFoundError(f"Message not found: {message_id}")

        if message.status != MessageStatus.IN_FLIGHT:
            raise QueueError(f"Message is not in-flight, cannot retry: {message.status}")

        self._remove_from_in_flight(message)
        message.make_visible()
        self._requeue_message(message)

    def peek_dead_letters(self, queue_name: str) -> List[Message]:
        dlq_name = f"{queue_name}-dlq"
        if dlq_name not in self._dead_letter_queues:
            return []

        msg_map = self._get_or_create_message_map(queue_name)
        result = []
        for msg_id in self._dead_letter_queues[dlq_name]:
            if msg_id in msg_map:
                result.append(msg_map[msg_id])
        return result

    def get_queue_size(self, queue_name: str) -> int:
        self._process_expired_in_flight(queue_name)

        if queue_name not in self._messages:
            return 0
        msg_map = self._messages[queue_name]
        count = 0
        for message in msg_map.values():
            if message.status != MessageStatus.PENDING:
                continue
            if message.is_delayed:
                continue
            if not message.is_visible:
                continue
            count += 1
        return count

    def get_dead_letter_count(self, queue_name: str) -> int:
        return len(self.peek_dead_letters(queue_name))

    def clear(self) -> None:
        self._messages.clear()
        self._queues.clear()
        self._dead_letter_queues.clear()
        self._dedup_records.clear()
        self._in_flight.clear()
        self._counter = 0
