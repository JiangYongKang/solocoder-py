from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .enums import NodeState


@dataclass
class VoteRequest:
    term: int
    candidate_id: str


@dataclass
class VoteResponse:
    term: int
    vote_granted: bool
    voter_id: str


@dataclass
class Heartbeat:
    term: int
    leader_id: str


@dataclass
class VoteRecord:
    term: int
    voted_for: Optional[str]


@dataclass
class ElectionResult:
    term: int
    leader_id: Optional[str]
    votes_received: Dict[str, List[str]] = field(default_factory=dict)
    voter_records: Dict[str, VoteRecord] = field(default_factory=dict)

    @property
    def is_successful(self) -> bool:
        return self.leader_id is not None


@dataclass
class NodeStatus:
    node_id: str
    state: NodeState
    current_term: int
    voted_for: Optional[str]


@dataclass
class ClusterStatus:
    current_term: int
    leader_id: Optional[str]
    nodes: List[NodeStatus]
    last_election: Optional[ElectionResult]
