from __future__ import annotations


class NotificationFanoutError(Exception):
    pass


class InvalidChannelConfigError(NotificationFanoutError):
    pass


class UnknownChannelError(NotificationFanoutError):
    def __init__(self, channel_name: str) -> None:
        self.channel_name = channel_name
        super().__init__(f"Unknown channel: {channel_name}")


class ChannelTimeoutError(NotificationFanoutError):
    def __init__(self, channel_name: str, timeout: float) -> None:
        self.channel_name = channel_name
        self.timeout = timeout
        super().__init__(f"Channel '{channel_name}' timed out after {timeout}s")


class FanoutExecutionError(NotificationFanoutError):
    pass
