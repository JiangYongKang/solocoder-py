from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional


class MemberState(str, Enum):
    ALIVE = "ALIVE"
    SUSPECT = "SUSPECT"
    DEAD = "DEAD"


class GossipError(Exception):
    pass


class InvalidConfigError(GossipError):
    pass


@dataclass
class GossipConfig:
    heartbeat_interval: float = 1.0
    suspect_missed_count: int = 5
    dead_timeout: float = 10.0
    cleanup_timeout: float = 60.0
    fanout: int = 3

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if self.heartbeat_interval <= 0:
            raise InvalidConfigError("heartbeat_interval must be positive")
        if self.suspect_missed_count <= 0:
            raise InvalidConfigError("suspect_missed_count must be positive")
        if self.dead_timeout <= 0:
            raise InvalidConfigError("dead_timeout must be positive")
        if self.cleanup_timeout <= self.dead_timeout:
            raise InvalidConfigError("cleanup_timeout must be greater than dead_timeout")
        if self.fanout <= 0:
            raise InvalidConfigError("fanout must be positive")


@dataclass
class Member:
    node_id: str
    state: MemberState = MemberState.ALIVE
    incarnation: int = 0
    version: int = 0
    last_heartbeat: float = 0.0
    state_changed_at: float = 0.0
    missed_heartbeats: int = 0

    def bump_version(self, now: float) -> None:
        self.version += 1
        self.last_heartbeat = now

    def increment_missed_heartbeats(self) -> int:
        self.missed_heartbeats += 1
        return self.missed_heartbeats

    def mark_alive(self, now: float, version: Optional[int] = None) -> None:
        if version is not None and version > self.version:
            self.version = version
        else:
            self.version += 1
        self.state = MemberState.ALIVE
        self.last_heartbeat = now
        self.state_changed_at = now
        self.missed_heartbeats = 0

    def mark_suspect(self, now: float) -> None:
        if self.state != MemberState.ALIVE:
            return
        self.state = MemberState.SUSPECT
        self.version += 1
        self.state_changed_at = now
        self.missed_heartbeats = 0

    def mark_dead(self, now: float) -> None:
        if self.state == MemberState.DEAD:
            return
        self.state = MemberState.DEAD
        self.version += 1
        self.state_changed_at = now
        self.missed_heartbeats = 0

    def is_newer_than(self, other: "Member") -> bool:
        if self.incarnation != other.incarnation:
            return self.incarnation > other.incarnation
        if self.version != other.version:
            return self.version > other.version
        return self.last_heartbeat > other.last_heartbeat

    def clone(self) -> "Member":
        return Member(
            node_id=self.node_id,
            state=self.state,
            incarnation=self.incarnation,
            version=self.version,
            last_heartbeat=self.last_heartbeat,
            state_changed_at=self.state_changed_at,
            missed_heartbeats=self.missed_heartbeats,
        )


@dataclass
class HeartbeatMessage:
    sender_id: str
    members: Dict[str, Member] = field(default_factory=dict)

    def clone(self) -> "HeartbeatMessage":
        return HeartbeatMessage(
            sender_id=self.sender_id,
            members={k: v.clone() for k, v in self.members.items()},
        )
