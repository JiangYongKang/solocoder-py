from solocoder_py.idempotency import (
    Clock,
    FailureReplayPolicy,
    IdempotencyStore,
    ManualClock,
    SystemClock,
)


def make_store(
    default_ttl_seconds: float = 86400.0,
    failure_replay_policy: FailureReplayPolicy = FailureReplayPolicy.REJECT,
    wait_timeout_seconds: float = 30.0,
    wait_poll_interval_seconds: float = 0.05,
    clock: Clock | None = None,
) -> IdempotencyStore:
    return IdempotencyStore(
        default_ttl_seconds=default_ttl_seconds,
        failure_replay_policy=failure_replay_policy,
        wait_timeout_seconds=wait_timeout_seconds,
        wait_poll_interval_seconds=wait_poll_interval_seconds,
        _clock=clock if clock is not None else SystemClock(),
    )


def make_manual_clock(start_time: float = 0.0) -> ManualClock:
    return ManualClock(start_time=start_time)
