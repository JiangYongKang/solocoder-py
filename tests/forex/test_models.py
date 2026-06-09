from __future__ import annotations

import pytest

from solocoder_py.forex import (
    ConversionPath,
    ConversionResult,
    CurrencyPrecision,
    ExchangeRate,
    InvalidExchangeRateError,
    RoundingMode,
)


class TestRoundingMode:
    def test_rounding_mode_values(self):
        assert RoundingMode.HALF_UP == "half_up"
        assert RoundingMode.FLOOR == "floor"
        assert RoundingMode.CEILING == "ceiling"

    def test_rounding_mode_is_enum(self):
        assert isinstance(RoundingMode.HALF_UP, RoundingMode)
        assert isinstance(RoundingMode.FLOOR, RoundingMode)
        assert isinstance(RoundingMode.CEILING, RoundingMode)


class TestExchangeRate:
    def test_valid_rate_creation(self):
        r = ExchangeRate(base_currency="USD", target_currency="CNY", rate=7.2, version=1)
        assert r.base_currency == "USD"
        assert r.target_currency == "CNY"
        assert r.rate == 7.2
        assert r.version == 1

    def test_rate_is_immutable(self):
        r = ExchangeRate(base_currency="USD", target_currency="CNY", rate=7.2, version=1)
        with pytest.raises(Exception):
            r.rate = 8.0

    def test_empty_base_currency(self):
        with pytest.raises(InvalidExchangeRateError, match="base_currency cannot be empty"):
            ExchangeRate(base_currency="", target_currency="CNY", rate=7.2, version=1)

    def test_empty_target_currency(self):
        with pytest.raises(InvalidExchangeRateError, match="target_currency cannot be empty"):
            ExchangeRate(base_currency="USD", target_currency="", rate=7.2, version=1)

    def test_same_currency(self):
        with pytest.raises(InvalidExchangeRateError, match="cannot be the same"):
            ExchangeRate(base_currency="USD", target_currency="USD", rate=1.0, version=1)

    def test_zero_rate(self):
        with pytest.raises(InvalidExchangeRateError, match="rate must be positive"):
            ExchangeRate(base_currency="USD", target_currency="CNY", rate=0, version=1)

    def test_negative_rate(self):
        with pytest.raises(InvalidExchangeRateError, match="rate must be positive"):
            ExchangeRate(base_currency="USD", target_currency="CNY", rate=-7.2, version=1)

    def test_zero_version_is_valid_for_derived_rates(self):
        r = ExchangeRate(base_currency="USD", target_currency="CNY", rate=7.2, version=0)
        assert r.version == 0

    def test_negative_version(self):
        with pytest.raises(InvalidExchangeRateError, match="version cannot be negative"):
            ExchangeRate(base_currency="USD", target_currency="CNY", rate=7.2, version=-1)


class TestCurrencyPrecision:
    def test_valid_precision(self):
        p = CurrencyPrecision(currency="USD", decimal_places=2)
        assert p.currency == "USD"
        assert p.decimal_places == 2

    def test_zero_decimal_places(self):
        p = CurrencyPrecision(currency="JPY", decimal_places=0)
        assert p.decimal_places == 0

    def test_many_decimal_places(self):
        p = CurrencyPrecision(currency="BTC", decimal_places=8)
        assert p.decimal_places == 8

    def test_empty_currency(self):
        with pytest.raises(ValueError, match="currency cannot be empty"):
            CurrencyPrecision(currency="", decimal_places=2)

    def test_negative_decimal_places(self):
        with pytest.raises(ValueError, match="decimal_places cannot be negative"):
            CurrencyPrecision(currency="USD", decimal_places=-1)


class TestConversionPath:
    def test_single_hop_path(self):
        r = ExchangeRate(base_currency="USD", target_currency="CNY", rate=7.2, version=1)
        path = ConversionPath(path=("USD", "CNY"), rates=(r,))
        assert path.length == 1
        assert path.hops == 1
        assert path.compute_rate() == 7.2

    def test_multi_hop_path(self):
        r1 = ExchangeRate(base_currency="USD", target_currency="EUR", rate=0.92, version=1)
        r2 = ExchangeRate(base_currency="EUR", target_currency="GBP", rate=0.85, version=1)
        path = ConversionPath(path=("USD", "EUR", "GBP"), rates=(r1, r2))
        assert path.length == 2
        assert path.hops == 2
        assert abs(path.compute_rate() - 0.92 * 0.85) < 1e-10

    def test_empty_path(self):
        path = ConversionPath(path=("USD", "USD"), rates=())
        assert path.length == 0
        assert path.hops == 0
        assert path.compute_rate() == 1.0


class TestConversionResult:
    def test_basic_result(self):
        r = ExchangeRate(base_currency="USD", target_currency="CNY", rate=7.2, version=1)
        path = ConversionPath(path=("USD", "CNY"), rates=(r,))
        result = ConversionResult(
            amount=100.0,
            source_currency="USD",
            target_currency="CNY",
            raw_amount=720.0,
            rounded_amount=720.0,
            rounding_loss=0.0,
            path=path,
            rounding_mode=RoundingMode.HALF_UP,
            target_decimal_places=2,
        )
        assert result.amount == 100.0
        assert result.source_currency == "USD"
        assert result.target_currency == "CNY"
        assert result.raw_amount == 720.0
        assert result.rounded_amount == 720.0
        assert result.rounding_loss == 0.0
        assert result.version is None

    def test_result_with_version(self):
        r = ExchangeRate(base_currency="USD", target_currency="CNY", rate=7.2, version=3)
        path = ConversionPath(path=("USD", "CNY"), rates=(r,))
        result = ConversionResult(
            amount=100.0,
            source_currency="USD",
            target_currency="CNY",
            raw_amount=720.0,
            rounded_amount=720.0,
            rounding_loss=0.0,
            path=path,
            rounding_mode=RoundingMode.HALF_UP,
            target_decimal_places=2,
            version=3,
        )
        assert result.version == 3

    def test_result_with_rounding_loss(self):
        r = ExchangeRate(base_currency="USD", target_currency="JPY", rate=150.123, version=1)
        path = ConversionPath(path=("USD", "JPY"), rates=(r,))
        result = ConversionResult(
            amount=100.0,
            source_currency="USD",
            target_currency="JPY",
            raw_amount=15012.3,
            rounded_amount=15012.0,
            rounding_loss=-0.3,
            path=path,
            rounding_mode=RoundingMode.FLOOR,
            target_decimal_places=0,
        )
        assert result.rounding_loss == -0.3
