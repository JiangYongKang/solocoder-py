from __future__ import annotations


class RegistryError(Exception):
    pass


class ServiceNotFoundError(RegistryError):
    pass


class InstanceNotFoundError(RegistryError):
    pass


class InstanceAlreadyRegisteredError(RegistryError):
    pass


class InvalidConfigError(RegistryError):
    pass
