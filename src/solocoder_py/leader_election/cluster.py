from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .clock import Clock, SystemClock
from .enums import NodeState
from .exceptions import (
    AlreadyVotedError,
    LeaderElectionError,
    NodeNotFoundError,
    StaleTermError,
)
from .models import (
    ClusterStatus,
    ElectionResult,
    Heartbeat,
    NodeStatus,
    VoteRecord,
    VoteRequest,
    VoteResponse,
)
from .node import RaftNode


@dataclass
class LeaderElectionCluster:
    node_count: int
    clock: Clock = field(default_factory=SystemClock)
    election_timeout_seconds: float = 5.0
    auto_election_interval: float = 0.5
    _nodes: Dict[str, RaftNode] = field(default_factory=dict)
    _current_term: int = 0
    _leader_id: Optional[str] = None
    _last_election: Optional[ElectionResult] = None
    _partitioned_nodes: set = field(default_factory=set)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _auto_election_running: bool = field(default=False, init=False)
    _auto_election_stop_event: threading.Event = field(default_factory=threading.Event, init=False)
    _auto_election_thread: Optional[threading.Thread] = field(default=None, init=False)

    def __post_init__(self) -> None:
        if self.node_count < 1:
            raise ValueError("node_count must be at least 1")
        if self.election_timeout_seconds <= 0:
            raise ValueError("election_timeout_seconds must be positive")
        if self.auto_election_interval <= 0:
            raise ValueError("auto_election_interval must be positive")
        for i in range(self.node_count):
            node_id = f"node-{i}"
            self._nodes[node_id] = RaftNode(
                node_id=node_id,
                clock=self.clock,
                election_timeout_seconds=self.election_timeout_seconds,
            )

    def start_auto_election(self) -> None:
        with self._lock:
            if self._auto_election_running:
                return
            self._auto_election_running = True
            self._auto_election_stop_event.clear()
            self._auto_election_thread = threading.Thread(
                target=self._auto_election_loop,
                name="LeaderElectionAutoElection",
                daemon=True,
            )
            self._auto_election_thread.start()

    def stop_auto_election(self) -> None:
        with self._lock:
            if not self._auto_election_running:
                return
            self._auto_election_running = False
            self._auto_election_stop_event.set()
            thread = self._auto_election_thread
        if thread is not None:
            thread.join(timeout=2.0)
        with self._lock:
            self._auto_election_thread = None

    @property
    def is_auto_election_running(self) -> bool:
        return self._auto_election_running

    def _auto_election_loop(self) -> None:
        while not self._auto_election_stop_event.is_set():
            try:
                self.check_and_run_elections()
            except LeaderElectionError:
                pass
            time.sleep(self.auto_election_interval)

    @property
    def majority_count(self) -> int:
        return self.node_count // 2 + 1

    @property
    def leader_id(self) -> Optional[str]:
        return self._leader_id

    @property
    def current_term(self) -> int:
        return self._current_term

    @property
    def last_election(self) -> Optional[ElectionResult]:
        return self._last_election

    def get_node(self, node_id: str) -> RaftNode:
        node = self._nodes.get(node_id)
        if node is None:
            raise NodeNotFoundError(f"Node {node_id} not found in cluster")
        return node

    def list_nodes(self) -> List[RaftNode]:
        return list(self._nodes.values())

    def get_reachable_nodes(self, from_node_id: str) -> List[RaftNode]:
        return [
            n
            for n in self._nodes.values()
            if n.node_id != from_node_id
            and n.node_id not in self._partitioned_nodes
            and from_node_id not in self._partitioned_nodes
        ]

    def partition_node(self, node_id: str) -> None:
        self.get_node(node_id)
        self._partitioned_nodes.add(node_id)

    def heal_partition(self, node_id: str) -> None:
        self._partitioned_nodes.discard(node_id)

    def _synch_term_from_node(self, node: RaftNode) -> None:
        if node.current_term > self._current_term:
            self._current_term = node.current_term

    def _step_down_all_other_leaders(self, new_leader_id: str) -> None:
        for node in self._nodes.values():
            if node.node_id != new_leader_id and node.state == NodeState.LEADER:
                node.step_down()

    def _collect_votes(
        self, candidate: RaftNode, vote_request: VoteRequest
    ) -> ElectionResult:
        votes_received: Dict[str, List[str]] = {candidate.node_id: [candidate.node_id]}
        voter_records: Dict[str, VoteRecord] = {}

        voter_records[candidate.node_id] = candidate.vote_record

        reachable = self.get_reachable_nodes(candidate.node_id)

        for node in reachable:
            try:
                response = node.handle_vote_request(vote_request)
                candidate.handle_vote_response(response)
                self._synch_term_from_node(node)

                if response.vote_granted:
                    if candidate.node_id not in votes_received:
                        votes_received[candidate.node_id] = []
                    if node.node_id not in votes_received[candidate.node_id]:
                        votes_received[candidate.node_id].append(node.node_id)

                voter_records[node.node_id] = node.vote_record
            except AlreadyVotedError:
                voter_records[node.node_id] = node.vote_record
                continue

        result = ElectionResult(
            term=candidate.current_term,
            leader_id=None,
            votes_received=votes_received,
            voter_records=voter_records,
        )

        votes_count = len(votes_received.get(candidate.node_id, []))
        if votes_count >= self.majority_count:
            result.leader_id = candidate.node_id

        return result

    def _broadcast_heartbeat_from_leader(self, leader: RaftNode) -> None:
        heartbeat = leader.send_heartbeat()
        for node in self.get_reachable_nodes(leader.node_id):
            try:
                node.receive_heartbeat(heartbeat)
            except StaleTermError:
                node_term = node.current_term
                if node_term > leader.current_term:
                    leader._update_term_if_newer(node_term)
                    if leader.state != NodeState.FOLLOWER:
                        leader.step_down()
                    self._leader_id = None
                    raise

    def _clear_old_leader(self) -> None:
        if self._leader_id is not None:
            old_leader = self._nodes.get(self._leader_id)
            if old_leader is not None and old_leader.state == NodeState.LEADER:
                old_leader.step_down()
        self._leader_id = None

    def run_election(self, candidate_node_id: str) -> ElectionResult:
        with self._lock:
            self._clear_old_leader()

            candidate = self.get_node(candidate_node_id)
            vote_request = candidate.start_election()
            self._synch_term_from_node(candidate)

            result = self._collect_votes(candidate, vote_request)

            if result.is_successful:
                candidate.become_leader()
                self._leader_id = candidate.node_id
                self._current_term = candidate.current_term
                self._step_down_all_other_leaders(candidate.node_id)
                try:
                    self._broadcast_heartbeat_from_leader(candidate)
                except StaleTermError:
                    result.leader_id = None
                    if candidate.state != NodeState.FOLLOWER:
                        candidate.step_down()
                    self._leader_id = None
            else:
                candidate.step_down()

            self._last_election = result
            return result

    def run_election_random(self) -> ElectionResult:
        with self._lock:
            self._clear_old_leader()

            eligible = [
                n
                for n in self._nodes.values()
                if n.state == NodeState.FOLLOWER
                and n.node_id not in self._partitioned_nodes
            ]
            if not eligible:
                eligible = [
                    n
                    for n in self._nodes.values()
                    if n.node_id not in self._partitioned_nodes
                ]
            if not eligible:
                raise LeaderElectionError("No eligible nodes to run election")

            candidate = random.choice(eligible)
            vote_request = candidate.start_election()
            self._synch_term_from_node(candidate)

            result = self._collect_votes(candidate, vote_request)

            if result.is_successful:
                candidate.become_leader()
                self._leader_id = candidate.node_id
                self._current_term = candidate.current_term
                self._step_down_all_other_leaders(candidate.node_id)
                try:
                    self._broadcast_heartbeat_from_leader(candidate)
                except StaleTermError:
                    result.leader_id = None
                    if candidate.state != NodeState.FOLLOWER:
                        candidate.step_down()
                    self._leader_id = None
            else:
                candidate.step_down()

            self._last_election = result
            return result

    def check_and_run_elections(self) -> Optional[ElectionResult]:
        with self._lock:
            timed_out = [
                n
                for n in self._nodes.values()
                if n.is_election_timed_out()
                and n.node_id not in self._partitioned_nodes
                and n.state != NodeState.LEADER
            ]
            if not timed_out:
                return None

            candidate = random.choice(timed_out)
            self._clear_old_leader()

            vote_request = candidate.start_election()
            self._synch_term_from_node(candidate)

            result = self._collect_votes(candidate, vote_request)

            if result.is_successful:
                candidate.become_leader()
                self._leader_id = candidate.node_id
                self._current_term = candidate.current_term
                self._step_down_all_other_leaders(candidate.node_id)
                try:
                    self._broadcast_heartbeat_from_leader(candidate)
                except StaleTermError:
                    result.leader_id = None
                    if candidate.state != NodeState.FOLLOWER:
                        candidate.step_down()
                    self._leader_id = None
            else:
                candidate.step_down()

            self._last_election = result
            return result

    def leader_send_heartbeat(self) -> List[Heartbeat]:
        with self._lock:
            if self._leader_id is None:
                raise LeaderElectionError("No leader in cluster")

            leader_id = self._leader_id
            leader = self.get_node(leader_id)
            if leader.state != NodeState.LEADER:
                self._leader_id = None
                raise LeaderElectionError(f"Node {leader_id} is not leader")

            heartbeat = leader.send_heartbeat()
            heartbeats: List[Heartbeat] = [heartbeat]

            for node in self.get_reachable_nodes(leader.node_id):
                try:
                    node.receive_heartbeat(heartbeat)
                except StaleTermError:
                    node_term = node.current_term
                    if node_term > leader.current_term:
                        leader._update_term_if_newer(node_term)
                        if leader.state != NodeState.FOLLOWER:
                            leader.step_down()
                        self._leader_id = None
                        raise

            return heartbeats

    def get_node_status(self, node_id: str) -> NodeStatus:
        node = self.get_node(node_id)
        return NodeStatus(
            node_id=node.node_id,
            state=node.state,
            current_term=node.current_term,
            voted_for=node.voted_for,
        )

    def get_vote_records(self) -> Dict[str, VoteRecord]:
        return {nid: node.vote_record for nid, node in self._nodes.items()}

    def get_status(self) -> ClusterStatus:
        return ClusterStatus(
            current_term=self._current_term,
            leader_id=self._leader_id,
            nodes=[self.get_node_status(nid) for nid in self._nodes],
            last_election=self._last_election,
        )

    def force_new_leader(self, node_id: str) -> None:
        with self._lock:
            node = self.get_node(node_id)
            if self._leader_id is not None:
                old_leader = self._nodes.get(self._leader_id)
                if old_leader is not None and old_leader.state == NodeState.LEADER:
                    old_leader.step_down()

            node._current_term += 1
            node._state = NodeState.CANDIDATE
            node._voted_for = node.node_id
            node._voted_term = node._current_term
            node._record_heartbeat()
            self._synch_term_from_node(node)

            for other in self.list_nodes():
                if other.node_id != node.node_id:
                    other._current_term = node.current_term
                    other._state = NodeState.FOLLOWER
                    other._voted_for = node.node_id
                    other._voted_term = node.current_term
                    other._leader_id = node.node_id
                    other._record_heartbeat()

            node.become_leader()
            self._leader_id = node.node_id
            self._current_term = node.current_term

            votes = {node.node_id: [n.node_id for n in self.list_nodes()]}
            voter_records = {nid: n.vote_record for nid, n in self._nodes.items()}
            self._last_election = ElectionResult(
                term=node.current_term,
                leader_id=node.node_id,
                votes_received=votes,
                voter_records=voter_records,
            )
