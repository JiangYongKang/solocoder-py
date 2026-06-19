import pytest

from solocoder_py.tsdelta import (
    InvalidSimple8bSelectorError,
    SIMPLE8B_MODES,
    Simple8bMode,
    Simple8bOverflowError,
    TruncatedDataError,
    count_blocks,
    pack_block,
    select_best_mode,
    simple8b_pack,
    simple8b_unpack,
    unpack_block,
)


class TestSimple8bModes:
    def test_mode_count(self):
        assert len(SIMPLE8B_MODES) == 15

    def test_mode_selectors(self):
        for i, mode in enumerate(SIMPLE8B_MODES):
            assert mode.selector == i

    def test_mode_bit_widths(self):
        expected_widths = [60, 30, 20, 15, 12, 10, 8, 7, 6, 5, 4, 3, 2, 1, 0]
        for mode, expected in zip(SIMPLE8B_MODES, expected_widths):
            assert mode.bit_width == expected

    def test_mode_counts(self):
        expected_counts = [1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 15, 20, 30, 60, 120]
        for mode, expected in zip(SIMPLE8B_MODES, expected_counts):
            assert mode.count == expected

    def test_mode_max_values(self):
        for mode in SIMPLE8B_MODES:
            if mode.bit_width == 0:
                assert mode.max_value == 0
            else:
                assert mode.max_value == (1 << mode.bit_width) - 1

    def test_total_bits(self):
        for mode in SIMPLE8B_MODES:
            assert mode.total_bits == 4 + mode.bit_width * mode.count
            assert mode.total_bits <= 64


class TestSelectBestMode:
    def test_empty_values(self):
        mode = select_best_mode([])
        assert mode.selector == 14

    def test_all_zeros_selects_mode_14(self):
        values = [0] * 200
        mode = select_best_mode(values)
        assert mode.selector == 14
        assert mode.bit_width == 0
        assert mode.count == 120

    def test_small_values_selects_high_mode(self):
        values = [1] * 100
        mode = select_best_mode(values)
        assert mode.selector == 13
        assert mode.bit_width == 1

    def test_medium_values(self):
        values = [15] * 50
        mode = select_best_mode(values)
        assert mode.selector == 10
        assert mode.bit_width == 4

    def test_large_values_uses_mode_0(self):
        values = [(1 << 60) - 1]
        mode = select_best_mode(values)
        assert mode.selector == 0
        assert mode.bit_width == 60

    def test_mixed_values_uses_max(self):
        values = [0, 1, 3, 7, 15]
        mode = select_best_mode(values)
        assert mode.bit_width >= 4

    def test_negative_values_rejected(self):
        with pytest.raises(Simple8bOverflowError, match="non-negative"):
            select_best_mode([-1, -2, -3])

    def test_exceeds_max_value(self):
        with pytest.raises(Simple8bOverflowError, match="exceeds maximum"):
            select_best_mode([1 << 60])


class TestPackBlock:
    def test_pack_single_value_mode_0(self):
        mode = SIMPLE8B_MODES[0]
        block = pack_block([100], mode)
        assert block & 0x0F == 0
        assert (block >> 4) & mode.max_value == 100

    def test_pack_two_values_mode_1(self):
        mode = SIMPLE8B_MODES[1]
        block = pack_block([100, 200], mode)
        assert block & 0x0F == 1
        assert (block >> 4) & mode.max_value == 100
        assert (block >> (4 + 30)) & mode.max_value == 200

    def test_pack_zeros_mode_14(self):
        mode = SIMPLE8B_MODES[14]
        block = pack_block([0] * 50, mode)
        assert block & 0x0F == 14

    def test_pack_nonzero_mode_14_rejected(self):
        mode = SIMPLE8B_MODES[14]
        with pytest.raises(Simple8bOverflowError, match="only encode zeros"):
            pack_block([0, 1, 0], mode)

    def test_value_exceeds_mode_max(self):
        mode = SIMPLE8B_MODES[13]
        with pytest.raises(Simple8bOverflowError, match="exceeds maximum"):
            pack_block([2], mode)

    def test_invalid_selector(self):
        invalid_mode = Simple8bMode(selector=15, bit_width=0, max_value=0, count=0)
        with pytest.raises(InvalidSimple8bSelectorError):
            pack_block([], invalid_mode)


class TestUnpackBlock:
    def test_unpack_mode_0(self):
        mode = SIMPLE8B_MODES[0]
        block = pack_block([12345], mode)
        values, unpacked_mode = unpack_block(block)
        assert unpacked_mode.selector == 0
        assert values[0] == 12345
        assert len(values) == 1

    def test_unpack_mode_1_two_values(self):
        mode = SIMPLE8B_MODES[1]
        block = pack_block([100, 200], mode)
        values, unpacked_mode = unpack_block(block)
        assert unpacked_mode.selector == 1
        assert values[:2] == [100, 200]
        assert len(values) == 2

    def test_unpack_mode_14_zeros(self):
        mode = SIMPLE8B_MODES[14]
        block = pack_block([0] * 120, mode)
        values, unpacked_mode = unpack_block(block)
        assert unpacked_mode.selector == 14
        assert all(v == 0 for v in values)
        assert len(values) == 120

    def test_invalid_selector_high(self):
        block = 0x0F
        with pytest.raises(InvalidSimple8bSelectorError):
            unpack_block(block)


class TestSimple8bPack:
    def test_empty_list(self):
        assert simple8b_pack([]) == b""

    def test_single_value(self):
        packed = simple8b_pack([42])
        assert len(packed) == 8
        unpacked = simple8b_unpack(packed, expected_count=1)
        assert unpacked == [42]

    def test_all_zeros(self):
        values = [0] * 240
        packed = simple8b_pack(values)
        assert len(packed) == 16
        unpacked = simple8b_unpack(packed, expected_count=240)
        assert unpacked == values

    def test_small_values(self):
        values = [1, 0, 1, 0, 1, 0] * 20
        packed = simple8b_pack(values)
        unpacked = simple8b_unpack(packed, expected_count=len(values))
        assert unpacked == values

    def test_mixed_values(self):
        values = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        packed = simple8b_pack(values)
        unpacked = simple8b_unpack(packed, expected_count=len(values))
        assert unpacked == values

    def test_large_values(self):
        values = [(1 << 30) - 1, 0, (1 << 30) - 1]
        packed = simple8b_pack(values)
        unpacked = simple8b_unpack(packed, expected_count=len(values))
        assert unpacked == values

    def test_maximum_value(self):
        max_val = (1 << 60) - 1
        packed = simple8b_pack([max_val])
        unpacked = simple8b_unpack(packed, expected_count=1)
        assert unpacked == [max_val]

    def test_multi_block(self):
        values = list(range(200))
        packed = simple8b_pack(values)
        assert len(packed) > 8
        unpacked = simple8b_unpack(packed, expected_count=200)
        assert unpacked == values


class TestSimple8bUnpack:
    def test_empty_data(self):
        assert simple8b_unpack(b"") == []

    def test_truncated_data(self):
        with pytest.raises(TruncatedDataError, match="multiple of 8"):
            simple8b_unpack(b"\x00\x01\x02")

    def test_expected_count_truncates(self):
        values = list(range(100))
        packed = simple8b_pack(values)
        unpacked = simple8b_unpack(packed, expected_count=50)
        assert unpacked == values[:50]

    def test_expected_count_larger_than_available(self):
        values = [1, 2, 3]
        packed = simple8b_pack(values)
        unpacked = simple8b_unpack(packed, expected_count=10)
        assert len(unpacked) >= 3


class TestCountBlocks:
    def test_empty(self):
        assert count_blocks(b"") == 0

    def test_single_block(self):
        assert count_blocks(b"\x00" * 8) == 1

    def test_multiple_blocks(self):
        assert count_blocks(b"\x00" * 40) == 5

    def test_truncated(self):
        with pytest.raises(TruncatedDataError):
            count_blocks(b"\x00" * 10)


class TestSimple8bRoundtrip:
    def test_roundtrip_all_zeros(self):
        for n in [0, 1, 10, 100, 1000]:
            values = [0] * n
            packed = simple8b_pack(values)
            unpacked = simple8b_unpack(packed, expected_count=n)
            assert unpacked == values, f"Failed for n={n}"

    def test_roundtrip_small_integers(self):
        for max_val in [1, 3, 7, 15, 31, 63, 127, 255, 1023]:
            values = [i % (max_val + 1) for i in range(500)]
            packed = simple8b_pack(values)
            unpacked = simple8b_unpack(packed, expected_count=500)
            assert unpacked == values, f"Failed for max_val={max_val}"

    def test_roundtrip_random_mixed(self):
        values = [0, 1, 2, 3, 10, 100, 1000, 10000, 100000, 1000000] * 10
        packed = simple8b_pack(values)
        unpacked = simple8b_unpack(packed, expected_count=len(values))
        assert unpacked == values

    def test_roundtrip_boundary_crossing(self):
        values = [15, 16] * 100
        packed = simple8b_pack(values)
        unpacked = simple8b_unpack(packed, expected_count=len(values))
        assert unpacked == values

    def test_typical_zigzag_encoded_deltas(self):
        deltas = [0, 0, 0, 2, 1, 4, 3, 0, 0, 0] * 10
        packed = simple8b_pack(deltas)
        unpacked = simple8b_unpack(packed, expected_count=len(deltas))
        assert unpacked == deltas
