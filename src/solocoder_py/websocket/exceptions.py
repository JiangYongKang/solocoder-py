from __future__ import annotations


class WebSocketError(Exception):
    pass


class SessionClosedError(WebSocketError):
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"Session {session_id} is closed")


class SessionNotFoundError(WebSocketError):
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"Session {session_id} not found")


class ConnectionClosedError(WebSocketError):
    pass


class HeartbeatTimeoutError(WebSocketError):
    def __init__(self, missed_pongs: int) -> None:
        self.missed_pongs = missed_pongs
        super().__init__(f"Heartbeat timed out after {missed_pongs} missed pongs")


class ReconnectionFailedError(WebSocketError):
    def __init__(self, attempts: int) -> None:
        self.attempts = attempts
        super().__init__(f"Reconnection failed after {attempts} attempts")


class ReorderBufferOverflowError(WebSocketError):
    def __init__(self, buffer_size: int) -> None:
        self.buffer_size = buffer_size
        super().__init__(f"Reorder buffer overflow, size={buffer_size}")


class InvalidSequenceError(WebSocketError):
    pass
