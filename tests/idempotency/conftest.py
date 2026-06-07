from datetime import timedelta

from solocoder_py.idempotency import (
    FailureReplayPolicy,
    IdempotencyStore,
)


def make_store(
    default_ttl: timedelta = timedelta(hours=24),
    failure_replay_policy: FailureReplayPolicy = FailureReplayPolicy.REJECT,
    wait_timeout: timedelta = timedelta(seconds=30),
    wait_poll_interval: timedelta = timedelta(milliseconds=50),
) -> IdempotencyStore:
    return IdempotencyStore(
        default_ttl=default_ttl,
        failure_replay_policy=failure_replay_policy,
        wait_timeout=wait_timeout,
        wait_poll_interval=wait_poll_interval,
    )
