from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from time import time
from typing import Optional
from uuid import uuid4


class TeamSize(Enum):
    ONE_V_ONE = 1
    TWO_V_TWO = 2
    THREE_V_THREE = 3


class MatchStatus(Enum):
    PENDING = "pending"
    FORMING = "forming"
    READY = "ready"
    MATCHED = "matched"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Player:
    player_id: str
    skill_rating: float

    def __post_init__(self) -> None:
        if self.skill_rating < 0:
            from .exceptions import InvalidSkillRatingError

            raise InvalidSkillRatingError(
                f"Skill rating must be non-negative, got {self.skill_rating}"
            )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Player):
            return NotImplemented
        return self.player_id == other.player_id

    def __hash__(self) -> int:
        return hash(self.player_id)


@dataclass
class MatchRequest:
    player: Player
    team_size: TeamSize
    initial_skill_range: float
    enqueue_time: float = field(default_factory=time)

    def current_skill_range(
        self,
        relax_step: float,
        relax_interval: float,
        max_skill_range: float,
        now: Optional[float] = None,
    ) -> float:
        if now is None:
            now = time()
        elapsed = now - self.enqueue_time
        steps = int(elapsed // relax_interval)
        expanded = self.initial_skill_range + steps * relax_step
        return min(expanded, max_skill_range)

    def current_skill_window(
        self,
        relax_step: float,
        relax_interval: float,
        max_skill_range: float,
        now: Optional[float] = None,
    ) -> tuple[float, float]:
        r = self.current_skill_range(relax_step, relax_interval, max_skill_range, now)
        return (self.player.skill_rating - r, self.player.skill_rating + r)


@dataclass
class Team:
    team_id: str = field(default_factory=lambda: str(uuid4()))
    team_size: TeamSize = TeamSize.ONE_V_ONE
    members: list[Player] = field(default_factory=list)
    requests: list[MatchRequest] = field(default_factory=list)
    formed_time: float = field(default_factory=time)

    @property
    def is_complete(self) -> bool:
        return len(self.members) == self.team_size.value

    @property
    def avg_skill(self) -> float:
        if not self.members:
            return 0.0
        return sum(p.skill_rating for p in self.members) / len(self.members)

    @property
    def earliest_enqueue_time(self) -> float:
        if not self.requests:
            return self.formed_time
        return min(r.enqueue_time for r in self.requests)

    def effective_skill_window(
        self,
        relax_step: float,
        relax_interval: float,
        max_skill_range: float,
        now: Optional[float] = None,
    ) -> tuple[float, float]:
        if now is None:
            now = time()
        if not self.requests:
            r = max_skill_range
            return (self.avg_skill - r, self.avg_skill + r)
        lo = float("-inf")
        hi = float("inf")
        for req in self.requests:
            r_lo, r_hi = req.current_skill_window(
                relax_step, relax_interval, max_skill_range, now
            )
            lo = max(lo, r_lo)
            hi = min(hi, r_hi)
        if lo > hi:
            lo, hi = self.avg_skill - max_skill_range, self.avg_skill + max_skill_range
        return (lo, hi)

    def add_player(self, player: Player, request: Optional[MatchRequest] = None) -> None:
        from .exceptions import DuplicatePlayerError

        if player in self.members:
            raise DuplicatePlayerError(
                f"Player {player.player_id} already in team {self.team_id}"
            )
        if len(self.members) >= self.team_size.value:
            from .exceptions import TeamSizeMismatchError

            raise TeamSizeMismatchError(
                f"Team {self.team_id} is already full"
            )
        self.members.append(player)
        if request is not None:
            self.requests.append(request)

    def remove_player(self, player: Player) -> None:
        if player in self.members:
            self.members.remove(player)
            self.requests = [
                r for r in self.requests if r.player.player_id != player.player_id
            ]


@dataclass
class Match:
    match_id: str = field(default_factory=lambda: str(uuid4()))
    team_size: TeamSize = TeamSize.ONE_V_ONE
    team_a: Team = field(default_factory=Team)
    team_b: Team = field(default_factory=Team)
    status: MatchStatus = MatchStatus.PENDING
    created_at: float = field(default_factory=time)
    original_skill_range: tuple[float, float] = (0.0, 0.0)

    @property
    def all_players(self) -> list[Player]:
        return [*self.team_a.members, *self.team_b.members]

    def cancel(self) -> None:
        self.status = MatchStatus.CANCELLED

    def confirm(self) -> None:
        self.status = MatchStatus.CONFIRMED

    def fail(self) -> None:
        self.status = MatchStatus.FAILED
