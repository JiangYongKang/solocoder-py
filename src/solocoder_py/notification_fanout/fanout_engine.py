from __future__ import annotations

import threading
import time
from typing import Callable, Optional

from .channel import NotificationChannel
from .exceptions import (
    ChannelTimeoutError,
    FanoutExecutionError,
    InvalidChannelConfigError,
    UnknownChannelError,
)
from .models import (
    ChannelAttempt,
    ChannelConfig,
    ChannelDeliveryStatus,
    ChannelResult,
    FanoutResult,
    Notification,
)


class FanoutEngine:
    def __init__(
        self,
        channels: Optional[dict[str, NotificationChannel]] = None,
        channel_configs: Optional[dict[str, ChannelConfig]] = None,
        max_workers: int = 10,
        time_provider: Optional[Callable[[], float]] = None,
        sleeper: Optional[Callable[[float], None]] = None,
    ) -> None:
        self._channels: dict[str, NotificationChannel] = {}
        self._channel_configs: dict[str, ChannelConfig] = {}
        self._max_workers = max_workers
        self._time_provider = time_provider or time.monotonic
        self._sleeper = sleeper or time.sleep

        if channels:
            for name, ch in channels.items():
                self.register_channel(
                    name, ch, channel_configs.get(name) if channel_configs else None
                )

    @property
    def registered_channels(self) -> list[str]:
        return list(self._channels.keys())

    @staticmethod
    def _validate_config_name(config_channel_name: str, expected_name: str) -> None:
        if config_channel_name != expected_name:
            raise InvalidChannelConfigError(
                f"Config channel_name '{config_channel_name}' does not match "
                f"registered channel name '{expected_name}'"
            )

    def register_channel(
        self,
        name: str,
        channel: NotificationChannel,
        config: Optional[ChannelConfig] = None,
    ) -> None:
        if config is not None:
            self._validate_config_name(config.channel_name, name)
        self._channels[name] = channel
        self._channel_configs[name] = config or ChannelConfig(channel_name=name)

    def get_channel(self, name: str) -> NotificationChannel:
        if name not in self._channels:
            raise UnknownChannelError(name)
        return self._channels[name]

    def get_channel_config(self, name: str) -> ChannelConfig:
        if name not in self._channel_configs:
            raise UnknownChannelError(name)
        return self._channel_configs[name]

    def set_channel_config(self, name: str, config: ChannelConfig) -> None:
        if name not in self._channels:
            raise UnknownChannelError(name)
        self._validate_config_name(config.channel_name, name)
        self._channel_configs[name] = config

    def fanout(
        self,
        notification: Notification,
        target_channels: Optional[list[str]] = None,
    ) -> FanoutResult:
        if target_channels is None:
            target_channels = list(self._channels.keys())

        for ch_name in target_channels:
            if ch_name not in self._channels:
                raise UnknownChannelError(ch_name)

        if not target_channels:
            raise FanoutExecutionError("No target channels specified for fanout")

        start_time = self._time_provider()
        channel_results: dict[str, ChannelResult] = {}

        results_lock = threading.Lock()
        threads: list[threading.Thread] = []

        def _worker(ch_name: str) -> None:
            try:
                result = self._deliver_with_retries(ch_name, notification)
            except BaseException as exc:
                result = ChannelResult(
                    channel_name=ch_name,
                    status=ChannelDeliveryStatus.FAILED,
                    attempts=0,
                    attempts_detail=[],
                    final_error=exc if isinstance(exc, Exception) else Exception(str(exc)),
                    total_duration=0.0,
                )
            with results_lock:
                channel_results[ch_name] = result

        for ch_name in target_channels:
            t = threading.Thread(target=_worker, args=(ch_name,), daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        total_duration = self._time_provider() - start_time
        return FanoutResult(
            notification_id=notification.notification_id,
            channel_results=channel_results,
            total_duration=total_duration,
        )

    def _deliver_with_retries(
        self,
        channel_name: str,
        notification: Notification,
    ) -> ChannelResult:
        channel = self._channels[channel_name]
        config = self._channel_configs[channel_name]
        attempts_detail: list[ChannelAttempt] = []
        start_time = self._time_provider()
        last_error: Optional[Exception] = None
        final_status: Optional[ChannelDeliveryStatus] = None

        delivered_event = threading.Event()
        delivery_lock = threading.Lock()
        error_slot: list[Optional[BaseException]] = [None]

        for attempt in range(1, config.max_attempts + 1):
            delay = config.calculate_delay(attempt)
            if delay > 0:
                self._sleeper(delay)

            attempt_start = self._time_provider()
            attempt_success = False
            attempt_error: Optional[Exception] = None

            if delivered_event.is_set():
                attempt_success = True
                final_status = ChannelDeliveryStatus.SUCCESS
                attempt_duration = self._time_provider() - attempt_start
                attempts_detail.append(
                    ChannelAttempt(
                        attempt_number=attempt,
                        executed_at=attempt_start,
                        success=True,
                        error=None,
                        duration=attempt_duration,
                    )
                )
                break

            try:
                self._deliver_with_timeout(
                    channel,
                    notification,
                    config.timeout,
                    delivered_event,
                    delivery_lock,
                    error_slot,
                )
                attempt_success = True
                final_status = ChannelDeliveryStatus.SUCCESS
            except ChannelTimeoutError as exc:
                attempt_error = exc
                last_error = exc
                final_status = ChannelDeliveryStatus.TIMEOUT
            except Exception as exc:
                attempt_error = exc
                last_error = exc
                final_status = ChannelDeliveryStatus.FAILED

            attempt_duration = self._time_provider() - attempt_start
            attempts_detail.append(
                ChannelAttempt(
                    attempt_number=attempt,
                    executed_at=attempt_start,
                    success=attempt_success,
                    error=attempt_error,
                    duration=attempt_duration,
                )
            )

            if attempt_success:
                break

        total_duration = self._time_provider() - start_time
        return ChannelResult(
            channel_name=channel_name,
            status=final_status or ChannelDeliveryStatus.FAILED,
            attempts=len(attempts_detail),
            attempts_detail=attempts_detail,
            final_error=None if final_status == ChannelDeliveryStatus.SUCCESS else last_error,
            total_duration=total_duration,
        )

    def _deliver_with_timeout(
        self,
        channel: NotificationChannel,
        notification: Notification,
        timeout: float,
        delivered_event: threading.Event,
        delivery_lock: threading.Lock,
        error_slot: list[Optional[BaseException]],
    ) -> None:
        def _target() -> None:
            if delivered_event.is_set():
                return
            with delivery_lock:
                if delivered_event.is_set():
                    return
                try:
                    channel.deliver(notification)
                except BaseException as exc:
                    error_slot[0] = exc
                    return
                delivered_event.set()

        t = threading.Thread(target=_target, daemon=True)
        t.start()
        t.join(timeout=timeout)

        if not t.is_alive():
            if delivered_event.is_set():
                return
            exc = error_slot[0]
            if exc is not None:
                error_slot[0] = None
                if isinstance(exc, Exception):
                    raise exc
                raise Exception(str(exc))
            return

        if delivered_event.is_set():
            return

        raise ChannelTimeoutError(channel.name, timeout)
