from __future__ import annotations

from collections import deque
from typing import Any, Optional

from .exceptions import ConnectionClosedError
from .models import Message, MessageType


class SimulatedWebSocketConnection:
    def __init__(self, connection_id: str) -> None:
        self._connection_id = connection_id
        self._connected: bool = False
        self._outgoing_messages: deque[Message] = deque()
        self._incoming_messages: deque[Message] = deque()
        self._peer: Optional[SimulatedWebSocketConnection] = None

    @property
    def connection_id(self) -> str:
        return self._connection_id

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def outgoing_queue_size(self) -> int:
        return len(self._outgoing_messages)

    @property
    def incoming_queue_size(self) -> int:
        return len(self._incoming_messages)

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False
        if self._peer and self._peer._connected:
            self._peer._connected = False
            self._peer = None
        self._peer = None

    def set_peer(self, peer: SimulatedWebSocketConnection) -> None:
        self._peer = peer
        peer._peer = self

    def send(self, message: Message) -> None:
        if not self._connected:
            raise ConnectionClosedError("Cannot send on closed connection")
        self._outgoing_messages.append(message)
        if self._peer and self._peer._connected:
            self._peer._incoming_messages.append(message)

    def send_data(self, sequence: int, payload: Any, timestamp: float = 0.0) -> None:
        msg = Message(sequence=sequence, payload=payload, type=MessageType.DATA, timestamp=timestamp)
        self.send(msg)

    def send_ping(self) -> None:
        msg = Message(sequence=0, payload=None, type=MessageType.PING)
        self.send(msg)

    def send_pong(self) -> None:
        msg = Message(sequence=0, payload=None, type=MessageType.PONG)
        self.send(msg)

    def send_close(self) -> None:
        msg = Message(sequence=0, payload=None, type=MessageType.CLOSE)
        try:
            self.send(msg)
        except ConnectionClosedError:
            pass
        self.disconnect()

    def receive(self) -> Optional[Message]:
        if not self._incoming_messages:
            return None
        return self._incoming_messages.popleft()

    def receive_all(self) -> list[Message]:
        messages: list[Message] = []
        while self._incoming_messages:
            messages.append(self._incoming_messages.popleft())
        return messages

    def peek_outgoing(self) -> Optional[Message]:
        if not self._outgoing_messages:
            return None
        return self._outgoing_messages[0]

    def pop_outgoing(self) -> Optional[Message]:
        if not self._outgoing_messages:
            return None
        return self._outgoing_messages.popleft()

    def clear_queues(self) -> None:
        self._outgoing_messages.clear()
        self._incoming_messages.clear()


def create_connected_pair(
    client_id: str = "client",
    server_id: str = "server",
) -> tuple[SimulatedWebSocketConnection, SimulatedWebSocketConnection]:
    client = SimulatedWebSocketConnection(client_id)
    server = SimulatedWebSocketConnection(server_id)
    client.set_peer(server)
    client.connect()
    server.connect()
    return client, server
