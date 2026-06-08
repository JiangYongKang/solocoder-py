from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .enums import NodeState
from .exceptions import AlreadyVotedError, StaleTermError
from .models import Heartbeat, VoteRecord, VoteRequest, VoteResponse


@dataclass
class RaftNode:
    node_id: str
    _state: NodeState = NodeState.FOLLOWER
    _current_term: int = 0
    _voted_for: Optional[str] = None
    _voted_term: int = 0
    _leader_id: Optional[str] = None

    @property
    def state(self) -> NodeState:
        return self._state

    @property
    def current_term(self) -> int:
        return self._current_term

    @property
    def voted_for(self) -> Optional[str]:
        return self._voted_for

    @property
    def voted_term(self) -> int:
        return self._voted_term

    @property
    def leader_id(self) -> Optional[str]:
        return self._leader_id

    @property
    def vote_record(self) -> VoteRecord:
        return VoteRecord(term=self._voted_term, voted_for=self._voted_for)

    def _update_term_if_newer(self, term: int) -> None:
        if term > self._current_term:
            self._current_term = term
            self._state = NodeState.FOLLOWER
            self._leader_id = None

    def start_election(self) -> VoteRequest:
        self._current_term += 1
        self._state = NodeState.CANDIDATE
        self._voted_for = self.node_id
        self._voted_term = self._current_term
        self._leader_id = None
        return VoteRequest(term=self._current_term, candidate_id=self.node_id)

    def handle_vote_request(self, request: VoteRequest) -> VoteResponse:
        if request.term < self._current_term:
            return VoteResponse(
                term=self._current_term, vote_granted=False, voter_id=self.node_id
            )

        self._update_term_if_newer(request.term)

        if self._voted_term == self._current_term and self._voted_for is not None:
            if self._voted_for != request.candidate_id:
                raise AlreadyVotedError(
                    f"Node {self.node_id} already voted for {self._voted_for} "
                    f"in term {self._current_term}"
                )

        self._voted_for = request.candidate_id
        self._voted_term = self._current_term
        return VoteResponse(
            term=self._current_term, vote_granted=True, voter_id=self.node_id
        )

    def handle_vote_response(self, response: VoteResponse) -> None:
        self._update_term_if_newer(response.term)

    def become_leader(self) -> None:
        if self._state != NodeState.CANDIDATE:
            raise StaleTermError(
                f"Node {self.node_id} is not a candidate, cannot become leader"
            )
        self._state = NodeState.LEADER
        self._leader_id = self.node_id

    def send_heartbeat(self) -> Heartbeat:
        if self._state != NodeState.LEADER:
            raise StaleTermError(f"Node {self.node_id} is not the leader")
        return Heartbeat(term=self._current_term, leader_id=self.node_id)

    def receive_heartbeat(self, heartbeat: Heartbeat) -> None:
        if heartbeat.term < self._current_term:
            raise StaleTermError(
                f"Stale heartbeat from leader {heartbeat.leader_id} "
                f"with term {heartbeat.term}, current term is {self._current_term}"
            )

        self._update_term_if_newer(heartbeat.term)

        if self._state in (NodeState.CANDIDATE, NodeState.LEADER):
            self._state = NodeState.FOLLOWER

        self._leader_id = heartbeat.leader_id

    def step_down(self) -> None:
        self._state = NodeState.FOLLOWER
        self._leader_id = None
