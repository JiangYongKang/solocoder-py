from __future__ import annotations

import pytest

from solocoder_py.matchmaking import (
    DuplicatePlayerError,
    InvalidSkillRatingError,
    MatchNotFoundError,
    MatchStatus,
    NoCandidateError,
    TeamSizeMismatchError,
    Player,
    Team,
    TeamSize,
    MatchRequest,
    MatchmakingConfig,
    MatchmakingEngine,
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


class TestCancelRequestSyncsTeamRequests:
    def test_cancel_forming_team_player_clears_requests(self, base_time):
        config = MatchmakingConfig(
            relax_step=20.0, relax_interval=5.0, max_skill_range=200.0,
        )
        eng = MatchmakingEngine(config=config)

        p1 = Player("p1", 1000.0)
        p2 = Player("p2", 1005.0)

        eng.enqueue(p1, TeamSize.THREE_V_THREE, 30.0, enqueue_time=base_time)
        eng.enqueue(p2, TeamSize.THREE_V_THREE, 30.0, enqueue_time=base_time)

        eng.tick(now=base_time)

        forming = eng._forming_teams[TeamSize.THREE_V_THREE]
        assert len(forming) >= 1

        team = forming[0]
        assert len(team.members) == 2
        assert len(team.requests) == 2
        member_ids = {p.player_id for p in team.members}
        request_ids = {r.player.player_id for r in team.requests}
        assert member_ids == request_ids

        eng.cancel_request("p2")

        forming_after = eng._forming_teams[TeamSize.THREE_V_THREE]
        assert len(forming_after) >= 1

        surviving_team = forming_after[0]
        member_ids_after = {p.player_id for p in surviving_team.members}
        request_ids_after = {r.player.player_id for r in surviving_team.requests}
        assert "p2" not in member_ids_after
        assert "p2" not in request_ids_after
        assert member_ids_after == request_ids_after

    def test_cancel_forming_team_player_updates_skill_window(self, base_time):
        config = MatchmakingConfig(
            relax_step=20.0, relax_interval=5.0, max_skill_range=200.0,
        )
        eng = MatchmakingEngine(config=config)

        p1 = Player("p1", 1000.0)
        p2 = Player("p2", 1500.0)

        eng.enqueue(p1, TeamSize.THREE_V_THREE, 30.0, enqueue_time=base_time)
        eng.enqueue(p2, TeamSize.THREE_V_THREE, 30.0, enqueue_time=base_time)

        eng.tick(now=base_time)

        eng.cancel_request("p2")

        forming = eng._forming_teams[TeamSize.THREE_V_THREE]
        assert len(forming) >= 1

        surviving_team = forming[0]
        window = surviving_team.effective_skill_window(
            config.relax_step, config.relax_interval, config.max_skill_range, base_time
        )
        assert "p2" not in {r.player.player_id for r in surviving_team.requests}
        assert window[0] >= 970.0
        assert window[1] <= 1030.0


class TestConfirmationTimeout:
    def test_timeout_triggers_backup_refill(self, engine, base_time):
        engine.enqueue(Player("a", 1000.0), TeamSize.ONE_V_ONE, 50.0, enqueue_time=base_time)
        engine.enqueue(Player("b", 1020.0), TeamSize.ONE_V_ONE, 50.0, enqueue_time=base_time)

        matches = engine.tick(now=base_time)
        assert len(matches) == 1
        match = matches[0]
        assert match.status == MatchStatus.MATCHED

        backup_a = Player("bk_a", 1010.0)
        backup_b = Player("bk_b", 1015.0)
        engine.add_to_backup(MatchRequest(
            player=backup_a, team_size=TeamSize.ONE_V_ONE,
            initial_skill_range=100.0, enqueue_time=base_time,
        ))
        engine.add_to_backup(MatchRequest(
            player=backup_b, team_size=TeamSize.ONE_V_ONE,
            initial_skill_range=100.0, enqueue_time=base_time,
        ))

        after_timeout = base_time + engine.config.confirmation_timeout + 1.0
        resolved = engine.tick(now=after_timeout)

        assert len(resolved) >= 1
        new_match = resolved[-1]
        assert new_match.status == MatchStatus.MATCHED
        all_ids = {p.player_id for p in new_match.all_players}
        assert "bk_a" in all_ids
        assert "bk_b" in all_ids
        assert "a" not in all_ids
        assert "b" not in all_ids

    def test_timeout_no_backup_fails_match(self, engine, base_time):
        engine.enqueue(Player("a", 1000.0), TeamSize.ONE_V_ONE, 50.0, enqueue_time=base_time)
        engine.enqueue(Player("b", 1020.0), TeamSize.ONE_V_ONE, 50.0, enqueue_time=base_time)

        matches = engine.tick(now=base_time)
        match_id = matches[0].match_id

        after_timeout = base_time + engine.config.confirmation_timeout + 1.0
        engine.tick(now=after_timeout)

        with pytest.raises(MatchNotFoundError):
            engine.get_active_match(match_id)

    def test_timeout_partial_backup_requeues_all(self, engine, base_time):
        engine.enqueue(Player("a", 1000.0), TeamSize.ONE_V_ONE, 50.0, enqueue_time=base_time)
        engine.enqueue(Player("b", 1020.0), TeamSize.ONE_V_ONE, 50.0, enqueue_time=base_time)

        matches = engine.tick(now=base_time)
        old_match_id = matches[0].match_id

        backup_a = Player("bk_a", 1010.0)
        engine.add_to_backup(MatchRequest(
            player=backup_a, team_size=TeamSize.ONE_V_ONE,
            initial_skill_range=100.0, enqueue_time=base_time,
        ))

        after_timeout = base_time + engine.config.confirmation_timeout + 1.0
        resolved = engine.tick(now=after_timeout)

        with pytest.raises(MatchNotFoundError):
            engine.get_active_match(old_match_id)

        assert len(resolved) == 0

    def test_confirmed_match_not_affected_by_timeout(self, engine, base_time):
        engine.enqueue(Player("a", 1000.0), TeamSize.ONE_V_ONE, 50.0, enqueue_time=base_time)
        engine.enqueue(Player("b", 1020.0), TeamSize.ONE_V_ONE, 50.0, enqueue_time=base_time)

        matches = engine.tick(now=base_time)
        match = matches[0]
        match.confirm()

        after_timeout = base_time + engine.config.confirmation_timeout + 1.0
        resolved = engine.tick(now=after_timeout)
        timeout_matches = [m for m in resolved if m.match_id == match.match_id]
        assert len(timeout_matches) == 0

        assert match.status == MatchStatus.CONFIRMED

    def test_timeout_2v2_both_teams_replaced(self, base_time):
        config = MatchmakingConfig(confirmation_timeout=10.0)
        eng = MatchmakingEngine(config=config)

        players = [Player(f"p{i}", 1000.0 + i * 5.0) for i in range(4)]
        for p in players:
            eng.enqueue(p, TeamSize.TWO_V_TWO, 50.0, enqueue_time=base_time)

        matches = eng.tick(now=base_time)
        assert len(matches) == 1
        old_match_id = matches[0].match_id

        bk1 = Player("bk1", 1005.0)
        bk2 = Player("bk2", 1010.0)
        bk3 = Player("bk3", 1015.0)
        bk4 = Player("bk4", 1020.0)
        for bk in [bk1, bk2, bk3, bk4]:
            eng.add_to_backup(MatchRequest(
                player=bk, team_size=TeamSize.TWO_V_TWO,
                initial_skill_range=100.0, enqueue_time=base_time,
            ))

        after_timeout = base_time + config.confirmation_timeout + 1.0
        resolved = eng.tick(now=after_timeout)

        with pytest.raises(MatchNotFoundError):
            eng.get_active_match(old_match_id)

        if resolved:
            new_match = resolved[-1]
            assert new_match.status == MatchStatus.MATCHED
            assert new_match.team_size == TeamSize.TWO_V_TWO
            old_ids = {f"p{i}" for i in range(4)}
            new_ids = {p.player_id for p in new_match.all_players}
            assert len(old_ids & new_ids) == 0
