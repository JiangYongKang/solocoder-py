from __future__ import annotations


class PackingError(Exception):
    pass


class InvalidItemError(PackingError):
    pass


class InvalidBinError(PackingError):
    pass
