from __future__ import annotations


class LoadBalancerError(Exception):
    pass


class InvalidConfigError(LoadBalancerError):
    pass


class InstanceNotFoundError(LoadBalancerError):
    pass


class InstanceAlreadyRegisteredError(LoadBalancerError):
    pass


class NoAvailableInstanceError(LoadBalancerError):
    pass


class ConnectionLeakError(LoadBalancerError):
    pass
