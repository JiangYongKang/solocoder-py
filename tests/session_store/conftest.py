from solocoder_py.session_store import (
    Clock,
    EvictionStrategy,
    SessionCreateConfig,
    SessionStore,
)


class FakeClock(Clock):
    def __init__(self, start_time: float = 1000000.0) -> None:
        self._time = start_time

    def now(self) -> float:
        return self._time

    def advance(self, seconds: float) -> None:
        self._time += seconds

    def set(self, time: float) -> None:
        self._time = time


def make_config(
    ttl: float = 3600.0,
    idle_timeout: float = 1800.0,
    max_concurrent_sessions: int = 5,
    eviction_strategy: EvictionStrategy = EvictionStrategy.EVICT_OLDEST,
) -> SessionCreateConfig:
    return SessionCreateConfig(
        ttl=ttl,
        idle_timeout=idle_timeout,
        max_concurrent_sessions=max_concurrent_sessions,
        eviction_strategy=eviction_strategy,
    )


def make_store(
    config: SessionCreateConfig = None,
    clock: Clock = None,
) -> SessionStore:
    if clock is None:
        clock = FakeClock()
    if config is None:
        config = make_config()
    return SessionStore(default_config=config, clock=clock)
