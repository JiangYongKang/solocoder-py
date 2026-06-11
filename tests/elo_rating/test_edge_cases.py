from __future__ import annotations

import pytest

from solocoder_py.elo_rating import (
    EloEngine,
    MatchResult,
    Matcher,
    Player,
)


def _make_veteran(engine: EloEngine, name: str, rating: float) -> Player:
    p = engine.register_player(name=name, initial_rating=rating)
    p.games_played = 30
    return p


class TestSymmetricRatingChange:
    def test_identical_ratings_win_symmetry(self, make_engine):
        engine = make_engine()
        a = _make_veteran(engine, "A", 1200.0)
        b = _make_veteran(engine, "B", 1200.0)

        record = engine.settle_match(a.player_id, b.player_id, MatchResult.WIN)

        assert record.player_a_delta == pytest.approx(-record.player_b_delta, abs=0.001)
        assert record.player_a_new_rating - 1200.0 == pytest.approx(
            -(record.player_b_new_rating - 1200.0), abs=0.001
        )

    def test_identical_ratings_loss_symmetry(self, make_engine):
        engine = make_engine()
        a = _make_veteran(engine, "A", 1400.0)
        b = _make_veteran(engine, "B", 1400.0)

        record = engine.settle_match(a.player_id, b.player_id, MatchResult.LOSS)

        assert record.player_a_delta == pytest.approx(-record.player_b_delta, abs=0.001)

    def test_identical_ratings_draw_symmetry(self, make_engine):
        engine = make_engine()
        a = _make_veteran(engine, "A", 1300.0)
        b = _make_veteran(engine, "B", 1300.0)

        record = engine.settle_match(a.player_id, b.player_id, MatchResult.DRAW)

        assert record.player_a_delta == pytest.approx(0.0, abs=0.001)
        assert record.player_b_delta == pytest.approx(0.0, abs=0.001)
        assert record.player_a_delta == pytest.approx(record.player_b_delta, abs=0.001)

    def test_different_ratings_k_same_approximate_symmetry(self, make_engine):
        engine = make_engine()
        a = _make_veteran(engine, "A", 1600.0)
        b = _make_veteran(engine, "B", 1000.0)
        a.games_played = 30
        b.games_played = 30

        record = engine.settle_match(a.player_id, b.player_id, MatchResult.WIN)

        assert record.player_a_delta > 0
        assert record.player_b_delta < 0


class TestProtectionPeriodVariance:
    def test_new_player_is_in_protection(self, make_engine):
        engine = make_engine()
        p = engine.register_player(name="New")

        assert p.is_in_protection is True
        assert p.games_played == 0

    def test_player_after_threshold_not_in_protection(self, make_engine):
        engine = make_engine()
        p = engine.register_player(name="Veteran")
        p.games_played = 10

        assert p.is_in_protection is False

    def test_boundary_nine_games_still_protected(self, make_engine):
        engine = make_engine()
        p = engine.register_player(name="Almost")
        p.games_played = 9

        assert p.is_in_protection is True

    def test_protection_k_factor_larger_than_veteran(self, make_engine):
        engine = make_engine()
        newbie = engine.register_player(name="Newbie")
        veteran = engine.register_player(name="Veteran")
        veteran.games_played = 30

        assert newbie.k_factor > veteran.k_factor
        assert newbie.k_factor == 48.0
        assert veteran.k_factor == 24.0

    def test_protection_player_has_larger_delta_than_veteran(self, make_engine):
        engine1 = make_engine()
        newbie_a = engine1.register_player(name="NA")
        newbie_b = engine1.register_player(name="NB")

        rec_newbie = engine1.settle_match(newbie_a.player_id, newbie_b.player_id, MatchResult.WIN)
        newbie_delta = abs(rec_newbie.player_a_delta)

        engine2 = make_engine()
        vet_a = _make_veteran(engine2, "VA", 1000.0)
        vet_b = _make_veteran(engine2, "VB", 1000.0)

        rec_vet = engine2.settle_match(vet_a.player_id, vet_b.player_id, MatchResult.WIN)
        vet_delta = abs(rec_vet.player_a_delta)

        assert newbie_delta > vet_delta

    def test_transitional_k_factor_between_protection_and_veteran(self, make_engine):
        engine = make_engine()
        p = engine.register_player(name="Transitional")
        p.games_played = 20

        assert p.is_in_protection is False
        assert p.k_factor == 32.0

        newbie = engine.register_player(name="N")
        veteran = engine.register_player(name="V")
        veteran.games_played = 30

        assert newbie.k_factor > p.k_factor > veteran.k_factor

    def test_high_rating_veteran_k_factor_reduced(self, make_engine):
        engine = make_engine()
        high_vet = engine.register_player(name="HighVet", initial_rating=2500.0)
        high_vet.games_played = 50

        normal_vet = engine.register_player(name="NormalVet", initial_rating=1800.0)
        normal_vet.games_played = 50

        assert high_vet.k_factor == 16.0
        assert normal_vet.k_factor == 24.0
        assert high_vet.k_factor < normal_vet.k_factor


class TestEmptyCandidateList:
    def test_find_best_match_returns_none_no_other_players(self, make_engine, make_matcher):
        engine = make_engine()
        matcher = make_matcher(engine)

        me = engine.register_player(name="Me")

        assert matcher.find_best_match(me.player_id) is None

    def test_rank_candidates_empty_no_other_players(self, make_engine, make_matcher):
        engine = make_engine()
        matcher = make_matcher(engine)

        me = engine.register_player(name="Me")

        ranked = matcher.rank_candidates(me.player_id)
        assert ranked == []

    def test_find_matches_empty_returns_empty_list(self, make_engine, make_matcher):
        engine = make_engine()
        matcher = make_matcher(engine)

        me = engine.register_player(name="Me")

        result = matcher.find_matches(me.player_id, top_n=5)
        assert result == []

    def test_all_candidates_exceed_max_diff_empty(self, make_engine, make_matcher):
        engine = make_engine()
        matcher = make_matcher(engine, max_rating_diff=50.0)

        me = _make_veteran(engine, "Me", 1000.0)
        _make_veteran(engine, "Far1", 1500.0)
        _make_veteran(engine, "Far2", 1800.0)

        ranked = matcher.rank_candidates(me.player_id)
        assert ranked == []

    def test_empty_candidate_ids_list(self, make_engine, make_matcher):
        engine = make_engine()
        matcher = make_matcher(engine)

        me = _make_veteran(engine, "Me", 1000.0)
        _make_veteran(engine, "Exists", 1010.0)

        ranked = matcher.rank_candidates(me.player_id, candidate_ids=[])
        assert ranked == []

    def test_only_self_in_candidate_ids_empty(self, make_engine, make_matcher):
        engine = make_engine()
        matcher = make_matcher(engine)

        me = _make_veteran(engine, "Me", 1000.0)

        ranked = matcher.rank_candidates(me.player_id, candidate_ids=[me.player_id])
        assert ranked == []

    def test_find_best_match_within_given_candidates_empty(self, make_engine, make_matcher):
        from uuid import uuid4
        engine = make_engine()
        matcher = make_matcher(engine)

        me = _make_veteran(engine, "Me", 1000.0)
        invalid_id = uuid4()

        best = matcher.find_best_match(me.player_id, candidate_ids=[invalid_id])
        assert best is None


class TestPlayerModelEdgeCases:
    def test_win_rate_none_with_zero_games(self, make_engine):
        engine = make_engine()
        p = engine.register_player(name="Noob")

        assert p.win_rate() is None

    def test_win_rate_correct_after_wins(self, make_engine):
        engine = make_engine()
        a = engine.register_player(name="A")
        b = engine.register_player(name="B")

        for _ in range(8):
            engine.settle_match(a.player_id, b.player_id, MatchResult.WIN)

        assert a.win_rate() == pytest.approx(1.0)
        assert b.win_rate() == pytest.approx(0.0)

    def test_win_rate_half_after_draws_only(self, make_engine):
        engine = make_engine()
        a = engine.register_player(name="A")
        b = engine.register_player(name="B")

        for _ in range(4):
            engine.settle_match(a.player_id, b.player_id, MatchResult.DRAW)

        assert a.win_rate() == pytest.approx(0.5)
        assert b.win_rate() == pytest.approx(0.5)

    def test_get_all_players_empty(self, make_engine):
        engine = make_engine()
        assert engine.get_all_players() == []

    def test_get_all_players_multiple(self, make_engine):
        engine = make_engine()
        p1 = engine.register_player(name="P1")
        p2 = engine.register_player(name="P2")
        p3 = engine.register_player(name="P3")

        all_p = engine.get_all_players()
        assert len(all_p) == 3
        ids = {p.player_id for p in all_p}
        assert p1.player_id in ids
        assert p2.player_id in ids
        assert p3.player_id in ids

    def test_match_history_empty(self, make_engine):
        engine = make_engine()
        assert engine.get_match_history() == []
        assert engine.get_match_count() == 0

    def test_match_history_after_games(self, make_engine):
        engine = make_engine()
        a = engine.register_player(name="A")
        b = engine.register_player(name="B")

        for i in range(3):
            engine.settle_match(a.player_id, b.player_id, MatchResult.WIN)

        assert engine.get_match_count() == 3
        assert len(engine.get_match_history()) == 3
