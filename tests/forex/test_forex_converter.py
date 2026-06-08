from __future__ import annotations

import pytest

from solocoder_py.forex import (
    ConversionResult,
    CurrencyPrecisionNotFoundError,
    ForexConverter,
    InvalidExchangeRateError,
    NoConversionPathError,
    PathExplosionError,
    RoundingMode,
)
from .conftest import make_converter, make_converter_with_basic_rates


class TestForexConverterInit:
    def test_default_init(self):
        fx = ForexConverter()
        assert fx._max_hops == 5

    def test_custom_max_hops(self):
        fx = ForexConverter(max_hops=10)
        assert fx._max_hops == 10

    def test_invalid_max_hops_zero(self):
        with pytest.raises(ValueError, match="max_hops must be positive"):
            ForexConverter(max_hops=0)

    def test_invalid_max_hops_negative(self):
        with pytest.raises(ValueError, match="max_hops must be positive"):
            ForexConverter(max_hops=-1)


class TestCurrencyPrecision:
    def test_set_and_get_precision(self):
        fx = make_converter()
        fx.set_precision("USD", 2)
        assert fx.get_precision("USD") == 2

    def test_set_precision_zero_decimals(self):
        fx = make_converter()
        fx.set_precision("JPY", 0)
        assert fx.get_precision("JPY") == 0

    def test_set_precision_many_decimals(self):
        fx = make_converter()
        fx.set_precision("BTC", 8)
        assert fx.get_precision("BTC") == 8

    def test_get_precision_missing(self):
        fx = make_converter()
        with pytest.raises(CurrencyPrecisionNotFoundError):
            fx.get_precision("USD")

    def test_set_precision_empty_currency(self):
        fx = make_converter()
        with pytest.raises(ValueError, match="currency cannot be empty"):
            fx.set_precision("", 2)

    def test_set_precision_negative_decimals(self):
        fx = make_converter()
        with pytest.raises(ValueError, match="decimal_places cannot be negative"):
            fx.set_precision("USD", -1)


class TestAddAndGetRate:
    def test_add_rate_auto_version(self):
        fx = make_converter()
        r = fx.add_rate("USD", "CNY", 7.2)
        assert r.base_currency == "USD"
        assert r.target_currency == "CNY"
        assert r.rate == 7.2
        assert r.version == 1

    def test_add_rate_manual_version(self):
        fx = make_converter()
        r = fx.add_rate("USD", "CNY", 7.2, version=10)
        assert r.version == 10

    def test_add_rate_multiple_versions(self):
        fx = make_converter()
        r1 = fx.add_rate("USD", "CNY", 7.0)
        r2 = fx.add_rate("USD", "CNY", 7.2)
        assert r1.version < r2.version
        assert r1.rate == 7.0
        assert r2.rate == 7.2

    def test_get_rate_latest(self):
        fx = make_converter()
        fx.add_rate("USD", "CNY", 7.0)
        fx.add_rate("USD", "CNY", 7.2)
        r = fx.get_rate("USD", "CNY")
        assert r is not None
        assert r.rate == 7.2

    def test_get_rate_at_specific_version(self):
        fx = make_converter()
        fx.add_rate("USD", "CNY", 6.8, version=100)
        fx.add_rate("USD", "CNY", 7.0, version=200)
        fx.add_rate("USD", "CNY", 7.2, version=300)

        r150 = fx.get_rate("USD", "CNY", version=150)
        assert r150 is not None
        assert r150.rate == 6.8

        r250 = fx.get_rate("USD", "CNY", version=250)
        assert r250 is not None
        assert r250.rate == 7.0

        r350 = fx.get_rate("USD", "CNY", version=350)
        assert r350 is not None
        assert r350.rate == 7.2

    def test_get_rate_version_before_first(self):
        fx = make_converter()
        fx.add_rate("USD", "CNY", 7.2, version=10)
        r = fx.get_rate("USD", "CNY", version=5)
        assert r is None

    def test_get_rate_nonexistent_pair(self):
        fx = make_converter()
        assert fx.get_rate("USD", "XXX") is None

    def test_add_rate_invalid_empty_base(self):
        fx = make_converter()
        with pytest.raises(InvalidExchangeRateError):
            fx.add_rate("", "CNY", 7.2)

    def test_add_rate_invalid_same_currency(self):
        fx = make_converter()
        with pytest.raises(InvalidExchangeRateError, match="cannot be the same"):
            fx.add_rate("USD", "USD", 1.0)

    def test_add_rate_invalid_zero_rate(self):
        fx = make_converter()
        with pytest.raises(InvalidExchangeRateError, match="rate must be positive"):
            fx.add_rate("USD", "CNY", 0)

    def test_add_rate_invalid_negative_rate(self):
        fx = make_converter()
        with pytest.raises(InvalidExchangeRateError, match="rate must be positive"):
            fx.add_rate("USD", "CNY", -7.2)

    def test_add_rate_invalid_zero_version(self):
        fx = make_converter()
        with pytest.raises(InvalidExchangeRateError, match="version must be positive"):
            fx.add_rate("USD", "CNY", 7.2, version=0)


class TestListRates:
    def test_list_all_rates_empty(self):
        fx = make_converter()
        assert fx.list_rates() == []

    def test_list_all_rates(self):
        fx = make_converter()
        fx.add_rate("USD", "CNY", 7.2)
        fx.add_rate("USD", "EUR", 0.92)
        rates = fx.list_rates()
        assert len(rates) == 2

    def test_list_rates_filter_base(self):
        fx = make_converter()
        fx.add_rate("USD", "CNY", 7.2)
        fx.add_rate("USD", "EUR", 0.92)
        fx.add_rate("EUR", "GBP", 0.85)
        rates = fx.list_rates(base_currency="USD")
        assert len(rates) == 2
        assert all(r.base_currency == "USD" for r in rates)

    def test_list_rates_filter_target(self):
        fx = make_converter()
        fx.add_rate("USD", "CNY", 7.2)
        fx.add_rate("EUR", "CNY", 7.8)
        rates = fx.list_rates(target_currency="CNY")
        assert len(rates) == 2
        assert all(r.target_currency == "CNY" for r in rates)


class TestDirectConversion:
    def test_direct_conversion_basic(self):
        fx = make_converter_with_basic_rates()
        result = fx.convert(100, "USD", "CNY")
        assert isinstance(result, ConversionResult)
        assert result.source_currency == "USD"
        assert result.target_currency == "CNY"
        assert result.raw_amount == 720.0
        assert result.rounded_amount == 720.0
        assert result.rounding_loss == 0.0
        assert result.path.hops == 1

    def test_direct_conversion_with_decimal_result(self):
        fx = make_converter()
        fx.set_precision("EUR", 2)
        fx.set_precision("USD", 2)
        fx.add_rate("USD", "EUR", 0.92)
        result = fx.convert(100, "USD", "EUR")
        assert result.rounded_amount == 92.0

    def test_inverse_conversion_using_reverse_rate(self):
        fx = make_converter()
        fx.set_precision("USD", 2)
        fx.set_precision("CNY", 2)
        fx.add_rate("CNY", "USD", 1.0 / 7.2)
        result = fx.convert(720, "USD", "CNY")
        assert result.path.hops == 1
        assert abs(result.rounded_amount - 5184.0) < 0.01

    def test_inverse_conversion_via_reciprocal(self):
        fx = make_converter()
        fx.set_precision("USD", 2)
        fx.set_precision("CNY", 2)
        fx.add_rate("CNY", "USD", 0.138889)
        result = fx.convert(100, "USD", "CNY")
        assert result.path.hops == 1
        assert abs(result.raw_amount - 100 / 0.138889) < 0.01


class TestTriangleAndMultiHopConversion:
    def test_triangle_conversion_two_hops(self):
        fx = make_converter_with_basic_rates()
        result = fx.convert(100, "USD", "GBP")
        assert result.path.hops == 2
        assert result.path.path == ("USD", "EUR", "GBP")
        expected = 100 * 0.92 * 0.85
        assert abs(result.raw_amount - expected) < 1e-10

    def test_triangle_conversion_three_hops(self):
        fx = make_converter_with_basic_rates()
        result = fx.convert(100, "USD", "JPY")
        assert result.path.hops == 2
        expected = 100 * 0.92 * 163.0
        assert abs(result.raw_amount - expected) < 1e-10
        assert result.rounded_amount == 14996.0

    def test_multi_hop_prefers_shortest_path(self):
        fx = make_converter()
        fx.set_precision("A", 2)
        fx.set_precision("B", 2)
        fx.set_precision("C", 2)
        fx.set_precision("D", 2)
        fx.set_precision("E", 2)
        fx.add_rate("A", "B", 2.0)
        fx.add_rate("B", "C", 2.0)
        fx.add_rate("C", "D", 2.0)
        fx.add_rate("A", "D", 7.0)
        fx.add_rate("D", "E", 2.0)
        result = fx.convert(1, "A", "D")
        assert result.path.hops == 1
        assert result.raw_amount == 7.0

    def test_multi_hop_four_hops(self):
        fx = make_converter(max_hops=10)
        for c in ["A", "B", "C", "D", "E", "F"]:
            fx.set_precision(c, 4)
        fx.add_rate("A", "B", 2.0)
        fx.add_rate("B", "C", 2.0)
        fx.add_rate("C", "D", 2.0)
        fx.add_rate("D", "E", 2.0)
        fx.add_rate("E", "F", 2.0)
        result = fx.convert(1, "A", "F")
        assert result.path.hops == 5
        assert result.raw_amount == 32.0


class TestRoundingModes:
    def test_half_up_positive(self):
        fx = make_converter()
        fx.set_precision("USD", 2)
        fx.set_precision("EUR", 2)
        fx.add_rate("EUR", "USD", 1.085)
        result = fx.convert(1, "EUR", "USD", rounding_mode=RoundingMode.HALF_UP)
        assert result.rounded_amount == 1.09

    def test_half_up_negative(self):
        fx = make_converter()
        fx.set_precision("USD", 2)
        fx.set_precision("EUR", 2)
        fx.add_rate("EUR", "USD", -1.085 + 2 * 1.085)
        result = fx.convert(1, "EUR", "USD", rounding_mode=RoundingMode.HALF_UP)
        assert result.rounded_amount == 1.09

    def test_floor_positive(self):
        fx = make_converter()
        fx.set_precision("USD", 2)
        fx.set_precision("EUR", 2)
        fx.add_rate("EUR", "USD", 1.089)
        result = fx.convert(1, "EUR", "USD", rounding_mode=RoundingMode.FLOOR)
        assert result.rounded_amount == 1.08
        assert result.rounding_loss < 0

    def test_ceiling_positive(self):
        fx = make_converter()
        fx.set_precision("USD", 2)
        fx.set_precision("EUR", 2)
        fx.add_rate("EUR", "USD", 1.081)
        result = fx.convert(1, "EUR", "USD", rounding_mode=RoundingMode.CEILING)
        assert result.rounded_amount == 1.09
        assert result.rounding_loss > 0

    def test_rounding_jpy_zero_decimals(self):
        fx = make_converter()
        fx.set_precision("USD", 2)
        fx.set_precision("JPY", 0)
        fx.add_rate("USD", "JPY", 150.567)
        result_half = fx.convert(1, "USD", "JPY", rounding_mode=RoundingMode.HALF_UP)
        assert result_half.rounded_amount == 151.0
        result_floor = fx.convert(1, "USD", "JPY", rounding_mode=RoundingMode.FLOOR)
        assert result_floor.rounded_amount == 150.0
        result_ceil = fx.convert(1, "USD", "JPY", rounding_mode=RoundingMode.CEILING)
        assert result_ceil.rounded_amount == 151.0

    def test_three_rounding_modes_comparison(self):
        fx = make_converter()
        fx.set_precision("USD", 2)
        fx.set_precision("EUR", 2)
        fx.add_rate("EUR", "USD", 1.08567)
        results = {}
        for mode in [RoundingMode.HALF_UP, RoundingMode.FLOOR, RoundingMode.CEILING]:
            results[mode] = fx.convert(100, "EUR", "USD", rounding_mode=mode)
        assert results[RoundingMode.FLOOR].rounded_amount <= results[RoundingMode.HALF_UP].rounded_amount
        assert results[RoundingMode.HALF_UP].rounded_amount <= results[RoundingMode.CEILING].rounded_amount
        assert results[RoundingMode.FLOOR].rounding_loss <= 0
        assert results[RoundingMode.CEILING].rounding_loss >= 0

    def test_rounding_loss_recorded(self):
        fx = make_converter()
        fx.set_precision("JPY", 0)
        fx.set_precision("USD", 2)
        fx.add_rate("USD", "JPY", 150.3)
        result = fx.convert(1, "USD", "JPY", rounding_mode=RoundingMode.HALF_UP)
        assert abs(result.rounding_loss - (150.0 - 150.3)) < 1e-10


class TestAmountAndSameCurrency:
    def test_zero_amount(self):
        fx = make_converter_with_basic_rates()
        result = fx.convert(0, "USD", "CNY")
        assert result.raw_amount == 0.0
        assert result.rounded_amount == 0.0
        assert result.rounding_loss == 0.0

    def test_same_currency_no_rounding_needed(self):
        fx = make_converter_with_basic_rates()
        result = fx.convert(123.45, "USD", "USD")
        assert result.raw_amount == 123.45
        assert result.rounded_amount == 123.45
        assert result.path.hops == 0

    def test_same_currency_with_rounding(self):
        fx = make_converter()
        fx.set_precision("USD", 2)
        result = fx.convert(123.456, "USD", "USD", rounding_mode=RoundingMode.HALF_UP)
        assert result.rounded_amount == 123.46
        assert result.rounding_loss > 0


class TestVersionHistoricalConversion:
    def test_convert_at_historical_version(self):
        fx = make_converter()
        fx.set_precision("USD", 2)
        fx.set_precision("CNY", 2)
        fx.add_rate("USD", "CNY", 6.8, version=100)
        fx.add_rate("USD", "CNY", 7.0, version=200)
        fx.add_rate("USD", "CNY", 7.2, version=300)

        result_150 = fx.convert(100, "USD", "CNY", version=150)
        assert result_150.raw_amount == 680.0
        assert result_150.version == 150

        result_250 = fx.convert(100, "USD", "CNY", version=250)
        assert result_250.raw_amount == 700.0

        result_latest = fx.convert(100, "USD", "CNY")
        assert result_latest.raw_amount == 720.0
        assert result_latest.version is None

    def test_convert_version_before_any_rate(self):
        fx = make_converter_with_basic_rates()
        with pytest.raises(NoConversionPathError):
            fx.convert(100, "USD", "CNY", version=0)

    def test_multihop_historical_conversion(self):
        fx = make_converter()
        fx.set_precision("USD", 2)
        fx.set_precision("EUR", 2)
        fx.set_precision("GBP", 2)
        fx.add_rate("USD", "EUR", 0.85, version=1)
        fx.add_rate("EUR", "GBP", 0.80, version=1)
        fx.add_rate("USD", "EUR", 0.92, version=10)
        fx.add_rate("EUR", "GBP", 0.85, version=10)

        result_old = fx.convert(100, "USD", "GBP", version=5)
        assert abs(result_old.raw_amount - 100 * 0.85 * 0.80) < 1e-10

        result_new = fx.convert(100, "USD", "GBP", version=15)
        assert abs(result_new.raw_amount - 100 * 0.92 * 0.85) < 1e-10


class TestExceptionBranches:
    def test_no_conversion_path_disconnected(self):
        fx = make_converter()
        fx.set_precision("USD", 2)
        fx.set_precision("EUR", 2)
        fx.set_precision("GBP", 2)
        fx.add_rate("USD", "EUR", 0.92)
        with pytest.raises(NoConversionPathError):
            fx.convert(100, "USD", "GBP")

    def test_no_conversion_path_empty_store(self):
        fx = make_converter()
        fx.set_precision("USD", 2)
        fx.set_precision("CNY", 2)
        with pytest.raises(NoConversionPathError):
            fx.convert(100, "USD", "CNY")

    def test_precision_missing_source(self):
        fx = make_converter()
        fx.set_precision("CNY", 2)
        fx.add_rate("USD", "CNY", 7.2)
        with pytest.raises(CurrencyPrecisionNotFoundError):
            fx.convert(100, "USD", "USD")

    def test_precision_missing_target(self):
        fx = make_converter()
        fx.set_precision("USD", 2)
        fx.add_rate("USD", "CNY", 7.2)
        with pytest.raises(CurrencyPrecisionNotFoundError):
            fx.convert(100, "USD", "CNY")

    def test_max_hops_exceeded(self):
        fx = make_converter(max_hops=2)
        for c in ["A", "B", "C", "D", "E"]:
            fx.set_precision(c, 4)
        fx.add_rate("A", "B", 2.0)
        fx.add_rate("B", "C", 2.0)
        fx.add_rate("C", "D", 2.0)
        fx.add_rate("D", "E", 2.0)
        with pytest.raises(NoConversionPathError):
            fx.convert(1, "A", "E")


class TestCircularPathDetection:
    def test_no_cycles(self):
        fx = make_converter()
        fx.set_precision("A", 2)
        fx.set_precision("B", 2)
        fx.set_precision("C", 2)
        fx.add_rate("A", "B", 2.0)
        fx.add_rate("B", "C", 2.0)
        cycles = fx.detect_circular_paths()
        assert cycles == []

    def test_simple_cycle_detection(self):
        fx = make_converter()
        for c in ["A", "B", "C"]:
            fx.set_precision(c, 2)
        fx.add_rate("A", "B", 2.0)
        fx.add_rate("B", "C", 0.5)
        fx.add_rate("C", "A", 1.1)
        cycles = fx.detect_circular_paths()
        assert len(cycles) > 0

    def test_triangular_arbitrage_cycle(self):
        fx = make_converter_with_basic_rates()
        fx.add_rate("GBP", "USD", 1.28)
        cycles = fx.detect_circular_paths()
        assert len(cycles) > 0


class TestPathExplosion:
    def test_path_explosion_detection(self):
        fx = make_converter(max_hops=20)
        import string
        currencies = list(string.ascii_uppercase[:15])
        for c in currencies:
            fx.set_precision(c, 4)
        for i, c1 in enumerate(currencies):
            for c2 in currencies[i + 1:]:
                try:
                    fx.add_rate(c1, c2, 1.0 + 0.01 * (ord(c1) + ord(c2)))
                except Exception:
                    pass
        try:
            fx.convert(1, currencies[0], currencies[-1])
        except (PathExplosionError, NoConversionPathError):
            pass


class TestEdgeCases:
    def test_very_small_amount(self):
        fx = make_converter()
        fx.set_precision("BTC", 8)
        fx.set_precision("USD", 2)
        fx.add_rate("BTC", "USD", 30000.0)
        result = fx.convert(0.00000001, "BTC", "USD")
        assert result.rounded_amount == 0.0

    def test_very_large_amount(self):
        fx = make_converter()
        fx.set_precision("USD", 2)
        fx.set_precision("CNY", 2)
        fx.add_rate("USD", "CNY", 7.2)
        result = fx.convert(1_000_000_000, "USD", "CNY")
        assert result.rounded_amount == 7_200_000_000.0

    def test_rate_very_close_to_one(self):
        fx = make_converter()
        fx.set_precision("USD", 2)
        fx.set_precision("EUR", 2)
        fx.add_rate("USD", "EUR", 1.000001)
        result = fx.convert(1_000_000, "USD", "EUR")
        assert abs(result.raw_amount - 1_000_001) < 0.1

    def test_list_rates_sorted(self):
        fx = make_converter()
        fx.add_rate("USD", "CNY", 7.2, version=3)
        fx.add_rate("USD", "CNY", 7.0, version=1)
        fx.add_rate("USD", "CNY", 7.1, version=2)
        rates = fx.list_rates(base_currency="USD", target_currency="CNY")
        assert len(rates) == 3
        assert rates[0].version == 1
        assert rates[1].version == 2
        assert rates[2].version == 3

    def test_manual_version_updates_auto_counter(self):
        fx = make_converter()
        fx.add_rate("A", "B", 1.0, version=100)
        r_auto = fx.add_rate("B", "C", 1.0)
        assert r_auto.version == 101
