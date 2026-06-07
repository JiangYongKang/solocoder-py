from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta
from typing import Dict

import pytest

from solocoder_py.outbox import (
    AtomicWriteError,
    BusinessRecord,
    InvalidStateTransitionError,
    MessageAlreadyClaimedError,
    MessageNotFoundError,
    OutboxMessage,
    OutboxMessageState,
    OutboxRepository,
    OutboxStateMachine,
)
from .conftest import make_repository


class TestBusinessRecordModel:
    def test_business_record_creation(self):
        record = BusinessRecord(
            id="rec-1",
            business_type="order_created",
            payload={"order_id": "ORD-001", "amount": 100},
        )
        assert record.id == "rec-1"
        assert record.business_type == "order_created"
        assert record.payload == {"order_id": "ORD-001", "amount": 100}
        assert isinstance(record.created_at, datetime)

    def test_business_record_empty_id_rejected(self):
        with pytest.raises(ValueError, match="id cannot be empty"):
            BusinessRecord(id="", business_type="test", payload={})

    def test_business_record_empty_type_rejected(self):
        with pytest.raises(ValueError, match="business_type cannot be empty"):
            BusinessRecord(id="rec-1", business_type="", payload={})


class TestOutboxMessageModel:
    def test_message_creation_default_state(self):
        msg = OutboxMessage(
            id="msg-1",
            business_record_id="rec-1",
            message_type="order_notification",
            payload={"order_id": "ORD-001"},
        )
        assert msg.id == "msg-1"
        assert msg.business_record_id == "rec-1"
        assert msg.message_type == "order_notification"
        assert msg.state == OutboxMessageState.PENDING
        assert msg.retry_count == 0
        assert msg.max_retries == 3
        assert msg.last_error is None
        assert msg.is_pending is True
        assert msg.can_retry is True

    def test_message_empty_id_rejected(self):
        with pytest.raises(ValueError, match="id cannot be empty"):
            OutboxMessage(id="", business_record_id="rec-1", message_type="test", payload={})

    def test_message_empty_business_record_id_rejected(self):
        with pytest.raises(ValueError, match="business_record_id cannot be empty"):
            OutboxMessage(id="msg-1", business_record_id="", message_type="test", payload={})

    def test_message_empty_type_rejected(self):
        with pytest.raises(ValueError, match="message_type cannot be empty"):
            OutboxMessage(id="msg-1", business_record_id="rec-1", message_type="", payload={})

    def test_message_negative_max_retries_rejected(self):
        with pytest.raises(ValueError, match="max_retries cannot be negative"):
            OutboxMessage(
                id="msg-1",
                business_record_id="rec-1",
                message_type="test",
                payload={},
                max_retries=-1,
            )

    def test_message_negative_retry_count_rejected(self):
        with pytest.raises(ValueError, match="retry_count cannot be negative"):
            OutboxMessage(
                id="msg-1",
                business_record_id="rec-1",
                message_type="test",
                payload={},
                retry_count=-1,
            )

    def test_message_mark_delivering(self):
        msg = OutboxMessage(
            id="msg-1",
            business_record_id="rec-1",
            message_type="test",
            payload={},
        )
        msg.mark_delivering("worker-1")
        assert msg.state == OutboxMessageState.DELIVERING
        assert msg.claimed_by == "worker-1"
        assert msg.claimed_at is not None
        assert msg.is_delivering is True

    def test_message_mark_confirmed(self):
        msg = OutboxMessage(
            id="msg-1",
            business_record_id="rec-1",
            message_type="test",
            payload={},
        )
        msg.mark_delivering("worker-1")
        msg.mark_confirmed()
        assert msg.state == OutboxMessageState.CONFIRMED
        assert msg.claimed_by is None
        assert msg.claimed_at is None
        assert msg.is_confirmed is True

    def test_message_mark_failed(self):
        msg = OutboxMessage(
            id="msg-1",
            business_record_id="rec-1",
            message_type="test",
            payload={},
        )
        msg.mark_delivering("worker-1")
        before = datetime.now()
        msg.mark_failed("connection timeout", retry_delay_seconds=10)
        assert msg.state == OutboxMessageState.FAILED
        assert msg.retry_count == 1
        assert msg.last_error == "connection timeout"
        assert msg.claimed_by is None
        assert msg.is_failed is True
        assert msg.next_retry_at is not None
        assert msg.next_retry_at >= before + timedelta(seconds=10)

    def test_message_mark_dead_letter(self):
        msg = OutboxMessage(
            id="msg-1",
            business_record_id="rec-1",
            message_type="test",
            payload={},
            retry_count=3,
            max_retries=3,
        )
        msg.mark_delivering("worker-1")
        msg.mark_failed("timeout", retry_delay_seconds=0)
        assert msg.state == OutboxMessageState.FAILED
        assert msg.can_retry is False
        msg.mark_dead_letter()
        assert msg.state == OutboxMessageState.DEAD_LETTER
        assert msg.is_dead_letter is True
        assert msg.next_retry_at is None

    def test_message_can_retry_boundary(self):
        msg = OutboxMessage(
            id="msg-1",
            business_record_id="rec-1",
            message_type="test",
            payload={},
            max_retries=2,
        )
        assert msg.can_retry is True
        msg.mark_delivering("w")
        msg.mark_failed("e1")
        assert msg.retry_count == 1
        assert msg.can_retry is True
        msg.mark_delivering("w")
        msg.mark_failed("e2")
        assert msg.retry_count == 2
        assert msg.can_retry is False

    def test_message_release_claim(self):
        msg = OutboxMessage(
            id="msg-1",
            business_record_id="rec-1",
            message_type="test",
            payload={},
        )
        msg.mark_delivering("worker-1")
        assert msg.claimed_by == "worker-1"
        msg.release_claim()
        assert msg.claimed_by is None
        assert msg.claimed_at is None


class TestOutboxStateMachine:
    def test_state_machine_initial_state(self):
        sm = OutboxStateMachine()
        assert sm.state == OutboxMessageState.PENDING

    def test_state_machine_pending_to_delivering(self):
        sm = OutboxStateMachine(OutboxMessageState.PENDING)
        assert sm.can_transition_to(OutboxMessageState.DELIVERING) is True
        sm.transition_to(OutboxMessageState.DELIVERING)
        assert sm.state == OutboxMessageState.DELIVERING

    def test_state_machine_delivering_to_confirmed(self):
        sm = OutboxStateMachine(OutboxMessageState.DELIVERING)
        assert sm.can_transition_to(OutboxMessageState.CONFIRMED) is True
        sm.transition_to(OutboxMessageState.CONFIRMED)
        assert sm.state == OutboxMessageState.CONFIRMED

    def test_state_machine_delivering_to_failed(self):
        sm = OutboxStateMachine(OutboxMessageState.DELIVERING)
        assert sm.can_transition_to(OutboxMessageState.FAILED) is True
        sm.transition_to(OutboxMessageState.FAILED)
        assert sm.state == OutboxMessageState.FAILED

    def test_state_machine_failed_to_delivering_retry(self):
        sm = OutboxStateMachine(OutboxMessageState.FAILED)
        assert sm.can_transition_to(OutboxMessageState.DELIVERING) is True
        sm.transition_to(OutboxMessageState.DELIVERING)
        assert sm.state == OutboxMessageState.DELIVERING

    def test_state_machine_failed_to_dead_letter(self):
        sm = OutboxStateMachine(OutboxMessageState.FAILED)
        assert sm.can_transition_to(OutboxMessageState.DEAD_LETTER) is True
        sm.transition_to(OutboxMessageState.DEAD_LETTER)
        assert sm.state == OutboxMessageState.DEAD_LETTER

    def test_state_machine_invalid_transition_pending_to_confirmed(self):
        sm = OutboxStateMachine(OutboxMessageState.PENDING)
        assert sm.can_transition_to(OutboxMessageState.CONFIRMED) is False
        with pytest.raises(InvalidStateTransitionError):
            sm.transition_to(OutboxMessageState.CONFIRMED)

    def test_state_machine_invalid_transition_confirmed_to_anything(self):
        sm = OutboxStateMachine(OutboxMessageState.CONFIRMED)
        for target in OutboxMessageState:
            if target != OutboxMessageState.CONFIRMED:
                assert sm.can_transition_to(target) is False
                with pytest.raises(InvalidStateTransitionError):
                    sm.transition_to(target)

    def test_state_machine_invalid_transition_dead_letter_to_anything(self):
        sm = OutboxStateMachine(OutboxMessageState.DEAD_LETTER)
        for target in OutboxMessageState:
            if target != OutboxMessageState.DEAD_LETTER:
                assert sm.can_transition_to(target) is False
                with pytest.raises(InvalidStateTransitionError):
                    sm.transition_to(target)

    def test_state_machine_invalid_transition_pending_to_failed(self):
        sm = OutboxStateMachine(OutboxMessageState.PENDING)
        assert sm.can_transition_to(OutboxMessageState.FAILED) is False
        with pytest.raises(InvalidStateTransitionError):
            sm.transition_to(OutboxMessageState.FAILED)

    def test_get_valid_transitions(self):
        transitions = OutboxStateMachine.get_valid_transitions(OutboxMessageState.PENDING)
        assert transitions == {OutboxMessageState.DELIVERING}
        transitions = OutboxStateMachine.get_valid_transitions(OutboxMessageState.DELIVERING)
        assert transitions == {OutboxMessageState.CONFIRMED, OutboxMessageState.FAILED}
        transitions = OutboxStateMachine.get_valid_transitions(OutboxMessageState.CONFIRMED)
        assert transitions == set()


class TestAtomicWrite:
    def test_write_with_message_creates_both(self):
        repo = make_repository()
        record, message = repo.write_with_message(
            business_type="order_created",
            message_type="send_order_email",
            business_payload={"order_id": "ORD-001", "amount": 99.9},
            message_payload={"order_id": "ORD-001", "email": "user@test.com"},
        )
        assert record.id is not None
        assert message.id is not None
        assert message.business_record_id == record.id
        assert repo.total_business_records() == 1
        assert repo.total_messages() == 1
        assert repo.get_business_record(record.id) is not None
        assert repo.get_message(message.id) is not None

    def test_write_with_message_links_messages_to_record(self):
        repo = make_repository()
        record, message = repo.write_with_message(
            business_type="order_created",
            message_type="notify",
            business_payload={},
            message_payload={},
        )
        linked = repo.get_messages_by_business(record.id)
        assert len(linked) == 1
        assert linked[0].id == message.id

    def test_write_with_multiple_messages(self):
        repo = make_repository()
        record, messages = repo.write_with_messages(
            business_type="order_created",
            business_payload={"order_id": "ORD-001"},
            message_specs=[
                ("send_email", {"to": "user@test.com"}),
                ("send_sms", {"phone": "+1234567890"}),
                ("update_inventory", {"sku": "SKU-001", "qty": -1}),
            ],
        )
        assert len(messages) == 3
        for msg in messages:
            assert msg.business_record_id == record.id
        assert repo.total_messages() == 3
        linked = repo.get_messages_by_business(record.id)
        assert len(linked) == 3

    def test_atomic_write_rollback_on_callback_failure(self):
        repo = make_repository()
        callback_called = {"value": False}

        def failing_callback(record: BusinessRecord) -> None:
            callback_called["value"] = True
            raise RuntimeError("Callback failed!")

        with pytest.raises(AtomicWriteError):
            repo.atomic_write_with_callback(
                callback=failing_callback,
                business_type="order_created",
                message_type="notify",
                business_payload={"key": "value"},
                message_payload={"key": "value"},
            )

        assert callback_called["value"] is True
        assert repo.total_business_records() == 0
        assert repo.total_messages() == 0

    def test_atomic_write_rollback_on_message_creation_failure(self):
        repo = make_repository()
        with pytest.raises(AtomicWriteError):
            repo.write_with_message(
                business_type="order_created",
                message_type="",
                business_payload={"key": "value"},
                message_payload={"key": "value"},
            )
        assert repo.total_business_records() == 0
        assert repo.total_messages() == 0

    def test_atomic_write_custom_ids(self):
        repo = make_repository()
        record, message = repo.write_with_message(
            business_type="order_created",
            message_type="notify",
            business_payload={},
            message_payload={},
            record_id="custom-rec-1",
            message_id="custom-msg-1",
        )
        assert record.id == "custom-rec-1"
        assert message.id == "custom-msg-1"

    def test_atomic_write_with_messages_rollback(self):
        repo = make_repository()
        with pytest.raises(AtomicWriteError):
            repo.write_with_messages(
                business_type="order_created",
                business_payload={},
                message_specs=[
                    ("ok_msg", {}),
                    ("", {}),
                ],
            )
        assert repo.total_business_records() == 0
        assert repo.total_messages() == 0

    def test_create_message_without_business_record_fails(self):
        repo = make_repository()
        with pytest.raises(ValueError, match="Business record not found"):
            repo.create_message(
                business_record_id="nonexistent",
                message_type="test",
                payload={},
            )


class TestDeliveryAndRetry:
    def test_claim_message_changes_state(self):
        repo = make_repository()
        _, msg = repo.write_with_message(
            business_type="test",
            message_type="test",
            business_payload={},
            message_payload={},
        )
        claimed = repo.claim_message(msg.id, "worker-1")
        assert claimed.state == OutboxMessageState.DELIVERING
        assert claimed.claimed_by == "worker-1"

    def test_confirm_message_after_claim(self):
        repo = make_repository()
        _, msg = repo.write_with_message(
            business_type="test",
            message_type="test",
            business_payload={},
            message_payload={},
        )
        repo.claim_message(msg.id, "worker-1")
        confirmed = repo.confirm_message(msg.id)
        assert confirmed.state == OutboxMessageState.CONFIRMED
        assert confirmed.claimed_by is None

    def test_fail_message_records_error_and_increments_retry(self):
        repo = make_repository()
        _, msg = repo.write_with_message(
            business_type="test",
            message_type="test",
            business_payload={},
            message_payload={},
        )
        repo.claim_message(msg.id, "worker-1")
        failed = repo.fail_message(msg.id, "connection refused")
        assert failed.state == OutboxMessageState.FAILED
        assert failed.retry_count == 1
        assert failed.last_error == "connection refused"
        assert failed.can_retry is True
        assert failed.next_retry_at is not None

    def test_fail_and_retry_flow_multiple_times(self):
        repo = make_repository(default_max_retries=2)
        _, msg = repo.write_with_message(
            business_type="test",
            message_type="test",
            business_payload={},
            message_payload={},
        )
        repo.claim_message(msg.id, "w")
        repo.fail_message(msg.id, "error 1")
        msg = repo.get_message(msg.id)
        assert msg.retry_count == 1
        assert msg.can_retry is True

        repo.claim_message(msg.id, "w")
        repo.fail_message(msg.id, "error 2")
        msg = repo.get_message(msg.id)
        assert msg.retry_count == 2
        assert msg.can_retry is False
        assert msg.state == OutboxMessageState.DEAD_LETTER

    def test_fail_message_then_success(self):
        repo = make_repository()
        _, msg = repo.write_with_message(
            business_type="test",
            message_type="test",
            business_payload={},
            message_payload={},
        )
        repo.claim_message(msg.id, "w")
        repo.fail_message(msg.id, "timeout")
        msg = repo.get_message(msg.id)
        assert msg.state == OutboxMessageState.FAILED
        assert msg.retry_count == 1

        repo.claim_message(msg.id, "w")
        repo.confirm_message(msg.id)
        msg = repo.get_message(msg.id)
        assert msg.state == OutboxMessageState.CONFIRMED
        assert msg.retry_count == 1

    def test_fail_message_exactly_max_retries_boundary(self):
        repo = make_repository(default_max_retries=1)
        _, msg = repo.write_with_message(
            business_type="test",
            message_type="test",
            business_payload={},
            message_payload={},
        )
        repo.claim_message(msg.id, "w")
        result = repo.fail_message(msg.id, "error")
        assert result.retry_count == 1
        assert result.state == OutboxMessageState.DEAD_LETTER
        assert result.can_retry is False

    def test_get_nonexistent_message_raises(self):
        repo = make_repository()
        with pytest.raises(MessageNotFoundError):
            repo.get_message("nonexistent")

    def test_confirm_message_without_claim(self):
        repo = make_repository()
        _, msg = repo.write_with_message(
            business_type="test",
            message_type="test",
            business_payload={},
            message_payload={},
        )
        with pytest.raises(InvalidStateTransitionError):
            repo.confirm_message(msg.id)

    def test_fail_message_without_claim(self):
        repo = make_repository()
        _, msg = repo.write_with_message(
            business_type="test",
            message_type="test",
            business_payload={},
            message_payload={},
        )
        with pytest.raises(InvalidStateTransitionError):
            repo.fail_message(msg.id, "error")


class TestCompensationScan:
    def test_scan_pending_messages_empty(self):
        repo = make_repository()
        result = repo.scan_pending_messages()
        assert result == []

    def test_scan_pending_messages_returns_sorted(self):
        repo = make_repository()
        messages = []
        for i in range(5):
            _, msg = repo.write_with_message(
                business_type=f"type-{i}",
                message_type=f"msg-{i}",
                business_payload={},
                message_payload={},
            )
            messages.append(msg)
            time.sleep(0.001)

        pending = repo.scan_pending_messages(limit=10)
        assert len(pending) == 5
        for i in range(1, len(pending)):
            assert pending[i - 1].created_at <= pending[i].created_at

    def test_scan_pending_does_not_include_delivering(self):
        repo = make_repository()
        _, msg1 = repo.write_with_message("t", "m", {}, {})
        _, msg2 = repo.write_with_message("t", "m", {}, {})
        repo.claim_message(msg1.id, "w")
        pending = repo.scan_pending_messages()
        assert len(pending) == 1
        assert pending[0].id == msg2.id

    def test_scan_pending_does_not_include_confirmed_or_dead(self):
        repo = make_repository(default_max_retries=1)
        _, msg1 = repo.write_with_message("t", "m", {}, {})
        _, msg2 = repo.write_with_message("t", "m", {}, {})
        _, msg3 = repo.write_with_message("t", "m", {}, {})

        repo.claim_message(msg1.id, "w")
        repo.confirm_message(msg1.id)

        repo.claim_message(msg2.id, "w")
        repo.fail_message(msg2.id, "e")

        pending = repo.scan_pending_messages()
        assert len(pending) == 1
        assert pending[0].id == msg3.id

        msg2_final = repo.get_message(msg2.id)
        assert msg2_final.state == OutboxMessageState.DEAD_LETTER

    def test_scan_retryable_messages_respects_next_retry_at(self):
        repo = make_repository(default_retry_delay_seconds=300)
        _, msg = repo.write_with_message("t", "m", {}, {})
        repo.claim_message(msg.id, "w")
        repo.fail_message(msg.id, "timeout")

        now = datetime.now()
        retryable = repo.scan_retryable_messages(now=now)
        assert len(retryable) == 0

        future = now + timedelta(seconds=301)
        retryable = repo.scan_retryable_messages(now=future)
        assert len(retryable) == 1
        assert retryable[0].id == msg.id

    def test_scan_retryable_does_not_include_maxed_out(self):
        repo = make_repository(default_max_retries=1, default_retry_delay_seconds=0)
        _, msg = repo.write_with_message("t", "m", {}, {})
        repo.claim_message(msg.id, "w")
        repo.fail_message(msg.id, "error")

        now = datetime.now() + timedelta(days=1)
        retryable = repo.scan_retryable_messages(now=now)
        assert len(retryable) == 0

    def test_scan_due_combines_pending_and_retryable(self):
        repo = make_repository(default_retry_delay_seconds=0)
        _, msg1 = repo.write_with_message("t", "m", {}, {})
        _, msg2 = repo.write_with_message("t", "m", {}, {})

        repo.claim_message(msg2.id, "w")
        repo.fail_message(msg2.id, "error")

        now = datetime.now() + timedelta(seconds=1)
        due = repo.scan_due_messages(now=now)
        ids = {m.id for m in due}
        assert msg1.id in ids
        assert msg2.id in ids
        assert len(due) == 2

    def test_scan_limit_applied(self):
        repo = make_repository()
        for i in range(10):
            repo.write_with_message("t", "m", {}, {})
        pending = repo.scan_pending_messages(limit=3)
        assert len(pending) == 3

    def test_claim_next_messages_batch(self):
        repo = make_repository()
        for i in range(5):
            repo.write_with_message("t", "m", {}, {})
        claimed = repo.claim_next_messages("worker-1", batch_size=3)
        assert len(claimed) == 3
        for msg in claimed:
            assert msg.state == OutboxMessageState.DELIVERING
            assert msg.claimed_by == "worker-1"
        remaining = repo.scan_pending_messages()
        assert len(remaining) == 2


class TestDeadLetterHandling:
    def test_fail_exceeds_max_retries_enters_dead_letter(self):
        repo = make_repository(default_max_retries=2)
        _, msg = repo.write_with_message(
            business_type="t",
            message_type="m",
            business_payload={},
            message_payload={},
        )
        for _ in range(2):
            repo.claim_message(msg.id, "w")
            repo.fail_message(msg.id, "error")

        final = repo.get_message(msg.id)
        assert final.state == OutboxMessageState.DEAD_LETTER
        assert final.is_dead_letter is True
        assert final.retry_count == 2

    def test_dead_letters_not_in_pending_scan(self):
        repo = make_repository(default_max_retries=1)
        _, msg = repo.write_with_message("t", "m", {}, {})
        repo.claim_message(msg.id, "w")
        repo.fail_message(msg.id, "e")
        msg = repo.get_message(msg.id)
        assert msg.state == OutboxMessageState.DEAD_LETTER

        pending = repo.scan_pending_messages()
        assert msg.id not in [m.id for m in pending]

    def test_dead_letters_not_in_retryable_scan(self):
        repo = make_repository(default_max_retries=1, default_retry_delay_seconds=0)
        _, msg = repo.write_with_message("t", "m", {}, {})
        repo.claim_message(msg.id, "w")
        repo.fail_message(msg.id, "e")

        now = datetime.now() + timedelta(days=1)
        retryable = repo.scan_retryable_messages(now=now)
        assert msg.id not in [m.id for m in retryable]

    def test_dead_letters_not_in_due_scan(self):
        repo = make_repository(default_max_retries=1, default_retry_delay_seconds=0)
        _, msg = repo.write_with_message("t", "m", {}, {})
        repo.claim_message(msg.id, "w")
        repo.fail_message(msg.id, "e")

        now = datetime.now() + timedelta(days=1)
        due = repo.scan_due_messages(now=now)
        assert msg.id not in [m.id for m in due]

    def test_get_dead_letters_returns_only_dead(self):
        repo = make_repository(default_max_retries=1)
        _, msg_ok = repo.write_with_message("t", "m", {}, {})
        _, msg_dead = repo.write_with_message("t", "m", {}, {})
        repo.claim_message(msg_dead.id, "w")
        repo.fail_message(msg_dead.id, "e")

        dead = repo.get_dead_letters()
        assert len(dead) == 1
        assert dead[0].id == msg_dead.id

    def test_force_to_dead_letter(self):
        repo = make_repository()
        _, msg = repo.write_with_message("t", "m", {}, {})
        repo.force_to_dead_letter(msg.id)
        final = repo.get_message(msg.id)
        assert final.state == OutboxMessageState.DEAD_LETTER

    def test_dead_letter_preserves_last_error(self):
        repo = make_repository(default_max_retries=1)
        _, msg = repo.write_with_message("t", "m", {}, {})
        repo.claim_message(msg.id, "w")
        repo.fail_message(msg.id, "final fatal error")
        final = repo.get_message(msg.id)
        assert final.state == OutboxMessageState.DEAD_LETTER
        assert final.last_error == "final fatal error"
        assert final.retry_count == 1


class TestConcurrentClaim:
    def test_concurrent_claim_same_message_different_workers(self):
        repo = make_repository()
        _, msg = repo.write_with_message("t", "m", {}, {})

        repo.claim_message(msg.id, "worker-A")
        with pytest.raises(MessageAlreadyClaimedError):
            repo.claim_message(msg.id, "worker-B")

    def test_same_worker_can_reclaim(self):
        repo = make_repository()
        _, msg = repo.write_with_message("t", "m", {}, {})
        repo.claim_message(msg.id, "worker-A")
        result = repo.claim_message(msg.id, "worker-A")
        assert result.state == OutboxMessageState.DELIVERING
        assert result.claimed_by == "worker-A"

    def test_concurrent_claim_next_no_duplicates(self):
        repo = make_repository()
        total_messages = 50
        for i in range(total_messages):
            repo.write_with_message("t", "m", {}, {})

        results: Dict[str, List[str]] = {"worker-1": [], "worker-2": [], "worker-3": []}
        barrier = threading.Barrier(3)

        def worker_claim(worker_id: str):
            barrier.wait()
            claimed = repo.claim_next_messages(worker_id, batch_size=30)
            results[worker_id] = [m.id for m in claimed]

        threads = [
            threading.Thread(target=worker_claim, args=("worker-1",)),
            threading.Thread(target=worker_claim, args=("worker-2",)),
            threading.Thread(target=worker_claim, args=("worker-3",)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        all_claimed = []
        for wid in ["worker-1", "worker-2", "worker-3"]:
            all_claimed.extend(results[wid])
        assert len(all_claimed) == total_messages
        assert len(set(all_claimed)) == total_messages

        for wid in ["worker-1", "worker-2", "worker-3"]:
            assert len(results[wid]) == len(set(results[wid]))

    def test_concurrent_atomic_writes_and_claims(self):
        repo = make_repository()
        write_errors = []
        claim_counts = {"w1": 0, "w2": 0}

        def writer_thread():
            try:
                for i in range(20):
                    repo.write_with_message("t", "m", {"i": i}, {"i": i})
            except Exception as e:
                write_errors.append(e)

        def claimer_thread(worker_id: str):
            for _ in range(30):
                claimed = repo.claim_next_messages(worker_id, batch_size=5)
                claim_counts[worker_id] += len(claimed)
                for msg in claimed:
                    try:
                        repo.confirm_message(msg.id)
                    except Exception:
                        pass

        wt = threading.Thread(target=writer_thread)
        ct1 = threading.Thread(target=claimer_thread, args=("w1",))
        ct2 = threading.Thread(target=claimer_thread, args=("w2",))

        wt.start()
        ct1.start()
        ct2.start()
        wt.join(timeout=5)
        ct1.join(timeout=5)
        ct2.join(timeout=5)

        assert len(write_errors) == 0
        assert repo.total_business_records() == 20


class TestRepositoryQueriesAndConfig:
    def test_count_by_state(self):
        repo = make_repository(default_max_retries=1)
        _, m1 = repo.write_with_message("t", "m", {}, {})
        _, m2 = repo.write_with_message("t", "m", {}, {})
        _, m3 = repo.write_with_message("t", "m", {}, {})

        repo.claim_message(m1.id, "w")
        repo.confirm_message(m1.id)

        repo.claim_message(m3.id, "w")
        repo.fail_message(m3.id, "e")

        counts = repo.count_by_state()
        assert counts[OutboxMessageState.PENDING] == 1
        assert counts[OutboxMessageState.CONFIRMED] == 1
        assert counts[OutboxMessageState.DEAD_LETTER] == 1

    def test_repository_clear(self):
        repo = make_repository()
        repo.write_with_message("t", "m", {}, {})
        assert repo.total_messages() == 1
        assert repo.total_business_records() == 1
        repo.clear()
        assert repo.total_messages() == 0
        assert repo.total_business_records() == 0

    def test_invalid_default_max_retries(self):
        with pytest.raises(ValueError, match="default_max_retries cannot be negative"):
            OutboxRepository(default_max_retries=-1)

    def test_invalid_default_retry_delay(self):
        with pytest.raises(ValueError, match="default_retry_delay_seconds cannot be negative"):
            OutboxRepository(default_retry_delay_seconds=-1)

    def test_custom_max_retries_per_message(self):
        repo = make_repository(default_max_retries=5)
        _, msg = repo.write_with_message(
            "t", "m", {}, {}, max_retries=1
        )
        repo.claim_message(msg.id, "w")
        repo.fail_message(msg.id, "e")
        final = repo.get_message(msg.id)
        assert final.state == OutboxMessageState.DEAD_LETTER
        assert final.retry_count == 1

    def test_get_messages_by_business_record_not_found(self):
        repo = make_repository()
        with pytest.raises(ValueError, match="Business record not found"):
            repo.get_messages_by_business("nonexistent")

    def test_get_business_record_not_found(self):
        repo = make_repository()
        with pytest.raises(ValueError, match="Business record not found"):
            repo.get_business_record("nonexistent")
