from __future__ import annotations


class CanaryError(Exception):
    pass


class ReleaseNotFoundError(CanaryError):
    pass


class ReleaseAlreadyExistsError(CanaryError):
    pass


class InvalidTrafficPercentageError(CanaryError):
    pass


class InvalidReleasePhaseError(CanaryError):
    pass


class VersionNotFoundError(CanaryError):
    pass


class InvalidMetricsThresholdError(CanaryError):
    pass


class RollbackNotAllowedError(CanaryError):
    pass
