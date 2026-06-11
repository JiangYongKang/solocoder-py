from __future__ import annotations

from typing import Any, List

from .exceptions import (
    CommandExecutionError,
    NoActiveTransactionError,
    RedoExecutionError,
    RedoStackEmptyError,
    TransactionAlreadyActiveError,
    UndoExecutionError,
    UndoStackEmptyError,
)
from .models import Command, TransactionGroup, UndoRedoState


class UndoRedoStack:
    def __init__(self) -> None:
        self._state: UndoRedoState = UndoRedoState()

    @property
    def state(self) -> UndoRedoState:
        return self._state

    @property
    def can_undo(self) -> bool:
        return self._state.can_undo

    @property
    def can_redo(self) -> bool:
        return self._state.can_redo

    @property
    def undo_count(self) -> int:
        return self._state.undo_count

    @property
    def redo_count(self) -> int:
        return self._state.redo_count

    def execute(self, command: Command) -> Any:
        if not isinstance(command, Command):
            raise TypeError("command must be an instance of Command")

        result = self._execute_command(command)

        if self._state.has_active_transaction:
            self._state.active_transaction.add_command(command)
        else:
            self._state.undo_stack.append(command)
            self._clear_redo_stack()

        return result

    def _execute_command(self, command: Command) -> Any:
        try:
            return command.execute()
        except Exception as e:
            raise CommandExecutionError(
                f"Failed to execute command '{command.name}': {e}"
            ) from e

    def _undo_command(self, command: Command) -> Any:
        try:
            return command.undo()
        except Exception as e:
            raise UndoExecutionError(
                f"Failed to undo command '{command.name}': {e}"
            ) from e

    def _redo_command(self, command: Command) -> Any:
        try:
            return command.execute()
        except Exception as e:
            raise RedoExecutionError(
                f"Failed to redo command '{command.name}': {e}"
            ) from e

    def undo(self) -> None:
        if not self.can_undo:
            raise UndoStackEmptyError("Cannot undo: undo stack is empty")

        item = self._state.undo_stack.pop()

        try:
            if isinstance(item, TransactionGroup):
                self._undo_transaction_group(item)
            else:
                self._undo_command(item)
        except Exception:
            self._state.undo_stack.append(item)
            raise

        self._state.redo_stack.append(item)

    def _undo_transaction_group(self, group: TransactionGroup) -> None:
        for command in reversed(group.commands):
            self._undo_command(command)

    def redo(self) -> None:
        if not self.can_redo:
            raise RedoStackEmptyError("Cannot redo: redo stack is empty")

        item = self._state.redo_stack.pop()

        try:
            if isinstance(item, TransactionGroup):
                self._redo_transaction_group(item)
            else:
                self._redo_command(item)
        except Exception:
            self._state.redo_stack.append(item)
            raise

        self._state.undo_stack.append(item)

    def _redo_transaction_group(self, group: TransactionGroup) -> None:
        for command in group.commands:
            self._redo_command(command)

    def begin_transaction(self, name: str, description: str = "") -> None:
        if self._state.has_active_transaction:
            raise TransactionAlreadyActiveError(
                "Cannot begin transaction: a transaction is already active"
            )
        self._state.active_transaction = TransactionGroup(
            name=name, description=description
        )

    def commit_transaction(self) -> None:
        if not self._state.has_active_transaction:
            raise NoActiveTransactionError(
                "Cannot commit transaction: no active transaction"
            )

        transaction = self._state.active_transaction
        self._state.active_transaction = None

        if not transaction.is_empty:
            self._state.undo_stack.append(transaction)
            self._clear_redo_stack()

    def rollback_transaction(self) -> None:
        if not self._state.has_active_transaction:
            raise NoActiveTransactionError(
                "Cannot rollback transaction: no active transaction"
            )

        transaction = self._state.active_transaction
        self._state.active_transaction = None

        for command in reversed(transaction.commands):
            self._undo_command(command)

    def _clear_redo_stack(self) -> None:
        self._state.redo_stack.clear()

    def clear(self) -> None:
        self._state.undo_stack.clear()
        self._state.redo_stack.clear()
        self._state.active_transaction = None
