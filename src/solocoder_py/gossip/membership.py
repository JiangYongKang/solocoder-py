from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .clock import Clock, SystemClock
from .models import GossipConfig, HeartbeatMessage, Member, MemberState


class MembershipView:
    def __init__(
        self,
        self_node_id: str,
        config: GossipConfig,
        clock: Optional[Clock] = None,
    ) -> None:
        self._self_node_id = self_node_id
        self._config = config
        self._clock: Clock = clock or SystemClock()
        self._lock = threading.RLock()
        self._members: Dict[str, Member] = {}
        self._add_self_member()

    def _add_self_member(self) -> None:
        now = self._clock.now()
        self._members[self._self_node_id] = Member(
            node_id=self._self_node_id,
            state=MemberState.ALIVE,
            incarnation=0,
            version=1,
            last_heartbeat=now,
            state_changed_at=now,
            missed_heartbeats=0,
        )

    @property
    def self_node_id(self) -> str:
        return self._self_node_id

    def get_member(self, node_id: str) -> Optional[Member]:
        with self._lock:
            member = self._members.get(node_id)
            return member.clone() if member else None

    def get_all_members(self) -> Dict[str, Member]:
        with self._lock:
            return {k: v.clone() for k, v in self._members.items()}

    def get_alive_members(self) -> Dict[str, Member]:
        with self._lock:
            return {
                k: v.clone()
                for k, v in self._members.items()
                if v.state == MemberState.ALIVE
            }

    def get_suspect_members(self) -> Dict[str, Member]:
        with self._lock:
            return {
                k: v.clone()
                for k, v in self._members.items()
                if v.state == MemberState.SUSPECT
            }

    def get_dead_members(self) -> Dict[str, Member]:
        with self._lock:
            return {
                k: v.clone()
                for k, v in self._members.items()
                if v.state == MemberState.DEAD
            }

    def get_other_alive_node_ids(self) -> List[str]:
        with self._lock:
            return [
                m.node_id
                for m in self._members.values()
                if m.state == MemberState.ALIVE and m.node_id != self._self_node_id
            ]

    def update_self_heartbeat(self) -> None:
        with self._lock:
            now = self._clock.now()
            self_member = self._members[self._self_node_id]
            self_member.bump_version(now)

    def add_or_update_member(self, incoming: Member) -> bool:
        with self._lock:
            now = self._clock.now()
            existing = self._members.get(incoming.node_id)

            if existing is None:
                new_member = incoming.clone()
                if new_member.last_heartbeat == 0:
                    new_member.last_heartbeat = now
                if new_member.state_changed_at == 0:
                    new_member.state_changed_at = now
                self._members[incoming.node_id] = new_member
                return True

            if incoming.node_id == self._self_node_id:
                if incoming.state == MemberState.ALIVE and incoming.version > existing.version:
                    existing.mark_alive(now, incoming.version)
                    return True
                return False

            if not incoming.is_newer_than(existing):
                return False

            old_state = existing.state
            existing.state = incoming.state
            existing.version = incoming.version
            existing.incarnation = incoming.incarnation
            existing.last_heartbeat = max(existing.last_heartbeat, incoming.last_heartbeat)
            if incoming.state != old_state:
                existing.state_changed_at = now
            existing.missed_heartbeats = 0
            return True

    def merge_heartbeat(self, message: HeartbeatMessage) -> Dict[str, bool]:
        results: Dict[str, bool] = {}
        for node_id, member in message.members.items():
            results[node_id] = self.add_or_update_member(member)
        return results

    def check_failures(self) -> Dict[str, MemberState]:
        transitions: Dict[str, MemberState] = {}
        with self._lock:
            now = self._clock.now()
            for node_id, member in list(self._members.items()):
                if node_id == self._self_node_id:
                    continue

                if member.state == MemberState.ALIVE:
                    member.increment_missed_heartbeats()
                    if member.missed_heartbeats >= self._config.suspect_missed_count:
                        member.mark_suspect(now)
                        transitions[node_id] = MemberState.SUSPECT
                elif member.state == MemberState.SUSPECT:
                    time_since_state_change = now - member.state_changed_at
                    if time_since_state_change >= self._config.dead_timeout:
                        member.mark_dead(now)
                        transitions[node_id] = MemberState.DEAD

        return transitions

    def cleanup_dead_nodes(self) -> List[str]:
        removed: List[str] = []
        with self._lock:
            now = self._clock.now()
            for node_id, member in list(self._members.items()):
                if node_id == self._self_node_id:
                    continue
                if member.state == MemberState.DEAD:
                    time_dead = now - member.state_changed_at
                    if time_dead >= self._config.cleanup_timeout:
                        del self._members[node_id]
                        removed.append(node_id)
        return removed

    def rejoin_node(self, node_id: str) -> None:
        with self._lock:
            now = self._clock.now()
            existing = self._members.get(node_id)
            new_incarnation = existing.incarnation + 1 if existing else 0
            self._members[node_id] = Member(
                node_id=node_id,
                state=MemberState.ALIVE,
                incarnation=new_incarnation,
                version=1,
                last_heartbeat=now,
                state_changed_at=now,
                missed_heartbeats=0,
            )

    def build_heartbeat_message(self) -> HeartbeatMessage:
        with self._lock:
            members_snapshot = {k: v.clone() for k, v in self._members.items()}
        return HeartbeatMessage(
            sender_id=self._self_node_id,
            members=members_snapshot,
        )

    def member_count(self) -> int:
        with self._lock:
            return len(self._members)
