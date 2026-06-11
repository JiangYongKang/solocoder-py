from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from uuid import UUID

from .exceptions import (
    EloRatingError,
    ForfeitMatchError,
    MatchValidationError,
    PlayerNotFoundError,
    ProtectionPeriodViolationError,
)
from .models import MatchRecord, MatchResult, Player


class EloEngine:
    DEFAULT_INITIAL_RATING = 1000.0
    PROTECTION_GAME_THRESHOLD = 10
    FORFEIT_PENALTY = 20.0
    RATING_DENOMINATOR = 400.0

    def __init__(self, initial_rating: float = DEFAULT_INITIAL_RATING):
        self._players: Dict[UUID, Player] = {}
        self._match_history: List[MatchRecord] = []
        self._initial_rating = initial_rating

    def register_player(self, name: str = "", initial_rating: Optional[float] = None) -> Player:
        player = Player(
            name=name,
            rating=initial_rating if initial_rating is not None else self._initial_rating,
        )
        self._players[player.player_id] = player
        return player

    def get_player(self, player_id: UUID) -> Player:
        if player_id not in self._players:
            raise PlayerNotFoundError(f"Player {player_id} not found")
        return self._players[player_id]

    def get_all_players(self) -> List[Player]:
        return list(self._players.values())

    @staticmethod
    def expected_score(rating_a: float, rating_b: float) -> float:
        return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / EloEngine.RATING_DENOMINATOR))

    @staticmethod
    def calculate_delta(
        current_rating: float,
        opponent_rating: float,
        actual_score: float,
        k_factor: float,
    ) -> float:
        expected = EloEngine.expected_score(current_rating, opponent_rating)
        return k_factor * (actual_score - expected)

    def _validate_match(self, player_a: Player, player_b: Player) -> None:
        if player_a.player_id == player_b.player_id:
            raise MatchValidationError("Cannot match a player against themselves")
        if player_a.is_in_protection != player_b.is_in_protection:
            raise ProtectionPeriodViolationError(
                "Players in different protection periods cannot be matched"
            )

    def _get_actual_scores(self, result: MatchResult) -> Tuple[float, float]:
        if result == MatchResult.WIN:
            return (1.0, 0.0)
        if result == MatchResult.LOSS:
            return (0.0, 1.0)
        if result == MatchResult.DRAW:
            return (0.5, 0.5)
        if result == MatchResult.FORFEIT_WIN:
            return (1.0, 0.0)
        if result == MatchResult.FORFEIT_LOSS:
            return (0.0, 1.0)
        raise MatchValidationError(f"Unknown match result: {result}")

    def settle_match(
        self,
        player_a_id: UUID,
        player_b_id: UUID,
        result: MatchResult,
    ) -> MatchRecord:
        player_a = self.get_player(player_a_id)
        player_b = self.get_player(player_b_id)

        self._validate_match(player_a, player_b)

        old_rating_a = player_a.rating
        old_rating_b = player_b.rating

        score_a, score_b = self._get_actual_scores(result)

        if result in (MatchResult.FORFEIT_WIN, MatchResult.FORFEIT_LOSS):
            if result == MatchResult.FORFEIT_WIN:
                delta_a = self.calculate_delta(old_rating_a, old_rating_b, score_a, player_a.k_factor)
                delta_b = -self.FORFEIT_PENALTY
            else:
                delta_a = -self.FORFEIT_PENALTY
                delta_b = self.calculate_delta(old_rating_b, old_rating_a, score_b, player_b.k_factor)
        else:
            delta_a = self.calculate_delta(old_rating_a, old_rating_b, score_a, player_a.k_factor)
            delta_b = self.calculate_delta(old_rating_b, old_rating_a, score_b, player_b.k_factor)

        new_rating_a = old_rating_a + delta_a
        new_rating_b = old_rating_b + delta_b

        player_a.rating = new_rating_a
        player_b.rating = new_rating_b

        player_a.games_played += 1
        player_b.games_played += 1

        if result in (MatchResult.WIN, MatchResult.FORFEIT_WIN):
            player_a.wins += 1
            player_b.losses += 1
        elif result in (MatchResult.LOSS, MatchResult.FORFEIT_LOSS):
            player_a.losses += 1
            player_b.wins += 1
        elif result == MatchResult.DRAW:
            player_a.draws += 1
            player_b.draws += 1

        record = MatchRecord(
            player_a_id=player_a_id,
            player_b_id=player_b_id,
            result=result,
            player_a_old_rating=old_rating_a,
            player_b_old_rating=old_rating_b,
            player_a_new_rating=new_rating_a,
            player_b_new_rating=new_rating_b,
            player_a_delta=delta_a,
            player_b_delta=delta_b,
        )
        self._match_history.append(record)
        return record

    def get_match_history(self) -> List[MatchRecord]:
        return list(self._match_history)

    def get_match_count(self) -> int:
        return len(self._match_history)
