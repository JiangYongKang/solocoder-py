from __future__ import annotations


class MultiLevelCacheError(Exception):
    pass


class CacheLevelNotFoundError(MultiLevelCacheError):
    pass


class DataSourceError(MultiLevelCacheError):
    pass


class InvalidCapacityError(MultiLevelCacheError):
    pass
