from __future__ import annotations

from typing import Generic, TypeVar, Optional, Callable
import time

from .exceptions import GameLoopNotRunningError, GameStateNotInterpolableError
from .models import GameState, InterpolatedState, GameLoopConfig, GameLoopStats

T = TypeVar("T", bound="GameState")
_EPSILON = 1e-9


class FixedTimeStepGameLoop(Generic[T]):
    def __init__(
        self,
        initial_state: T,
        config: Optional[GameLoopConfig] = None,
        time_provider: Optional[Callable[[], float]] = None,
    ) -> None:
        self._config = config or GameLoopConfig()
        self._initial_state: T = initial_state.copy()
        self._state: T = initial_state.copy()
        self._previous_state: T = initial_state.copy()
        self._time_provider = time_provider or time.monotonic
        self._stats = GameLoopStats()
        self._is_running = False
        self._start_time: Optional[float] = None
        self._last_frame_time: Optional[float] = None
        self._supports_interpolation: bool = self._check_interpolation_support()

    def _check_interpolation_support(self) -> bool:
        if not self._config.enable_interpolation:
            return False
        try:
            test_prev = self._state.copy()
            test_curr = self._state.copy()
            test_curr.update(self._config.time_step)
            test_prev.interpolate(test_curr, 0.5)
            return True
        except GameStateNotInterpolableError:
            return False

    @property
    def config(self) -> GameLoopConfig:
        return self._config

    @property
    def stats(self) -> GameLoopStats:
        return self._stats

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def current_state(self) -> T:
        return self._state.copy()

    @property
    def previous_state(self) -> T:
        return self._previous_state.copy()

    def start(self) -> None:
        if self._is_running:
            return
        self._start_time = self._time_provider()
        self._last_frame_time = self._start_time
        self._stats.current_time = 0.0
        self._stats.last_logic_update_time = 0.0
        self._stats.accumulator = 0.0
        self._is_running = True

    def stop(self) -> None:
        self._is_running = False
        self._start_time = None
        self._last_frame_time = None

    def reset(self, new_state: Optional[T] = None) -> None:
        self._is_running = False
        if new_state is not None:
            self._initial_state = new_state.copy()
            self._state = new_state.copy()
            self._previous_state = new_state.copy()
        else:
            self._state = self._initial_state.copy()
            self._previous_state = self._initial_state.copy()
        self._start_time = None
        self._last_frame_time = None
        self._stats.reset()
        self._supports_interpolation = self._check_interpolation_support()

    def tick(self) -> InterpolatedState[T]:
        if not self._is_running:
            raise GameLoopNotRunningError(
                "Game loop is not running. Call start() first."
            )

        assert self._start_time is not None
        assert self._last_frame_time is not None

        now = self._time_provider()
        frame_time = now - self._last_frame_time
        self._last_frame_time = now

        self._stats.current_time = now - self._start_time
        self._stats.total_frames += 1
        self._stats.steps_this_frame = 0
        self._stats.is_catching_up = False
        catch_up_event_recorded = False

        self._stats.accumulator += frame_time

        max_catch_up_time = self._config.max_catch_up_steps * self._config.time_step
        frame_skip_threshold = max_catch_up_time * 2
        if self._stats.accumulator > frame_skip_threshold + _EPSILON:
            self._stats.frame_skips += 1
            self._stats.accumulator = self._config.time_step

        has_updates = self._stats.accumulator >= self._config.time_step - _EPSILON
        if has_updates:
            self._previous_state = self._state.copy()

        while self._stats.accumulator >= self._config.time_step - _EPSILON:
            self._state.update(self._config.time_step)
            self._stats.accumulator -= self._config.time_step
            self._stats.total_logic_updates += 1
            self._stats.steps_this_frame += 1
            self._stats.last_logic_update_time = self._stats.current_time

            if self._stats.steps_this_frame > 1:
                self._stats.is_catching_up = True
                if not catch_up_event_recorded:
                    self._stats.catch_up_events += 1
                    catch_up_event_recorded = True

            if self._stats.steps_this_frame >= self._config.max_catch_up_steps:
                self._stats.accumulator = 0.0
                break

        if self._stats.accumulator < 0.0:
            self._stats.accumulator = 0.0

        alpha = self._stats.accumulator / self._config.time_step
        alpha = max(0.0, min(1.0, alpha))

        if self._config.enable_interpolation and self._supports_interpolation:
            if alpha <= 0.0:
                _interpolated = self._previous_state.copy()
            elif alpha >= 1.0:
                _interpolated = self._state.copy()
            else:
                _interpolated = self._previous_state.interpolate(
                    self._state, alpha
                )
            return InterpolatedState(
                state=self._state.copy(),
                alpha=alpha,
                _interpolated=_interpolated,
            )
        else:
            return InterpolatedState(
                state=self._state.copy(),
                alpha=1.0,
                _interpolated=self._state.copy(),
            )
