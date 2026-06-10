from datetime import date


def make_date(year: int, month: int, day: int) -> date:
    return date(year, month, day)


def make_dates(dates_list: list[tuple[int, int, int]]) -> list[date]:
    return [make_date(y, m, d) for y, m, d in dates_list]
