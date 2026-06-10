from __future__ import annotations


class ConfigHotReloadError(Exception):
    pass


class VersionNotFoundError(ConfigHotReloadError):
    pass


class NoActiveVersionError(ConfigHotReloadError):
    pass


class ListenerError(ConfigHotReloadError):
    pass


class EmptyConfigError(ConfigHotReloadError):
    pass
