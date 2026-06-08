from __future__ import annotations


class LedgerError(Exception):
    pass


class AccountError(LedgerError):
    pass


class AccountNotFoundError(AccountError):
    pass


class AccountExistsError(AccountError):
    pass


class OverdraftError(AccountError):
    pass


class TransactionError(LedgerError):
    pass


class TransactionNotFoundError(TransactionError):
    pass


class TransactionStateError(TransactionError):
    pass


class TransactionBalanceError(TransactionError):
    pass


class DuplicatePostError(TransactionError):
    pass


class EntryValidationError(TransactionError):
    pass
