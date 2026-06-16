from __future__ import annotations

import pytest

from solocoder_py.matchmaking import (
    DuplicatePlayerError,
    InvalidSkillRatingError,
    MatchNotFoundError,
    TeamSizeMismatchError,
    Player,
    Team,
    TeamSize,
    MatchRequest,
)


class TestDuplicatePlayer:
    def test_duplicate_player_enqueue_rejected(self, engine, player_1000, base_time):
        engine.enqueue(player_1000, TeamSize.ONE_V_ONE, 50.0, enqueue_time=base_time)

        with pytest.raises(DuplicatePlayerError):
            engine.enqueue(player_1000, TeamSize.ONE_V_ONE, 50.0, enqueue_time=base_time)

    def test_same_player_cannot_join_same_team_twice(self):
        team = Team(team_size=TeamSize.TWO_V_TWO)
        p = Player("dup", 1000.0)
        team.add_player(p)

        with pytest.raises(DuplicatePlayerError):
            team.add_player(p)

    def test_duplicate_backup_rejected(self, engine, player_1000, base_time):
        engine.enqueue(player_1000, TeamSize.ONE_V_ONE, 50.0, enqueue_time=base_time)

        req = MatchRequest(
            player=player_1000,
            team_size=TeamSize.ONE_V_ONE,
            initial_skill_range=100.0,
            enqueue_time=base_time,
        )
        with pytest.raises(DuplicatePlayerError):
            engine.add_to_backup(req)


class TestInvalidSkillRating:
    def test_negative_skill_rejected_on_player_creation(self):
        with pytest.raises(InvalidSkillRatingError):
            Player("bad", -1.0)

    def test_very_negative_skill_rejected(self):
        with pytest.raises(InvalidSkillRatingError):
            Player("bad2", -999.9)

    def test_zero_skill_allowed(self):
        p = Player("zero", 0.0)
        assert p.skill_rating == 0.0


class TestCancelNonexistent:
    def test_cancel_nonexistent_request(self, engine):
        with pytest.raises(MatchNotFoundError):
            engine.cancel_request("nobody")

    def test_get_nonexistent_match(self, engine):
        with pytest.raises(MatchNotFoundError):
            engine.get_active_match("non-existent-match-id")

    def test_cancel_player_in_nonexistent_match(
        self, engine, player_1000, player_1020, base_time
    ):
        engine.enqueue(player_1000, TeamSize.ONE_V_ONE, 50.0, enqueue_time=base_time)
        engine.enqueue(player_1020, TeamSize.ONE_V_ONE, 50.0, enqueue_time=base_time)

        matches = engine.tick(now=base_time)
        match = matches[0]

        with pytest.raises(MatchNotFoundError):
            engine.handle_player_cancellation(match.match_id, "nonexistent_player")

        with pytest.raises(MatchNotFoundError):
            engine.handle_player_cancellation("bad-match-id", player_1000.player_id)


class TestTeamSizeMismatch:
    def test_team_overfilled_raises(self):
        team = Team(team_size=TeamSize.ONE_V_ONE)
        team.add_player(Player("p1", 1000.0))

        with pytest.raises(TeamSizeMismatchError):
            team.add_player(Player("p2", 1010.0))

    def test_different_sizes_dont_match(self, engine, base_time):
        p_a = Player("pa", 1000.0)
        p_b = Player("pb", 1010.0)
        p_c = Player("pc", 1020.0)

        engine.enqueue(p_a, TeamSize.ONE_V_ONE, 100.0, enqueue_time=base_time)
        engine.enqueue(p_b, TeamSize.TWO_V_TWO, 100.0, enqueue_time=base_time)
        engine.enqueue(p_c, TeamSize.TWO_V_TWO, 100.0, enqueue_time=base_time)

        matches = engine.tick(now=base_time)

        solo_matches = [m for m in matches if m.team_size == TeamSize.ONE_V_ONE]
        assert len(solo_matches) == 0

        team_matches = [m for m in matches if m.team_size == TeamSize.TWO_V_TWO]
        assert len(team_matches) == 0
        assert engine.total_waiting == 3


class TestOtherEdgeCancellation:
    def test_cancel_removes_from_wait_queue(self, engine, player_1000, base_time):
        engine.enqueue(player_1000, TeamSize.ONE_V_ONE, 50.0, enqueue_time=base_time)
        assert engine.total_waiting == 1

        engine.cancel_request(player_1000.player_id)
        assert engine.total_waiting == 0
        assert player_1000.player_id not in engine._player_index

        engine.enqueue(player_1000, TeamSize.ONE_V_ONE, 50.0, enqueue_time=base_time)
        assert engine.total_waiting == 1
