from __future__ import annotations

import pytest

from solocoder_py.matchmaking import (
    MatchRequest,
    MatchStatus,
    NoCandidateError,
    Player,
    TeamSize,
)


class TestMaxWaitAndWideRange:
    def test_skill_range_capped_at_max(self, base_time):
        player = Player("p1", 1000.0)
        req = MatchRequest(
            player=player,
            team_size=TeamSize.ONE_V_ONE,
            initial_skill_range=30.0,
            enqueue_time=base_time,
        )

        very_late = base_time + 10000.0
        range_val = req.current_skill_range(50.0, 10.0, 500.0, very_late)
        assert range_val == 500.0

    def test_very_wide_range_matches_disparate_players(
        self, engine, base_time
    ):
        p_low = Player("p_low", 800.0)
        p_high = Player("p_high", 1100.0)

        engine.enqueue(p_low, TeamSize.ONE_V_ONE, 50.0, enqueue_time=base_time)
        engine.enqueue(p_high, TeamSize.ONE_V_ONE, 50.0, enqueue_time=base_time)

        for i in range(100):
            matches = engine.tick(now=base_time + i * 10.0)
            if matches:
                break
        else:
            pytest.fail("Should have matched after wide range expansion")

        assert len(matches) == 1
        all_ids = {p.player_id for p in matches[0].all_players}
        assert all_ids == {"p_low", "p_high"}

    def test_zero_initial_range_still_relaxes(self, engine, base_time):
        p_a = Player("pa", 1000.0)
        p_b = Player("pb", 1100.0)

        engine.enqueue(p_a, TeamSize.ONE_V_ONE, 0.0, enqueue_time=base_time)
        engine.enqueue(p_b, TeamSize.ONE_V_ONE, 0.0, enqueue_time=base_time)

        matches_t0 = engine.tick(now=base_time)
        assert len(matches_t0) == 0

        matches_t10 = engine.tick(now=base_time + 10.0)
        assert len(matches_t10) == 0

        matches_t20 = engine.tick(now=base_time + 20.0)
        assert len(matches_t20) == 1


class TestBackupQueueEmpty:
    def test_no_backup_candidate_fails_match(
        self, engine, player_1000, player_1020, base_time
    ):
        engine.enqueue(player_1000, TeamSize.ONE_V_ONE, 50.0, enqueue_time=base_time)
        engine.enqueue(player_1020, TeamSize.ONE_V_ONE, 50.0, enqueue_time=base_time)

        matches = engine.tick(now=base_time)
        match = matches[0]
        match_id = match.match_id

        with pytest.raises(NoCandidateError):
            engine.handle_player_cancellation(match_id, "p1000")

        retrieved = engine.get_active_match
        with pytest.raises(Exception):
            retrieved(match_id)

        assert engine.total_waiting == 1

    def test_backup_wrong_skill_skipped_then_fails(
        self, engine, player_1000, player_1020, base_time
    ):
        engine.enqueue(player_1000, TeamSize.ONE_V_ONE, 50.0, enqueue_time=base_time)
        engine.enqueue(player_1020, TeamSize.ONE_V_ONE, 50.0, enqueue_time=base_time)

        matches = engine.tick(now=base_time)
        match = matches[0]

        bad_backup = Player("bad", 9999.0)
        engine.add_to_backup(MatchRequest(
            player=bad_backup,
            team_size=TeamSize.ONE_V_ONE,
            initial_skill_range=10.0,
            enqueue_time=base_time,
        ))

        with pytest.raises(NoCandidateError):
            engine.handle_player_cancellation(match.match_id, "p1000")


class TestMixedTeamSizes:
    def test_different_team_sizes_match_independently(
        self, engine, base_time
    ):
        p1v1a = Player("solo_a", 1000.0)
        p1v1b = Player("solo_b", 1010.0)
        team_players = [Player(f"t{i}", 1000.0 + i) for i in range(4)]

        engine.enqueue(p1v1a, TeamSize.ONE_V_ONE, 50.0, enqueue_time=base_time)
        for tp in team_players:
            engine.enqueue(tp, TeamSize.TWO_V_TWO, 50.0, enqueue_time=base_time)
        engine.enqueue(p1v1b, TeamSize.ONE_V_ONE, 50.0, enqueue_time=base_time)

        matches = engine.tick(now=base_time)

        assert len(matches) == 2
        sizes = {m.team_size for m in matches}
        assert sizes == {TeamSize.ONE_V_ONE, TeamSize.TWO_V_TWO}

        solo_match = [m for m in matches if m.team_size == TeamSize.ONE_V_ONE][0]
        team_match = [m for m in matches if m.team_size == TeamSize.TWO_V_TWO][0]

        solo_ids = {p.player_id for p in solo_match.all_players}
        assert solo_ids == {"solo_a", "solo_b"}

        team_ids = {p.player_id for p in team_match.all_players}
        assert team_ids == {f"t{i}" for i in range(4)}

    def test_partial_teams_wait_for_more_players(
        self, engine, base_time
    ):
        p1 = Player("p1", 1000.0)
        p2 = Player("p2", 1005.0)

        engine.enqueue(p1, TeamSize.TWO_V_TWO, 50.0, enqueue_time=base_time)
        engine.enqueue(p2, TeamSize.TWO_V_TWO, 50.0, enqueue_time=base_time)

        matches = engine.tick(now=base_time)
        assert len(matches) == 0
        assert engine.total_waiting == 2

        p3 = Player("p3", 1010.0)
        p4 = Player("p4", 1015.0)
        engine.enqueue(p3, TeamSize.TWO_V_TWO, 50.0, enqueue_time=base_time + 1.0)
        engine.enqueue(p4, TeamSize.TWO_V_TWO, 50.0, enqueue_time=base_time + 1.0)

        matches_later = engine.tick(now=base_time + 2.0)
        assert len(matches_later) == 1
        assert len(matches_later[0].all_players) == 4
