from __future__ import annotations


class PhoneticError(Exception):
    pass


class EmptyNameError(PhoneticError):
    pass


class NameNotFoundError(PhoneticError):
    pass


class NameExistsError(PhoneticError):
    pass


class InvalidMatchModeError(PhoneticError):
    pass
