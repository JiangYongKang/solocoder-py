from __future__ import annotations

import threading
from typing import Optional

from .exceptions import (
    NodeNotFoundError,
    RedirectRequiredError,
    SlotAlreadyAssignedError,
    SlotMigrationInProgressError,
    SlotNotAssignedError,
    SlotNotMigratingError,
    SlotRangeInvalidError,
)
from .models import (
    MigrationInfo,
    MigrationProgress,
    RouteResult,
    RouterSnapshot,
    ShardNode,
    SlotAssignment,
    SlotRange,
    WriteResult,
    WriteStatus,
)

DEFAULT_SLOT_COUNT = 16384


def _crc16(data: bytes) -> int:
    crc = 0
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc


class ShardRouter:
    def __init__(self, total_slots: int = DEFAULT_SLOT_COUNT) -> None:
        if total_slots <= 0:
            raise ValueError("total_slots must be positive")
        self._total_slots = total_slots
        self._nodes: dict[str, ShardNode] = {}
        self._slot_to_node: dict[int, str] = {}
        self._node_to_slots: dict[str, set[int]] = {}
        self._migrating_slots: dict[int, MigrationInfo] = {}
        self._completed_migrations: list[MigrationInfo] = []
        self._lock = threading.RLock()

    @property
    def total_slots(self) -> int:
        return self._total_slots

    @staticmethod
    def key_to_slot(key: str, total_slots: int = DEFAULT_SLOT_COUNT) -> int:
        start = key.find("{")
        end = key.find("}")
        if start != -1 and end != -1 and end > start + 1:
            hash_key = key[start + 1 : end]
        else:
            hash_key = key
        return _crc16(hash_key.encode("utf-8")) % total_slots

    def add_node(self, node_id: str, host: str = "", port: int = 0) -> None:
        if not node_id:
            raise ValueError("node_id must not be empty")
        with self._lock:
            if node_id in self._nodes:
                return
            self._nodes[node_id] = ShardNode(node_id=node_id, host=host, port=port)
            self._node_to_slots.setdefault(node_id, set())

    def remove_node(self, node_id: str) -> None:
        with self._lock:
            if node_id not in self._nodes:
                raise NodeNotFoundError(f"node '{node_id}' not found")
            slots = self._node_to_slots.get(node_id, set())
            if slots:
                raise ValueError(f"node '{node_id}' still has assigned slots, unassign them first")
            migrating = [s for s, info in self._migrating_slots.items()
                         if info.source_node_id == node_id or info.target_node_id == node_id]
            if migrating:
                raise ValueError(f"node '{node_id}' has ongoing migrations, complete them first")
            self._nodes.pop(node_id, None)
            self._node_to_slots.pop(node_id, None)

    def assign_slot_range(self, node_id: str, start: int, end: int) -> None:
        self._validate_slot_range(start, end)
        with self._lock:
            if node_id not in self._nodes:
                raise NodeNotFoundError(f"node '{node_id}' not found")
            for slot in range(start, end + 1):
                if slot in self._migrating_slots:
                    raise SlotMigrationInProgressError(
                        f"slot {slot} is currently being migrated"
                    )
                if slot in self._slot_to_node:
                    raise SlotAlreadyAssignedError(
                        f"slot {slot} is already assigned to node '{self._slot_to_node[slot]}'"
                    )
            for slot in range(start, end + 1):
                self._slot_to_node[slot] = node_id
                self._node_to_slots.setdefault(node_id, set()).add(slot)

    def unassign_slot_range(self, start: int, end: int) -> None:
        self._validate_slot_range(start, end)
        with self._lock:
            for slot in range(start, end + 1):
                if slot in self._migrating_slots:
                    raise SlotMigrationInProgressError(
                        f"slot {slot} is currently being migrated"
                    )
                if slot not in self._slot_to_node:
                    continue
                node_id = self._slot_to_node.pop(slot)
                self._node_to_slots.get(node_id, set()).discard(slot)

    def start_migration(self, slot: int, target_node_id: str) -> None:
        if slot < 0 or slot >= self._total_slots:
            raise SlotRangeInvalidError(f"slot {slot} out of range [0, {self._total_slots})")
        with self._lock:
            if slot not in self._slot_to_node:
                raise SlotNotAssignedError(f"slot {slot} is not assigned")
            if slot in self._migrating_slots:
                raise SlotMigrationInProgressError(f"slot {slot} is already being migrated")
            if target_node_id not in self._nodes:
                raise NodeNotFoundError(f"node '{target_node_id}' not found")
            source_node_id = self._slot_to_node[slot]
            if source_node_id == target_node_id:
                raise ValueError("source and target node must be different")
            self._migrating_slots[slot] = MigrationInfo(
                slot=slot,
                source_node_id=source_node_id,
                target_node_id=target_node_id,
                in_progress=True,
            )

    def complete_migration(self, slot: int) -> None:
        if slot < 0 or slot >= self._total_slots:
            raise SlotRangeInvalidError(f"slot {slot} out of range [0, {self._total_slots})")
        with self._lock:
            if slot not in self._migrating_slots:
                raise SlotNotMigratingError(f"slot {slot} is not being migrated")
            info = self._migrating_slots.pop(slot)
            completed_info = MigrationInfo(
                slot=slot,
                source_node_id=info.source_node_id,
                target_node_id=info.target_node_id,
                in_progress=False,
            )
            self._completed_migrations.append(completed_info)
            old_node = self._slot_to_node.pop(slot, None)
            if old_node:
                self._node_to_slots.get(old_node, set()).discard(slot)
            self._slot_to_node[slot] = info.target_node_id
            self._node_to_slots.setdefault(info.target_node_id, set()).add(slot)

    def get_route(self, key: str) -> RouteResult:
        slot = self.key_to_slot(key, self._total_slots)
        with self._lock:
            if slot not in self._slot_to_node:
                raise SlotNotAssignedError(f"slot {slot} for key '{key}' is not assigned")
            node_id = self._slot_to_node[slot]
            if slot in self._migrating_slots:
                info = self._migrating_slots[slot]
                return RouteResult(
                    node_id=node_id,
                    slot=slot,
                    migrating=True,
                    migration_target=info.target_node_id,
                )
            return RouteResult(node_id=node_id, slot=slot)

    def prepare_write(self, key: str) -> WriteResult:
        slot = self.key_to_slot(key, self._total_slots)
        with self._lock:
            if slot not in self._slot_to_node:
                raise SlotNotAssignedError(f"slot {slot} for key '{key}' is not assigned")
            current_node = self._slot_to_node[slot]
            if slot in self._migrating_slots:
                info = self._migrating_slots[slot]
                return WriteResult(
                    status=WriteStatus.DUAL,
                    primary_node_id=current_node,
                    secondary_node_id=info.target_node_id,
                    slot=slot,
                )
            return WriteResult(
                status=WriteStatus.SINGLE,
                primary_node_id=current_node,
                slot=slot,
            )

    def route_from_node(self, key: str, source_node_id: str) -> RouteResult:
        route = self.get_route(key)
        if route.node_id != source_node_id:
            raise RedirectRequiredError(slot=route.slot, target_node_id=route.node_id)
        return route

    def get_slot_owner(self, slot: int) -> Optional[str]:
        if slot < 0 or slot >= self._total_slots:
            raise SlotRangeInvalidError(f"slot {slot} out of range [0, {self._total_slots})")
        with self._lock:
            return self._slot_to_node.get(slot)

    def get_node_slots(self, node_id: str) -> list[SlotRange]:
        with self._lock:
            if node_id not in self._nodes:
                raise NodeNotFoundError(f"node '{node_id}' not found")
            slots = sorted(self._node_to_slots.get(node_id, set()))
            return self._slots_to_ranges(slots)

    def get_migration_progress(self) -> MigrationProgress:
        with self._lock:
            in_progress = list(self._migrating_slots.values())
            return MigrationProgress(
                total_migrating=len(self._migrating_slots) + len(self._completed_migrations),
                completed_migrations=len(self._completed_migrations),
                in_progress_slots=in_progress,
            )

    def get_migrating_slots(self) -> list[MigrationInfo]:
        with self._lock:
            return list(self._migrating_slots.values())

    def get_all_assignments(self) -> dict[str, SlotAssignment]:
        with self._lock:
            result: dict[str, SlotAssignment] = {}
            for node_id in self._nodes:
                slots = sorted(self._node_to_slots.get(node_id, set()))
                ranges = self._slots_to_ranges(slots)
                result[node_id] = SlotAssignment(node_id=node_id, slot_ranges=ranges)
            return result

    def list_nodes(self) -> list[ShardNode]:
        with self._lock:
            return list(self._nodes.values())

    def get_snapshot(self) -> RouterSnapshot:
        with self._lock:
            assigned = len(self._slot_to_node)
            return RouterSnapshot(
                total_slots=self._total_slots,
                assigned_slots=assigned,
                unassigned_slots=self._total_slots - assigned,
                nodes=list(self._nodes.values()),
                assignments=self.get_all_assignments(),
                migrations=self.get_migration_progress(),
            )

    def _validate_slot_range(self, start: int, end: int) -> None:
        if start < 0 or end >= self._total_slots:
            raise SlotRangeInvalidError(
                f"slot range [{start}, {end}] out of valid range [0, {self._total_slots})"
            )
        if start > end:
            raise SlotRangeInvalidError(f"start {start} must be <= end {end}")

    @staticmethod
    def _slots_to_ranges(slots: list[int]) -> list[SlotRange]:
        if not slots:
            return []
        ranges: list[SlotRange] = []
        range_start = slots[0]
        prev = slots[0]
        for s in slots[1:]:
            if s == prev + 1:
                prev = s
            else:
                ranges.append(SlotRange(start=range_start, end=prev))
                range_start = s
                prev = s
        ranges.append(SlotRange(start=range_start, end=prev))
        return ranges
