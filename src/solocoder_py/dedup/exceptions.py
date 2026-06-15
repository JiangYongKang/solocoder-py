from __future__ import annotations


class DedupError(Exception):
    pass


class InvalidConfigError(DedupError):
    pass


class EmptyMatchKeysError(InvalidConfigError):
    pass


class InvalidThresholdError(InvalidConfigError):
    pass


class UnknownStrategyError(InvalidConfigError):
    pass


class MergeConflictError(DedupError):
    pass
