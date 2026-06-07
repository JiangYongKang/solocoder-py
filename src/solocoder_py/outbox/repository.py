from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple

from .exceptions import (
    AtomicWriteError,
    MessageAlreadyClaimedError,
    MessageNotFoundError,
)
from .models import BusinessRecord, OutboxMessage
from .states import OutboxMessageState


@dataclass
class OutboxRepository:
    _business_records: Dict[str, BusinessRecord] = field(default_factory=dict)
    _messages: Dict[str, OutboxMessage] = field(default_factory=dict)
    _messages_by_business: Dict[str, List[str]] = field(default_factory=dict)
    _lock: threading.RLock = field(default_factory=threading.RLock)
    default_max_retries: int = 3
    default_retry_delay_seconds: int = 5

    def __post_init__(self) -> None:
        if self.default_max_retries < 0:
            raise ValueError("default_max_retries cannot be negative")
        if self.default_retry_delay_seconds < 0:
            raise ValueError("default_retry_delay_seconds cannot be negative")

    def create_business_record(
        self,
        business_type: str,
        payload: Dict[str, Any],
        record_id: Optional[str] = None,
    ) -> BusinessRecord:
        with self._lock:
            record = BusinessRecord(
                id=record_id or str(uuid.uuid4()),
                business_type=business_type,
                payload=payload,
            )
            self._business_records[record.id] = record
            self._messages_by_business[record.id] = []
            return record

    def create_message(
        self,
        business_record_id: str,
        message_type: str,
        payload: Dict[str, Any],
        message_id: Optional[str] = None,
        max_retries: Optional[int] = None,
    ) -> OutboxMessage:
        with self._lock:
            if business_record_id not in self._business_records:
                raise ValueError(
                    f"Business record not found: {business_record_id}"
                )
            message = OutboxMessage(
                id=message_id or str(uuid.uuid4()),
                business_record_id=business_record_id,
                message_type=message_type,
                payload=payload,
                max_retries=max_retries if max_retries is not None else self.default_max_retries,
            )
            self._messages[message.id] = message
            self._messages_by_business[business_record_id].append(message.id)
            return message

    def write_with_message(
        self,
        business_type: str,
        message_type: str,
        business_payload: Dict[str, Any],
        message_payload: Dict[str, Any],
        record_id: Optional[str] = None,
        message_id: Optional[str] = None,
        max_retries: Optional[int] = None,
    ) -> Tuple[BusinessRecord, OutboxMessage]:
        """原子写入一条业务记录和一条关联消息。

        原子性边界：仅保证在本方法调用期间，create_business_record 与
        create_message 两步中任意一步抛异常时，已写入的数据会被回滚。
        方法成功返回后，业务记录与消息均已落库（内存结构），此后调用方
        发生崩溃不会触发回滚——这是内存实现的固有局限，生产环境应
        使用带事务的持久化存储（如数据库事务）来获得更强的原子性保证。

        Raises:
            AtomicWriteError: 写入过程中发生异常，已自动回滚。
        """
        with self._lock:
            created_record_id: Optional[str] = None
            created_message_id: Optional[str] = None
            try:
                record = self.create_business_record(
                    business_type=business_type,
                    payload=business_payload,
                    record_id=record_id,
                )
                created_record_id = record.id
                message = self.create_message(
                    business_record_id=record.id,
                    message_type=message_type,
                    payload=message_payload,
                    message_id=message_id,
                    max_retries=max_retries,
                )
                created_message_id = message.id
                return record, message
            except Exception as e:
                self._rollback_write(
                    created_record_id,
                    [created_message_id] if created_message_id else [],
                )
                raise AtomicWriteError(f"Atomic write failed: {e}") from e

    def write_with_messages(
        self,
        business_type: str,
        message_specs: List[Tuple[str, Dict[str, Any]]],
        business_payload: Dict[str, Any],
        record_id: Optional[str] = None,
        message_ids: Optional[List[str]] = None,
        max_retries: Optional[int] = None,
    ) -> Tuple[BusinessRecord, List[OutboxMessage]]:
        """原子写入一条业务记录和多条关联消息。

        原子性边界同 write_with_message：仅在方法调用期间保证回滚。
        成功返回后数据已持久化（内存），调用方后续崩溃不触发回滚。

        Raises:
            AtomicWriteError: 写入过程中发生异常，已自动回滚。
        """
        with self._lock:
            created_record_id: Optional[str] = None
            created_message_ids: List[str] = []
            try:
                record = self.create_business_record(
                    business_type=business_type,
                    payload=business_payload,
                    record_id=record_id,
                )
                created_record_id = record.id

                messages: List[OutboxMessage] = []
                for i, (msg_type, msg_payload) in enumerate(message_specs):
                    mid = message_ids[i] if message_ids and i < len(message_ids) else None
                    msg = self.create_message(
                        business_record_id=record.id,
                        message_type=msg_type,
                        payload=msg_payload,
                        message_id=mid,
                        max_retries=max_retries,
                    )
                    created_message_ids.append(msg.id)
                    messages.append(msg)

                return record, messages
            except Exception as e:
                self._rollback_write(created_record_id, created_message_ids)
                raise AtomicWriteError(f"Atomic write failed: {e}") from e

    def atomic_write_with_callback(
        self,
        callback: Callable[[BusinessRecord], None],
        business_type: str,
        message_type: str,
        business_payload: Dict[str, Any],
        message_payload: Dict[str, Any],
        record_id: Optional[str] = None,
        message_id: Optional[str] = None,
        max_retries: Optional[int] = None,
    ) -> Tuple[BusinessRecord, OutboxMessage]:
        """原子写入并在创建业务记录后、创建消息前执行自定义回调。

        若回调抛出异常，业务记录与后续消息均会回滚。
        原子性边界同 write_with_message：仅方法内部异常触发回滚，
        方法成功返回后调用方崩溃不回滚。

        Raises:
            AtomicWriteError: 写入或回调过程中发生异常，已自动回滚。
        """
        with self._lock:
            created_record_id: Optional[str] = None
            created_message_id: Optional[str] = None
            try:
                record = self.create_business_record(
                    business_type=business_type,
                    payload=business_payload,
                    record_id=record_id,
                )
                created_record_id = record.id

                callback(record)

                message = self.create_message(
                    business_record_id=record.id,
                    message_type=message_type,
                    payload=message_payload,
                    message_id=message_id,
                    max_retries=max_retries,
                )
                created_message_id = message.id

                return record, message
            except Exception as e:
                self._rollback_write(created_record_id, [created_message_id] if created_message_id else [])
                raise AtomicWriteError(f"Atomic write failed: {e}") from e

    def _rollback_last_write(
        self,
        record_id: Optional[str],
        message_id: Optional[str],
    ) -> None:
        self._rollback_write(record_id, [message_id] if message_id else [])

    def _rollback_write(
        self,
        record_id: Optional[str],
        message_ids: List[str],
    ) -> None:
        for mid in message_ids:
            if mid and mid in self._messages:
                msg = self._messages[mid]
                del self._messages[mid]
                if msg.business_record_id in self._messages_by_business:
                    if mid in self._messages_by_business[msg.business_record_id]:
                        self._messages_by_business[msg.business_record_id].remove(mid)
        if record_id and record_id in self._business_records:
            del self._business_records[record_id]
            if record_id in self._messages_by_business:
                del self._messages_by_business[record_id]

    def get_message(self, message_id: str) -> OutboxMessage:
        with self._lock:
            if message_id not in self._messages:
                raise MessageNotFoundError(message_id)
            return self._messages[message_id]

    def get_business_record(self, record_id: str) -> BusinessRecord:
        with self._lock:
            if record_id not in self._business_records:
                raise ValueError(f"Business record not found: {record_id}")
            return self._business_records[record_id]

    def get_messages_by_business(self, record_id: str) -> List[OutboxMessage]:
        with self._lock:
            if record_id not in self._messages_by_business:
                raise ValueError(f"Business record not found: {record_id}")
            return [
                self._messages[mid]
                for mid in self._messages_by_business[record_id]
                if mid in self._messages
            ]

    def claim_message(
        self,
        message_id: str,
        worker_id: str,
    ) -> OutboxMessage:
        with self._lock:
            message = self.get_message(message_id)
            if message.is_delivering:
                if message.claimed_by == worker_id:
                    return message
                raise MessageAlreadyClaimedError(message_id)
            message.mark_delivering(worker_id)
            return message

    def claim_next_messages(
        self,
        worker_id: str,
        batch_size: int = 10,
    ) -> List[OutboxMessage]:
        with self._lock:
            candidates = self._get_scannable_messages()
            claimed: List[OutboxMessage] = []
            for msg in candidates:
                if len(claimed) >= batch_size:
                    break
                if msg.is_delivering and msg.claimed_by != worker_id:
                    continue
                if msg.can_transition_to(OutboxMessageState.DELIVERING):
                    msg.mark_delivering(worker_id)
                    claimed.append(msg)
                elif msg.is_delivering and msg.claimed_by == worker_id:
                    claimed.append(msg)
            return claimed

    def confirm_message(self, message_id: str) -> OutboxMessage:
        with self._lock:
            message = self.get_message(message_id)
            message.mark_confirmed()
            return message

    def fail_message(
        self,
        message_id: str,
        error: str,
        retry_delay_seconds: Optional[int] = None,
    ) -> OutboxMessage:
        with self._lock:
            message = self.get_message(message_id)
            delay = (
                retry_delay_seconds
                if retry_delay_seconds is not None
                else self.default_retry_delay_seconds
            )
            message.mark_failed(error, delay)
            if not message.can_retry:
                message.mark_dead_letter()
            return message

    def force_to_dead_letter(self, message_id: str) -> OutboxMessage:
        with self._lock:
            message = self.get_message(message_id)
            if message.state == OutboxMessageState.DEAD_LETTER:
                return message
            if message.state == OutboxMessageState.CONFIRMED:
                raise ValueError(
                    f"Cannot move confirmed message to dead letter: {message_id}"
                )
            message.claimed_by = None
            message.claimed_at = None
            message.next_retry_at = None
            message.mark_dead_letter()
            return message

    def scan_pending_messages(
        self,
        limit: int = 100,
    ) -> List[OutboxMessage]:
        with self._lock:
            pending = [
                msg for msg in self._messages.values()
                if msg.state == OutboxMessageState.PENDING
            ]
            pending.sort(key=lambda m: m.created_at)
            return pending[:limit]

    def scan_retryable_messages(
        self,
        limit: int = 100,
        now: Optional[datetime] = None,
    ) -> List[OutboxMessage]:
        with self._lock:
            current_time = now or datetime.now()
            retryable = [
                msg for msg in self._messages.values()
                if msg.state == OutboxMessageState.FAILED
                and msg.can_retry
                and (msg.next_retry_at is None or msg.next_retry_at <= current_time)
            ]
            retryable.sort(key=lambda m: m.next_retry_at or m.created_at)
            return retryable[:limit]

    def scan_due_messages(
        self,
        limit: int = 100,
        now: Optional[datetime] = None,
    ) -> List[OutboxMessage]:
        with self._lock:
            pending = self.scan_pending_messages(limit=limit)
            retryable = self.scan_retryable_messages(limit=limit, now=now)
            combined = pending + retryable
            combined.sort(key=lambda m: self._sort_key(m))
            return combined[:limit]

    def get_dead_letters(
        self,
        limit: int = 100,
    ) -> List[OutboxMessage]:
        with self._lock:
            dead = [
                msg for msg in self._messages.values()
                if msg.state == OutboxMessageState.DEAD_LETTER
            ]
            dead.sort(key=lambda m: m.created_at)
            return dead[:limit]

    def count_by_state(self) -> Dict[OutboxMessageState, int]:
        with self._lock:
            counts: Dict[OutboxMessageState, int] = {
                state: 0 for state in OutboxMessageState
            }
            for msg in self._messages.values():
                counts[msg.state] = counts.get(msg.state, 0) + 1
            return counts

    def total_messages(self) -> int:
        with self._lock:
            return len(self._messages)

    def total_business_records(self) -> int:
        with self._lock:
            return len(self._business_records)

    def clear(self) -> None:
        with self._lock:
            self._business_records.clear()
            self._messages.clear()
            self._messages_by_business.clear()

    def _get_scannable_messages(self) -> List[OutboxMessage]:
        now = datetime.now()
        scannable: List[OutboxMessage] = []
        for msg in self._messages.values():
            if msg.state == OutboxMessageState.PENDING:
                scannable.append(msg)
            elif (
                msg.state == OutboxMessageState.FAILED
                and msg.can_retry
                and (msg.next_retry_at is None or msg.next_retry_at <= now)
            ):
                scannable.append(msg)
        scannable.sort(key=lambda m: self._sort_key(m))
        return scannable

    def _sort_key(self, message: OutboxMessage) -> datetime:
        if message.is_failed and message.next_retry_at is not None:
            return message.next_retry_at
        return message.created_at
