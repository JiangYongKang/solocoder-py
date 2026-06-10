from __future__ import annotations


class AutocompleteError(Exception):
    pass


class EmptyWordError(AutocompleteError):
    pass


class InvalidWeightError(AutocompleteError):
    pass


class InvalidPrefixError(AutocompleteError):
    pass
