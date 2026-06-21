import math
import pytest

from solocoder_py.ewma import (
    EWMA,
    EWMAResult,
    EWMAError,
    InvalidAlphaError,
    InvalidWarmupError,
    InfinityEncounteredError,
)


def approx_equal(a, b, tol=1e-9):
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(a - b) < tol


class TestEWMANormalFlows:
    def test_fixed_sequence_manual_recurrence(self):
        ewma = EWMA(alpha=0.5)
        values = [2.0, 4.0, 6.0, 8.0, 10.0]

        s = None
        for x in values:
            if s is None:
                s = x
            else:
                s = 0.5 * x + 0.5 * s
            ewma.update(x)

        assert approx_equal(ewma.value, s)
        assert ewma.count == 5

    def test_fixed_sequence_detailed_steps(self):
        ewma = EWMA(alpha=0.5)
        ewma.update(2.0)
        assert approx_equal(ewma.value, 2.0)
        assert ewma.count == 1

        ewma.update(4.0)
        expected = 0.5 * 4.0 + 0.5 * 2.0
        assert approx_equal(ewma.value, expected)

        ewma.update(6.0)
        expected = 0.5 * 6.0 + 0.5 * expected
        assert approx_equal(ewma.value, expected)

    def test_bias_correction_warmup_matches_theory(self):
        alpha = 0.3
        warmup = 10
        ewma = EWMA(alpha=alpha, warmup_period=warmup)

        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        s = None
        correction_power = 1.0

        for t, x in enumerate(values, 1):
            if s is None:
                s = x
            else:
                s = alpha * x + (1.0 - alpha) * s
            correction_power *= 1.0 - alpha

            ewma.update(x)

            correction = 1.0 - correction_power
            expected_corrected = s / correction
            if t < warmup:
                assert ewma.in_warmup is True
                assert approx_equal(ewma.value, expected_corrected)
            else:
                assert ewma.in_warmup is False
                assert approx_equal(ewma.value, s)

    def test_exit_warmup_after_period(self):
        alpha = 0.5
        warmup = 3
        ewma = EWMA(alpha=alpha, warmup_period=warmup)

        for i in range(warmup):
            ewma.update(float(i + 1))
            if i + 1 < warmup:
                assert ewma.in_warmup is True

        assert ewma.in_warmup is True
        assert ewma.count == warmup

        ewma.update(10.0)
        assert ewma.in_warmup is False
        assert ewma.count == warmup + 1

    def test_exit_warmup_correction_factor_near_1(self):
        alpha = 0.5
        warmup = 5
        ewma = EWMA(alpha=alpha, warmup_period=warmup)

        for i in range(warmup + 5):
            ewma.update(1.0)

        assert ewma.in_warmup is False

    def test_reset_then_recalculate(self):
        ewma = EWMA(alpha=0.5)
        ewma.update(10.0)
        ewma.update(20.0)
        assert ewma.count == 2

        ewma.reset()
        assert ewma.count == 0
        assert ewma.value is None
        assert ewma.contaminated is False
        assert ewma.last_valid is None

        ewma.update(5.0)
        ewma.update(15.0)
        expected = 0.5 * 15.0 + 0.5 * 5.0
        assert approx_equal(ewma.value, expected)
        assert ewma.count == 2

    def test_update_all_sequence(self):
        ewma = EWMA(alpha=0.5)
        values = [1.0, 2.0, 3.0]
        result = ewma.update_all(values)

        s = 1.0
        s = 0.5 * 2.0 + 0.5 * s
        s = 0.5 * 3.0 + 0.5 * s
        assert approx_equal(result, s)
        assert ewma.count == 3

    def test_initial_value_behavior(self):
        ewma = EWMA(alpha=0.5, initial_value=100.0)
        assert ewma.count == 0
        assert approx_equal(ewma.value, 100.0)

        ewma.update(50.0)
        expected = 0.5 * 50.0 + 0.5 * 100.0
        assert approx_equal(ewma.value, expected)
        assert ewma.count == 1

    def test_initial_value_with_warmup_no_bias_correction(self):
        alpha = 0.5
        initial = 100.0
        ewma = EWMA(alpha=alpha, warmup_period=10, initial_value=initial)
        assert ewma.count == 0
        assert approx_equal(ewma.value, initial)

        result = ewma.update(50.0)
        expected_raw = alpha * 50.0 + (1.0 - alpha) * initial
        assert approx_equal(result, expected_raw)
        assert approx_equal(ewma.value, expected_raw)
        assert approx_equal(ewma.raw_value, expected_raw)

        correction_power = (1.0 - alpha) ** 1
        correction = 1.0 - correction_power
        expected_corrected = (expected_raw - correction_power * initial) / correction
        assert approx_equal(ewma.corrected_value, expected_corrected)
        assert approx_equal(ewma.corrected_value, 50.0)
        assert ewma.corrected_value != ewma.raw_value
        assert ewma.in_warmup is True
        assert ewma.count == 1

    def test_initial_value_with_warmup_multiple_steps(self):
        alpha = 0.3
        warmup = 5
        initial = 100.0
        ewma = EWMA(alpha=alpha, warmup_period=warmup, initial_value=initial)

        s = initial
        correction_power = 1.0
        values = [80.0, 90.0, 70.0, 85.0, 95.0, 100.0]
        for i, x in enumerate(values):
            s = alpha * x + (1.0 - alpha) * s
            correction_power *= 1.0 - alpha
            ewma.update(x)
            assert approx_equal(ewma.value, s)
            assert approx_equal(ewma.raw_value, s)

            correction = 1.0 - correction_power
            expected_corrected = (s - correction_power * initial) / correction
            assert approx_equal(ewma.corrected_value, expected_corrected)
            assert ewma.corrected_value != ewma.raw_value

            if i + 1 < warmup:
                assert ewma.in_warmup is True
            else:
                assert ewma.in_warmup is (i + 1 <= warmup)

    def test_initial_value_zero_with_warmup(self):
        alpha = 0.5
        initial = 0.0
        ewma = EWMA(alpha=alpha, warmup_period=5, initial_value=initial)
        ewma.update(10.0)
        expected_raw = alpha * 10.0 + (1.0 - alpha) * initial
        assert approx_equal(ewma.value, expected_raw)
        assert approx_equal(ewma.raw_value, expected_raw)

        correction_power = (1.0 - alpha) ** 1
        correction = 1.0 - correction_power
        expected_corrected = (expected_raw - correction_power * initial) / correction
        assert approx_equal(ewma.corrected_value, expected_corrected)
        assert approx_equal(ewma.corrected_value, expected_raw / correction)
        assert approx_equal(ewma.corrected_value, 10.0)
        assert ewma.in_warmup is True

    def test_no_initial_value_with_warmup_has_correction(self):
        alpha = 0.5
        warmup = 5
        ewma = EWMA(alpha=alpha, warmup_period=warmup)

        ewma.update(10.0)
        raw = ewma.raw_value
        corrected = ewma.value
        corrected_alt = ewma.corrected_value
        assert approx_equal(raw, 10.0)
        correction = 1.0 - (1.0 - alpha) ** 1
        assert approx_equal(corrected, raw / correction)
        assert approx_equal(corrected_alt, raw / correction)
        assert raw != corrected
        assert ewma.in_warmup is True

    def test_raw_value_property(self):
        alpha = 0.3
        warmup = 5
        ewma = EWMA(alpha=alpha, warmup_period=warmup)

        ewma.update(10.0)
        raw = ewma.raw_value
        corrected = ewma.value
        assert approx_equal(raw, 10.0)
        correction = 1.0 - (1.0 - alpha) ** 1
        assert approx_equal(corrected, raw / correction)
        assert raw != corrected

    def test_corrected_value_property(self):
        alpha = 0.5
        warmup = 0
        ewma = EWMA(alpha=alpha, warmup_period=warmup)
        ewma.update(10.0)
        ewma.update(20.0)

        assert approx_equal(ewma.value, ewma.corrected_value)

    def test_corrected_value_independent_of_value_with_initial_value(self):
        alpha = 0.3
        initial = 200.0
        ewma = EWMA(alpha=alpha, warmup_period=10, initial_value=initial)

        ewma.update(50.0)
        raw = ewma.raw_value
        val = ewma.value
        corrected = ewma.corrected_value

        assert approx_equal(val, raw)
        assert corrected != raw
        assert approx_equal(corrected, 50.0)

    def test_corrected_value_converges_to_data_mean(self):
        alpha = 0.2
        initial = 1000.0
        ewma = EWMA(alpha=alpha, warmup_period=100, initial_value=initial)

        ewma.update(50.0)
        ewma.update(50.0)
        assert abs(ewma.corrected_value - 50.0) < 1e-6

        for _ in range(50):
            ewma.update(50.0)

        assert abs(ewma.corrected_value - 50.0) < 0.1
        assert ewma.value != ewma.corrected_value or abs(ewma.value - 50.0) < 1.0

    def test_corrected_value_after_warmup_with_initial_value(self):
        alpha = 0.5
        warmup = 2
        initial = 100.0
        ewma = EWMA(alpha=alpha, warmup_period=warmup, initial_value=initial)

        ewma.update(10.0)
        ewma.update(20.0)
        assert ewma.in_warmup is True

        ewma.update(30.0)
        assert ewma.in_warmup is False

        raw_after = ewma.raw_value
        value_after = ewma.value
        corrected_after = ewma.corrected_value

        assert approx_equal(value_after, raw_after)
        assert corrected_after != raw_after

    def test_get_result_dataclass(self):
        ewma = EWMA(alpha=0.5, warmup_period=3)
        ewma.update(1.0)
        result = ewma.get_result()

        assert isinstance(result, EWMAResult)
        assert result.count == 1
        assert result.alpha == 0.5
        assert result.in_warmup is True
        assert result.contaminated is False
        assert result.value is not None
        assert result.corrected_value is not None

    def test_copy_method(self):
        ewma = EWMA(alpha=0.5, warmup_period=5)
        ewma.update(1.0)
        ewma.update(2.0)

        copied = ewma.copy()
        assert copied.alpha == ewma.alpha
        assert copied.warmup_period == ewma.warmup_period
        assert copied.count == ewma.count
        assert approx_equal(copied.value, ewma.value)
        assert copied.in_warmup == ewma.in_warmup

        copied.update(100.0)
        assert copied.count != ewma.count

    def test_repr_string(self):
        ewma = EWMA(alpha=0.5, warmup_period=3)
        r = repr(ewma)
        assert "EWMA" in r
        assert "0.5" in r


class TestEWMABoundaryConditions:
    def test_alpha_near_zero_extreme_smoothing(self):
        alpha = 1e-6
        ewma = EWMA(alpha=alpha)
        ewma.update(100.0)
        assert approx_equal(ewma.value, 100.0)

        ewma.update(200.0)
        expected = alpha * 200.0 + (1.0 - alpha) * 100.0
        assert approx_equal(ewma.value, expected)
        assert abs(ewma.value - 100.0) < 0.01

    def test_alpha_equals_one_passthrough(self):
        ewma = EWMA(alpha=1.0)

        values = [1.0, 5.0, 3.0, 10.0, -7.0]
        for v in values:
            result = ewma.update(v)
            assert approx_equal(result, v)
            assert approx_equal(ewma.value, v)

    def test_single_data_point(self):
        ewma = EWMA(alpha=0.3)
        ewma.update(42.0)
        assert ewma.count == 1
        assert approx_equal(ewma.value, 42.0)
        assert ewma.last_valid == 42.0

    def test_single_data_point_with_warmup(self):
        ewma = EWMA(alpha=0.5, warmup_period=10)
        ewma.update(10.0)

        correction = 1.0 - (1.0 - 0.5) ** 1
        expected = 10.0 / correction
        assert approx_equal(ewma.value, expected)
        assert ewma.in_warmup is True

    def test_alpha_boundary_one(self):
        ewma = EWMA(alpha=1.0)
        ewma.update(5.0)
        assert approx_equal(ewma.value, 5.0)

    def test_alpha_boundary_just_above_zero(self):
        alpha = 1e-10
        ewma = EWMA(alpha=alpha)
        ewma.update(1.0)
        ewma.update(2.0)
        expected = alpha * 2.0 + (1.0 - alpha) * 1.0
        assert approx_equal(ewma.value, expected)

    def test_warmup_period_zero(self):
        ewma = EWMA(alpha=0.5, warmup_period=0)
        ewma.update(1.0)
        ewma.update(2.0)
        assert ewma.in_warmup is False
        expected = 0.5 * 2.0 + 0.5 * 1.0
        assert approx_equal(ewma.value, expected)

    def test_warmup_period_large(self):
        warmup = 1000
        ewma = EWMA(alpha=0.01, warmup_period=warmup)
        for i in range(500):
            ewma.update(float(i))
        assert ewma.in_warmup is True
        assert ewma.count == 500

        for i in range(500):
            ewma.update(float(i + 500))
        assert ewma.in_warmup is True
        assert ewma.count == 1000

        ewma.update(9999.0)
        assert ewma.in_warmup is False
        assert ewma.count == 1001

    def test_all_same_values(self):
        ewma = EWMA(alpha=0.3, warmup_period=5)
        for _ in range(100):
            ewma.update(5.0)
        assert approx_equal(ewma.value, 5.0, tol=1e-6)

    def test_negative_values(self):
        ewma = EWMA(alpha=0.5)
        ewma.update(-10.0)
        ewma.update(-20.0)
        expected = 0.5 * (-20.0) + 0.5 * (-10.0)
        assert approx_equal(ewma.value, expected)

    def test_large_values_numeric_stability(self):
        ewma = EWMA(alpha=0.5)
        ewma.update(1e15)
        ewma.update(1e15 + 1.0)
        assert not math.isinf(ewma.value)
        assert not math.isnan(ewma.value)


class TestEWMAErrorBranches:
    def test_alpha_zero_rejected(self):
        with pytest.raises(InvalidAlphaError):
            EWMA(alpha=0.0)

    def test_alpha_negative_rejected(self):
        with pytest.raises(InvalidAlphaError):
            EWMA(alpha=-0.5)

    def test_alpha_greater_than_one_rejected(self):
        with pytest.raises(InvalidAlphaError):
            EWMA(alpha=1.5)

    def test_alpha_nan_rejected(self):
        with pytest.raises(InvalidAlphaError):
            EWMA(alpha=float("nan"))

    def test_alpha_inf_rejected(self):
        with pytest.raises(InvalidAlphaError):
            EWMA(alpha=float("inf"))

    def test_alpha_negative_inf_rejected(self):
        with pytest.raises(InvalidAlphaError):
            EWMA(alpha=float("-inf"))

    def test_alpha_bool_rejected(self):
        with pytest.raises(InvalidAlphaError):
            EWMA(alpha=True)

    def test_alpha_non_numeric_rejected(self):
        with pytest.raises(InvalidAlphaError):
            EWMA(alpha="0.5")

    def test_warmup_negative_rejected(self):
        with pytest.raises(InvalidWarmupError):
            EWMA(alpha=0.5, warmup_period=-1)

    def test_warmup_bool_rejected(self):
        with pytest.raises(InvalidWarmupError):
            EWMA(alpha=0.5, warmup_period=True)

    def test_warmup_non_int_rejected(self):
        with pytest.raises(InvalidWarmupError):
            EWMA(alpha=0.5, warmup_period=5.5)

    def test_warmup_string_rejected(self):
        with pytest.raises(InvalidWarmupError):
            EWMA(alpha=0.5, warmup_period="5")

    def test_nan_input_skipped_state_preserved(self):
        ewma = EWMA(alpha=0.5)
        ewma.update(10.0)
        ewma.update(20.0)
        value_before_nan = ewma.value
        count_before_nan = ewma.count

        result = ewma.update(float("nan"))
        assert approx_equal(result, value_before_nan)
        assert ewma.count == count_before_nan
        assert ewma.last_valid == 20.0
        assert ewma.contaminated is False

    def test_multiple_nan_inputs(self):
        ewma = EWMA(alpha=0.5, warmup_period=5)
        ewma.update(10.0)
        val1 = ewma.value
        cnt1 = ewma.count

        for _ in range(5):
            ewma.update(float("nan"))

        assert approx_equal(ewma.value, val1)
        assert ewma.count == cnt1

    def test_nan_between_valid_values(self):
        ewma = EWMA(alpha=0.5)
        ewma.update(10.0)
        ewma.update(float("nan"))
        ewma.update(30.0)

        s = 10.0
        s = 0.5 * 30.0 + 0.5 * s
        assert approx_equal(ewma.value, s)
        assert ewma.count == 2

    def test_inf_input_triggers_contamination(self):
        ewma = EWMA(alpha=0.5)
        ewma.update(10.0)

        with pytest.raises(InfinityEncounteredError):
            ewma.update(float("inf"))

        assert ewma.contaminated is True
        assert ewma.value is None

    def test_negative_inf_input(self):
        ewma = EWMA(alpha=0.5)
        with pytest.raises(InfinityEncounteredError):
            ewma.update(float("-inf"))
        assert ewma.contaminated is True

    def test_inf_then_update_blocked(self):
        ewma = EWMA(alpha=0.5)
        ewma.update(10.0)

        with pytest.raises(InfinityEncounteredError):
            ewma.update(float("inf"))

        with pytest.raises(InfinityEncounteredError):
            ewma.update(5.0)

        assert ewma.count == 1

    def test_inf_then_reset_recovers(self):
        ewma = EWMA(alpha=0.5)
        ewma.update(10.0)

        with pytest.raises(InfinityEncounteredError):
            ewma.update(float("inf"))

        assert ewma.contaminated is True
        ewma.reset()
        assert ewma.contaminated is False
        assert ewma.count == 0
        assert ewma.value is None

        ewma.update(5.0)
        assert approx_equal(ewma.value, 5.0)
        assert ewma.count == 1

    def test_nan_before_any_data(self):
        ewma = EWMA(alpha=0.5)
        result = ewma.update(float("nan"))
        assert result is None
        assert ewma.count == 0
        assert ewma.value is None

    def test_inf_before_any_data(self):
        ewma = EWMA(alpha=0.5)
        with pytest.raises(InfinityEncounteredError):
            ewma.update(float("inf"))
        assert ewma.contaminated is True

    def test_invalid_input_type_raises(self):
        ewma = EWMA(alpha=0.5)
        with pytest.raises(EWMAError):
            ewma.update("not a number")

    def test_warmup_exceeds_reasonable_range_valid(self):
        ewma = EWMA(alpha=0.5, warmup_period=100000)
        assert ewma.warmup_period == 100000

        ewma.update(1.0)
        assert ewma.in_warmup is True

    def test_reset_with_initial_value(self):
        ewma = EWMA(alpha=0.5, initial_value=100.0)
        ewma.update(50.0)
        ewma.reset()

        assert ewma.count == 0
        assert approx_equal(ewma.value, 100.0)

    def test_initial_value_nan_ignored_in_alpha_validation(self):
        ewma = EWMA(alpha=0.5, initial_value=float("nan"))
        assert ewma.count == 0

    def test_reset_does_not_change_config(self):
        ewma = EWMA(alpha=0.3, warmup_period=7, initial_value=5.0)
        ewma.update(1.0)
        ewma.update(2.0)
        ewma.reset()

        assert ewma.alpha == 0.3
        assert ewma.warmup_period == 7
        assert approx_equal(ewma.value, 5.0)
