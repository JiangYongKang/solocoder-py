from __future__ import annotations

import uuid
from collections import deque
from typing import Any, Dict, List, Optional

from .models import (
    Command,
    CommandNotFoundError,
    CommandStatus,
    DuplicateCommandError,
    InvalidTtlError,
)


class CommandQueue:
    def __init__(self) -> None:
        self._queue: deque[str] = deque()
        self._commands: Dict[str, Command] = {}

    def enqueue(
        self,
        payload: Any,
        *,
        command_id: Optional[str] = None,
        ttl: Optional[float] = None,
    ) -> Command:
        cmd_id = command_id or str(uuid.uuid4())

        if ttl is not None and ttl < 0:
            raise InvalidTtlError("TTL cannot be negative")

        if cmd_id in self._commands:
            raise DuplicateCommandError(f"Command with id '{cmd_id}' already exists")

        command = Command(
            id=cmd_id,
            payload=payload,
            ttl=ttl,
        )

        self._commands[cmd_id] = command
        self._queue.append(cmd_id)

        return command

    def _check_expired(self, command: Command) -> bool:
        if command.status == CommandStatus.PENDING and command.is_expired:
            command._mark_ttl_expired()
            return True
        return False

    def dequeue(self) -> Optional[Command]:
        while self._queue:
            cmd_id = self._queue[0]
            command = self._commands.get(cmd_id)

            if command is None:
                self._queue.popleft()
                continue

            if self._check_expired(command):
                self._queue.popleft()
                continue

            if command.status != CommandStatus.PENDING:
                self._queue.popleft()
                continue

            self._queue.popleft()
            command.mark_sent()
            return command

        return None

    def get_command(self, command_id: str) -> Command:
        if command_id not in self._commands:
            raise CommandNotFoundError(f"Command not found: {command_id}")
        return self._commands[command_id]

    def get_status(self, command_id: str) -> CommandStatus:
        command = self.get_command(command_id)
        return command.status

    def list_by_status(self, status: CommandStatus) -> List[Command]:
        result: List[Command] = []
        for command in self._commands.values():
            if command.status == status:
                result.append(command)
        return result

    def mark_delivered(self, command_id: str) -> bool:
        command = self.get_command(command_id)
        return command.mark_delivered()

    def mark_timeout(self, command_id: str) -> bool:
        command = self.get_command(command_id)
        return command.mark_timeout()

    def size(self) -> int:
        count = 0
        for cmd_id in self._queue:
            command = self._commands.get(cmd_id)
            if command is None:
                continue
            if command.status == CommandStatus.PENDING and not command.is_expired:
                count += 1
        return count

    def total_count(self) -> int:
        return len(self._commands)

    def clear(self) -> None:
        self._queue.clear()
        self._commands.clear()
