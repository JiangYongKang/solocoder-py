import pytest

from solocoder_py.elo_rating import EloEngine, Matcher


@pytest.fixture
def make_engine():
    def _factory(initial_rating: float = 1000.0) -> EloEngine:
        return EloEngine(initial_rating=initial_rating)
    return _factory


@pytest.fixture
def make_matcher():
    def _factory(engine: EloEngine, max_rating_diff: float = 200.0) -> Matcher:
        return Matcher(engine=engine, max_rating_diff=max_rating_diff)
    return _factory
