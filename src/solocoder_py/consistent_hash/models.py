from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NodeInfo:
    node_id: str
    virtual_nodes: int
    weight: float
    hash_space_share: float = 0.0


@dataclass
class MigrationStats:
    total_keys: int
    migrated_keys: int
    migration_ratio: float
    migrated_from: dict[str, int] = field(default_factory=dict)
    migrated_to: dict[str, int] = field(default_factory=dict)


@dataclass
class VirtualNodeInfo:
    hash_value: int
    physical_node_id: str
    virtual_index: int


@dataclass
class RingSnapshot:
    nodes: list[NodeInfo]
    total_virtual_nodes: int
    virtual_nodes: list[VirtualNodeInfo]
