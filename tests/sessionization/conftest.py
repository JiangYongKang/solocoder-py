from datetime import datetime

from solocoder_py.sessionization import ManualClock, Sessionizer


def make_sessionizer(
    idle_threshold: float = 300.0,
    merge_threshold: float = 0.0,
    timeout: float = 1800.0,
    clock: ManualClock | None = None,
) -> Sessionizer:
    if clock is None:
        clock = ManualClock(datetime(2025, 1, 1, 12, 0, 0))
    return Sessionizer(
        idle_threshold=idle_threshold,
        merge_threshold=merge_threshold,
        timeout=timeout,
        _clock=clock,
    )
