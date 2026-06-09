from __future__ import annotations


class PointsError(Exception):
    pass


class AccountError(PointsError):
    pass


class AccountNotFoundError(AccountError):
    pass


class AccountExistsError(AccountError):
    pass


class InsufficientPointsError(AccountError):
    pass


class PointsExpiredError(AccountError):
    pass


class InvalidAmountError(AccountError):
    pass


class FreezeNotFoundError(AccountError):
    pass


class FreezeStateError(AccountError):
    pass
