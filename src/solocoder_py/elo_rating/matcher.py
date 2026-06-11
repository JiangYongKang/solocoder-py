from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from .engine import EloEngine
from .exceptions import (
    EloRatingError,
    MatchValidationError,
    PlayerNotFoundError,
    ProtectionPeriodViolationError,
)
from .models import MatchCandidate, Player


class Matcher:
    DEFAULT_MAX_RATING_DIFF = 200.0

    def __init__(self, engine: EloEngine, max_rating_diff: float = DEFAULT_MAX_RATING_DIFF):
        self._engine = engine
        if max_rating_diff < 0:
            raise ValueError("max_rating_diff cannot be negative")
        self._max_rating_diff = max_rating_diff

    @property
    def max_rating_diff(self) -> float:
        return self._max_rating_diff

    @max_rating_diff.setter
    def max_rating_diff(self, value: float) -> None:
        if value < 0:
            raise ValueError("max_rating_diff cannot be negative")
        self._max_rating_diff = value

    def find_best_match(
        self,
        player_id: UUID,
        candidate_ids: Optional[List[UUID]] = None,
    ) -> Optional[MatchCandidate]:
        ranked = self.rank_candidates(player_id, candidate_ids)
        if not ranked:
            return None
        return ranked[0]

    def rank_candidates(
        self,
        player_id: UUID,
        candidate_ids: Optional[List[UUID]] = None,
    ) -> List[MatchCandidate]:
        player = self._engine.get_player(player_id)

        if candidate_ids is None:
            all_ids = [p.player_id for p in self._engine.get_all_players() if p.player_id != player_id]
        else:
            all_ids = [cid for cid in candidate_ids if cid != player_id]

        candidates: List[MatchCandidate] = []
        for cid in all_ids:
            try:
                candidate = self._engine.get_player(cid)
            except PlayerNotFoundError:
                continue

            if player.is_in_protection != candidate.is_in_protection:
                continue

            diff = abs(player.rating - candidate.rating)
            if diff > self._max_rating_diff:
                continue

            candidates.append(
                MatchCandidate(
                    player_id=candidate.player_id,
                    rating=candidate.rating,
                    score_difference=diff,
                    is_in_protection=candidate.is_in_protection,
                )
            )

        candidates.sort(key=lambda c: c.score_difference)
        return candidates

    def find_matches(
        self,
        player_id: UUID,
        top_n: int = 5,
        candidate_ids: Optional[List[UUID]] = None,
    ) -> List[MatchCandidate]:
        if top_n <= 0:
            raise ValueError("top_n must be positive")
        ranked = self.rank_candidates(player_id, candidate_ids)
        return ranked[:top_n]

    def can_match(self, player_a_id: UUID, player_b_id: UUID) -> bool:
        try:
            player_a = self._engine.get_player(player_a_id)
            player_b = self._engine.get_player(player_b_id)
        except PlayerNotFoundError:
            return False

        if player_a.player_id == player_b.player_id:
            return False

        if player_a.is_in_protection != player_b.is_in_protection:
            return False

        diff = abs(player_a.rating - player_b.rating)
        return diff <= self._max_rating_diff

    def validate_match(self, player_a_id: UUID, player_b_id: UUID) -> None:
        player_a = self._engine.get_player(player_a_id)
        player_b = self._engine.get_player(player_b_id)

        if player_a.player_id == player_b.player_id:
            raise MatchValidationError("Cannot match a player against themselves")

        if player_a.is_in_protection != player_b.is_in_protection:
            raise ProtectionPeriodViolationError(
                "Players in different protection periods cannot be matched"
            )

        diff = abs(player_a.rating - player_b.rating)
        if diff > self._max_rating_diff:
            raise MatchValidationError(
                f"Rating difference {diff} exceeds maximum allowed {self._max_rating_diff}"
            )
