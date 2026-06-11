from __future__ import annotations

from typing import Optional

from .clock import Clock, SystemClock
from .exceptions import ReorderBufferOverflowError
from .models import Message, ReorderConfig


class ReorderBuffer:
    def __init__(
        self,
        config: Optional[ReorderConfig] = None,
        clock: Optional[Clock] = None,
        initial_next_expected: int = 0,
    ) -> None:
        self._config = config or ReorderConfig()
        self._clock = clock or SystemClock()
        self._next_expected: int = initial_next_expected
        self._buffer: dict[int, Message] = {}
        self._first_gap_detected_at: Optional[float] = None

    @property
    def next_expected(self) -> int:
        return self._next_expected

    @property
    def buffer_size(self) -> int:
        return len(self._buffer)

    @property
    def max_buffer_size(self) -> int:
        return self._config.max_buffer_size

    def _seq_diff(self, a: int, b: int) -> int:
        max_seq = self._config.max_sequence
        half = (max_seq + 1) // 2
        diff = (a - b) % (max_seq + 1)
        if diff > half:
            diff -= (max_seq + 1)
        return diff

    def _seq_greater(self, a: int, b: int) -> bool:
        return self._seq_diff(a, b) > 0

    def _seq_greater_or_equal(self, a: int, b: int) -> bool:
        return self._seq_diff(a, b) >= 0

    def _increment_seq(self, seq: int) -> int:
        return (seq + 1) % (self._config.max_sequence + 1)

    def receive(self, message: Message) -> list[Message]:
        if self._seq_greater_or_equal(message.sequence, self._next_expected) is False:
            return []

        if message.sequence == self._next_expected:
            return self._deliver_contiguous(message)

        if self.buffer_size >= self._config.max_buffer_size:
            raise ReorderBufferOverflowError(self.buffer_size)

        self._buffer[message.sequence] = message
        if self._first_gap_detected_at is None:
            self._first_gap_detected_at = self._clock.now()

        return []

    def _deliver_contiguous(self, first_message: Message) -> list[Message]:
        delivered: list[Message] = [first_message]
        current = self._increment_seq(first_message.sequence)

        while current in self._buffer:
            delivered.append(self._buffer.pop(current))
            current = self._increment_seq(current)

        self._next_expected = current
        self._first_gap_detected_at = None if not self._buffer else self._clock.now()

        return delivered

    def check_timeout(self) -> list[Message]:
        if not self._buffer or self._first_gap_detected_at is None:
            return []

        elapsed = self._clock.now() - self._first_gap_detected_at
        if elapsed < self._config.wait_timeout:
            return []

        return self._skip_gap_and_deliver()

    def _skip_gap_and_deliver(self) -> list[Message]:
        if not self._buffer:
            return []

        min_seq = min(self._buffer.keys(), key=lambda s: self._seq_diff(s, self._next_expected))

        delivered: list[Message] = []
        current = min_seq
        while current in self._buffer:
            delivered.append(self._buffer.pop(current))
            current = self._increment_seq(current)

        self._next_expected = current
        self._first_gap_detected_at = None if not self._buffer else self._clock.now()

        return delivered

    def force_flush(self) -> list[Message]:
        if not self._buffer:
            return []

        sorted_seqs = sorted(self._buffer.keys(), key=lambda s: self._seq_diff(s, self._next_expected))
        delivered = [self._buffer[seq] for seq in sorted_seqs]
        self._buffer.clear()
        self._first_gap_detected_at = None
        if delivered:
            last = delivered[-1]
            self._next_expected = self._increment_seq(last.sequence)
        return delivered

    def reset(self, next_expected: int = 0) -> None:
        self._next_expected = next_expected
        self._buffer.clear()
        self._first_gap_detected_at = None
