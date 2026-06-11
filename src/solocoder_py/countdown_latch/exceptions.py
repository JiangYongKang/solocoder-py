from __future__ import annotations


class CountdownLatchError(Exception):
    pass


class InvalidCountError(CountdownLatchError):
    pass


class LatchTimeoutError(CountdownLatchError):
    pass
