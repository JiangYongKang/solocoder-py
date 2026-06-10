from __future__ import annotations

import threading
import time
from typing import Any, Optional

from .exceptions import PartitionNotFoundError
from .models import Message
from .partitioner import Partitioner


class PartitionedTopic:
    def __init__(self, name: str, num_partitions: int) -> None:
        if num_partitions <= 0:
            raise ValueError("num_partitions must be positive")
        if not name:
            raise ValueError("topic name must not be empty")
        self._name = name
        self._num_partitions = num_partitions
        self._partitioner = Partitioner(num_partitions)
        self._partitions: list[list[Message]] = [[] for _ in range(num_partitions)]
        self._next_offsets: list[int] = [0] * num_partitions
        self._lock = threading.RLock()

    @property
    def name(self) -> str:
        return self._name

    @property
    def num_partitions(self) -> int:
        return self._num_partitions

    @property
    def partitioner(self) -> Partitioner:
        return self._partitioner

    def produce(self, key: str, value: Any, timestamp: Optional[float] = None) -> Message:
        partition_id = self._partitioner.partition(key)
        return self._produce_to_partition(partition_id, key, value, timestamp)

    def produce_to_partition(
        self, partition_id: int, key: str, value: Any, timestamp: Optional[float] = None
    ) -> Message:
        if partition_id < 0 or partition_id >= self._num_partitions:
            raise PartitionNotFoundError(
                f"partition {partition_id} not found, valid range: [0, {self._num_partitions})"
            )
        return self._produce_to_partition(partition_id, key, value, timestamp)

    def _produce_to_partition(
        self, partition_id: int, key: str, value: Any, timestamp: Optional[float]
    ) -> Message:
        with self._lock:
            offset = self._next_offsets[partition_id]
            msg = Message(
                offset=offset,
                key=key,
                value=value,
                partition_id=partition_id,
                timestamp=timestamp if timestamp is not None else time.time(),
            )
            self._partitions[partition_id].append(msg)
            self._next_offsets[partition_id] = offset + 1
            return msg

    def get_messages(self, partition_id: int, start_offset: int, max_count: int = 1) -> list[Message]:
        if partition_id < 0 or partition_id >= self._num_partitions:
            raise PartitionNotFoundError(
                f"partition {partition_id} not found, valid range: [0, {self._num_partitions})"
            )
        if max_count <= 0:
            raise ValueError("max_count must be positive")
        with self._lock:
            partition = self._partitions[partition_id]
            if start_offset < 0:
                start_offset = 0
            if start_offset >= len(partition):
                return []
            end = min(start_offset + max_count, len(partition))
            return list(partition[start_offset:end])

    def get_latest_offset(self, partition_id: int) -> int:
        if partition_id < 0 or partition_id >= self._num_partitions:
            raise PartitionNotFoundError(
                f"partition {partition_id} not found, valid range: [0, {self._num_partitions})"
            )
        with self._lock:
            return self._next_offsets[partition_id] - 1 if self._next_offsets[partition_id] > 0 else -1

    def get_partition_size(self, partition_id: int) -> int:
        if partition_id < 0 or partition_id >= self._num_partitions:
            raise PartitionNotFoundError(
                f"partition {partition_id} not found, valid range: [0, {self._num_partitions})"
            )
        with self._lock:
            return len(self._partitions[partition_id])
