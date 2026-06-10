from __future__ import annotations

import threading
from typing import Callable, Optional

from .consumer import OrderedPartitionConsumer
from .exceptions import (
    ConsumerNotFoundError,
    PartitionAlreadyAssignedError,
    PartitionNotFoundError,
    RebalanceInProgressError,
)
from .models import ConsumerAssignment, RebalanceEvent
from .topic import PartitionedTopic


RebalanceListener = Callable[[RebalanceEvent], None]


class ConsumerGroupCoordinator:
    def __init__(self, group_id: str, topic: PartitionedTopic) -> None:
        if not group_id:
            raise ValueError("group_id must not be empty")
        self._group_id = group_id
        self._topic = topic
        self._consumers: dict[str, OrderedPartitionConsumer] = {}
        self._partition_owner: dict[int, str] = {}
        self._group_committed_offsets: dict[int, int] = {}
        self._generation_id: int = 0
        self._rebalancing: bool = False
        self._rebalance_listeners: dict[str, RebalanceListener] = {}
        self._lock = threading.RLock()

    @property
    def group_id(self) -> str:
        return self._group_id

    @property
    def topic(self) -> PartitionedTopic:
        return self._topic

    @property
    def generation_id(self) -> int:
        with self._lock:
            return self._generation_id

    @property
    def is_rebalancing(self) -> bool:
        with self._lock:
            return self._rebalancing

    def join_group(
        self,
        consumer_id: str,
        listener: Optional[RebalanceListener] = None,
    ) -> OrderedPartitionConsumer:
        if not consumer_id:
            raise ValueError("consumer_id must not be empty")
        with self._lock:
            if self._rebalancing:
                raise RebalanceInProgressError("Cannot join group during rebalance")
            if consumer_id in self._consumers:
                return self._consumers[consumer_id]

            consumer = OrderedPartitionConsumer(consumer_id, self._topic)
            self._consumers[consumer_id] = consumer
            if listener is not None:
                self._rebalance_listeners[consumer_id] = listener

            self._trigger_rebalance()
            return consumer

    def leave_group(self, consumer_id: str) -> None:
        with self._lock:
            if self._rebalancing:
                raise RebalanceInProgressError("Cannot leave group during rebalance")
            if consumer_id not in self._consumers:
                raise ConsumerNotFoundError(f"consumer '{consumer_id}' not found in group")

            consumer = self._consumers.pop(consumer_id)
            self._rebalance_listeners.pop(consumer_id, None)

            for pid in list(consumer.assigned_partitions):
                stored = consumer.get_stored_committed_offset(pid)
                if stored > self._group_committed_offsets.get(pid, -1):
                    self._group_committed_offsets[pid] = stored
                consumer.revoke_partition(pid)
                self._partition_owner.pop(pid, None)

            if self._consumers:
                self._trigger_rebalance()

    def get_consumer(self, consumer_id: str) -> OrderedPartitionConsumer:
        with self._lock:
            if consumer_id not in self._consumers:
                raise ConsumerNotFoundError(f"consumer '{consumer_id}' not found in group")
            return self._consumers[consumer_id]

    def get_partition_owner(self, partition_id: int) -> Optional[str]:
        if partition_id < 0 or partition_id >= self._topic.num_partitions:
            raise PartitionNotFoundError(
                f"partition {partition_id} not found, valid range: [0, {self._topic.num_partitions})"
            )
        with self._lock:
            return self._partition_owner.get(partition_id)

    def get_group_committed_offset(self, partition_id: int) -> int:
        if partition_id < 0 or partition_id >= self._topic.num_partitions:
            raise PartitionNotFoundError(
                f"partition {partition_id} not found, valid range: [0, {self._topic.num_partitions})"
            )
        with self._lock:
            owner = self._partition_owner.get(partition_id)
            if owner and owner in self._consumers:
                consumer = self._consumers[owner]
                if partition_id in consumer.assigned_partitions:
                    return consumer.get_committed_offset(partition_id)
            return self._group_committed_offsets.get(partition_id, -1)

    def get_all_assignments(self) -> list[ConsumerAssignment]:
        with self._lock:
            result = []
            for cid, consumer in self._consumers.items():
                result.append(
                    ConsumerAssignment(
                        consumer_id=cid,
                        partition_ids=sorted(consumer.assigned_partitions),
                    )
                )
            return result

    def _trigger_rebalance(self) -> None:
        self._rebalancing = True
        self._generation_id += 1
        try:
            self._do_rebalance()
        finally:
            self._rebalancing = False

    def _snapshot_offsets(self) -> None:
        for pid, owner_id in self._partition_owner.items():
            if owner_id in self._consumers:
                consumer = self._consumers[owner_id]
                stored = consumer.get_stored_committed_offset(pid)
                if stored > self._group_committed_offsets.get(pid, -1):
                    self._group_committed_offsets[pid] = stored

    def _do_rebalance(self) -> None:
        consumer_ids = sorted(self._consumers.keys())
        num_consumers = len(consumer_ids)
        if num_consumers == 0:
            self._partition_owner.clear()
            return

        self._snapshot_offsets()

        num_partitions = self._topic.num_partitions
        new_owner_map: dict[int, str] = {}

        for pid in range(num_partitions):
            owner_idx = pid % num_consumers
            new_owner_map[pid] = consumer_ids[owner_idx]

        old_owner_map = dict(self._partition_owner)
        revoked_map: dict[str, list[int]] = {cid: [] for cid in consumer_ids}
        assigned_map: dict[str, list[int]] = {cid: [] for cid in consumer_ids}

        for pid, old_owner in old_owner_map.items():
            new_owner = new_owner_map.get(pid)
            if old_owner != new_owner and old_owner in self._consumers:
                revoked_map[old_owner].append(pid)

        for pid, new_owner in new_owner_map.items():
            old_owner = old_owner_map.get(pid)
            if old_owner != new_owner:
                assigned_map[new_owner].append(pid)

        for cid in consumer_ids:
            consumer = self._consumers[cid]
            revoked = sorted(revoked_map.get(cid, []))
            for pid in revoked:
                stored = consumer.get_stored_committed_offset(pid)
                if stored > self._group_committed_offsets.get(pid, -1):
                    self._group_committed_offsets[pid] = stored
                consumer.revoke_partition(pid)

        for cid in consumer_ids:
            consumer = self._consumers[cid]
            assigned = sorted(assigned_map.get(cid, []))
            for pid in assigned:
                current_owner = self._partition_owner.get(pid)
                if current_owner and current_owner != cid:
                    if current_owner in self._consumers:
                        old_consumer = self._consumers[current_owner]
                        if pid in old_consumer.assigned_partitions:
                            stored = old_consumer.get_stored_committed_offset(pid)
                            if stored > self._group_committed_offsets.get(pid, -1):
                                self._group_committed_offsets[pid] = stored
                            old_consumer.revoke_partition(pid)
                    if self._partition_owner.get(pid) == current_owner:
                        del self._partition_owner[pid]

                if pid in consumer.assigned_partitions:
                    raise PartitionAlreadyAssignedError(
                        f"partition {pid} is already assigned to consumer '{cid}' "
                        f"during rebalance, possible ownership conflict"
                    )

                initial_offset = self._group_committed_offsets.get(pid, -1)
                consumer.assign_partition(pid, initial_committed_offset=initial_offset)

        self._partition_owner = new_owner_map

        for cid in consumer_ids:
            listener = self._rebalance_listeners.get(cid)
            if listener is not None:
                event = RebalanceEvent(
                    consumer_id=cid,
                    assigned_partitions=sorted(assigned_map.get(cid, [])),
                    revoked_partitions=sorted(revoked_map.get(cid, [])),
                    generation_id=self._generation_id,
                )
                listener(event)

    def force_rebalance(self) -> int:
        with self._lock:
            if self._rebalancing:
                raise RebalanceInProgressError("Rebalance already in progress")
            self._trigger_rebalance()
            return self._generation_id

    def get_consumer_count(self) -> int:
        with self._lock:
            return len(self._consumers)
