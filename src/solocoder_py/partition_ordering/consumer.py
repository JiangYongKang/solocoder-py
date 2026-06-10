from __future__ import annotations

import threading
from typing import Optional

from .exceptions import (
    NotAssignedPartitionError,
    OffsetOutOfRangeError,
    OutOfOrderCommitError,
    PartitionAlreadyAssignedError,
    PartitionNotFoundError,
    UnknownPartitionError,
)
from .models import ConsumerState, Message, PartitionOffset
from .topic import PartitionedTopic


class OrderedPartitionConsumer:
    def __init__(self, consumer_id: str, topic: PartitionedTopic) -> None:
        if not consumer_id:
            raise ValueError("consumer_id must not be empty")
        self._consumer_id = consumer_id
        self._topic = topic
        self._state = ConsumerState(consumer_id=consumer_id)
        self._lock = threading.RLock()

    @property
    def consumer_id(self) -> str:
        return self._consumer_id

    @property
    def topic(self) -> PartitionedTopic:
        return self._topic

    @property
    def assigned_partitions(self) -> set[int]:
        with self._lock:
            return set(self._state.assigned_partitions)

    def assign_partition(self, partition_id: int, initial_committed_offset: Optional[int] = None) -> None:
        if partition_id < 0 or partition_id >= self._topic.num_partitions:
            raise PartitionNotFoundError(
                f"partition {partition_id} not found, valid range: [0, {self._topic.num_partitions})"
            )
        with self._lock:
            if partition_id in self._state.assigned_partitions:
                raise PartitionAlreadyAssignedError(
                    f"partition {partition_id} is already assigned to consumer '{self._consumer_id}'"
                )
            self._state.assigned_partitions.add(partition_id)
            offset = self._state.get_offset(partition_id)
            if initial_committed_offset is not None:
                if initial_committed_offset < -1:
                    raise OffsetOutOfRangeError(
                        f"initial_committed_offset must be >= -1, got {initial_committed_offset}"
                    )
                offset.committed_offset = initial_committed_offset
                offset.last_pulled_offset = initial_committed_offset
            if partition_id not in self._state.in_flight_messages:
                self._state.in_flight_messages[partition_id] = []

    def revoke_partition(self, partition_id: int) -> list[Message]:
        with self._lock:
            if partition_id not in self._state.assigned_partitions:
                return []
            self._state.assigned_partitions.discard(partition_id)
            uncommitted = self._state.in_flight_messages.pop(partition_id, [])
            if partition_id in self._state.partition_offsets:
                offset = self._state.partition_offsets[partition_id]
                offset.last_pulled_offset = offset.committed_offset
            return list(uncommitted)

    def poll(self, partition_id: int, max_messages: int = 1) -> list[Message]:
        if max_messages <= 0:
            raise ValueError("max_messages must be positive")
        with self._lock:
            if partition_id not in self._state.assigned_partitions:
                raise NotAssignedPartitionError(
                    f"partition {partition_id} is not assigned to consumer '{self._consumer_id}'"
                )

            in_flight = self._state.in_flight_messages.get(partition_id, [])
            if in_flight:
                return []

            offset = self._state.get_offset(partition_id)
            next_offset = offset.committed_offset + 1

            messages = self._topic.get_messages(partition_id, next_offset, max_messages)
            if messages:
                offset.last_pulled_offset = messages[-1].offset
                self._state.in_flight_messages[partition_id] = list(messages)
            return list(messages)

    def poll_all(self, max_messages_per_partition: int = 1) -> dict[int, list[Message]]:
        result: dict[int, list[Message]] = {}
        with self._lock:
            partitions = list(self._state.assigned_partitions)
        for pid in partitions:
            msgs = self.poll(pid, max_messages_per_partition)
            if msgs:
                result[pid] = msgs
        return result

    def commit(self, partition_id: int, offset: int) -> None:
        with self._lock:
            if partition_id not in self._state.assigned_partitions:
                raise NotAssignedPartitionError(
                    f"partition {partition_id} is not assigned to consumer '{self._consumer_id}'"
                )

            partition_offset = self._state.get_offset(partition_id)
            expected_offset = partition_offset.committed_offset + 1

            if offset != expected_offset:
                raise OutOfOrderCommitError(
                    f"Cannot commit offset {offset} for partition {partition_id}: "
                    f"expected {expected_offset} (last committed: {partition_offset.committed_offset})"
                )

            in_flight = self._state.in_flight_messages.get(partition_id, [])
            if not in_flight or in_flight[0].offset != offset:
                raise OutOfOrderCommitError(
                    f"Cannot commit offset {offset} for partition {partition_id}: "
                    f"message not in-flight at expected position"
                )

            in_flight.pop(0)
            partition_offset.committed_offset = offset

            latest = self._topic.get_latest_offset(partition_id)
            if partition_offset.committed_offset > latest:
                raise OffsetOutOfRangeError(
                    f"Committed offset {partition_offset.committed_offset} exceeds "
                    f"latest available offset {latest} for partition {partition_id}"
                )

    def get_committed_offset(self, partition_id: int) -> int:
        with self._lock:
            if partition_id not in self._state.assigned_partitions:
                raise NotAssignedPartitionError(
                    f"partition {partition_id} is not assigned to consumer '{self._consumer_id}'"
                )
            return self._state.get_offset(partition_id).committed_offset

    def get_stored_committed_offset(self, partition_id: int) -> int:
        with self._lock:
            if partition_id in self._state.partition_offsets:
                return self._state.partition_offsets[partition_id].committed_offset
            return -1

    def get_in_flight_count(self, partition_id: int) -> int:
        with self._lock:
            if partition_id not in self._state.assigned_partitions:
                raise NotAssignedPartitionError(
                    f"partition {partition_id} is not assigned to consumer '{self._consumer_id}'"
                )
            return len(self._state.in_flight_messages.get(partition_id, []))

    def seek(self, partition_id: int, offset: int) -> None:
        with self._lock:
            if partition_id not in self._state.assigned_partitions:
                raise NotAssignedPartitionError(
                    f"partition {partition_id} is not assigned to consumer '{self._consumer_id}'"
                )
            if offset < -1:
                raise OffsetOutOfRangeError(f"offset must be >= -1, got {offset}")
            latest = self._topic.get_latest_offset(partition_id)
            if offset > latest:
                raise OffsetOutOfRangeError(
                    f"offset {offset} exceeds latest available offset {latest}"
                )
            partition_offset = self._state.get_offset(partition_id)
            partition_offset.committed_offset = offset
            partition_offset.last_pulled_offset = offset
            self._state.in_flight_messages[partition_id] = []
