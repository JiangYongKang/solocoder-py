from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional


@dataclass
class Command:
    name: str
    execute: Callable[[], Any]
    undo: Callable[[], Any]
    description: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Command name cannot be empty")
        if not callable(self.execute):
            raise ValueError("execute must be callable")
        if not callable(self.undo):
            raise ValueError("undo must be callable")


@dataclass
class TransactionGroup:
    name: str
    commands: List[Command] = field(default_factory=list)
    description: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("TransactionGroup name cannot be empty")

    @property
    def size(self) -> int:
        return len(self.commands)

    @property
    def is_empty(self) -> bool:
        return len(self.commands) == 0

    def add_command(self, command: Command) -> None:
        self.commands.append(command)


@dataclass
class UndoRedoState:
    undo_stack: List[Command | TransactionGroup] = field(default_factory=list)
    redo_stack: List[Command | TransactionGroup] = field(default_factory=list)
    active_transaction: Optional[TransactionGroup] = None

    @property
    def can_undo(self) -> bool:
        return len(self.undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        return len(self.redo_stack) > 0

    @property
    def undo_count(self) -> int:
        return len(self.undo_stack)

    @property
    def redo_count(self) -> int:
        return len(self.redo_stack)

    @property
    def has_active_transaction(self) -> bool:
        return self.active_transaction is not None
