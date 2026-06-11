from __future__ import annotations


class ConnPoolError(Exception):
    pass


class PoolClosedError(ConnPoolError):
    pass


class PoolExhaustedError(ConnPoolError):
    pass


class ConnectionNotFoundError(ConnPoolError):
    pass


class ConnectionClosedError(ConnPoolError):
    pass


class HealthCheckFailedError(ConnPoolError):
    pass
