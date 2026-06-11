from __future__ import annotations

import random

import pytest

from solocoder_py.elo_rating import (
    EloEngine,
    ForfeitMatchError,
    MatchResult,
    MatchValidationError,
    Matcher,
    Player,
    PlayerNotFoundError,
    ProtectionPeriodViolationError,
)


def _make_veteran(engine: EloEngine, name: str, rating: float) -> Player:
    p = engine.register_player(name=name, initial_rating=rating)
    p.games_played = 30
    return p


class TestCrossProtectionPeriodRejection:
    def test_settle_match_rejects_protection_vs_veteran(self, make_engine):
        engine = make_engine()

        newbie = engine.register_player(name="Newbie")
        veteran = engine.register_player(name="Veteran")
        veteran.games_played = 30

        with pytest.raises(ProtectionPeriodViolationError):
            engine.settle_match(newbie.player_id, veteran.player_id, MatchResult.WIN)

    def test_settle_match_rejects_veteran_vs_protection(self, make_engine):
        engine = make_engine()

        veteran = engine.register_player(name="Veteran")
        veteran.games_played = 30
        newbie = engine.register_player(name="Newbie")

        with pytest.raises(ProtectionPeriodViolationError):
            engine.settle_match(veteran.player_id, newbie.player_id, MatchResult.WIN)

    def test_matcher_can_match_rejects_cross_protection(self, make_engine, make_matcher):
        engine = make_engine()
        matcher = make_matcher(engine, max_rating_diff=500.0)

        newbie = engine.register_player(name="Newbie")
        veteran = engine.register_player(name="Veteran")
        veteran.games_played = 30

        assert matcher.can_match(newbie.player_id, veteran.player_id) is False
        assert matcher.can_match(veteran.player_id, newbie.player_id) is False

    def test_matcher_validate_match_rejects_cross_protection(self, make_engine, make_matcher):
        engine = make_engine()
        matcher = make_matcher(engine, max_rating_diff=500.0)

        newbie = engine.register_player(name="Newbie")
        veteran = engine.register_player(name="Veteran")
        veteran.games_played = 30

        with pytest.raises(ProtectionPeriodViolationError):
            matcher.validate_match(newbie.player_id, veteran.player_id)

    def test_rank_candidates_filters_cross_protection(self, make_engine, make_matcher):
        engine = make_engine()
        matcher = make_matcher(engine, max_rating_diff=500.0)

        newbie = engine.register_player(name="Newbie", initial_rating=1000.0)
        veteran = _make_veteran(engine, "Veteran", 1000.0)
        fellow_newbie = engine.register_player(name="FellowNewbie", initial_rating=1000.0)

        newbie_candidates = matcher.rank_candidates(newbie.player_id)
        assert len(newbie_candidates) == 1
        assert newbie_candidates[0].player_id == fellow_newbie.player_id

        veteran_candidates = matcher.rank_candidates(veteran.player_id)
        assert len(veteran_candidates) == 0

    def test_protection_players_match_among_themselves(self, make_engine):
        engine = make_engine()

        a = engine.register_player(name="A")
        b = engine.register_player(name="B")

        record = engine.settle_match(a.player_id, b.player_id, MatchResult.WIN)
        assert record is not None
        assert a.games_played == 1
        assert b.games_played == 1

    def test_after_10_games_exit_protection_can_match_veterans(self, make_engine, make_matcher):
        engine = make_engine()
        matcher = make_matcher(engine, max_rating_diff=500.0)

        a = engine.register_player(name="A")
        b = engine.register_player(name="B")

        for _ in range(10):
            engine.settle_match(a.player_id, b.player_id, MatchResult.WIN)

        assert a.is_in_protection is False
        assert b.is_in_protection is False

        veteran = _make_veteran(engine, "Veteran", a.rating)

        assert matcher.can_match(a.player_id, veteran.player_id) is True


class TestForfeitMatchHandling:
    def test_forfeit_win_b_gets_penalty(self, make_engine):
        engine = make_engine()
        a = _make_veteran(engine, "A", 1200.0)
        b = _make_veteran(engine, "B", 1200.0)

        record = engine.settle_match(a.player_id, b.player_id, MatchResult.FORFEIT_WIN)

        assert record.player_a_delta > 0
        assert record.player_b_delta == -engine.FORFEIT_PENALTY
        assert b.rating == pytest.approx(1200.0 - engine.FORFEIT_PENALTY)
        assert a.wins == 1
        assert b.losses == 1

    def test_forfeit_loss_a_gets_penalty(self, make_engine):
        engine = make_engine()
        a = _make_veteran(engine, "A", 1200.0)
        b = _make_veteran(engine, "B", 1200.0)

        record = engine.settle_match(a.player_id, b.player_id, MatchResult.FORFEIT_LOSS)

        assert record.player_a_delta == -engine.FORFEIT_PENALTY
        assert record.player_b_delta > 0
        assert a.rating == pytest.approx(1200.0 - engine.FORFEIT_PENALTY)
        assert a.losses == 1
        assert b.wins == 1

    def test_forfeit_penalty_is_fixed_regardless_of_rating_gap(self, make_engine):
        engine = make_engine()

        penalties = []
        ratings = [(1000, 1500), (1200, 1200), (1800, 1000)]

        for r_a, r_b in ratings:
            a = _make_veteran(engine, f"A{r_a}{r_b}", float(r_a))
            b = _make_veteran(engine, f"B{r_a}{r_b}", float(r_b))
            rec = engine.settle_match(a.player_id, b.player_id, MatchResult.FORFEIT_WIN)
            penalties.append(rec.player_b_delta)

        for p in penalties:
            assert p == -engine.FORFEIT_PENALTY

    def test_forfeit_result_counts_as_games_played(self, make_engine):
        engine = make_engine()
        a = engine.register_player(name="A")
        b = engine.register_player(name="B")

        initial_games = a.games_played
        engine.settle_match(a.player_id, b.player_id, MatchResult.FORFEIT_WIN)

        assert a.games_played == initial_games + 1
        assert b.games_played == initial_games + 1


class TestRatingConvergence:
    def test_many_games_equal_skill_ratings_converge_together(self, make_engine):
        engine = make_engine()
        a = engine.register_player(name="A")
        b = engine.register_player(name="B")

        for _ in range(10):
            engine.settle_match(a.player_id, b.player_id, MatchResult.WIN)

        for _ in range(20):
            engine.settle_match(a.player_id, b.player_id, MatchResult.DRAW)

        for _ in range(10):
            engine.settle_match(b.player_id, a.player_id, MatchResult.WIN)

        diff = abs(a.rating - b.rating)
        assert diff < 200.0

    def test_superior_player_rating_rises_over_time(self, make_engine):
        engine = make_engine()
        strong = engine.register_player(name="Strong")
        weak = engine.register_player(name="Weak")

        initial_strong = strong.rating
        initial_weak = weak.rating

        for _ in range(50):
            engine.settle_match(strong.player_id, weak.player_id, MatchResult.WIN)

        assert strong.rating > initial_strong
        assert weak.rating < initial_weak
        assert strong.rating > weak.rating

    def test_rating_changes_get_smaller_with_more_games_veterans(self, make_engine):
        engine = make_engine()
        a = engine.register_player(name="A")
        b = engine.register_player(name="B")

        early_deltas = []
        for i in range(10):
            rec = engine.settle_match(a.player_id, b.player_id, MatchResult.WIN)
            early_deltas.append(abs(rec.player_a_delta))

        for i in range(20):
            engine.settle_match(a.player_id, b.player_id, MatchResult.WIN)

        a.rating = 1000.0
        b.rating = 1000.0

        late_deltas = []
        for i in range(10):
            rec = engine.settle_match(a.player_id, b.player_id, MatchResult.WIN)
            late_deltas.append(abs(rec.player_a_delta))

        avg_early = sum(early_deltas) / len(early_deltas)
        avg_late = sum(late_deltas) / len(late_deltas)
        assert avg_early > avg_late

    def test_50_win_rate_player_stabilizes(self, make_engine):
        random.seed(42)
        engine = make_engine()
        a = engine.register_player(name="A")
        b = engine.register_player(name="B")

        for _ in range(100):
            if random.random() < 0.5:
                engine.settle_match(a.player_id, b.player_id, MatchResult.WIN)
            else:
                engine.settle_match(b.player_id, a.player_id, MatchResult.WIN)

        for _ in range(100):
            if random.random() < 0.5:
                engine.settle_match(a.player_id, b.player_id, MatchResult.WIN)
            else:
                engine.settle_match(b.player_id, a.player_id, MatchResult.WIN)

        diff = abs(a.rating - b.rating)
        assert diff < 200.0

    def test_rating_does_not_explode_with_many_wins(self, make_engine):
        engine = make_engine()
        strong = engine.register_player(name="Strong", initial_rating=1000.0)
        weak = engine.register_player(name="Weak", initial_rating=1000.0)

        for _ in range(200):
            engine.settle_match(strong.player_id, weak.player_id, MatchResult.WIN)

        assert strong.rating < 3000.0
        assert weak.rating > 0.0


class TestOtherExceptions:
    def test_player_not_found_on_settle(self, make_engine):
        from uuid import uuid4
        engine = make_engine()
        a = engine.register_player(name="A")
        fake_id = uuid4()

        with pytest.raises(PlayerNotFoundError):
            engine.settle_match(a.player_id, fake_id, MatchResult.WIN)

    def test_player_not_found_on_get(self, make_engine):
        from uuid import uuid4
        engine = make_engine()

        with pytest.raises(PlayerNotFoundError):
            engine.get_player(uuid4())

    def test_self_match_rejected(self, make_engine):
        engine = make_engine()
        a = engine.register_player(name="A")

        with pytest.raises(MatchValidationError):
            engine.settle_match(a.player_id, a.player_id, MatchResult.WIN)

    def test_matcher_validate_self_match_rejected(self, make_engine, make_matcher):
        engine = make_engine()
        matcher = make_matcher(engine)
        a = _make_veteran(engine, "A", 1000.0)

        with pytest.raises(MatchValidationError):
            matcher.validate_match(a.player_id, a.player_id)

    def test_matcher_validate_rating_diff_exceeded(self, make_engine, make_matcher):
        engine = make_engine()
        matcher = make_matcher(engine, max_rating_diff=50.0)

        a = _make_veteran(engine, "A", 1000.0)
        b = _make_veteran(engine, "B", 1200.0)

        with pytest.raises(MatchValidationError):
            matcher.validate_match(a.player_id, b.player_id)

    def test_matcher_negative_max_diff_rejected(self, make_engine):
        engine = make_engine()

        with pytest.raises(ValueError, match="negative"):
            Matcher(engine, max_rating_diff=-10.0)

    def test_find_matches_zero_top_n_rejected(self, make_engine, make_matcher):
        engine = make_engine()
        matcher = make_matcher(engine)
        a = _make_veteran(engine, "A", 1000.0)

        with pytest.raises(ValueError, match="positive"):
            matcher.find_matches(a.player_id, top_n=0)

    def test_matcher_can_match_unknown_player_returns_false(self, make_engine, make_matcher):
        from uuid import uuid4
        engine = make_engine()
        matcher = make_matcher(engine)
        a = _make_veteran(engine, "A", 1000.0)
        fake = uuid4()

        assert matcher.can_match(a.player_id, fake) is False
        assert matcher.can_match(fake, a.player_id) is False
