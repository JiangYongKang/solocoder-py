from __future__ import annotations

import pytest

from solocoder_py.timeout_manager import (
    ContextNotFoundError,
    ContextTerminalStateError,
    InvalidCallbackError,
    InvalidDeadlineError,
    ManualClock,
    TimeoutContext,
    TimeoutManager,
)

from .conftest import make_manager


class TestClock:
    def test_manual_clock_initial_time(self):
        clock = ManualClock(start_time=100.0)
        assert clock.now() == 100.0

    def test_manual_clock_advance(self):
        clock = ManualClock()
        clock.advance(5.0)
        assert clock.now() == 5.0
        clock.advance(3.0)
        assert clock.now() == 8.0

    def test_manual_clock_advance_negative_raises(self):
        clock = ManualClock()
        with pytest.raises(ValueError):
            clock.advance(-1)

    def test_manual_clock_set(self):
        clock = ManualClock()
        clock.set(42.0)
        assert clock.now() == 42.0


class TestRootContextCreation:
    def test_create_root_context(self, manager: TimeoutManager, clock: ManualClock):
        deadline = 100.0
        ctx = manager.create_root_context(deadline)
        assert ctx is not None
        assert ctx.deadline == deadline
        assert ctx.created_at == clock.now()
        assert ctx.parent is None
        assert ctx.is_active() is True
        assert ctx.is_cancelled is False
        assert ctx.is_expired is False

    def test_create_root_context_deadline_in_past_raises(self, manager: TimeoutManager, clock: ManualClock):
        clock.set(50.0)
        with pytest.raises(InvalidDeadlineError):
            manager.create_root_context(40.0)

    def test_create_root_context_deadline_equals_now_raises(self, manager: TimeoutManager, clock: ManualClock):
        clock.set(50.0)
        with pytest.raises(InvalidDeadlineError):
            manager.create_root_context(50.0)

    def test_root_context_has_no_parent(self, manager: TimeoutManager):
        ctx = manager.create_root_context(100.0)
        assert ctx.parent is None


class TestChildContextCreation:
    def test_create_child_with_deadline(self, manager: TimeoutManager, clock: ManualClock):
        parent = manager.create_root_context(100.0)
        child = manager.create_child_context(parent.context_id, deadline=80.0)
        assert child.parent is not None
        assert child.parent.context_id == parent.context_id
        assert child.deadline == 80.0

    def test_create_child_with_timeout(self, manager: TimeoutManager, clock: ManualClock):
        clock.set(0.0)
        parent = manager.create_root_context(100.0)
        child = manager.create_child_context(parent.context_id, timeout=30.0)
        assert child.deadline == 30.0

    def test_create_child_inherits_parent_deadline(self, manager: TimeoutManager):
        parent = manager.create_root_context(100.0)
        child = manager.create_child_context(parent.context_id)
        assert child.deadline == parent.deadline

    def test_child_deadline_capped_by_parent(self, manager: TimeoutManager, clock: ManualClock):
        clock.set(0.0)
        parent = manager.create_root_context(50.0)
        child = manager.create_child_context(parent.context_id, timeout=60.0)
        assert child.deadline == 50.0

    def test_child_deadline_earlier_than_parent(self, manager: TimeoutManager, clock: ManualClock):
        clock.set(0.0)
        parent = manager.create_root_context(100.0)
        child = manager.create_child_context(parent.context_id, deadline=30.0)
        assert child.deadline == 30.0

    def test_create_child_on_cancelled_parent_raises(self, manager: TimeoutManager):
        parent = manager.create_root_context(100.0)
        manager.cancel_context(parent.context_id, "test cancel")
        with pytest.raises(ContextTerminalStateError):
            manager.create_child_context(parent.context_id, deadline=80.0)

    def test_create_child_on_nonexistent_parent_raises(self, manager: TimeoutManager):
        with pytest.raises(ContextNotFoundError):
            manager.create_child_context("nonexistent-id", deadline=80.0)

    def test_create_child_with_both_deadline_and_timeout_raises(self, manager: TimeoutManager):
        parent = manager.create_root_context(100.0)
        with pytest.raises(InvalidDeadlineError):
            manager.create_child_context(
                parent.context_id, deadline=80.0, timeout=30.0
            )

    def test_create_child_with_zero_timeout_raises(self, manager: TimeoutManager):
        parent = manager.create_root_context(100.0)
        with pytest.raises(InvalidDeadlineError):
            manager.create_child_context(parent.context_id, timeout=0)

    def test_create_child_with_negative_timeout_raises(self, manager: TimeoutManager):
        parent = manager.create_root_context(100.0)
        with pytest.raises(InvalidDeadlineError):
            manager.create_child_context(parent.context_id, timeout=-5.0)

    def test_create_child_deadline_in_past_raises(self, manager: TimeoutManager, clock: ManualClock):
        clock.set(50.0)
        parent = manager.create_root_context(100.0)
        with pytest.raises(InvalidDeadlineError):
            manager.create_child_context(parent.context_id, deadline=40.0)


class TestDeadlinePropagation:
    def test_three_level_deadline_propagation(self, manager: TimeoutManager, clock: ManualClock):
        clock.set(0.0)
        level1 = manager.create_root_context(100.0)
        level2 = manager.create_child_context(level1.context_id, deadline=80.0)
        level3 = manager.create_child_context(level2.context_id, deadline=60.0)
        assert level1.deadline == 100.0
        assert level2.deadline == 80.0
        assert level3.deadline == 60.0

    def test_middle_level_caps_child_deadline(self, manager: TimeoutManager, clock: ManualClock):
        clock.set(0.0)
        level1 = manager.create_root_context(100.0)
        level2 = manager.create_child_context(level1.context_id, deadline=50.0)
        level3 = manager.create_child_context(level2.context_id, deadline=70.0)
        assert level3.deadline == 50.0

    def test_deep_nesting_deadline_propagation(self, manager: TimeoutManager, clock: ManualClock):
        clock.set(0.0)
        level1 = manager.create_root_context(200.0)
        level2 = manager.create_child_context(level1.context_id, deadline=180.0)
        level3 = manager.create_child_context(level2.context_id, deadline=150.0)
        level4 = manager.create_child_context(level3.context_id, deadline=120.0)
        level5 = manager.create_child_context(level4.context_id, deadline=100.0)

        assert level1.deadline == 200.0
        assert level2.deadline == 180.0
        assert level3.deadline == 150.0
        assert level4.deadline == 120.0
        assert level5.deadline == 100.0

    def test_millisecond_precision_deadline(self, manager: TimeoutManager, clock: ManualClock):
        clock.set(0.0)
        parent = manager.create_root_context(1.000)
        child = manager.create_child_context(parent.context_id, deadline=0.500)
        grandchild = manager.create_child_context(child.context_id, deadline=0.250)
        assert parent.deadline == 1.0
        assert child.deadline == 0.5
        assert grandchild.deadline == 0.25


class TestCancellation:
    def test_manual_cancel_context(self, manager: TimeoutManager):
        ctx = manager.create_root_context(100.0)
        manager.cancel_context(ctx.context_id, "user cancelled")
        info = manager.get_context(ctx.context_id)
        assert info is not None
        assert info.is_cancelled is True
        assert info.cancel_reason == "user cancelled"

    def test_cancel_idempotent(self, manager: TimeoutManager):
        ctx = manager.create_root_context(100.0)
        manager.cancel_context(ctx.context_id, "first")
        manager.cancel_context(ctx.context_id, "second")
        info = manager.get_context(ctx.context_id)
        assert info is not None
        assert info.is_cancelled is True
        assert info.cancel_reason == "first"

    def test_cancel_nonexistent_context_raises(self, manager: TimeoutManager):
        with pytest.raises(ContextNotFoundError):
            manager.cancel_context("nonexistent")

    def test_cancelled_context_not_active(self, manager: TimeoutManager):
        ctx = manager.create_root_context(100.0)
        manager.cancel_context(ctx.context_id)
        assert manager.is_active(ctx.context_id) is False


class TestCascadeCancellation:
    def test_parent_cancel_cascades_to_child(self, manager: TimeoutManager):
        parent = manager.create_root_context(100.0)
        child = manager.create_child_context(parent.context_id, deadline=80.0)
        manager.cancel_context(parent.context_id, "parent cancelled")
        assert manager.get_context(parent.context_id).is_cancelled is True
        assert manager.get_context(child.context_id).is_cancelled is True

    def test_parent_cancel_cascades_to_grandchildren(self, manager: TimeoutManager):
        level1 = manager.create_root_context(100.0)
        level2 = manager.create_child_context(level1.context_id, deadline=80.0)
        level3 = manager.create_child_context(level2.context_id, deadline=60.0)
        level4 = manager.create_child_context(level3.context_id, deadline=40.0)

        manager.cancel_context(level1.context_id, "root cancelled")

        assert manager.get_context(level1.context_id).is_cancelled is True
        assert manager.get_context(level2.context_id).is_cancelled is True
        assert manager.get_context(level3.context_id).is_cancelled is True
        assert manager.get_context(level4.context_id).is_cancelled is True

    def test_child_cancel_does_not_affect_parent(self, manager: TimeoutManager):
        parent = manager.create_root_context(100.0)
        child = manager.create_child_context(parent.context_id, deadline=80.0)
        manager.cancel_context(child.context_id, "child cancelled")
        assert manager.get_context(child.context_id).is_cancelled is True
        assert manager.get_context(parent.context_id).is_cancelled is False
        assert manager.is_active(parent.context_id) is True

    def test_sibling_cancellation_independent(self, manager: TimeoutManager):
        parent = manager.create_root_context(100.0)
        child1 = manager.create_child_context(parent.context_id, deadline=80.0)
        child2 = manager.create_child_context(parent.context_id, deadline=90.0)
        child3 = manager.create_child_context(parent.context_id, deadline=70.0)

        manager.cancel_context(child2.context_id, "child2 cancelled")

        assert manager.get_context(child1.context_id).is_cancelled is False
        assert manager.get_context(child2.context_id).is_cancelled is True
        assert manager.get_context(child3.context_id).is_cancelled is False
        assert manager.get_context(parent.context_id).is_cancelled is False

    def test_deep_cascade_with_multiple_children(self, manager: TimeoutManager):
        root = manager.create_root_context(200.0)
        child1 = manager.create_child_context(root.context_id, deadline=180.0)
        child2 = manager.create_child_context(root.context_id, deadline=190.0)
        grandchild1a = manager.create_child_context(child1.context_id, deadline=160.0)
        grandchild1b = manager.create_child_context(child1.context_id, deadline=170.0)
        grandchild2a = manager.create_child_context(child2.context_id, deadline=150.0)

        manager.cancel_context(root.context_id, "root cancelled")

        assert manager.get_context(root.context_id).is_cancelled is True
        assert manager.get_context(child1.context_id).is_cancelled is True
        assert manager.get_context(child2.context_id).is_cancelled is True
        assert manager.get_context(grandchild1a.context_id).is_cancelled is True
        assert manager.get_context(grandchild1b.context_id).is_cancelled is True
        assert manager.get_context(grandchild2a.context_id).is_cancelled is True

    def test_cancel_reason_propagates(self, manager: TimeoutManager):
        parent = manager.create_root_context(100.0)
        child = manager.create_child_context(parent.context_id, deadline=80.0)
        manager.cancel_context(parent.context_id, "timeout exceeded")
        child_info = manager.get_context(child.context_id)
        assert child_info.cancel_reason == "timeout exceeded"


class TestExpiration:
    def test_context_expires_after_deadline(self, manager: TimeoutManager, clock: ManualClock):
        ctx = manager.create_root_context(100.0)
        clock.set(99.9)
        expired = manager.check_expired()
        assert expired == []
        assert manager.is_active(ctx.context_id) is True

        clock.set(100.0)
        expired = manager.check_expired()
        assert ctx.context_id in expired
        assert manager.get_context(ctx.context_id).is_expired is True

    def test_expired_context_not_active(self, manager: TimeoutManager, clock: ManualClock):
        ctx = manager.create_root_context(100.0)
        clock.set(100.0)
        manager.check_expired()
        assert manager.is_active(ctx.context_id) is False

    def test_expiration_cascades_to_children(self, manager: TimeoutManager, clock: ManualClock):
        clock.set(0.0)
        parent = manager.create_root_context(50.0)
        child = manager.create_child_context(parent.context_id, deadline=80.0)
        grandchild = manager.create_child_context(child.context_id, deadline=90.0)

        clock.set(50.0)
        expired = manager.check_expired()

        assert parent.context_id in expired
        assert manager.get_context(parent.context_id).is_expired is True
        assert manager.get_context(child.context_id).is_expired is True
        assert manager.get_context(grandchild.context_id).is_expired is True

    def test_child_expires_before_parent(self, manager: TimeoutManager, clock: ManualClock):
        clock.set(0.0)
        parent = manager.create_root_context(100.0)
        child = manager.create_child_context(parent.context_id, deadline=30.0)

        clock.set(30.0)
        expired = manager.check_expired()

        assert child.context_id in expired
        assert parent.context_id not in expired
        assert manager.get_context(child.context_id).is_expired is True
        assert manager.get_context(parent.context_id).is_expired is False
        assert manager.is_active(parent.context_id) is True

    def test_multiple_children_expire_at_different_times(self, manager: TimeoutManager, clock: ManualClock):
        clock.set(0.0)
        parent = manager.create_root_context(100.0)
        child1 = manager.create_child_context(parent.context_id, deadline=30.0)
        child2 = manager.create_child_context(parent.context_id, deadline=60.0)
        child3 = manager.create_child_context(parent.context_id, deadline=90.0)

        clock.set(30.0)
        expired1 = manager.check_expired()
        assert child1.context_id in expired1
        assert child2.context_id not in expired1
        assert child3.context_id not in expired1

        clock.set(60.0)
        expired2 = manager.check_expired()
        assert child2.context_id in expired2

        clock.set(90.0)
        expired3 = manager.check_expired()
        assert child3.context_id in expired3

    def test_millisecond_precision_expiration(self, manager: TimeoutManager, clock: ManualClock):
        clock.set(0.0)
        ctx = manager.create_root_context(0.500)
        clock.advance(0.499)
        expired = manager.check_expired()
        assert expired == []
        assert manager.is_active(ctx.context_id) is True

        clock.advance(0.001)
        expired = manager.check_expired()
        assert ctx.context_id in expired


class TestCallbacks:
    def test_callback_triggered_on_expiration(self, manager: TimeoutManager, clock: ManualClock):
        triggered = []

        def on_expire(ctx: TimeoutContext) -> None:
            triggered.append(ctx.context_id)

        ctx = manager.create_root_context(100.0)
        manager.add_callback(ctx.context_id, on_expire)

        clock.set(100.0)
        manager.check_expired()

        assert ctx.context_id in triggered
        assert len(triggered) == 1

    def test_multiple_callbacks_triggered_in_order(self, manager: TimeoutManager, clock: ManualClock):
        order = []

        def callback1(ctx: TimeoutContext) -> None:
            order.append("cb1")

        def callback2(ctx: TimeoutContext) -> None:
            order.append("cb2")

        def callback3(ctx: TimeoutContext) -> None:
            order.append("cb3")

        ctx = manager.create_root_context(100.0)
        manager.add_callback(ctx.context_id, callback1)
        manager.add_callback(ctx.context_id, callback2)
        manager.add_callback(ctx.context_id, callback3)

        clock.set(100.0)
        manager.check_expired()

        assert order == ["cb1", "cb2", "cb3"]

    def test_callback_exception_does_not_affect_others(self, manager: TimeoutManager, clock: ManualClock):
        triggered = []

        def bad_callback(ctx: TimeoutContext) -> None:
            raise RuntimeError("boom")

        def good_callback(ctx: TimeoutContext) -> None:
            triggered.append(ctx.context_id)

        ctx = manager.create_root_context(100.0)
        manager.add_callback(ctx.context_id, bad_callback)
        manager.add_callback(ctx.context_id, good_callback)

        clock.set(100.0)
        manager.check_expired()

        assert ctx.context_id in triggered

    def test_callback_not_triggered_on_cancel_before_expiry(self, manager: TimeoutManager, clock: ManualClock):
        triggered = []

        def on_expire(ctx: TimeoutContext) -> None:
            triggered.append(ctx.context_id)

        ctx = manager.create_root_context(100.0)
        manager.add_callback(ctx.context_id, on_expire)
        manager.cancel_context(ctx.context_id, "manual cancel")

        clock.set(100.0)
        manager.check_expired()

        assert triggered == []

    def test_cancelled_context_callbacks_never_fire(self, manager: TimeoutManager, clock: ManualClock):
        triggered = []

        def on_expire(ctx: TimeoutContext) -> None:
            triggered.append(ctx.context_id)

        ctx = manager.create_root_context(100.0)
        manager.add_callback(ctx.context_id, on_expire)
        manager.cancel_context(ctx.context_id, "manual cancel")

        clock.set(200.0)
        manager.check_expired()
        manager.check_expired()

        assert triggered == []
        assert ctx.is_cancelled is True
        assert ctx.is_expired is False

    def test_add_callback_to_cancelled_context_raises(self, manager: TimeoutManager):
        ctx = manager.create_root_context(100.0)
        manager.cancel_context(ctx.context_id)

        def cb(ctx: TimeoutContext) -> None:
            pass

        with pytest.raises(ContextTerminalStateError):
            manager.add_callback(ctx.context_id, cb)

    def test_add_callback_to_expired_context_raises(self, manager: TimeoutManager, clock: ManualClock):
        ctx = manager.create_root_context(100.0)
        clock.set(100.0)
        manager.check_expired()

        def cb(ctx: TimeoutContext) -> None:
            pass

        with pytest.raises(ContextTerminalStateError):
            manager.add_callback(ctx.context_id, cb)

    def test_add_none_callback_raises(self, manager: TimeoutManager):
        ctx = manager.create_root_context(100.0)
        with pytest.raises(InvalidCallbackError):
            manager.add_callback(ctx.context_id, None)

    def test_callbacks_only_triggered_once(self, manager: TimeoutManager, clock: ManualClock):
        count = 0

        def on_expire(ctx: TimeoutContext) -> None:
            nonlocal count
            count += 1

        ctx = manager.create_root_context(100.0)
        manager.add_callback(ctx.context_id, on_expire)

        clock.set(100.0)
        manager.check_expired()
        manager.check_expired()
        manager.check_expired()

        assert count == 1

    def test_callback_receives_context_as_param(self, manager: TimeoutManager, clock: ManualClock):
        received_ctx = None

        def on_expire(ctx: TimeoutContext) -> None:
            nonlocal received_ctx
            received_ctx = ctx

        ctx = manager.create_root_context(100.0)
        manager.add_callback(ctx.context_id, on_expire)

        clock.set(100.0)
        manager.check_expired()

        assert received_ctx is not None
        assert received_ctx.context_id == ctx.context_id

    def test_callback_registers_new_callback(self, manager: TimeoutManager, clock: ManualClock):
        triggered = []
        manager_ref: TimeoutManager | None = None

        def callback1(ctx: TimeoutContext) -> None:
            triggered.append("cb1")

        def callback2(ctx: TimeoutContext) -> None:
            triggered.append("cb2")

        def callback_registrar(ctx: TimeoutContext) -> None:
            triggered.append("registrar")
            assert manager_ref is not None

        ctx = manager.create_root_context(100.0)
        manager_ref = manager
        manager.add_callback(ctx.context_id, callback1)
        manager.add_callback(ctx.context_id, callback_registrar)
        manager.add_callback(ctx.context_id, callback2)

        clock.set(100.0)
        manager.check_expired()

        assert "cb1" in triggered
        assert "registrar" in triggered
        assert "cb2" in triggered


class TestCascadeCallbacks:
    def test_parent_expiry_triggers_child_callbacks(self, manager: TimeoutManager, clock: ManualClock):
        triggered = {}

        def make_callback(name: str):
            def cb(ctx: TimeoutContext) -> None:
                triggered[name] = ctx.context_id

            return cb

        clock.set(0.0)
        parent = manager.create_root_context(50.0)
        child = manager.create_child_context(parent.context_id, deadline=80.0)
        grandchild = manager.create_child_context(child.context_id, deadline=90.0)

        manager.add_callback(parent.context_id, make_callback("parent"))
        manager.add_callback(child.context_id, make_callback("child"))
        manager.add_callback(grandchild.context_id, make_callback("grandchild"))

        clock.set(50.0)
        manager.check_expired()

        assert "parent" in triggered
        assert "child" in triggered
        assert "grandchild" in triggered

    def test_child_expiry_does_not_trigger_parent_callback(self, manager: TimeoutManager, clock: ManualClock):
        triggered = {}

        def make_callback(name: str):
            def cb(ctx: TimeoutContext) -> None:
                triggered[name] = ctx.context_id

            return cb

        clock.set(0.0)
        parent = manager.create_root_context(100.0)
        child = manager.create_child_context(parent.context_id, deadline=30.0)

        manager.add_callback(parent.context_id, make_callback("parent"))
        manager.add_callback(child.context_id, make_callback("child"))

        clock.set(30.0)
        manager.check_expired()

        assert "child" in triggered
        assert "parent" not in triggered


class TestContextInfo:
    def test_get_context_returns_info(self, manager: TimeoutManager):
        ctx = manager.create_root_context(100.0)
        info = manager.get_context(ctx.context_id)
        assert info is not None
        assert info.context_id == ctx.context_id
        assert info.deadline == 100.0
        assert info.is_cancelled is False
        assert info.is_expired is False
        assert info.parent_id is None

    def test_get_nonexistent_context_returns_none(self, manager: TimeoutManager):
        assert manager.get_context("nonexistent") is None

    def test_get_all_contexts(self, manager: TimeoutManager):
        ctx1 = manager.create_root_context(100.0)
        ctx2 = manager.create_root_context(200.0)
        all_ctx = manager.get_all_contexts()
        assert len(all_ctx) == 2
        assert ctx1.context_id in all_ctx
        assert ctx2.context_id in all_ctx

    def test_child_context_info_has_parent_id(self, manager: TimeoutManager):
        parent = manager.create_root_context(100.0)
        child = manager.create_child_context(parent.context_id, deadline=80.0)
        child_info = manager.get_context(child.context_id)
        assert child_info is not None
        assert child_info.parent_id == parent.context_id


class TestNormalFlows:
    def test_full_lifecycle_create_use_cancel(self, manager: TimeoutManager, clock: ManualClock):
        triggered = []

        def on_expire(ctx: TimeoutContext) -> None:
            triggered.append(ctx.context_id)

        ctx = manager.create_root_context(100.0)
        assert manager.is_active(ctx.context_id) is True

        manager.add_callback(ctx.context_id, on_expire)

        clock.advance(30.0)
        assert manager.is_active(ctx.context_id) is True

        manager.cancel_context(ctx.context_id, "work completed early")

        assert manager.is_active(ctx.context_id) is False
        info = manager.get_context(ctx.context_id)
        assert info.is_cancelled is True
        assert info.cancel_reason == "work completed early"

        manager.check_expired()
        assert triggered == []
        assert ctx.is_cancelled is True

    def test_full_lifecycle_expiration(self, manager: TimeoutManager, clock: ManualClock):
        triggered = []

        def on_expire(ctx: TimeoutContext) -> None:
            triggered.append(ctx.context_id)

        clock.set(0.0)
        ctx = manager.create_root_context(60.0)
        manager.add_callback(ctx.context_id, on_expire)

        clock.advance(30.0)
        manager.check_expired()
        assert triggered == []
        assert manager.is_active(ctx.context_id) is True

        clock.advance(30.0)
        expired = manager.check_expired()
        assert ctx.context_id in expired
        assert ctx.context_id in triggered
        assert manager.is_active(ctx.context_id) is False

    def test_nested_contexts_with_mixed_expiry(self, manager: TimeoutManager, clock: ManualClock):
        clock.set(0.0)
        root = manager.create_root_context(500.0)

        branch1 = manager.create_child_context(root.context_id, deadline=100.0)
        branch1_child1 = manager.create_child_context(branch1.context_id, deadline=50.0)
        branch1_child2 = manager.create_child_context(branch1.context_id, deadline=80.0)

        branch2 = manager.create_child_context(root.context_id, deadline=200.0)
        branch2_child = manager.create_child_context(branch2.context_id, deadline=150.0)

        clock.set(50.0)
        expired1 = manager.check_expired()
        assert branch1_child1.context_id in expired1
        assert branch1.is_active() is True
        assert branch2.is_active() is True

        clock.set(100.0)
        expired2 = manager.check_expired()
        assert branch1.context_id in expired2

        branch1_info = manager.get_context(branch1.context_id)
        assert branch1_info.is_expired is True
        assert manager.get_context(branch1_child2.context_id).is_expired is True

        assert manager.get_context(branch2.context_id).is_expired is False
        assert manager.get_context(branch2_child.context_id).is_expired is False


class TestEdgeCases:
    def test_callback_during_callback_execution(self, manager: TimeoutManager, clock: ManualClock):
        triggered = []
        manager_ref: TimeoutManager | None = None

        def callback2(ctx: TimeoutContext) -> None:
            triggered.append("cb2")

        def callback1(ctx: TimeoutContext) -> None:
            triggered.append("cb1")

        ctx = manager.create_root_context(100.0)
        manager_ref = manager
        manager.add_callback(ctx.context_id, callback1)
        manager.add_callback(ctx.context_id, callback2)

        clock.set(100.0)
        manager.check_expired()

        assert triggered == ["cb1", "cb2"]

    def test_expired_context_cannot_create_child(self, manager: TimeoutManager, clock: ManualClock):
        ctx = manager.create_root_context(100.0)
        clock.set(100.0)
        manager.check_expired()
        with pytest.raises(ContextTerminalStateError):
            manager.create_child_context(ctx.context_id, deadline=50.0)

    def test_cancel_already_expired_context(self, manager: TimeoutManager, clock: ManualClock):
        ctx = manager.create_root_context(100.0)
        clock.set(100.0)
        manager.check_expired()
        manager.cancel_context(ctx.context_id, "late cancel")
        info = manager.get_context(ctx.context_id)
        assert info.is_expired is True
        assert info.is_cancelled is False

    def test_zero_time_children_not_allowed(self, manager: TimeoutManager, clock: ManualClock):
        clock.set(10.0)
        parent = manager.create_root_context(100.0)
        with pytest.raises(InvalidDeadlineError):
            manager.create_child_context(parent.context_id, deadline=10.0)

    def test_large_number_of_children(self, manager: TimeoutManager, clock: ManualClock):
        clock.set(0.0)
        parent = manager.create_root_context(100.0)
        child_ids = []
        for i in range(100):
            child = manager.create_child_context(parent.context_id, deadline=50.0 + i)
            child_ids.append(child.context_id)

        assert len(parent.children) == 100

        clock.set(100.0)
        expired = manager.check_expired()

        assert parent.context_id in expired
        for cid in child_ids:
            assert manager.get_context(cid).is_expired is True

    def test_deeply_nested_tree_structure(self, manager: TimeoutManager, clock: ManualClock):
        clock.set(0.0)
        root = manager.create_root_context(100.0)
        current = root
        all_ids = [root.context_id]

        for i in range(10):
            child = manager.create_child_context(current.context_id, deadline=90.0 - i * 5)
            all_ids.append(child.context_id)
            current = child

        clock.set(50.0)
        manager.check_expired()

        assert manager.get_context(all_ids[0]).is_expired is False

        clock.set(100.0)
        manager.check_expired()

        for cid in all_ids:
            assert manager.get_context(cid).is_expired is True


class TestExceptionMessages:
    def test_terminal_state_error_message_on_cancelled(self, manager: TimeoutManager):
        ctx = manager.create_root_context(100.0)
        manager.cancel_context(ctx.context_id, "test")
        try:
            manager.create_child_context(ctx.context_id, deadline=50.0)
            assert False, "Expected ContextTerminalStateError"
        except ContextTerminalStateError as e:
            assert ctx.context_id in str(e)
            assert "terminal state" in str(e).lower()

    def test_terminal_state_error_message_on_expired(self, manager: TimeoutManager, clock: ManualClock):
        ctx = manager.create_root_context(100.0)
        clock.set(100.0)
        manager.check_expired()
        try:
            manager.create_child_context(ctx.context_id, deadline=50.0)
            assert False, "Expected ContextTerminalStateError"
        except ContextTerminalStateError as e:
            assert ctx.context_id in str(e)
            assert "terminal state" in str(e).lower()

    def test_context_not_found_error_message(self, manager: TimeoutManager):
        try:
            manager.cancel_context("nonexistent-id")
            assert False, "Expected ContextNotFoundError"
        except ContextNotFoundError as e:
            assert "nonexistent-id" in str(e)
            assert "not found" in str(e).lower()

    def test_invalid_callback_error_message(self, manager: TimeoutManager):
        ctx = manager.create_root_context(100.0)
        try:
            manager.add_callback(ctx.context_id, None)
            assert False, "Expected InvalidCallbackError"
        except InvalidCallbackError as e:
            assert "Callback cannot be None" in str(e)

    def test_invalid_deadline_error_message_past(self, manager: TimeoutManager, clock: ManualClock):
        clock.set(50.0)
        try:
            manager.create_root_context(30.0)
            assert False, "Expected InvalidDeadlineError"
        except InvalidDeadlineError as e:
            assert "30.0" in str(e)
            assert "50.0" in str(e)


class TestAdditionalExceptionScenarios:
    def test_add_callback_to_nonexistent_context_raises(self, manager: TimeoutManager):
        def cb(ctx: TimeoutContext) -> None:
            pass
        with pytest.raises(ContextNotFoundError):
            manager.add_callback("nonexistent", cb)

    def test_get_nonexistent_context_returns_none(self, manager: TimeoutManager):
        assert manager.get_context("nonexistent") is None

    def test_is_active_nonexistent_context_returns_false(self, manager: TimeoutManager):
        assert manager.is_active("nonexistent") is False

    def test_cancelled_and_expired_are_mutually_exclusive(self, manager: TimeoutManager, clock: ManualClock):
        ctx = manager.create_root_context(100.0)
        manager.cancel_context(ctx.context_id, "cancelled first")
        clock.set(200.0)
        manager.check_expired()
        info = manager.get_context(ctx.context_id)
        assert info.is_cancelled is True
        assert info.is_expired is False

    def test_expired_and_cancelled_are_mutually_exclusive(self, manager: TimeoutManager, clock: ManualClock):
        ctx = manager.create_root_context(100.0)
        clock.set(100.0)
        manager.check_expired()
        manager.cancel_context(ctx.context_id, "late cancel")
        info = manager.get_context(ctx.context_id)
        assert info.is_expired is True
        assert info.is_cancelled is False
