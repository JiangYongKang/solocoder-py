from solocoder_py.seat import ManualClock, SeatReservationManager


def make_manager(
    rows: int = 5,
    columns: int = 10,
    default_reservation_timeout: float = 300.0,
    cleanup_interval: float = 1.0,
    clock: ManualClock | None = None,
) -> SeatReservationManager:
    if clock is None:
        clock = ManualClock()
    return SeatReservationManager(
        rows=rows,
        columns=columns,
        default_reservation_timeout=default_reservation_timeout,
        cleanup_interval=cleanup_interval,
        clock=clock,
    )
