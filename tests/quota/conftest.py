from datetime import datetime

from solocoder_py.quota import ManualClock, QuotaManager


def make_manager(clock: ManualClock | None = None) -> QuotaManager:
    if clock is None:
        clock = ManualClock(datetime(2025, 1, 1, 12, 0, 0))
    return QuotaManager(_clock=clock)
