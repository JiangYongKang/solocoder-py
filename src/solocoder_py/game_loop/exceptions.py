from __future__ import annotations


class GameLoopError(Exception):
    pass


class InvalidTimeStepError(GameLoopError):
    pass


class InvalidMaxCatchUpStepsError(GameLoopError):
    pass


class GameLoopNotRunningError(GameLoopError):
    pass


class GameStateNotInterpolableError(GameLoopError):
    pass
