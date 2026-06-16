import pytest

from solocoder_py.matchmaking import (
    MatchmakingConfig,
    MatchmakingEngine,
    Player,
    TeamSize,
)


@pytest.fixture
def default_config() -> MatchmakingConfig:
    return MatchmakingConfig(
        relax_step=50.0,
        relax_interval=10.0,
        max_skill_range=500.0,
        confirmation_timeout=30.0,
    )


@pytest.fixture
def engine(default_config) -> MatchmakingEngine:
    return MatchmakingEngine(config=default_config)


@pytest.fixture
def tight_config() -> MatchmakingConfig:
    return MatchmakingConfig(
        relax_step=20.0,
        relax_interval=5.0,
        max_skill_range=200.0,
        confirmation_timeout=30.0,
    )


@pytest.fixture
def tight_engine(tight_config) -> MatchmakingEngine:
    return MatchmakingEngine(config=tight_config)


@pytest.fixture
def player_1000() -> Player:
    return Player(player_id="p1000", skill_rating=1000.0)


@pytest.fixture
def player_1020() -> Player:
    return Player(player_id="p1020", skill_rating=1020.0)


@pytest.fixture
def player_1050() -> Player:
    return Player(player_id="p1050", skill_rating=1050.0)


@pytest.fixture
def player_1100() -> Player:
    return Player(player_id="p1100", skill_rating=1100.0)


@pytest.fixture
def player_1500() -> Player:
    return Player(player_id="p1500", skill_rating=1500.0)


@pytest.fixture
def base_time() -> float:
    return 1_700_000_000.0
