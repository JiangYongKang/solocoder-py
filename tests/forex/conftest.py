from typing import Optional

from solocoder_py.forex import ForexConverter


def make_converter(
    max_hops: int = 5,
    max_paths_explored: Optional[int] = None,
) -> ForexConverter:
    kwargs = {"max_hops": max_hops}
    if max_paths_explored is not None:
        kwargs["max_paths_explored"] = max_paths_explored
    return ForexConverter(**kwargs)


def make_converter_with_basic_rates(
    max_hops: int = 5,
    max_paths_explored: Optional[int] = None,
) -> ForexConverter:
    kwargs = {"max_hops": max_hops}
    if max_paths_explored is not None:
        kwargs["max_paths_explored"] = max_paths_explored
    fx = ForexConverter(**kwargs)
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
