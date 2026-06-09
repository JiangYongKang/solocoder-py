from __future__ import annotations


class SeatReservationError(Exception):
    pass


class SeatNotFoundError(SeatReservationError):
    pass


class SeatAlreadyReservedError(SeatReservationError):
    pass


class SeatAlreadyOccupiedError(SeatReservationError):
    pass


class SeatNotReservedError(SeatReservationError):
    pass


class SeatReservationExpiredError(SeatReservationError):
    pass


class SeatReservationMismatchError(SeatReservationError):
    pass


class ConsecutiveSeatsNotFoundError(SeatReservationError):
    pass


class InvalidSeatCountError(SeatReservationError):
    pass
