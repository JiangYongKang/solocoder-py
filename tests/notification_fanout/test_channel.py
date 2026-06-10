from __future__ import annotations

import pytest

from solocoder_py.notification_fanout import InMemoryChannel, Notification


class TestInMemoryChannel:
    def _make_notice(self, nid: str = "n1") -> Notification:
        return Notification(
            notification_id=nid, title="t", content="c", recipient="u"
        )

    def test_name_property(self):
        ch = InMemoryChannel("email")
        assert ch.name == "email"

    def test_successful_delivery(self):
        ch = InMemoryChannel("email")
        notice = self._make_notice()
        ch.deliver(notice)
        assert ch.delivered_count == 1
        assert ch.delivered[0] is notice

    def test_multiple_deliveries(self):
        ch = InMemoryChannel("email")
        for i in range(3):
            ch.deliver(self._make_notice(f"n{i}"))
        assert ch.delivered_count == 3
        assert [n.notification_id for n in ch.delivered] == ["n0", "n1", "n2"]

    def test_delivered_is_snapshot(self):
        ch = InMemoryChannel("email")
        ch.deliver(self._make_notice("n1"))
        snap = ch.delivered
        ch.deliver(self._make_notice("n2"))
        assert len(snap) == 1
        assert ch.delivered_count == 2

    def test_fail_next_n_simulation(self):
        ch = InMemoryChannel("sms")
        ch.set_fail_next_n(2)
        with pytest.raises(RuntimeError):
            ch.deliver(self._make_notice("n1"))
        with pytest.raises(RuntimeError):
            ch.deliver(self._make_notice("n2"))
        ch.deliver(self._make_notice("n3"))
        assert ch.delivered_count == 1
        assert ch.failure_count == 2

    def test_reset_clears_state(self):
        ch = InMemoryChannel("x")
        ch.set_fail_next_n(1)
        with pytest.raises(RuntimeError):
            ch.deliver(self._make_notice())
        ch.set_delay(0.01)
        ch.reset()
        ch.deliver(self._make_notice())
        assert ch.delivered_count == 1
        assert ch.failure_count == 0
