from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Mapping, Optional

from .clock import Clock, SystemClock
from .exceptions import (
    DeliveryFailedError,
    MaxRetriesExceededError,
    WebhookTargetNotFoundError,
)
from .models import (
    DeadLetterMessage,
    DeliveryAttempt,
    DeliveryStatus,
    SignedRequest,
    WebhookMessage,
    WebhookTarget,
    generate_delivery_attempt_id,
    generate_message_id,
)
from .repository import WebhookTargetRepository
from .signature import compute_signature


class HttpTransport(ABC):
    @abstractmethod
    def post(
        self,
        url: str,
        headers: Mapping[str, str],
        body: bytes,
    ) -> tuple[int, str]:
        ...


class InMemoryTransport(HttpTransport):
    def __init__(self) -> None:
        self._deliveries: list[tuple[str, dict[str, str], bytes]] = []
        self._should_fail: bool = False
        self._failure_status_code: int = 500
        self._failure_message: str = "Internal Server Error"
        self._custom_handler: Optional[
            callable[[str, Mapping[str, str], bytes], tuple[int, str]]
        ] = None

    def set_should_fail(
        self,
        should_fail: bool,
        status_code: int = 500,
        message: str = "Internal Server Error",
    ) -> None:
        self._should_fail = should_fail
        self._failure_status_code = status_code
        self._failure_message = message

    def set_custom_handler(
        self,
        handler: Optional[
            callable[[str, Mapping[str, str], bytes], tuple[int, str]]
        ],
    ) -> None:
        self._custom_handler = handler

    def post(
        self,
        url: str,
        headers: Mapping[str, str],
        body: bytes,
    ) -> tuple[int, str]:
        self._deliveries.append((url, dict(headers), body))

        if self._custom_handler is not None:
            return self._custom_handler(url, headers, body)

        if self._should_fail:
            return self._failure_status_code, self._failure_message

        return 200, "OK"

    @property
    def deliveries(self) -> list[tuple[str, dict[str, str], bytes]]:
        return list(self._deliveries)

    @property
    def delivery_count(self) -> int:
        return len(self._deliveries)

    def clear_deliveries(self) -> None:
        self._deliveries.clear()


class WebhookDeliveryEngine:
    def __init__(
        self,
        repository: Optional[WebhookTargetRepository] = None,
        transport: Optional[HttpTransport] = None,
        clock: Optional[Clock] = None,
    ) -> None:
        self._repository = repository or WebhookTargetRepository()
        self._transport = transport or InMemoryTransport()
        self._clock = clock or SystemClock()

        self._pending_messages: dict[str, WebhookMessage] = {}
        self._dead_letter_queue: dict[str, DeadLetterMessage] = {}
        self._delivery_attempts: dict[str, list[DeliveryAttempt]] = {}

    @property
    def repository(self) -> WebhookTargetRepository:
        return self._repository

    @property
    def transport(self) -> HttpTransport:
        return self._transport

    @property
    def clock(self) -> Clock:
        return self._clock

    @property
    def pending_count(self) -> int:
        return len(self._pending_messages)

    @property
    def dead_letter_count(self) -> int:
        return len(self._dead_letter_queue)

    def get_dead_letter_messages(self) -> list[DeadLetterMessage]:
        return list(self._dead_letter_queue.values())

    def get_pending_messages(self) -> list[WebhookMessage]:
        return list(self._pending_messages.values())

    def get_message(self, message_id: str) -> Optional[WebhookMessage]:
        return self._pending_messages.get(message_id)

    def get_delivery_history(
        self, message_id: str
    ) -> list[DeliveryAttempt]:
        return list(self._delivery_attempts.get(message_id, []))

    def enqueue(
        self,
        target_id: str,
        event_type: str,
        payload: Mapping[str, Any],
        message_id: Optional[str] = None,
    ) -> WebhookMessage:
        if not self._repository.exists(target_id):
            raise WebhookTargetNotFoundError(
                f"Webhook target not found: {target_id}"
            )

        mid = message_id or generate_message_id()
        now = self._clock.now()

        message = WebhookMessage(
            id=mid,
            target_id=target_id,
            event_type=event_type,
            payload=dict(payload),
            created_at=now,
            delivery_attempts=0,
            last_error=None,
            next_delivery_at=now,
            status=DeliveryStatus.PENDING,
        )
        self._pending_messages[mid] = message
        self._delivery_attempts[mid] = []
        return message

    def build_signed_request(
        self,
        message: WebhookMessage,
        target: WebhookTarget,
    ) -> SignedRequest:
        timestamp = self._clock.now()
        signature = compute_signature(
            payload=message.payload,
            signing_secret=target.signing_secret,
            timestamp=timestamp,
        )
        return SignedRequest(
            target_id=target.id,
            url=target.url,
            payload=message.payload,
            signature=signature,
            timestamp=timestamp,
            event_type=message.event_type,
            message_id=message.id,
        )

    def deliver(self, message_id: str) -> WebhookMessage:
        if message_id not in self._pending_messages:
            raise ValueError(f"Message not found: {message_id}")

        message = self._pending_messages[message_id]
        target = self._repository.get(message.target_id)

        if not target.is_active:
            self._move_to_dead_letter(
                message, "Target is inactive", target
            )
            return message

        signed_request = self.build_signed_request(message, target)
        body = json.dumps(message.payload, sort_keys=True).encode("utf-8")

        message.status = DeliveryStatus.DELIVERING
        attempt_number = message.delivery_attempts + 1

        transport_error: Optional[Exception] = None
        status_code: Optional[int] = None
        response_body: Optional[str] = None

        try:
            status_code, response_body = self._transport.post(
                url=signed_request.url,
                headers=signed_request.headers,
                body=body,
            )
        except Exception as exc:
            transport_error = exc

        if transport_error is not None:
            error_msg = f"Transport error: {str(transport_error)}"
            self._handle_delivery_failure(
                message=message,
                target=target,
                error_msg=error_msg,
                status_code=None,
                attempt_number=attempt_number,
            )
        elif 200 <= status_code < 300:
            self._record_attempt(
                message=message,
                target=target,
                success=True,
                status_code=status_code,
                response_body=response_body,
            )
            message.status = DeliveryStatus.SUCCESS
            message.delivery_attempts = attempt_number
            message.last_error = None
            message.next_delivery_at = None
            del self._pending_messages[message_id]
        else:
            error_msg = f"HTTP {status_code}: {response_body}"
            self._handle_delivery_failure(
                message=message,
                target=target,
                error_msg=error_msg,
                status_code=status_code,
                attempt_number=attempt_number,
            )

        return message

    def _handle_delivery_failure(
        self,
        message: WebhookMessage,
        target: WebhookTarget,
        error_msg: str,
        status_code: Optional[int],
        attempt_number: int,
    ) -> None:
        self._record_attempt(
            message=message,
            target=target,
            success=False,
            status_code=status_code,
            error_message=error_msg,
        )

        message.delivery_attempts = attempt_number
        message.last_error = error_msg

        strategy = target.retry_strategy
        if strategy.should_retry(message.delivery_attempts):
            message.status = DeliveryStatus.FAILED
            delay = strategy.calculate_delay(attempt_number + 1)
            message.next_delivery_at = self._clock.now() + delay
        else:
            self._move_to_dead_letter(message, error_msg, target)

    def _record_attempt(
        self,
        message: WebhookMessage,
        target: WebhookTarget,
        success: bool,
        status_code: Optional[int] = None,
        error_message: Optional[str] = None,
        response_body: Optional[str] = None,
    ) -> None:
        attempt = DeliveryAttempt(
            id=generate_delivery_attempt_id(),
            message_id=message.id,
            target_id=target.id,
            attempted_at=self._clock.now(),
            success=success,
            status_code=status_code,
            error_message=error_message,
            response_body=response_body,
        )
        if message.id not in self._delivery_attempts:
            self._delivery_attempts[message.id] = []
        self._delivery_attempts[message.id].append(attempt)

    def _move_to_dead_letter(
        self,
        message: WebhookMessage,
        last_error: str,
        target: WebhookTarget,
    ) -> None:
        message.status = DeliveryStatus.DEAD_LETTER
        message.next_delivery_at = None

        dlq = DeadLetterMessage(
            message_id=message.id,
            target_id=message.target_id,
            event_type=message.event_type,
            payload=dict(message.payload),
            failure_count=message.delivery_attempts,
            last_error=last_error,
            moved_to_dead_letter_at=self._clock.now(),
            delivery_history=self.get_delivery_history(message.id),
        )
        self._dead_letter_queue[message.id] = dlq

        if message.id in self._pending_messages:
            del self._pending_messages[message.id]

        raise MaxRetriesExceededError(
            retries=message.delivery_attempts,
            message_id=message.id,
        )

    def deliver_all_ready(self) -> int:
        now = self._clock.now()
        ready = [
            mid
            for mid, msg in self._pending_messages.items()
            if msg.next_delivery_at is not None and msg.next_delivery_at <= now
            and msg.status in (DeliveryStatus.PENDING, DeliveryStatus.FAILED)
        ]
        delivered = 0
        for mid in ready:
            try:
                self.deliver(mid)
                delivered += 1
            except MaxRetriesExceededError:
                delivered += 1
        return delivered
