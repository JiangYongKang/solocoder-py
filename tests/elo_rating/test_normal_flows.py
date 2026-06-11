from __future__ import annotations

import pytest

from solocoder_py.elo_rating import (
    EloEngine,
    MatchResult,
    Matcher,
)


def _make_veteran_player(engine: EloEngine, name: str, rating: float) -> "Player":
    from solocoder_py.elo_rating import Player
    player = engine.register_player(name=name, initial_rating=rating)
    player.games_played = 30
    return player


class TestHighRatingBeatsLowRating:
    def test_high_rating_win_small_gain(self, make_engine):
        engine = make_engine()
        high = _make_veteran_player(engine, "High", 1600.0)
        low = _make_veteran_player(engine, "Low", 1200.0)

        record = engine.settle_match(high.player_id, low.player_id, MatchResult.WIN)

        assert record.player_a_delta > 0
        assert record.player_b_delta < 0
        assert abs(record.player_a_delta) < 10.0
        assert abs(record.player_b_delta) < 10.0
        assert record.player_a_new_rating > 1600.0
        assert record.player_b_new_rating < 1200.0

    def test_high_rating_gain_less_than_low_rating_gain(self, make_engine):
        engine = make_engine()
        high = _make_veteran_player(engine, "High", 1600.0)
        low = _make_veteran_player(engine, "Low", 1200.0)
        high.games_played = 30
        low.games_played = 30

        record_high_win = engine.settle_match(high.player_id, low.player_id, MatchResult.WIN)
        high_gain = abs(record_high_win.player_a_delta)

        high.rating = 1600.0
        low.rating = 1200.0

        record_low_win = engine.settle_match(low.player_id, high.player_id, MatchResult.WIN)
        low_gain = abs(record_low_win.player_a_delta)

        assert high_gain < low_gain

    def test_rating_gap_correlates_with_gain_size(self, make_engine):
        engine = make_engine()

        gaps = [50, 200, 400, 800]
        high_gains = []

        for gap in gaps:
            p1 = _make_veteran_player(engine, f"H{gap}", 1200.0 + gap)
            p2 = _make_veteran_player(engine, f"L{gap}", 1200.0)
            rec = engine.settle_match(p1.player_id, p2.player_id, MatchResult.WIN)
            high_gains.append(abs(rec.player_a_delta))

        for i in range(1, len(high_gains)):
            assert high_gains[i] < high_gains[i - 1]


class TestLowRatingBeatsHighRating:
    def test_low_rating_win_large_gain(self, make_engine):
        engine = make_engine()
        high = _make_veteran_player(engine, "High", 1600.0)
        low = _make_veteran_player(engine, "Low", 1200.0)

        record = engine.settle_match(low.player_id, high.player_id, MatchResult.WIN)

        assert record.player_a_delta > 0
        assert record.player_b_delta < 0
        assert abs(record.player_a_delta) > 15.0
        assert abs(record.player_b_delta) > 15.0

    def test_low_rating_upset_recorded_correctly(self, make_engine):
        engine = make_engine()
        high = _make_veteran_player(engine, "High", 1500.0)
        low = _make_veteran_player(engine, "Low", 1000.0)

        old_high = high.rating
        old_low = low.rating

        engine.settle_match(low.player_id, high.player_id, MatchResult.WIN)

        assert low.rating > old_low
        assert high.rating < old_high
        assert low.wins == 1
        assert high.losses == 1
        assert low.games_played == 31
        assert high.games_played == 31


class TestDrawMatch:
    def test_draw_equal_ratings_no_change(self, make_engine):
        engine = make_engine()
        a = _make_veteran_player(engine, "A", 1200.0)
        b = _make_veteran_player(engine, "B", 1200.0)

        record = engine.settle_match(a.player_id, b.player_id, MatchResult.DRAW)

        assert record.player_a_delta == pytest.approx(0.0, abs=0.001)
        assert record.player_b_delta == pytest.approx(0.0, abs=0.001)
        assert record.player_a_new_rating == pytest.approx(1200.0, abs=0.001)
        assert record.player_b_new_rating == pytest.approx(1200.0, abs=0.001)

    def test_draw_unequal_ratings_high_rating_drops(self, make_engine):
        engine = make_engine()
        high = _make_veteran_player(engine, "High", 1500.0)
        low = _make_veteran_player(engine, "Low", 1100.0)

        record = engine.settle_match(high.player_id, low.player_id, MatchResult.DRAW)

        assert record.player_a_delta < 0
        assert record.player_b_delta > 0

    def test_draw_changes_are_smaller_than_win_changes(self, make_engine):
        engine = make_engine()
        a1 = _make_veteran_player(engine, "A1", 1200.0)
        b1 = _make_veteran_player(engine, "B1", 1200.0)

        draw_rec = engine.settle_match(a1.player_id, b1.player_id, MatchResult.DRAW)
        draw_total_delta = abs(draw_rec.player_a_delta) + abs(draw_rec.player_b_delta)

        a2 = _make_veteran_player(engine, "A2", 1200.0)
        b2 = _make_veteran_player(engine, "B2", 1200.0)

        win_rec = engine.settle_match(a2.player_id, b2.player_id, MatchResult.WIN)
        win_total_delta = abs(win_rec.player_a_delta) + abs(win_rec.player_b_delta)

        assert draw_total_delta < win_total_delta

    def test_draw_records_draw_count(self, make_engine):
        engine = make_engine()
        a = _make_veteran_player(engine, "A", 1200.0)
        b = _make_veteran_player(engine, "B", 1200.0)

        engine.settle_match(a.player_id, b.player_id, MatchResult.DRAW)

        assert a.draws == 1
        assert b.draws == 1
        assert a.wins == 0
        assert a.losses == 0


class TestMatchByRatingDifference:
    def test_find_closest_rating_match(self, make_engine, make_matcher):
        engine = make_engine()
        matcher = make_matcher(engine, max_rating_diff=500.0)

        me = _make_veteran_player(engine, "Me", 1000.0)
        _make_veteran_player(engine, "Far", 1300.0)
        _make_veteran_player(engine, "Close", 1010.0)
        _make_veteran_player(engine, "Mid", 1100.0)

        best = matcher.find_best_match(me.player_id)
        matched = engine.get_player(best.player_id)

        assert matched.name == "Close"
        assert best.score_difference == pytest.approx(10.0)

    def test_rank_candidates_sorted_by_difference(self, make_engine, make_matcher):
        engine = make_engine()
        matcher = make_matcher(engine, max_rating_diff=500.0)

        me = _make_veteran_player(engine, "Me", 1000.0)
        _make_veteran_player(engine, "P1", 1050.0)
        _make_veteran_player(engine, "P2", 980.0)
        _make_veteran_player(engine, "P3", 1020.0)

        ranked = matcher.rank_candidates(me.player_id)

        assert len(ranked) == 3
        assert ranked[0].score_difference <= ranked[1].score_difference
        assert ranked[1].score_difference <= ranked[2].score_difference

        prev_diff = 0.0
        for cand in ranked:
            assert cand.score_difference >= prev_diff
            prev_diff = cand.score_difference

    def test_filter_out_exceeds_max_diff(self, make_engine, make_matcher):
        engine = make_engine()
        matcher = make_matcher(engine, max_rating_diff=100.0)

        me = _make_veteran_player(engine, "Me", 1000.0)
        _make_veteran_player(engine, "Within", 1050.0)
        _make_veteran_player(engine, "Beyond", 1200.0)
        _make_veteran_player(engine, "Exactly", 1100.0)

        ranked = matcher.rank_candidates(me.player_id)
        names = [engine.get_player(c.player_id).name for c in ranked]

        assert "Within" in names
        assert "Exactly" in names
        assert "Beyond" not in names

    def test_find_matches_top_n(self, make_engine, make_matcher):
        engine = make_engine()
        matcher = make_matcher(engine, max_rating_diff=500.0)

        me = _make_veteran_player(engine, "Me", 1000.0)
        for i in range(10):
            _make_veteran_player(engine, f"P{i}", 1000.0 + i * 10)

        top3 = matcher.find_matches(me.player_id, top_n=3)

        assert len(top3) == 3
        assert top3[0].score_difference <= top3[1].score_difference
        assert top3[1].score_difference <= top3[2].score_difference

    def test_can_match_within_threshold(self, make_engine, make_matcher):
        engine = make_engine()
        matcher = make_matcher(engine, max_rating_diff=100.0)

        a = _make_veteran_player(engine, "A", 1000.0)
        b = _make_veteran_player(engine, "B", 1080.0)
        c = _make_veteran_player(engine, "C", 1300.0)

        assert matcher.can_match(a.player_id, b.player_id) is True
        assert matcher.can_match(a.player_id, c.player_id) is False

    def test_validate_match_success(self, make_engine, make_matcher):
        engine = make_engine()
        matcher = make_matcher(engine, max_rating_diff=200.0)

        a = _make_veteran_player(engine, "A", 1000.0)
        b = _make_veteran_player(engine, "B", 1100.0)

        matcher.validate_match(a.player_id, b.player_id)
