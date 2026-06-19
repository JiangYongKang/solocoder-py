import pytest

from solocoder_py.tsdelta import (
    InvalidTimestampError,
    NonMonotonicTimestampError,
    compute_deltas,
    compute_first_order_deltas,
    compute_second_order_deltas,
    reconstruct_first_order_deltas,
    reconstruct_timestamps,
    validate_timestamps,
)


class TestValidateTimestamps:
    def test_empty_timestamps(self):
        validate_timestamps([])

    def test_single_timestamp(self):
        validate_timestamps([1000])

    def test_strictly_increasing(self):
        validate_timestamps([1000, 1001, 1002, 1003])

    def test_equal_timestamps_rejected(self):
        with pytest.raises(NonMonotonicTimestampError, match="strictly increasing"):
            validate_timestamps([1000, 1000, 1001])

    def test_decreasing_timestamps_rejected(self):
        with pytest.raises(NonMonotonicTimestampError, match="strictly increasing"):
            validate_timestamps([1003, 1002, 1001])

    def test_non_integer_rejected(self):
        with pytest.raises(InvalidTimestampError, match="must be integer"):
            validate_timestamps([1000, "not_an_int", 1002])

    def test_float_rejected(self):
        with pytest.raises(InvalidTimestampError, match="must be integer"):
            validate_timestamps([1000, 1001.5, 1002])


class TestFirstOrderDeltas:
    def test_empty_list(self):
        assert compute_first_order_deltas([]) == []

    def test_single_element(self):
        assert compute_first_order_deltas([1000]) == []

    def test_two_elements(self):
        assert compute_first_order_deltas([1000, 1005]) == [5]

    def test_equal_intervals(self):
        timestamps = [1000, 1005, 1010, 1015, 1020]
        assert compute_first_order_deltas(timestamps) == [5, 5, 5, 5]

    def test_variable_intervals(self):
        timestamps = [1000, 1001, 1003, 1006, 1010]
        assert compute_first_order_deltas(timestamps) == [1, 2, 3, 4]

    def test_large_intervals(self):
        timestamps = [0, 1000000, 2000000, 3000000]
        assert compute_first_order_deltas(timestamps) == [1000000, 1000000, 1000000]


class TestSecondOrderDeltas:
    def test_empty_list(self):
        assert compute_second_order_deltas([]) == []

    def test_single_element(self):
        assert compute_second_order_deltas([100]) == []

    def test_two_elements(self):
        assert compute_second_order_deltas([100, 100]) == [0]

    def test_constant_first_order(self):
        first_order = [5, 5, 5, 5]
        assert compute_second_order_deltas(first_order) == [0, 0, 0]

    def test_increasing_first_order(self):
        first_order = [1, 2, 3, 4, 5]
        assert compute_second_order_deltas(first_order) == [1, 1, 1, 1]

    def test_variable_first_order(self):
        first_order = [10, 8, 12, 6, 14]
        assert compute_second_order_deltas(first_order) == [-2, 4, -6, 8]


class TestComputeDeltas:
    def test_empty_timestamps(self):
        result = compute_deltas([])
        assert result.first_order_deltas == []
        assert result.second_order_deltas == []
        assert result.base_timestamp == 0
        assert result.first_delta is None
        assert result.count == 0

    def test_single_timestamp(self):
        result = compute_deltas([1718841600000])
        assert result.first_order_deltas == []
        assert result.second_order_deltas == []
        assert result.base_timestamp == 1718841600000
        assert result.first_delta is None
        assert result.count == 0

    def test_two_timestamps(self):
        timestamps = [1000, 1005]
        result = compute_deltas(timestamps)
        assert result.first_order_deltas == [5]
        assert result.second_order_deltas == []
        assert result.base_timestamp == 1000
        assert result.first_delta == 5
        assert result.count == 0

    def test_equal_interval_timestamps(self):
        base = 1718841600000
        timestamps = [base + i * 1000 for i in range(10)]
        result = compute_deltas(timestamps)

        assert result.base_timestamp == base
        assert result.first_delta == 1000
        assert result.first_order_deltas == [1000] * 9
        assert result.second_order_deltas == [0] * 8
        assert result.count == 8

    def test_variable_interval_timestamps(self):
        base = 1000
        timestamps = [base, base + 10, base + 25, base + 45, base + 70]
        result = compute_deltas(timestamps)

        assert result.base_timestamp == base
        assert result.first_delta == 10
        assert result.first_order_deltas == [10, 15, 20, 25]
        assert result.second_order_deltas == [5, 5, 5]
        assert result.count == 3

    def test_skip_validation(self):
        timestamps = [1000, 999, 1001]
        result = compute_deltas(timestamps, validate=False)
        assert result.first_order_deltas == [-1, 2]
        assert result.second_order_deltas == [3]


class TestReconstructFirstOrderDeltas:
    def test_empty_second_order(self):
        result = reconstruct_first_order_deltas(100, [])
        assert result == [100]

    def test_constant_second_order(self):
        result = reconstruct_first_order_deltas(10, [5, 5, 5])
        assert result == [10, 15, 20, 25]

    def test_variable_second_order(self):
        result = reconstruct_first_order_deltas(100, [-10, 20, -15])
        assert result == [100, 90, 110, 95]


class TestReconstructTimestamps:
    def test_empty(self):
        result = reconstruct_timestamps(0, None, [], expected_count=0)
        assert result == []

    def test_single_timestamp(self):
        result = reconstruct_timestamps(1000, None, [], expected_count=1)
        assert result == [1000]

    def test_two_timestamps(self):
        result = reconstruct_timestamps(1000, 5, [], expected_count=2)
        assert result == [1000, 1005]

    def test_equal_intervals(self):
        base = 1718841600000
        result = reconstruct_timestamps(base, 1000, [0, 0, 0, 0], expected_count=6)
        expected = [base + i * 1000 for i in range(6)]
        assert result == expected

    def test_variable_intervals(self):
        result = reconstruct_timestamps(1000, 10, [5, 5, 5], expected_count=5)
        assert result == [1000, 1010, 1025, 1045, 1070]

    def test_roundtrip_equal_interval(self):
        base = 1718841600000
        original = [base + i * 1000 for i in range(50)]

        deltas = compute_deltas(original)
        reconstructed = reconstruct_timestamps(
            deltas.base_timestamp,
            deltas.first_delta,
            deltas.second_order_deltas,
        )

        assert reconstructed == original

    def test_roundtrip_variable_interval(self):
        base = 1000
        original = [base, base + 1, base + 3, base + 6, base + 10, base + 15]

        deltas = compute_deltas(original)
        reconstructed = reconstruct_timestamps(
            deltas.base_timestamp,
            deltas.first_delta,
            deltas.second_order_deltas,
        )

        assert reconstructed == original

    def test_length_mismatch(self):
        with pytest.raises(Exception):
            reconstruct_timestamps(1000, 5, [], expected_count=3)
