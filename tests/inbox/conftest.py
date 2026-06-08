from solocoder_py.inbox import (
    Clock,
    InboxDedupStore,
    ManualClock,
    SystemClock,
)


def make_store(
    max_count: int | None = None,
    max_time_seconds: float | None = None,
    ttl_seconds: float = 3600.0,
    cleanup_interval_seconds: float | None = None,
    clock: Clock | None = None,
) -> InboxDedupStore:
    return InboxDedupStore(
        max_count=max_count,
        max_time_seconds=max_time_seconds,
        ttl_seconds=ttl_seconds,
        cleanup_interval_seconds=cleanup_interval_seconds,
        _clock=clock if clock is not None else SystemClock(),
    )


def make_manual_clock(start_time: float = 0.0) -> ManualClock:
    return ManualClock(start_time=start_time)
