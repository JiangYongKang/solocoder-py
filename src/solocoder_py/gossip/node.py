from __future__ import annotations

import random
import threading
from typing import Callable, Dict, List, Optional

from .clock import Clock, SystemClock
from .membership import MembershipView
from .models import GossipConfig, HeartbeatMessage, Member, MemberState


class GossipNode:
    def __init__(
        self,
        node_id: str,
        config: Optional[GossipConfig] = None,
        clock: Optional[Clock] = None,
        rng: Optional[random.Random] = None,
    ) -> None:
        self._node_id = node_id
        self._config: GossipConfig = config or GossipConfig()
        self._clock: Clock = clock or SystemClock()
        self._rng: random.Random = rng or random.Random()
        self._membership = MembershipView(node_id, self._config, self._clock)
        self._peers: Dict[str, "GossipNode"] = {}
        self._lock = threading.RLock()
        self._running = False
        self._timer: Optional[threading.Timer] = None
        self._state_listeners: List[Callable[[str, MemberState, MemberState], None]] = []

    @property
    def node_id(self) -> str:
        return self._node_id

    @property
    def config(self) -> GossipConfig:
        return self._config

    @property
    def membership(self) -> MembershipView:
        return self._membership

    def add_state_listener(
        self, listener: Callable[[str, MemberState, MemberState], None]
    ) -> None:
        self._state_listeners.append(listener)

    def connect(self, peer: "GossipNode") -> None:
        with self._lock, peer._lock:
            if peer.node_id not in self._peers:
                self._peers[peer.node_id] = peer
            if self._node_id not in peer._peers:
                peer._peers[self._node_id] = self

    def disconnect(self, peer: "GossipNode") -> None:
        with self._lock, peer._lock:
            self._peers.pop(peer.node_id, None)
            peer._peers.pop(self._node_id, None)

    def get_connected_peers(self) -> Dict[str, "GossipNode"]:
        with self._lock:
            return dict(self._peers)

    def seed_member(self, node_id: str) -> None:
        now = self._clock.now()
        self._membership.add_or_update_member(
            Member(
                node_id=node_id,
                state=MemberState.ALIVE,
                incarnation=0,
                version=1,
                last_heartbeat=now,
                state_changed_at=now,
                missed_heartbeats=0,
            )
        )

    def send_heartbeat(self) -> List[str]:
        with self._lock:
            self._membership.update_self_heartbeat()

            alive_others = self._membership.get_other_alive_node_ids()
            connected_ids = list(self._peers.keys())
            candidate_ids = list(set(alive_others) & set(connected_ids))

            if not candidate_ids:
                candidate_ids = connected_ids
            if not candidate_ids:
                return []

            fanout = min(self._config.fanout, len(candidate_ids))
            targets = self._rng.sample(candidate_ids, fanout)

            message = self._membership.build_heartbeat_message()
            sent_to: List[str] = []
            for target_id in targets:
                peer = self._peers.get(target_id)
                if peer is not None:
                    peer.receive_heartbeat(message.clone())
                    sent_to.append(target_id)

            return sent_to

    def receive_heartbeat(self, message: HeartbeatMessage) -> None:
        with self._lock:
            before_states: Dict[str, MemberState] = {}
            new_member_ids: set[str] = set()
            for node_id in message.members:
                existing = self._membership.get_member(node_id)
                if existing:
                    before_states[node_id] = existing.state
                else:
                    new_member_ids.add(node_id)

            self._membership.merge_heartbeat(message)

            for node_id in new_member_ids:
                current = self._membership.get_member(node_id)
                if current:
                    self._notify_listeners(node_id, None, current.state)

            for node_id, before_state in before_states.items():
                current = self._membership.get_member(node_id)
                if current and current.state != before_state:
                    self._notify_listeners(node_id, before_state, current.state)

            if message.sender_id not in self._membership.get_all_members():
                now = self._clock.now()
                self._membership.add_or_update_member(
                    Member(
                        node_id=message.sender_id,
                        state=MemberState.ALIVE,
                        incarnation=0,
                        version=1,
                        last_heartbeat=now,
                        state_changed_at=now,
                        missed_heartbeats=0,
                    )
                )
                self._notify_listeners(message.sender_id, None, MemberState.ALIVE)

    def check_failures(self) -> Dict[str, MemberState]:
        with self._lock:
            before: Dict[str, MemberState] = {}
            for node_id, member in self._membership.get_all_members().items():
                before[node_id] = member.state

            transitions = self._membership.check_failures()

            for node_id, new_state in transitions.items():
                old_state = before.get(node_id)
                if old_state != new_state:
                    self._notify_listeners(node_id, old_state, new_state)

            return transitions

    def cleanup_dead_nodes(self) -> List[str]:
        with self._lock:
            return self._membership.cleanup_dead_nodes()

    def rejoin(self) -> None:
        with self._lock:
            self._membership.rejoin_node(self._node_id)

    def mark_node_alive(self, node_id: str) -> None:
        with self._lock:
            existing = self._membership.get_member(node_id)
            before = existing.state if existing else None
            now = self._clock.now()
            if existing:
                existing.mark_alive(now)
                self._membership.add_or_update_member(existing)
            else:
                self._membership.add_or_update_member(
                    Member(
                        node_id=node_id,
                        state=MemberState.ALIVE,
                        incarnation=0,
                        version=1,
                        last_heartbeat=now,
                        state_changed_at=now,
                        missed_heartbeats=0,
                    )
                )
            if before != MemberState.ALIVE:
                self._notify_listeners(node_id, before, MemberState.ALIVE)

    def _notify_listeners(
        self, node_id: str, old_state: Optional[MemberState], new_state: MemberState
    ) -> None:
        for listener in self._state_listeners:
            try:
                listener(node_id, old_state, new_state)
            except Exception:
                pass

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._schedule_next_heartbeat()

    def stop(self) -> None:
        with self._lock:
            self._running = False
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None

    def _schedule_next_heartbeat(self) -> None:
        if not self._running:
            return
        self._timer = threading.Timer(self._config.heartbeat_interval, self._tick)
        self._timer.daemon = True
        self._timer.start()

    def _tick(self) -> None:
        try:
            self.send_heartbeat()
            self.check_failures()
            self.cleanup_dead_nodes()
        finally:
            with self._lock:
                if self._running:
                    self._schedule_next_heartbeat()
