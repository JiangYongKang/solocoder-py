from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4


class MatchResult(str, Enum):
    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"
    FORFEIT_WIN = "forfeit_win"
    FORFEIT_LOSS = "forfeit_loss"


@dataclass
class Player:
    player_id: UUID = field(default_factory=uuid4)
    name: str = ""
    rating: float = 1000.0
    games_played: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0

    @property
    def is_in_protection(self) -> bool:
        return self.games_played < 10

    @property
    def k_factor(self) -> float:
        if self.is_in_protection:
            return 48.0
        if self.games_played < 30:
            return 32.0
        if self.rating >= 2400:
            return 16.0
        return 24.0

    def win_rate(self) -> Optional[float]:
        if self.games_played == 0:
            return None
        return (self.wins + 0.5 * self.draws) / self.games_played


@dataclass
class MatchRecord:
    match_id: UUID = field(default_factory=uuid4)
    player_a_id: UUID = field(default_factory=uuid4)
    player_b_id: UUID = field(default_factory=uuid4)
    result: MatchResult = MatchResult.DRAW
    player_a_old_rating: float = 1000.0
    player_b_old_rating: float = 1000.0
    player_a_new_rating: float = 1000.0
    player_b_new_rating: float = 1000.0
    player_a_delta: float = 0.0
    player_b_delta: float = 0.0


@dataclass
class MatchCandidate:
    player_id: UUID
    rating: float
    score_difference: float
    is_in_protection: bool
