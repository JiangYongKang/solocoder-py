from __future__ import annotations

import json

import pytest

from solocoder_py.webhook_delivery import (
    DeliveryNotReadyError,
    DeliveryStatus,
    InMemoryTransport,
    ManualClock,
    MaxRetriesExceededError,
    RetryStrategy,
    WebhookDeliveryEngine,
    WebhookTargetNotFoundError,
    WebhookTargetRepository,
    compute_signature,
)


@pytest.fixture
def setup():
    clock = ManualClock(start_time=1000.0)
    transport = InMemoryTransport()
    repository = WebhookTargetRepository()
    engine = WebhookDeliveryEngine(
        repository=repository,
        transport=transport,
        clock=clock,
    )
    target = repository.register(
        url="https://example.com/webhook",
        signing_secret="my-secret-key",
        retry_strategy=RetryStrategy(
            initial_delay=1.0,
            backoff_multiplier=2.0,
            max_delay=10.0,
            max_retries=3,
        ),
    )
    return clock, transport, repository, engine, target


class TestEnqueue:
    def test_enqueue_basic(self, setup):
        _, _, _, engine, target = setup
        msg = engine.enqueue(
            target_id=target.id,
            event_type="order.created",
            payload={"order_id": "123", "amount": 99.99},
        )
        assert msg.id.startswith("msg_")
        assert msg.target_id == target.id
        assert msg.event_type == "order.created"
        assert msg.payload == {"order_id": "123", "amount": 99.99}
        assert msg.status == DeliveryStatus.PENDING
        assert msg.delivery_attempts == 0
        assert engine.pending_count == 1

    def test_enqueue_with_custom_message_id(self, setup):
        _, _, _, engine, target = setup
        msg = engine.enqueue(
            target_id=target.id,
            event_type="x",
            payload={},
            message_id="msg_custom",
        )
        assert msg.id == "msg_custom"
        assert engine.get_message("msg_custom") is not None

    def test_enqueue_nonexistent_target_raises(self, setup):
        _, _, _, engine, _ = setup
        with pytest.raises(WebhookTargetNotFoundError):
            engine.enqueue(
                target_id="tgt_nonexistent",
                event_type="x",
                payload={},
            )


class TestSuccessfulDelivery:
    def test_first_attempt_success(self, setup):
        clock, transport, _, engine, target = setup

        msg = engine.enqueue(target.id, "order.created", {"id": "1"})
        result = engine.deliver(msg.id)

        assert result.status == DeliveryStatus.SUCCESS
        assert result.delivery_attempts == 1
        assert result.last_error is None
        assert result.next_delivery_at is None

        assert engine.pending_count == 0
        assert transport.delivery_count == 1

        delivery = transport.deliveries[0]
        assert delivery[0] == "https://example.com/webhook"
        headers = delivery[1]
        assert "X-Webhook-Signature" in headers
        assert headers["X-Webhook-Event-Type"] == "order.created"
        assert headers["X-Webhook-Message-Id"] == msg.id
        assert headers["Content-Type"] == "application/json"

        body = json.loads(delivery[2])
        assert body == {"id": "1"}

    def test_signature_on_delivery_is_valid(self, setup):
        _, transport, _, engine, target = setup

        msg = engine.enqueue(target.id, "evt", {"a": 1, "b": 2})
        engine.deliver(msg.id)

        delivery = transport.deliveries[0]
        headers = delivery[1]
        timestamp = float(headers["X-Webhook-Timestamp"])
        signature = headers["X-Webhook-Signature"]
        expected = compute_signature(
            payload={"a": 1, "b": 2},
            signing_secret=target.signing_secret,
            timestamp=timestamp,
        )
        assert signature == expected

    def test_delivery_attempt_recorded(self, setup):
        _, _, _, engine, target = setup

        msg = engine.enqueue(target.id, "evt", {})
        engine.deliver(msg.id)

        history = engine.get_delivery_history(msg.id)
        assert len(history) == 1
        assert history[0].success is True
        assert history[0].status_code == 200
        assert history[0].error_message is None

    def test_deliver_nonexistent_message_raises(self, setup):
        _, _, _, engine, _ = setup
        with pytest.raises(ValueError):
            engine.deliver("msg_nope")


class TestFailedDeliveryAndRetry:
    def test_single_failure_then_success(self, setup):
        clock, transport, _, engine, target = setup

        call_count = [0]

        def handler(url, headers, body):
            call_count[0] += 1
            if call_count[0] < 2:
                return 500, "Internal Error"
            return 200, "OK"

        transport.set_custom_handler(handler)

        msg = engine.enqueue(target.id, "evt", {"x": 1})

        result1 = engine.deliver(msg.id)
        assert result1.status == DeliveryStatus.FAILED
        assert result1.delivery_attempts == 1
        assert result1.last_error is not None
        assert result1.next_delivery_at is not None
        assert result1.next_delivery_at == clock.now() + 1.0
        assert engine.pending_count == 1

        clock.advance(1.0)
        result2 = engine.deliver(msg.id)
        assert result2.status == DeliveryStatus.SUCCESS
        assert result2.delivery_attempts == 2
        assert engine.pending_count == 0

        history = engine.get_delivery_history(msg.id)
        assert len(history) == 2
        assert history[0].success is False
        assert history[0].status_code == 500
        assert history[1].success is True
        assert history[1].status_code == 200

    def test_exponential_backoff_delays(self, setup):
        clock, transport, _, engine, target = setup
        transport.set_should_fail(True, 500, "Fail")

        msg = engine.enqueue(target.id, "evt", {})

        engine.deliver(msg.id)
        msg = engine.get_message(msg.id)
        assert msg.next_delivery_at == clock.now() + 1.0

        clock.advance(1.0)
        engine.deliver(msg.id)
        msg = engine.get_message(msg.id)
        assert msg.next_delivery_at == clock.now() + 2.0

        clock.advance(2.0)
        engine.deliver(msg.id)
        msg = engine.get_message(msg.id)
        assert msg.next_delivery_at == clock.now() + 4.0

    def test_max_delay_capping(self, setup):
        clock, transport, repository, engine = setup[:4]
        target = repository.register(
            url="https://capped.com",
            signing_secret="s",
            retry_strategy=RetryStrategy(
                initial_delay=1.0,
                backoff_multiplier=2.0,
                max_delay=3.0,
                max_retries=10,
            ),
        )
        transport.set_should_fail(True, 500, "Fail")

        msg = engine.enqueue(target.id, "evt", {})

        delays = []
        for _ in range(6):
            engine.deliver(msg.id)
            m = engine.get_message(msg.id)
            if m.next_delivery_at is not None:
                delays.append(m.next_delivery_at - clock.now())
                clock.advance(m.next_delivery_at - clock.now())

        assert delays[0] == pytest.approx(1.0)
        assert delays[1] == pytest.approx(2.0)
        assert delays[2] == pytest.approx(3.0)
        assert delays[3] == pytest.approx(3.0)
        assert delays[4] == pytest.approx(3.0)
        assert delays[5] == pytest.approx(3.0)

    def test_transport_exception_handled(self, setup):
        _, transport, _, engine, target = setup

        def raising_handler(url, headers, body):
            raise ConnectionError("Network unreachable")

        transport.set_custom_handler(raising_handler)

        msg = engine.enqueue(target.id, "evt", {})
        result = engine.deliver(msg.id)

        assert result.status == DeliveryStatus.FAILED
        assert result.delivery_attempts == 1
        assert "Transport error" in result.last_error
        assert "Network unreachable" in result.last_error

        history = engine.get_delivery_history(msg.id)
        assert len(history) == 1
        assert history[0].success is False
        assert history[0].status_code is None


class TestDeadLetterQueue:
    def test_exceeds_max_retries_moves_to_dlq(self, setup):
        clock, transport, _, engine, target = setup
        transport.set_should_fail(True, 500, "Server Error")

        msg = engine.enqueue(target.id, "evt", {"data": 1})

        with pytest.raises(MaxRetriesExceededError) as exc_info:
            for _ in range(10):
                engine.deliver(msg.id)
                m = engine.get_message(msg.id)
                if m is not None and m.next_delivery_at is not None:
                    clock.set(m.next_delivery_at)

        assert exc_info.value.message_id == msg.id
        assert exc_info.value.retries == 4

        assert engine.pending_count == 0
        assert engine.dead_letter_count == 1

        dlq = engine.get_dead_letter_messages()
        assert len(dlq) == 1
        assert dlq[0].message_id == msg.id
        assert dlq[0].target_id == target.id
        assert dlq[0].event_type == "evt"
        assert dlq[0].payload == {"data": 1}
        assert dlq[0].failure_count == 4
        assert "Server Error" in dlq[0].last_error
        assert len(dlq[0].delivery_history) == 4
        assert all(not a.success for a in dlq[0].delivery_history)

    def test_zero_max_retries_moves_to_dlq_immediately(self, setup):
        _, transport, repository, engine = setup[:4]
        target = repository.register(
            url="https://zero.com",
            signing_secret="s",
            retry_strategy=RetryStrategy(max_retries=0),
        )
        transport.set_should_fail(True, 500, "Fail")

        msg = engine.enqueue(target.id, "evt", {})

        with pytest.raises(MaxRetriesExceededError) as exc_info:
            engine.deliver(msg.id)

        assert exc_info.value.retries == 1
        assert engine.dead_letter_count == 1
        assert engine.get_dead_letter_messages()[0].failure_count == 1

    def test_max_retries_one_allows_single_retry(self, setup):
        clock, transport, repository, engine = setup[:4]
        target = repository.register(
            url="https://one.com",
            signing_secret="s",
            retry_strategy=RetryStrategy(
                initial_delay=1.0,
                backoff_multiplier=2.0,
                max_delay=10.0,
                max_retries=1,
            ),
        )
        transport.set_should_fail(True, 500, "Fail")

        msg = engine.enqueue(target.id, "evt", {})

        engine.deliver(msg.id)
        m = engine.get_message(msg.id)
        assert m.status == DeliveryStatus.FAILED
        assert m.delivery_attempts == 1

        clock.advance(1.0)
        with pytest.raises(MaxRetriesExceededError):
            engine.deliver(msg.id)

        assert engine.dead_letter_count == 1

    def test_inactive_target_moves_to_dlq(self, setup):
        _, _, repository, engine, target = setup
        repository.update(target.id, is_active=False)

        msg = engine.enqueue(target.id, "evt", {})
        with pytest.raises(MaxRetriesExceededError):
            engine.deliver(msg.id)

        assert engine.dead_letter_count == 1
        dlq = engine.get_dead_letter_messages()[0]
        assert "inactive" in dlq.last_error.lower()


class TestDeliverAllReady:
    def test_deliver_all_ready_multiple_messages(self, setup):
        clock, transport, _, engine, target = setup

        for i in range(3):
            engine.enqueue(target.id, f"evt_{i}", {"i": i})

        assert engine.pending_count == 3
        delivered = engine.deliver_all_ready()
        assert delivered == 3
        assert engine.pending_count == 0

    def test_deliver_all_ready_skips_future_messages(self, setup):
        clock, transport, _, engine, target = setup
        transport.set_should_fail(True, 500, "Fail")

        msg = engine.enqueue(target.id, "evt", {})
        engine.deliver(msg.id)
        assert engine.pending_count == 1

        delivered = engine.deliver_all_ready()
        assert delivered == 0

        clock.advance(1.0)
        delivered = engine.deliver_all_ready()
        assert delivered == 1

    def test_deliver_all_ready_mixed_success_and_dlq(self, setup):
        _, transport, repository, engine = setup[:4]
        target_zero = repository.register(
            url="https://z.com",
            signing_secret="s",
            retry_strategy=RetryStrategy(max_retries=0),
        )

        def handler(url, headers, body):
            if "z.com" in url:
                return 500, "Fail"
            return 200, "OK"

        transport.set_custom_handler(handler)

        engine.enqueue(setup[4].id, "ok", {})
        engine.enqueue(target_zero.id, "fail", {})

        delivered = engine.deliver_all_ready()
        assert delivered == 2
        assert engine.pending_count == 0
        assert engine.dead_letter_count == 1


class TestSignedRequest:
    def test_build_signed_request(self, setup):
        clock, _, _, engine, target = setup
        clock.set(5000.0)

        msg = engine.enqueue(target.id, "order.created", {"id": "123"})
        signed = engine.build_signed_request(msg, target)

        assert signed.target_id == target.id
        assert signed.url == target.url
        assert signed.payload == {"id": "123"}
        assert signed.timestamp == 5000.0
        assert signed.event_type == "order.created"
        assert signed.message_id == msg.id

        expected_sig = compute_signature(
            payload={"id": "123"},
            signing_secret=target.signing_secret,
            timestamp=5000.0,
        )
        assert signed.signature == expected_sig

        headers = signed.headers
        assert headers["X-Webhook-Signature"] == expected_sig
        assert headers["X-Webhook-Timestamp"] == "5000.0"
        assert headers["X-Webhook-Event-Type"] == "order.created"
        assert headers["X-Webhook-Message-Id"] == msg.id
        assert headers["Content-Type"] == "application/json"


class TestInMemoryTransport:
    def test_default_deliveries_success(self):
        transport = InMemoryTransport()
        status, body = transport.post(
            "https://example.com", {"H": "v"}, b"data"
        )
        assert status == 200
        assert body == "OK"
        assert transport.delivery_count == 1

    def test_set_should_fail(self):
        transport = InMemoryTransport()
        transport.set_should_fail(True, status_code=503, message="Unavailable")
        status, body = transport.post(
            "https://example.com", {}, b""
        )
        assert status == 503
        assert body == "Unavailable"

    def test_custom_handler(self):
        transport = InMemoryTransport()

        def my_handler(url, headers, body):
            return 201, "Created"

        transport.set_custom_handler(my_handler)
        status, body = transport.post("", {}, b"")
        assert status == 201
        assert body == "Created"

    def test_clear_deliveries(self):
        transport = InMemoryTransport()
        transport.post("", {}, b"")
        assert transport.delivery_count == 1
        transport.clear_deliveries()
        assert transport.delivery_count == 0

    def test_deliveries_snapshot(self):
        transport = InMemoryTransport()
        transport.post("url1", {}, b"a")
        deliveries = transport.deliveries
        transport.post("url2", {}, b"b")
        assert len(deliveries) == 1
        assert transport.delivery_count == 2


class TestDeliveryTimeGating:
    def test_pending_message_can_be_delivered_immediately(self, setup):
        _, _, _, engine, target = setup
        msg = engine.enqueue(target.id, "evt", {})
        result = engine.deliver(msg.id)
        assert result.status == DeliveryStatus.SUCCESS

    def test_deliver_before_retry_window_raises_not_ready(self, setup):
        clock, transport, _, engine, target = setup
        transport.set_should_fail(True, 500, "Fail")

        msg = engine.enqueue(target.id, "evt", {})
        engine.deliver(msg.id)

        with pytest.raises(DeliveryNotReadyError) as exc_info:
            engine.deliver(msg.id)

        assert exc_info.value.message_id == msg.id
        assert exc_info.value.next_delivery_at > exc_info.value.current_time

    def test_deliver_exactly_at_retry_window_succeeds(self, setup):
        clock, transport, _, engine, target = setup
        transport.set_should_fail(True, 500, "Fail")

        msg = engine.enqueue(target.id, "evt", {})
        engine.deliver(msg.id)

        m = engine.get_message(msg.id)
        retry_at = m.next_delivery_at

        clock.set(retry_at)

        m2 = engine.deliver(msg.id)
        assert m2.status == DeliveryStatus.FAILED
        assert m2.delivery_attempts == 2

    def test_deliver_after_retry_window_succeeds(self, setup):
        clock, transport, _, engine, target = setup
        transport.set_should_fail(True, 500, "Fail")

        msg = engine.enqueue(target.id, "evt", {})
        engine.deliver(msg.id)

        m = engine.get_message(msg.id)
        clock.advance(m.next_delivery_at - clock.now() + 100.0)

        m2 = engine.deliver(msg.id)
        assert m2.status == DeliveryStatus.FAILED
        assert m2.delivery_attempts == 2

    def test_not_ready_error_contains_wait_time(self, setup):
        clock, transport, _, engine, target = setup
        transport.set_should_fail(True, 500, "Fail")

        msg = engine.enqueue(target.id, "evt", {})
        engine.deliver(msg.id)

        with pytest.raises(DeliveryNotReadyError) as exc_info:
            engine.deliver(msg.id)

        assert "not ready" in str(exc_info.value).lower()
        assert "next delivery available" in str(exc_info.value).lower()

    def test_multiple_failures_enforce_each_retry_window(self, setup):
        clock, transport, _, engine, target = setup
        transport.set_should_fail(True, 500, "Fail")

        msg = engine.enqueue(target.id, "evt", {})

        for i in range(3):
            engine.deliver(msg.id)
            with pytest.raises(DeliveryNotReadyError):
                engine.deliver(msg.id)
            m = engine.get_message(msg.id)
            clock.set(m.next_delivery_at)

        with pytest.raises(MaxRetriesExceededError):
            engine.deliver(msg.id)

        assert engine.dead_letter_count == 1


class TestMaxRetriesBoundary:
    def test_max_retries_zero_single_attempt_then_dlq(self, setup):
        _, transport, repository, engine = setup[:4]
        target = repository.register(
            url="https://zero.com",
            signing_secret="s",
            retry_strategy=RetryStrategy(max_retries=0),
        )
        transport.set_should_fail(True, 500, "Fail")

        msg = engine.enqueue(target.id, "evt", {})
        with pytest.raises(MaxRetriesExceededError) as exc_info:
            engine.deliver(msg.id)

        assert exc_info.value.retries == 1
        assert engine.dead_letter_count == 1
        dlq = engine.get_dead_letter_messages()[0]
        assert dlq.failure_count == 1
        assert len(dlq.delivery_history) == 1

    def test_max_retries_one_two_attempts_then_dlq(self, setup):
        clock, transport, repository, engine = setup[:4]
        target = repository.register(
            url="https://one.com",
            signing_secret="s",
            retry_strategy=RetryStrategy(
                initial_delay=1.0,
                backoff_multiplier=2.0,
                max_delay=10.0,
                max_retries=1,
            ),
        )
        transport.set_should_fail(True, 500, "Fail")

        msg = engine.enqueue(target.id, "evt", {})

        engine.deliver(msg.id)
        m = engine.get_message(msg.id)
        assert m.delivery_attempts == 1
        assert m.status == DeliveryStatus.FAILED

        clock.advance(1.0)
        with pytest.raises(MaxRetriesExceededError) as exc_info:
            engine.deliver(msg.id)

        assert exc_info.value.retries == 2
        assert engine.dead_letter_count == 1
        dlq = engine.get_dead_letter_messages()[0]
        assert dlq.failure_count == 2
        assert len(dlq.delivery_history) == 2

    def test_max_retries_three_four_attempts_then_dlq(self, setup):
        clock, transport, _, engine, target = setup
        transport.set_should_fail(True, 500, "Fail")

        msg = engine.enqueue(target.id, "evt", {})

        engine.deliver(msg.id)
        assert engine.get_message(msg.id).delivery_attempts == 1
        clock.advance(1.0)

        engine.deliver(msg.id)
        assert engine.get_message(msg.id).delivery_attempts == 2
        clock.advance(2.0)

        engine.deliver(msg.id)
        assert engine.get_message(msg.id).delivery_attempts == 3
        clock.advance(4.0)

        with pytest.raises(MaxRetriesExceededError) as exc_info:
            engine.deliver(msg.id)

        assert exc_info.value.retries == 4
        assert engine.dead_letter_count == 1
        dlq = engine.get_dead_letter_messages()[0]
        assert dlq.failure_count == 4
        assert len(dlq.delivery_history) == 4

    def test_max_retries_boundary_final_attempt_succeeds_no_dlq(self, setup):
        clock, transport, repository, engine = setup[:4]
        target = repository.register(
            url="https://boundary.com",
            signing_secret="s",
            retry_strategy=RetryStrategy(
                initial_delay=1.0,
                backoff_multiplier=2.0,
                max_delay=10.0,
                max_retries=2,
            ),
        )

        call_count = [0]

        def handler(url, headers, body):
            call_count[0] += 1
            if call_count[0] < 3:
                return 500, "Fail"
            return 200, "OK"

        transport.set_custom_handler(handler)

        msg = engine.enqueue(target.id, "evt", {})

        engine.deliver(msg.id)
        clock.advance(1.0)

        engine.deliver(msg.id)
        clock.advance(2.0)

        result = engine.deliver(msg.id)

        assert result.status == DeliveryStatus.SUCCESS
        assert result.delivery_attempts == 3
        assert engine.dead_letter_count == 0
        assert engine.pending_count == 0

    def test_max_retries_zero_succeeds_on_first_attempt(self, setup):
        _, transport, repository, engine = setup[:4]
        target = repository.register(
            url="https://zero-ok.com",
            signing_secret="s",
            retry_strategy=RetryStrategy(max_retries=0),
        )

        msg = engine.enqueue(target.id, "evt", {})
        result = engine.deliver(msg.id)

        assert result.status == DeliveryStatus.SUCCESS
        assert result.delivery_attempts == 1
        assert engine.dead_letter_count == 0
