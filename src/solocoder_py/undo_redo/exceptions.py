from __future__ import annotations


class UndoRedoError(Exception):
    pass


class UndoStackEmptyError(UndoRedoError):
    pass


class RedoStackEmptyError(UndoRedoError):
    pass


class NoActiveTransactionError(UndoRedoError):
    pass


class TransactionAlreadyActiveError(UndoRedoError):
    pass


class CommandExecutionError(UndoRedoError):
    pass


class UndoExecutionError(UndoRedoError):
    pass


class RedoExecutionError(UndoRedoError):
    pass
