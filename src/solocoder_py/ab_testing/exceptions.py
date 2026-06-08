from __future__ import annotations


class ABTestingError(Exception):
    pass


class ExperimentNotFoundError(ABTestingError):
    pass


class ExperimentAlreadyExistsError(ABTestingError):
    pass


class InvalidTrafficPercentageError(ABTestingError):
    pass


class TrafficOverflowError(ABTestingError):
    pass


class InvalidExperimentStatusError(ABTestingError):
    pass


class MutexGroupNotFoundError(ABTestingError):
    pass
