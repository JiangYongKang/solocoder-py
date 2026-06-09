from datetime import datetime, timedelta
from typing import List, Tuple

from solocoder_py.booking import BookingEngine, TimeSlot


def make_datetime(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute)


def build_engine_with_daily_slots(
    start_date: datetime,
    num_days: int,
    capacity: int = 10,
    slot_hours: int = 1,
) -> Tuple[BookingEngine, List[TimeSlot]]:
    engine = BookingEngine()
    slots: List[TimeSlot] = []
    for day_offset in range(num_days):
        current_date = start_date + timedelta(days=day_offset)
        for hour in range(9, 18):
            start = current_date.replace(hour=hour, minute=0)
            end = start + timedelta(hours=slot_hours)
            slot = engine.create_time_slot(start, end, capacity)
            slots.append(slot)
    return engine, slots


def build_engine_with_continuous_slots(
    base: datetime,
    num_slots: int,
    slot_minutes: int = 60,
    capacity: int = 10,
) -> Tuple[BookingEngine, List[TimeSlot]]:
    engine = BookingEngine()
    slots: List[TimeSlot] = []
    current = base
    for _ in range(num_slots):
        end = current + timedelta(minutes=slot_minutes)
        slot = engine.create_time_slot(current, end, capacity)
        slots.append(slot)
        current = end
    return engine, slots


def build_engine_with_24h_slots(
    start_date: datetime,
    num_days: int,
    slot_hours: int = 1,
    capacity: int = 10,
) -> Tuple[BookingEngine, List[TimeSlot]]:
    engine = BookingEngine()
    slots: List[TimeSlot] = []
    current = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    total_slots = num_days * 24 // slot_hours
    for _ in range(total_slots):
        end = current + timedelta(hours=slot_hours)
        slot = engine.create_time_slot(current, end, capacity)
        slots.append(slot)
        current = end
    return engine, slots
