from datetime import date, timedelta
from typing import List

from solocoder_py.shift_scheduler import ShiftScheduler, Staff, StaffId


def make_staff_list(count: int, prefix: str = "staff") -> List[Staff]:
    result = []
    for i in range(count):
        sid = StaffId(f"{prefix}-{i + 1}")
        result.append(Staff(staff_id=sid, name=f"{prefix.capitalize()} {i + 1}"))
    return result


def register_staff(scheduler: ShiftScheduler, staff_list: List[Staff]) -> List[StaffId]:
    return [scheduler.register_staff(s) for s in staff_list]


def make_scheduler_with_staff(count: int) -> tuple[ShiftScheduler, List[StaffId]]:
    scheduler = ShiftScheduler()
    staff_list = make_staff_list(count)
    ids = register_staff(scheduler, staff_list)
    return scheduler, ids


def date_n_days_from_today(n: int, today: date | None = None) -> date:
    base = today if today is not None else date.today()
    return base + timedelta(days=n)
