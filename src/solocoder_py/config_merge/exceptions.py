from __future__ import annotations


class ConfigMergeError(Exception):
    pass


class ConfigTypeConflictError(ConfigMergeError):
    pass


class UnknownArrayMergeStrategyError(ConfigMergeError):
    pass


class CircularReferenceError(ConfigMergeError):
    pass


class InvalidConfigLayerError(ConfigMergeError):
    pass
