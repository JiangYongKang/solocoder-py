from __future__ import annotations

import pytest
from dataclasses import dataclass

from solocoder_py.game_loop import GameState


@dataclass
class SimpleState(GameState):
    position: float = 0.0
    velocity: float = 1.0

    def update(self, delta_time: float) -> None:
        self.position += self.velocity * delta_time

    def interpolate(self, other: "SimpleState", alpha: float) -> "SimpleState":
        return SimpleState(
            position=self.position + (other.position - self.position) * alpha,
            velocity=self.velocity + (other.velocity - self.velocity) * alpha,
        )


@dataclass
class NonInterpolableState(GameState):
    value: int = 0

    def update(self, delta_time: float) -> None:
        self.value += 1


class MockTimeProvider:
    def __init__(self, start_time: float = 0.0) -> None:
        self._current_time = start_time

    def advance(self, delta: float) -> None:
        self._current_time += delta

    def set_time(self, time: float) -> None:
        self._current_time = time

    def __call__(self) -> float:
        return self._current_time


@pytest.fixture
def simple_state() -> SimpleState:
    return SimpleState(position=0.0, velocity=1.0)


@pytest.fixture
def non_interpolable_state() -> NonInterpolableState:
    return NonInterpolableState(value=0)


@pytest.fixture
def mock_time() -> MockTimeProvider:
    return MockTimeProvider(0.0)
