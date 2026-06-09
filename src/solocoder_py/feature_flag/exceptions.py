from __future__ import annotations


class FeatureFlagError(Exception):
    pass


class FlagNotFoundError(FeatureFlagError):
    pass


class CyclicDependencyError(FeatureFlagError):
    pass


class InvalidFlagConfigError(FeatureFlagError):
    pass


class DependencyNotFoundError(FeatureFlagError):
    pass


class MissingAttributeError(FeatureFlagError):
    pass
