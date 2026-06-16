from __future__ import annotations

import pytest

from solocoder_py.game_loop import (
    FixedTimeStepGameLoop,
    GameLoopConfig,
    GameLoopStats,
    InterpolatedState,
    InvalidTimeStepError,
    InvalidMaxCatchUpStepsError,
    GameLoopNotRunningError,
    GameStateNotInterpolableError,
)

from .conftest import SimpleState, NonInterpolableState, MockTimeProvider


# ============================================================
# GameLoopConfig Tests - Configuration Validation
# ============================================================


class TestGameLoopConfigValidation:
    def test_default_config_valid(self):
        config = GameLoopConfig()
        assert config.time_step == pytest.approx(1.0 / 60.0)
        assert config.max_catch_up_steps == 5
        assert config.enable_interpolation is True

    def test_zero_time_step_raises(self):
        with pytest.raises(InvalidTimeStepError):
            GameLoopConfig(time_step=0.0)

    def test_negative_time_step_raises(self):
        with pytest.raises(InvalidTimeStepError):
            GameLoopConfig(time_step=-0.016)

    def test_zero_max_catch_up_steps_raises(self):
        with pytest.raises(InvalidMaxCatchUpStepsError):
            GameLoopConfig(max_catch_up_steps=0)

    def test_negative_max_catch_up_steps_raises(self):
        with pytest.raises(InvalidMaxCatchUpStepsError):
            GameLoopConfig(max_catch_up_steps=-1)

    def test_custom_valid_config(self):
        config = GameLoopConfig(
            time_step=1.0 / 30.0,
            max_catch_up_steps=10,
            enable_interpolation=False,
        )
        assert config.time_step == pytest.approx(1.0 / 30.0)
        assert config.max_catch_up_steps == 10
        assert config.enable_interpolation is False


# ============================================================
# FixedTimeStepGameLoop Basic Tests
# ============================================================


class TestGameLoopBasicOperations:
    def test_initial_state_not_running(self, simple_state: SimpleState):
        loop = FixedTimeStepGameLoop(simple_state)
        assert loop.is_running is False
        assert loop.stats.total_logic_updates == 0
        assert loop.stats.total_frames == 0

    def test_start_sets_running(self, simple_state: SimpleState, mock_time: MockTimeProvider):
        loop = FixedTimeStepGameLoop(simple_state, time_provider=mock_time)
        loop.start()
        assert loop.is_running is True

    def test_start_idempotent(self, simple_state: SimpleState, mock_time: MockTimeProvider):
        loop = FixedTimeStepGameLoop(simple_state, time_provider=mock_time)
        loop.start()
        loop.start()
        assert loop.is_running is True

    def test_stop_clears_running(self, simple_state: SimpleState, mock_time: MockTimeProvider):
        loop = FixedTimeStepGameLoop(simple_state, time_provider=mock_time)
        loop.start()
        loop.stop()
        assert loop.is_running is False

    def test_reset_without_new_state(self, simple_state: SimpleState, mock_time: MockTimeProvider):
        config = GameLoopConfig(time_step=0.1)
        loop = FixedTimeStepGameLoop(simple_state, config, mock_time)
        loop.start()
        mock_time.advance(0.5)
        loop.tick()
        assert loop.stats.total_logic_updates == 5
        loop.reset()
        assert loop.is_running is False
        assert loop.stats.total_logic_updates == 0
        assert loop.current_state.position == pytest.approx(0.0)

    def test_reset_with_new_state(self, simple_state: SimpleState, mock_time: MockTimeProvider):
        loop = FixedTimeStepGameLoop(simple_state, time_provider=mock_time)
        loop.start()
        mock_time.advance(0.1)
        loop.tick()
        new_state = SimpleState(position=100.0, velocity=2.0)
        loop.reset(new_state)
        assert loop.is_running is False
        assert loop.stats.total_logic_updates == 0
        assert loop.current_state.position == pytest.approx(100.0)
        assert loop.current_state.velocity == pytest.approx(2.0)

    def test_tick_without_start_raises(self, simple_state: SimpleState):
        loop = FixedTimeStepGameLoop(simple_state)
        with pytest.raises(GameLoopNotRunningError):
            loop.tick()

    def test_current_state_returns_copy(self, simple_state: SimpleState):
        loop = FixedTimeStepGameLoop(simple_state)
        state = loop.current_state
        state.position = 999.0
        assert loop.current_state.position == pytest.approx(0.0)


# ============================================================
# Fixed Time Step Logic Update Tests - Normal Flow
# ============================================================


class TestFixedTimeStepUpdates:
    def test_single_logic_update_per_frame(self, simple_state: SimpleState, mock_time: MockTimeProvider):
        config = GameLoopConfig(time_step=0.1)
        loop = FixedTimeStepGameLoop(simple_state, config, mock_time)
        loop.start()

        mock_time.advance(0.1)
        result = loop.tick()

        assert loop.stats.total_logic_updates == 1
        assert loop.stats.total_frames == 1
        assert loop.stats.steps_this_frame == 1
        assert result.state.position == pytest.approx(0.1)

    def test_multiple_frames_single_step_each(self, simple_state: SimpleState, mock_time: MockTimeProvider):
        config = GameLoopConfig(time_step=0.1)
        loop = FixedTimeStepGameLoop(simple_state, config, mock_time)
        loop.start()

        for i in range(10):
            mock_time.advance(0.1)
            loop.tick()
            assert loop.stats.steps_this_frame == 1
            assert loop.stats.total_logic_updates == i + 1

        assert loop.current_state.position == pytest.approx(1.0)

    def test_no_logic_update_when_frame_time_less_than_step(
        self, simple_state: SimpleState, mock_time: MockTimeProvider
    ):
        config = GameLoopConfig(time_step=0.1)
        loop = FixedTimeStepGameLoop(simple_state, config, mock_time)
        loop.start()

        mock_time.advance(0.05)
        result = loop.tick()

        assert loop.stats.total_logic_updates == 0
        assert loop.stats.total_frames == 1
        assert result.state.position == pytest.approx(0.0)
        assert result.alpha == pytest.approx(0.5)

    def test_accumulator_carries_over_remaining_time(
        self, simple_state: SimpleState, mock_time: MockTimeProvider
    ):
        config = GameLoopConfig(time_step=0.1)
        loop = FixedTimeStepGameLoop(simple_state, config, mock_time)
        loop.start()

        mock_time.advance(0.15)
        loop.tick()
        assert loop.stats.total_logic_updates == 1
        assert loop.stats.accumulator == pytest.approx(0.05)

        mock_time.advance(0.1)
        loop.tick()
        assert loop.stats.total_logic_updates == 2
        assert loop.stats.accumulator == pytest.approx(0.05)

    def test_sixty_updates_per_second_default(self, simple_state: SimpleState, mock_time: MockTimeProvider):
        loop = FixedTimeStepGameLoop(simple_state, time_provider=mock_time)
        loop.start()

        for _ in range(60):
            mock_time.advance(1.0 / 60.0)
            loop.tick()

        assert loop.stats.total_logic_updates == 60
        assert loop.current_state.position == pytest.approx(1.0)


# ============================================================
# Logic Interpolation Tests
# ============================================================


class TestLogicInterpolation:
    def test_interpolation_alpha_calculation(self, simple_state: SimpleState, mock_time: MockTimeProvider):
        config = GameLoopConfig(time_step=0.1)
        loop = FixedTimeStepGameLoop(simple_state, config, mock_time)
        loop.start()

        mock_time.advance(0.07)
        result = loop.tick()
        assert result.alpha == pytest.approx(0.7)

    def test_interpolated_state_between_updates(self, simple_state: SimpleState, mock_time: MockTimeProvider):
        config = GameLoopConfig(time_step=0.1)
        loop = FixedTimeStepGameLoop(simple_state, config, mock_time)
        loop.start()

        mock_time.advance(0.1)
        loop.tick()
        assert loop.current_state.position == pytest.approx(0.1)

        mock_time.advance(0.05)
        result = loop.tick()
        assert result.alpha == pytest.approx(0.5)

        interpolated = result.get_interpolated()
        assert interpolated.position == pytest.approx(0.0 + 0.5 * 0.1)

    def test_interpolation_at_alpha_zero(self, simple_state: SimpleState, mock_time: MockTimeProvider):
        config = GameLoopConfig(time_step=0.1)
        loop = FixedTimeStepGameLoop(simple_state, config, mock_time)
        loop.start()

        mock_time.advance(0.1)
        result = loop.tick()
        assert result.alpha == pytest.approx(0.0)

        interpolated = result.get_interpolated()
        assert interpolated.position == pytest.approx(0.0)

    def test_interpolation_at_alpha_one(self, simple_state: SimpleState, mock_time: MockTimeProvider):
        config = GameLoopConfig(time_step=0.1)
        loop = FixedTimeStepGameLoop(simple_state, config, mock_time)
        loop.start()

        mock_time.advance(0.1)
        loop.tick()
        assert loop.current_state.position == pytest.approx(0.1)

        mock_time.advance(0.0999)
        result = loop.tick()
        assert result.alpha == pytest.approx(0.999, abs=0.01)

        interpolated = result.get_interpolated()
        assert interpolated.position == pytest.approx(0.0 + 0.999 * 0.1, abs=0.01)

    def test_interpolation_clamped_between_zero_and_one(
        self, simple_state: SimpleState, mock_time: MockTimeProvider
    ):
        config = GameLoopConfig(time_step=0.1)
        loop = FixedTimeStepGameLoop(simple_state, config, mock_time)
        loop.start()

        mock_time.advance(-0.05)
        result = loop.tick()
        assert result.alpha == pytest.approx(0.0)

        mock_time.advance(0.2)
        result = loop.tick()
        assert result.alpha <= 1.0

    def test_interpolation_disabled_returns_current_state(
        self, simple_state: SimpleState, mock_time: MockTimeProvider
    ):
        config = GameLoopConfig(time_step=0.1, enable_interpolation=False)
        loop = FixedTimeStepGameLoop(simple_state, config, mock_time)
        loop.start()

        mock_time.advance(0.05)
        result = loop.tick()
        assert result.alpha == pytest.approx(1.0)
        assert result.get_interpolated().position == pytest.approx(0.0)

    def test_non_interpolable_state_falls_back(
        self, non_interpolable_state: NonInterpolableState, mock_time: MockTimeProvider
    ):
        config = GameLoopConfig(time_step=0.1)
        loop = FixedTimeStepGameLoop(non_interpolable_state, config, mock_time)
        loop.start()

        mock_time.advance(0.05)
        result = loop.tick()
        assert result.alpha == pytest.approx(1.0)
        assert result.get_interpolated().value == 0

    def test_interpolation_smoothness_over_frames(self, simple_state: SimpleState, mock_time: MockTimeProvider):
        config = GameLoopConfig(time_step=0.1)
        loop = FixedTimeStepGameLoop(simple_state, config, mock_time)
        loop.start()

        positions = []
        for i in range(20):
            mock_time.advance(0.033)
            result = loop.tick()
            interpolated = result.get_interpolated()
            positions.append(interpolated.position)

        for i in range(1, len(positions)):
            assert positions[i] >= positions[i - 1] - 1e-9
            if positions[i] > positions[i - 1]:
                diff = positions[i] - positions[i - 1]
                assert diff == pytest.approx(0.033, abs=0.02)


# ============================================================
# Catch-up Compensation Tests - Boundary Conditions
# ============================================================


class TestCatchUpCompensation:
    def test_multiple_steps_in_single_frame(self, simple_state: SimpleState, mock_time: MockTimeProvider):
        config = GameLoopConfig(time_step=0.1)
        loop = FixedTimeStepGameLoop(simple_state, config, mock_time)
        loop.start()

        mock_time.advance(0.3)
        result = loop.tick()

        assert loop.stats.total_logic_updates == 3
        assert loop.stats.steps_this_frame == 3
        assert loop.stats.is_catching_up is True
        assert loop.stats.catch_up_events == 1
        assert result.state.position == pytest.approx(0.3)

    def test_catch_up_after_slow_frame(self, simple_state: SimpleState, mock_time: MockTimeProvider):
        config = GameLoopConfig(time_step=0.1)
        loop = FixedTimeStepGameLoop(simple_state, config, mock_time)
        loop.start()

        mock_time.advance(0.5)
        loop.tick()
        assert loop.stats.total_logic_updates == 5
        assert loop.stats.is_catching_up is True
        assert loop.stats.accumulator == pytest.approx(0.0)

        mock_time.advance(0.1)
        loop.tick()
        assert loop.stats.total_logic_updates == 6
        assert loop.stats.steps_this_frame == 1
        assert loop.stats.is_catching_up is False

    def test_max_catch_up_steps_limit(self, simple_state: SimpleState, mock_time: MockTimeProvider):
        config = GameLoopConfig(time_step=0.1, max_catch_up_steps=3)
        loop = FixedTimeStepGameLoop(simple_state, config, mock_time)
        loop.start()

        mock_time.advance(0.35)
        result = loop.tick()

        assert loop.stats.steps_this_frame == 3
        assert loop.stats.total_logic_updates == 3
        assert loop.stats.accumulator == pytest.approx(0.0)
        assert result.state.position == pytest.approx(0.3)

    def test_max_catch_up_steps_prevents_death_spiral(
        self, simple_state: SimpleState, mock_time: MockTimeProvider
    ):
        config = GameLoopConfig(time_step=0.1, max_catch_up_steps=2)
        loop = FixedTimeStepGameLoop(simple_state, config, mock_time)
        loop.start()

        for _ in range(10):
            mock_time.advance(0.5)
            loop.tick()
            assert loop.stats.steps_this_frame <= 2

        assert loop.stats.total_logic_updates <= 20

    def test_catch_up_stats_tracking(self, simple_state: SimpleState, mock_time: MockTimeProvider):
        config = GameLoopConfig(time_step=0.1, max_catch_up_steps=5)
        loop = FixedTimeStepGameLoop(simple_state, config, mock_time)
        loop.start()

        mock_time.advance(0.3)
        loop.tick()
        assert loop.stats.catch_up_events == 1
        assert loop.stats.is_catching_up is True

        mock_time.advance(0.1)
        loop.tick()
        assert loop.stats.catch_up_events == 1
        assert loop.stats.is_catching_up is False

        mock_time.advance(0.4)
        loop.tick()
        assert loop.stats.catch_up_events == 2

    def test_recovery_after_catch_up(self, simple_state: SimpleState, mock_time: MockTimeProvider):
        config = GameLoopConfig(time_step=0.1, max_catch_up_steps=4)
        loop = FixedTimeStepGameLoop(simple_state, config, mock_time)
        loop.start()

        mock_time.advance(0.5)
        loop.tick()
        assert loop.stats.is_catching_up is True
        assert loop.stats.accumulator == pytest.approx(0.0)

        for _ in range(5):
            mock_time.advance(0.1)
            loop.tick()
            assert loop.stats.steps_this_frame == 1
            assert loop.stats.is_catching_up is False

        assert loop.stats.total_logic_updates == 4 + 5


# ============================================================
# Frame Skip Tests - Extreme Lag Handling
# ============================================================


class TestFrameSkipExtremeLag:
    def test_extreme_lag_triggers_frame_skip(self, simple_state: SimpleState, mock_time: MockTimeProvider):
        config = GameLoopConfig(time_step=0.1, max_catch_up_steps=5)
        loop = FixedTimeStepGameLoop(simple_state, config, mock_time)
        loop.start()

        mock_time.advance(10.0)
        result = loop.tick()

        assert loop.stats.frame_skips == 1
        assert loop.stats.total_logic_updates == 1
        assert result.state.position == pytest.approx(0.1)
        assert loop.stats.accumulator == pytest.approx(0.0)

    def test_frame_skip_when_exceeds_max_accumulated(
        self, simple_state: SimpleState, mock_time: MockTimeProvider
    ):
        config = GameLoopConfig(time_step=0.1, max_catch_up_steps=3)
        max_catch_up_time = 3 * 0.1
        frame_skip_threshold = max_catch_up_time * 2
        extreme_lag = frame_skip_threshold + 0.001
        loop = FixedTimeStepGameLoop(simple_state, config, mock_time)
        loop.start()

        mock_time.advance(extreme_lag)
        loop.tick()
        assert loop.stats.frame_skips == 1

        mock_time.advance(max_catch_up_time)
        loop.tick()
        assert loop.stats.frame_skips == 1

    def test_recovery_after_frame_skip(self, simple_state: SimpleState, mock_time: MockTimeProvider):
        config = GameLoopConfig(time_step=0.1, max_catch_up_steps=3)
        loop = FixedTimeStepGameLoop(simple_state, config, mock_time)
        loop.start()

        mock_time.advance(5.0)
        loop.tick()
        assert loop.stats.frame_skips == 1
        assert loop.stats.total_logic_updates == 1

        for _ in range(10):
            mock_time.advance(0.1)
            loop.tick()

        assert loop.stats.total_logic_updates == 11
        assert loop.stats.frame_skips == 1

    def test_multiple_frame_skips(self, simple_state: SimpleState, mock_time: MockTimeProvider):
        config = GameLoopConfig(time_step=0.1, max_catch_up_steps=3)
        loop = FixedTimeStepGameLoop(simple_state, config, mock_time)
        loop.start()

        for _ in range(5):
            mock_time.advance(4.0)
            loop.tick()

        assert loop.stats.frame_skips == 5
        assert loop.stats.total_logic_updates == 5


# ============================================================
# Alpha Boundary Tests - Frame Rate Fluctuation
# ============================================================


class TestAlphaBoundaryUnderFluctuation:
    def test_alpha_never_negative(self, simple_state: SimpleState, mock_time: MockTimeProvider):
        config = GameLoopConfig(time_step=0.1)
        loop = FixedTimeStepGameLoop(simple_state, config, mock_time)
        loop.start()

        mock_time.set_time(-100.0)
        result = loop.tick()
        assert result.alpha >= 0.0

    def test_alpha_never_exceeds_one(self, simple_state: SimpleState, mock_time: MockTimeProvider):
        config = GameLoopConfig(time_step=0.1)
        loop = FixedTimeStepGameLoop(simple_state, config, mock_time)
        loop.start()

        mock_time.advance(0.999)
        result = loop.tick()
        assert result.alpha <= 1.0

    def test_alpha_stable_under_variable_frame_rate(
        self, simple_state: SimpleState, mock_time: MockTimeProvider
    ):
        import random

        random.seed(42)
        config = GameLoopConfig(time_step=0.1)
        loop = FixedTimeStepGameLoop(simple_state, config, mock_time)
        loop.start()

        for _ in range(100):
            frame_time = random.uniform(0.005, 0.05)
            mock_time.advance(frame_time)
            result = loop.tick()
            assert 0.0 <= result.alpha <= 1.0

    def test_interpolated_state_always_monotonic(
        self, simple_state: SimpleState, mock_time: MockTimeProvider
    ):
        import random

        random.seed(123)
        config = GameLoopConfig(time_step=0.1)
        loop = FixedTimeStepGameLoop(simple_state, config, mock_time)
        loop.start()

        last_position = -1.0
        for _ in range(50):
            frame_time = random.uniform(0.001, 0.2)
            mock_time.advance(frame_time)
            result = loop.tick()
            interpolated = result.get_interpolated()
            assert interpolated.position >= last_position - 1e-9
            last_position = interpolated.position


# ============================================================
# Exception and Edge Case Tests
# ============================================================


class TestExceptionAndEdgeCases:
    def test_negative_time_step_rejected(self):
        with pytest.raises(InvalidTimeStepError):
            GameLoopConfig(time_step=-0.016)

    def test_zero_time_step_rejected(self):
        with pytest.raises(InvalidTimeStepError):
            GameLoopConfig(time_step=0.0)

    def test_negative_max_catch_up_steps_rejected(self):
        with pytest.raises(InvalidMaxCatchUpStepsError):
            GameLoopConfig(max_catch_up_steps=-5)

    def test_zero_max_catch_up_steps_rejected(self):
        with pytest.raises(InvalidMaxCatchUpStepsError):
            GameLoopConfig(max_catch_up_steps=0)

    def test_tick_when_not_running_raises(self, simple_state: SimpleState):
        loop = FixedTimeStepGameLoop(simple_state)
        with pytest.raises(GameLoopNotRunningError):
            loop.tick()

    def test_state_interpolate_not_implemented_raises(self, non_interpolable_state: NonInterpolableState):
        other = NonInterpolableState(value=5)
        with pytest.raises(GameStateNotInterpolableError):
            non_interpolable_state.interpolate(other, 0.5)

    def test_interpolated_state_returns_state_when_no_interpolated(self, simple_state: SimpleState):
        interp = InterpolatedState(state=simple_state, alpha=0.5)
        result = interp.get_interpolated()
        assert result.position == pytest.approx(0.0)

    def test_interpolated_state_returns_precomputed_interpolated(self, simple_state: SimpleState):
        curr = SimpleState(position=1.0)
        interpolated = SimpleState(position=0.5)
        interp = InterpolatedState(state=curr, alpha=0.5, _interpolated=interpolated)
        result = interp.get_interpolated()
        assert result.position == pytest.approx(0.5)

    def test_interpolated_state_alpha_does_not_affect_precomputed(self, simple_state: SimpleState):
        curr = SimpleState(position=1.0)
        interpolated = SimpleState(position=0.3)
        interp = InterpolatedState(state=curr, alpha=0.0, _interpolated=interpolated)
        result = interp.get_interpolated()
        assert result.position == pytest.approx(0.3)

        interp2 = InterpolatedState(state=curr, alpha=1.0, _interpolated=interpolated)
        result2 = interp2.get_interpolated()
        assert result2.position == pytest.approx(0.3)

    def test_game_loop_stats_reset(self):
        stats = GameLoopStats(
            total_logic_updates=100,
            total_frames=60,
            catch_up_events=5,
            frame_skips=2,
            accumulator=0.5,
            current_time=10.0,
            last_logic_update_time=9.9,
            steps_this_frame=2,
            is_catching_up=True,
        )
        stats.reset()
        assert stats.total_logic_updates == 0
        assert stats.total_frames == 0
        assert stats.catch_up_events == 0
        assert stats.frame_skips == 0
        assert stats.accumulator == 0.0
        assert stats.current_time == 0.0
        assert stats.last_logic_update_time == 0.0
        assert stats.steps_this_frame == 0
        assert stats.is_catching_up is False


# ============================================================
# Full Integration Tests
# ============================================================


class TestFullIntegration:
    def test_simulation_with_variable_frame_rate(self, simple_state: SimpleState, mock_time: MockTimeProvider):
        config = GameLoopConfig(time_step=0.01, max_catch_up_steps=10)
        loop = FixedTimeStepGameLoop(simple_state, config, mock_time)
        loop.start()

        frame_times = [0.005, 0.02, 0.01, 0.015, 0.008, 0.025, 0.01, 0.01, 0.03, 0.01]

        for ft in frame_times:
            mock_time.advance(ft)
            loop.tick()

        total_time = sum(frame_times)
        expected_updates = int(total_time / config.time_step)
        assert abs(loop.stats.total_logic_updates - expected_updates) <= config.max_catch_up_steps

        final_position = loop.current_state.position
        assert final_position == pytest.approx(expected_updates * config.time_step, abs=0.01)

    def test_interpolation_produces_smooth_output(self, simple_state: SimpleState, mock_time: MockTimeProvider):
        config = GameLoopConfig(time_step=0.1)
        loop = FixedTimeStepGameLoop(simple_state, config, mock_time)
        loop.start()

        render_times = []
        positions = []

        for i in range(30):
            mock_time.advance(0.03)
            result = loop.tick()
            interp = result.get_interpolated()
            render_times.append(mock_time())
            positions.append(interp.position)

        for i in range(4, len(positions)):
            dt = render_times[i] - render_times[i - 1]
            dp = positions[i] - positions[i - 1]
            velocity = dp / dt if dt > 0 else 0
            assert abs(velocity - 1.0) < 0.15

    def test_catch_up_and_recovery_full_scenario(
        self, simple_state: SimpleState, mock_time: MockTimeProvider
    ):
        config = GameLoopConfig(time_step=0.016, max_catch_up_steps=5)
        loop = FixedTimeStepGameLoop(simple_state, config, mock_time)
        loop.start()

        for _ in range(30):
            mock_time.advance(0.016)
            loop.tick()
        assert loop.stats.total_logic_updates == 30
        assert loop.stats.is_catching_up is False

        mock_time.advance(0.1)
        loop.tick()
        assert loop.stats.steps_this_frame == 5
        assert loop.stats.is_catching_up is True
        assert loop.stats.catch_up_events == 1

        for _ in range(10):
            mock_time.advance(0.016)
            loop.tick()
            assert loop.stats.steps_this_frame == 1
            assert loop.stats.is_catching_up is False

        assert loop.stats.total_logic_updates == 30 + 5 + 10

    def test_extreme_lag_recovery(self, simple_state: SimpleState, mock_time: MockTimeProvider):
        config = GameLoopConfig(time_step=0.016, max_catch_up_steps=3)
        loop = FixedTimeStepGameLoop(simple_state, config, mock_time)
        loop.start()

        mock_time.advance(100.0)
        loop.tick()
        assert loop.stats.frame_skips == 1
        assert loop.stats.total_logic_updates == 1

        for _ in range(60):
            mock_time.advance(0.016)
            loop.tick()

        assert loop.stats.total_logic_updates == 61
        assert loop.stats.frame_skips == 1
        assert loop.current_state.position == pytest.approx(61 * 0.016, abs=0.001)
