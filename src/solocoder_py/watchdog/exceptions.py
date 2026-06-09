from __future__ import annotations


class WatchdogError(Exception):
    pass


class InvalidConfigError(WatchdogError):
    pass


class EntityNotFoundError(WatchdogError):
    pass


class EntityAlreadyRegisteredError(WatchdogError):
    pass
