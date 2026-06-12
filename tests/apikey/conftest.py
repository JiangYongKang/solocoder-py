from solocoder_py.apikey import APIKeyManager, Clock


class FakeClock(Clock):
    def __init__(self, start_time: float = 1000000.0) -> None:
        self._time = start_time

    def now(self) -> float:
        return self._time

    def advance(self, seconds: float) -> None:
        self._time += seconds

    def set(self, time: float) -> None:
        self._time = time


def make_manager(clock: Clock = None) -> APIKeyManager:
    if clock is None:
        clock = FakeClock()
    return APIKeyManager(clock=clock, prefix_length=8, idle_threshold_days=30, window_seconds=3600)
