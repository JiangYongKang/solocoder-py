from __future__ import annotations

import bisect
import hashlib
import threading
from typing import Optional

from .exceptions import (
    EmptyRingError,
    InvalidVirtualNodesError,
    InvalidWeightError,
    NodeAlreadyExistsError,
    NodeNotFoundError,
)
from .models import MigrationStats, NodeInfo, RingSnapshot, VirtualNodeInfo


_DEFAULT_VIRTUAL_NODES = 150
_HASH_SPACE = 2**32


class ConsistentHashRing:
    def __init__(
        self,
        default_virtual_nodes: int = _DEFAULT_VIRTUAL_NODES,
    ) -> None:
        if default_virtual_nodes <= 0:
            raise InvalidVirtualNodesError("default_virtual_nodes must be positive")

        self._default_virtual_nodes = default_virtual_nodes
        self._nodes: dict[str, dict] = {}
        self._ring: list[int] = []
        self._hash_to_vnode: dict[int, tuple[str, int]] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _hash(key: str) -> int:
        digest = hashlib.md5(key.encode("utf-8")).digest()
        return int.from_bytes(digest[:4], byteorder="big", signed=False)

    @property
    def node_count(self) -> int:
        with self._lock:
            return len(self._nodes)

    @property
    def total_virtual_nodes(self) -> int:
        with self._lock:
            return len(self._ring)

    def add_node(
        self,
        node_id: str,
        virtual_nodes: Optional[int] = None,
        weight: float = 1.0,
    ) -> None:
        if not node_id:
            raise ValueError("node_id must not be empty")
        if weight <= 0:
            raise InvalidWeightError("weight must be positive")
        if virtual_nodes is not None and virtual_nodes <= 0:
            raise InvalidVirtualNodesError("virtual_nodes must be positive")

        with self._lock:
            if node_id in self._nodes:
                raise NodeAlreadyExistsError(f"node '{node_id}' already exists")

            effective_vnodes = (
                virtual_nodes
                if virtual_nodes is not None
                else int(self._default_virtual_nodes * weight)
            )
            if effective_vnodes <= 0:
                effective_vnodes = 1

            self._nodes[node_id] = {
                "virtual_nodes": effective_vnodes,
                "weight": weight,
            }

            for i in range(effective_vnodes):
                vkey = f"{node_id}#{i}"
                h = self._hash(vkey)
                while h in self._hash_to_vnode:
                    vkey = f"{node_id}#{i}#{h}"
                    h = self._hash(vkey)
                bisect.insort(self._ring, h)
                self._hash_to_vnode[h] = (node_id, i)

    def remove_node(self, node_id: str) -> None:
        with self._lock:
            if node_id not in self._nodes:
                raise NodeNotFoundError(f"node '{node_id}' not found")

            info = self._nodes.pop(node_id)
            vcount = info["virtual_nodes"]

            for i in range(vcount):
                vkey = f"{node_id}#{i}"
                h = self._hash(vkey)
                if h not in self._hash_to_vnode:
                    alt = 0
                    while True:
                        vkey_alt = f"{node_id}#{i}#{alt}"
                        h = self._hash(vkey_alt)
                        if h in self._hash_to_vnode:
                            break
                        alt += 1
                idx = bisect.bisect_left(self._ring, h)
                if idx < len(self._ring) and self._ring[idx] == h:
                    self._ring.pop(idx)
                self._hash_to_vnode.pop(h, None)

    def get_node(self, key: str) -> str:
        with self._lock:
            if not self._ring:
                raise EmptyRingError("hash ring is empty")

            h = self._hash(key)
            idx = bisect.bisect(self._ring, h)
            if idx == len(self._ring):
                idx = 0
            return self._hash_to_vnode[self._ring[idx]][0]

    def get_nodes(self) -> list[NodeInfo]:
        with self._lock:
            result = []
            for nid, info in self._nodes.items():
                estimated = self._estimate_key_count(nid)
                result.append(
                    NodeInfo(
                        node_id=nid,
                        virtual_nodes=info["virtual_nodes"],
                        weight=info["weight"],
                        estimated_key_count=estimated,
                    )
                )
            return result

    def get_node_info(self, node_id: str) -> NodeInfo:
        with self._lock:
            if node_id not in self._nodes:
                raise NodeNotFoundError(f"node '{node_id}' not found")
            info = self._nodes[node_id]
            return NodeInfo(
                node_id=node_id,
                virtual_nodes=info["virtual_nodes"],
                weight=info["weight"],
                estimated_key_count=self._estimate_key_count(node_id),
            )

    def _estimate_key_count(self, node_id: str) -> int:
        if not self._ring:
            return 0
        total = len(self._ring)
        vnodes = self._nodes[node_id]["virtual_nodes"]
        return int(_HASH_SPACE * (vnodes / total))

    def get_snapshot(self) -> RingSnapshot:
        with self._lock:
            nodes = self.get_nodes()
            vnodes = []
            for h in self._ring:
                nid, idx = self._hash_to_vnode[h]
                vnodes.append(
                    VirtualNodeInfo(
                        hash_value=h,
                        physical_node_id=nid,
                        virtual_index=idx,
                    )
                )
            return RingSnapshot(
                nodes=nodes,
                total_virtual_nodes=len(self._ring),
                virtual_nodes=vnodes,
            )

    def get_migration_stats(
        self,
        keys: list[str],
        before: Optional[RingSnapshot] = None,
        after: Optional[RingSnapshot] = None,
    ) -> MigrationStats:
        if before is None and after is None:
            raise ValueError("at least one of before or after must be provided")

        if before is None:
            before = self.get_snapshot()
        if after is None:
            after = self.get_snapshot()

        before_map = self._build_ring_from_snapshot(before)
        after_map = self._build_ring_from_snapshot(after)

        total = len(keys)
        migrated = 0
        from_counts: dict[str, int] = {}
        to_counts: dict[str, int] = {}

        for key in keys:
            before_node = self._route_with_map(key, before_map)
            after_node = self._route_with_map(key, after_map)
            if before_node != after_node:
                migrated += 1
                from_counts[before_node] = from_counts.get(before_node, 0) + 1
                to_counts[after_node] = to_counts.get(after_node, 0) + 1

        ratio = migrated / total if total > 0 else 0.0
        return MigrationStats(
            total_keys=total,
            migrated_keys=migrated,
            migration_ratio=ratio,
            migrated_from=from_counts,
            migrated_to=to_counts,
        )

    @staticmethod
    def _build_ring_from_snapshot(
        snapshot: RingSnapshot,
    ) -> tuple[list[int], dict[int, str]]:
        ring = sorted(v.hash_value for v in snapshot.virtual_nodes)
        hmap = {v.hash_value: v.physical_node_id for v in snapshot.virtual_nodes}
        return ring, hmap

    @classmethod
    def _route_with_map(cls, key: str, ring_map: tuple[list[int], dict[int, str]]) -> str:
        ring, hmap = ring_map
        if not ring:
            raise EmptyRingError("hash ring is empty")
        h = cls._hash(key)
        idx = bisect.bisect(ring, h)
        if idx == len(ring):
            idx = 0
        return hmap[ring[idx]]
