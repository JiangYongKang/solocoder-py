from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional

from .exceptions import (
    ConsumerAlreadyRegisteredError,
    ConsumerNotFoundError,
    EmptyConsumerGroupError,
    InvalidPartitionIdError,
    PartitionNotFoundError,
)
from .models import (
    AssignmentChange,
    Consumer,
    ConsumerStatus,
    Partition,
    RebalanceResult,
)


@dataclass
class PartitionAssignor:
    partitions: dict[int, Partition] = field(default_factory=dict)
    consumers: dict[str, Consumer] = field(default_factory=dict)
    unassigned_partitions: set[int] = field(default_factory=set)
    orphan_partitions: set[int] = field(default_factory=set)
    partition_to_consumer: dict[int, str] = field(default_factory=dict)
    generation_id: int = 0

    def register_consumer(self, consumer_id: str) -> None:
        if consumer_id in self.consumers:
            raise ConsumerAlreadyRegisteredError(
                f"Consumer '{consumer_id}' is already registered"
            )
        self.consumers[consumer_id] = Consumer(consumer_id=consumer_id)

    def unregister_consumer(self, consumer_id: str) -> None:
        if consumer_id not in self.consumers:
            raise ConsumerNotFoundError(
                f"Consumer '{consumer_id}' is not registered"
            )
        consumer = self.consumers[consumer_id]
        for partition_id in consumer.assigned_partitions:
            self.orphan_partitions.add(partition_id)
            if partition_id in self.partition_to_consumer:
                del self.partition_to_consumer[partition_id]
        del self.consumers[consumer_id]

    def add_partitions(self, partition_ids: Iterable[int]) -> None:
        for pid in partition_ids:
            if pid < 0:
                raise InvalidPartitionIdError(
                    f"Partition id '{pid}' must be non-negative"
                )
            if pid not in self.partitions:
                self.partitions[pid] = Partition(partition_id=pid)
                self.unassigned_partitions.add(pid)

    def remove_partitions(self, partition_ids: Iterable[int]) -> None:
        for pid in partition_ids:
            if pid not in self.partitions:
                raise PartitionNotFoundError(
                    f"Partition '{pid}' does not exist"
                )
            if pid in self.partition_to_consumer:
                consumer_id = self.partition_to_consumer[pid]
                if consumer_id in self.consumers:
                    self.consumers[consumer_id].assigned_partitions.discard(pid)
                del self.partition_to_consumer[pid]
            self.unassigned_partitions.discard(pid)
            self.orphan_partitions.discard(pid)
            del self.partitions[pid]

    def get_consumer(self, consumer_id: str) -> Consumer:
        if consumer_id not in self.consumers:
            raise ConsumerNotFoundError(
                f"Consumer '{consumer_id}' is not registered"
            )
        return self.consumers[consumer_id]

    def get_all_consumers(self) -> list[Consumer]:
        return list(self.consumers.values())

    def get_all_partitions(self) -> list[Partition]:
        return list(self.partitions.values())

    def get_unassigned_partitions(self) -> list[int]:
        return sorted(self.unassigned_partitions)

    def get_orphan_partitions(self) -> list[int]:
        return sorted(self.orphan_partitions)

    def get_assignment(self, consumer_id: str) -> list[int]:
        consumer = self.get_consumer(consumer_id)
        return sorted(consumer.assigned_partitions)

    def get_all_assignments(self) -> dict[str, list[int]]:
        return {
            cid: sorted(c.assigned_partitions)
            for cid, c in self.consumers.items()
        }

    def heartbeat(self, consumer_id: str, timestamp: float) -> None:
        consumer = self.get_consumer(consumer_id)
        consumer.last_heartbeat = timestamp

    def check_heartbeat_timeout(self, current_time: float, timeout_seconds: float) -> list[str]:
        timed_out_consumers: list[str] = []
        for cid, consumer in self.consumers.items():
            if consumer.status == ConsumerStatus.ACTIVE:
                if current_time - consumer.last_heartbeat > timeout_seconds:
                    consumer.status = ConsumerStatus.LEAVING
                    timed_out_consumers.append(cid)
        return timed_out_consumers

    def _process_leaving_consumers(self) -> list[int]:
        newly_orphaned: list[int] = []
        consumers_to_remove: list[str] = []
        for cid, consumer in self.consumers.items():
            if consumer.status == ConsumerStatus.LEAVING:
                for partition_id in consumer.assigned_partitions:
                    self.orphan_partitions.add(partition_id)
                    newly_orphaned.append(partition_id)
                    if partition_id in self.partition_to_consumer:
                        del self.partition_to_consumer[partition_id]
                consumer.assigned_partitions.clear()
                consumers_to_remove.append(cid)
        for cid in consumers_to_remove:
            del self.consumers[cid]
        return newly_orphaned

    def rebalance(self) -> RebalanceResult:
        self._process_leaving_consumers()

        if not self.consumers:
            raise EmptyConsumerGroupError(
                "Cannot rebalance with empty consumer group"
            )

        active_consumers = sorted(
            [cid for cid, c in self.consumers.items() if c.status == ConsumerStatus.ACTIVE]
        )
        all_partition_ids = sorted(self.partitions.keys())

        num_consumers = len(active_consumers)
        num_partitions = len(all_partition_ids)

        if num_consumers == 0:
            raise EmptyConsumerGroupError(
                "Cannot rebalance with no active consumers"
            )

        base_count = num_partitions // num_consumers
        extra_count = num_partitions % num_consumers

        target_counts: dict[str, int] = {}
        for i, cid in enumerate(active_consumers):
            target_counts[cid] = base_count + (1 if i < extra_count else 0)

        previous_assignments: dict[str, set[int]] = {
            cid: set(self.consumers[cid].assigned_partitions)
            for cid in active_consumers
        }

        new_assignments: dict[str, set[int]] = {cid: set() for cid in active_consumers}
        partitions_to_reassign: list[int] = []

        for cid in active_consumers:
            prev = previous_assignments.get(cid, set())
            target = target_counts[cid]
            keep_count = min(len(prev), target)
            sorted_prev = sorted(prev)
            for pid in sorted_prev[:keep_count]:
                new_assignments[cid].add(pid)

        for cid in active_consumers:
            prev = previous_assignments.get(cid, set())
            kept = new_assignments[cid]
            for pid in prev:
                if pid not in kept:
                    partitions_to_reassign.append(pid)

        for pid in sorted(self.orphan_partitions):
            if pid in all_partition_ids:
                partitions_to_reassign.append(pid)

        for pid in sorted(self.unassigned_partitions):
            if pid in all_partition_ids and pid not in partitions_to_reassign:
                partitions_to_reassign.append(pid)

        orphan_recovered = sorted(set(self.orphan_partitions) & set(all_partition_ids))
        unassigned_assigned = sorted(set(self.unassigned_partitions) & set(all_partition_ids))
        self.orphan_partitions.clear()
        self.unassigned_partitions.clear()

        consumers_needing_more = []
        for cid in active_consumers:
            deficit = target_counts[cid] - len(new_assignments[cid])
            if deficit > 0:
                consumers_needing_more.extend([cid] * deficit)

        consumers_needing_more.sort()

        partitions_to_reassign.sort()
        for i, pid in enumerate(partitions_to_reassign):
            if i < len(consumers_needing_more):
                cid = consumers_needing_more[i]
                new_assignments[cid].add(pid)

        changes: list[AssignmentChange] = []
        for cid in active_consumers:
            prev = previous_assignments.get(cid, set())
            new = new_assignments[cid]
            assigned = sorted(new - prev)
            revoked = sorted(prev - new)
            if assigned or revoked:
                changes.append(
                    AssignmentChange(
                        consumer_id=cid,
                        assigned_partitions=assigned,
                        revoked_partitions=revoked,
                    )
                )

        for cid in active_consumers:
            consumer = self.consumers[cid]
            consumer.assigned_partitions = set(new_assignments[cid])

        self.partition_to_consumer.clear()
        for cid in active_consumers:
            for pid in new_assignments[cid]:
                self.partition_to_consumer[pid] = cid

        self.generation_id += 1

        assignments_result = {
            cid: sorted(new_assignments[cid]) for cid in active_consumers
        }

        return RebalanceResult(
            generation_id=self.generation_id,
            assignments=assignments_result,
            changes=changes,
            orphan_partitions_recovered=orphan_recovered,
        )
