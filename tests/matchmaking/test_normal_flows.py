from __future__ import annotations

import pytest

from solocoder_py.matchmaking import (
    MatchRequest,
    MatchStatus,
    Player,
    TeamSize,
)


class TestSkillRangeMatching:
    def test_1v1_skill_within_range_matches_immediately(
        self, engine, player_1000, player_1020, base_time
    ):
        engine.enqueue(player_1000, TeamSize.ONE_V_ONE, 50.0, enqueue_time=base_time)
        engine.enqueue(player_1020, TeamSize.ONE_V_ONE, 50.0, enqueue_time=base_time)

        matches = engine.tick(now=base_time)

        assert len(matches) == 1
        match = matches[0]
        assert match.team_size == TeamSize.ONE_V_ONE
        assert match.status == MatchStatus.MATCHED
        all_ids = {p.player_id for p in match.all_players}
        assert all_ids == {"p1000", "p1020"}

    def test_1v1_skill_range_relaxation_after_wait(
        self, engine, player_1000, base_time
    ):
        p_far = Player("p_far", 1150.0)
        engine.enqueue(player_1000, TeamSize.ONE_V_ONE, 50.0, enqueue_time=base_time)
        engine.enqueue(p_far, TeamSize.ONE_V_ONE, 50.0, enqueue_time=base_time)

        matches_now = engine.tick(now=base_time)
        assert len(matches_now) == 0

        later_10 = base_time + 10.0
        matches_10 = engine.tick(now=later_10)
        assert len(matches_10) == 0

        later_20 = base_time + 20.0
        matches_20 = engine.tick(now=later_20)
        assert len(matches_20) == 1
        match = matches_20[0]
        all_ids = {p.player_id for p in match.all_players}
        assert all_ids == {"p1000", "p_far"}

    def test_request_skill_range_expands_over_time(self, base_time):
        player = Player("p1", 1000.0)
        req = MatchRequest(
            player=player,
            team_size=TeamSize.ONE_V_ONE,
            initial_skill_range=30.0,
            enqueue_time=base_time,
        )

        assert req.current_skill_range(50.0, 10.0, 500.0, base_time) == 30.0
        assert req.current_skill_range(50.0, 10.0, 500.0, base_time + 9.9) == 30.0
        assert req.current_skill_range(50.0, 10.0, 500.0, base_time + 10.0) == 80.0
        assert req.current_skill_range(50.0, 10.0, 500.0, base_time + 25.0) == 130.0

    def test_request_skill_window(self, base_time):
        player = Player("p1", 1000.0)
        req = MatchRequest(
            player=player,
            team_size=TeamSize.ONE_V_ONE,
            initial_skill_range=30.0,
            enqueue_time=base_time,
        )
        lo, hi = req.current_skill_window(50.0, 10.0, 500.0, base_time)
        assert lo == 970.0
        assert hi == 1030.0


class TestTeamFormation:
    def test_2v2_team_formation_and_match(self, engine, base_time):
        players = [
            Player(f"p{i}", 1000.0 + i * 5.0) for i in range(4)
        ]

        for p in players:
            engine.enqueue(p, TeamSize.TWO_V_TWO, 50.0, enqueue_time=base_time)

        matches = engine.tick(now=base_time)

        assert len(matches) == 1
        match = matches[0]
        assert match.team_size == TeamSize.TWO_V_TWO
        assert match.team_a.is_complete
        assert match.team_b.is_complete
        assert len(match.all_players) == 4

    def test_3v3_team_formation_and_match(self, engine, base_time):
        players = [
            Player(f"p{i}", 1000.0 + i * 3.0) for i in range(6)
        ]

        for p in players:
            engine.enqueue(p, TeamSize.THREE_V_THREE, 50.0, enqueue_time=base_time)

        matches = engine.tick(now=base_time)

        assert len(matches) == 1
        match = matches[0]
        assert match.team_size == TeamSize.THREE_V_THREE
        assert len(match.all_players) == 6
        assert match.team_a.is_complete
        assert match.team_b.is_complete

    def test_team_requires_same_skill_range_to_form(
        self, tight_engine, base_time
    ):
        p_close_1 = Player("pc1", 1000.0)
        p_close_2 = Player("pc2", 1010.0)
        p_far_1 = Player("pf1", 1180.0)
        p_far_2 = Player("pf2", 1190.0)

        tight_engine.enqueue(p_close_1, TeamSize.TWO_V_TWO, 25.0, enqueue_time=base_time)
        tight_engine.enqueue(p_far_1, TeamSize.TWO_V_TWO, 25.0, enqueue_time=base_time)
        tight_engine.enqueue(p_close_2, TeamSize.TWO_V_TWO, 25.0, enqueue_time=base_time)
        tight_engine.enqueue(p_far_2, TeamSize.TWO_V_TWO, 25.0, enqueue_time=base_time)

        matches = tight_engine.tick(now=base_time)
        assert len(matches) == 0

        later = base_time + 40.0
        matches_later = tight_engine.tick(now=later)
        assert len(matches_later) == 1
        match = matches_later[0]
        all_ids = {p.player_id for p in match.all_players}
        assert all_ids == {"pc1", "pc2", "pf1", "pf2"}


class TestBackupRefill:
    def test_backup_refill_on_1v1_cancellation(
        self, engine, player_1000, player_1020, base_time
    ):
        engine.enqueue(player_1000, TeamSize.ONE_V_ONE, 50.0, enqueue_time=base_time)
        engine.enqueue(player_1020, TeamSize.ONE_V_ONE, 50.0, enqueue_time=base_time)

        matches = engine.tick(now=base_time)
        match = matches[0]

        backup_player = Player("backup", 1010.0)
        backup_req = MatchRequest(
            player=backup_player,
            team_size=TeamSize.ONE_V_ONE,
            initial_skill_range=100.0,
            enqueue_time=base_time,
        )
        engine.add_to_backup(backup_req)

        updated = engine.handle_player_cancellation(match.match_id, "p1000")
        assert updated.status == MatchStatus.MATCHED
        updated_ids = {p.player_id for p in updated.all_players}
        assert updated_ids == {"backup", "p1020"}

    def test_backup_refill_team_size_must_match(
        self, engine, base_time
    ):
        players_2v2 = [Player(f"p2v2_{i}", 1000.0) for i in range(4)]
        for p in players_2v2:
            engine.enqueue(p, TeamSize.TWO_V_TWO, 50.0, enqueue_time=base_time)

        matches = engine.tick(now=base_time)
        match = matches[0]

        wrong_size_backup = Player("wrong", 1010.0)
        engine.add_to_backup(MatchRequest(
            player=wrong_size_backup,
            team_size=TeamSize.ONE_V_ONE,
            initial_skill_range=100.0,
            enqueue_time=base_time,
        ))

        correct_backup = Player("correct", 1010.0)
        engine.add_to_backup(MatchRequest(
            player=correct_backup,
            team_size=TeamSize.TWO_V_TWO,
            initial_skill_range=100.0,
            enqueue_time=base_time,
        ))

        cancelled_id = players_2v2[0].player_id
        updated = engine.handle_player_cancellation(match.match_id, cancelled_id)
        assert updated.status == MatchStatus.MATCHED
        assert any(p.player_id == "correct" for p in updated.all_players)
