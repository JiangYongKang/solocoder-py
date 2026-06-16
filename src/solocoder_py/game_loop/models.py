from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Generic, TypeVar

from .exceptions import GameStateNotInterpolableError

T = TypeVar("T", bound="GameState")


class GameState(ABC):
    @abstractmethod
    def update(self, delta_time: float) -> None:
        pass

    def interpolate(self: T, other: T, alpha: float) -> T:
        raise GameStateNotInterpolableError(
            f"{self.__class__.__name__} does not support interpolation. "
            "Override interpolate() method to enable interpolation."
        )

    def copy(self: T) -> T:
        import copy
        return copy.deepcopy(self)


@dataclass
class InterpolatedState(Generic[T]):
    state: T
    alpha: float
    _interpolated: Optional[T] = None

    def get_interpolated(self) -> T:
        if self._interpolated is not None:
            return self._interpolated
        return self.state


@dataclass
class GameLoopConfig:
    time_step: float = 1.0 / 60.0
    max_catch_up_steps: int = 5
    enable_interpolation: bool = True

    def __post_init__(self) -> None:
        from .exceptions import InvalidTimeStepError, InvalidMaxCatchUpStepsError

        if self.time_step <= 0.0:
            raise InvalidTimeStepError(
                f"Time step must be positive, got {self.time_step}"
            )
        if self.max_catch_up_steps <= 0:
            raise InvalidMaxCatchUpStepsError(
                f"Max catch-up steps must be positive, got {self.max_catch_up_steps}"
            )


@dataclass
class GameLoopStats:
    total_logic_updates: int = 0
    total_frames: int = 0
    catch_up_events: int = 0
    frame_skips: int = 0
    accumulator: float = 0.0
    current_time: float = 0.0
    last_logic_update_time: float = 0.0
    steps_this_frame: int = 0
    is_catching_up: bool = False

    def reset(self) -> None:
        self.total_logic_updates = 0
        self.total_frames = 0
        self.catch_up_events = 0
        self.frame_skips = 0
        self.accumulator = 0.0
        self.current_time = 0.0
        self.last_logic_update_time = 0.0
        self.steps_this_frame = 0
        self.is_catching_up = False
