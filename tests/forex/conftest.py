from solocoder_py.forex import ForexConverter


def make_converter(max_hops: int = 5) -> ForexConverter:
    return ForexConverter(max_hops=max_hops)


def make_converter_with_basic_rates(max_hops: int = 5) -> ForexConverter:
    fx = ForexConverter(max_hops=max_hops)
    fx.set_precision("USD", 2)
    fx.set_precision("CNY", 2)
    fx.set_precision("EUR", 2)
    fx.set_precision("JPY", 0)
    fx.set_precision("GBP", 2)
    fx.set_precision("BTC", 8)
    fx.add_rate("USD", "CNY", 7.2)
    fx.add_rate("USD", "EUR", 0.92)
    fx.add_rate("EUR", "JPY", 163.0)
    fx.add_rate("EUR", "GBP", 0.85)
    return fx
