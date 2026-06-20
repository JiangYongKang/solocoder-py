from __future__ import annotations


class ReservoirError(Exception):
    pass


class InvalidCapacityError(ReservoirError):
    pass


class InvalidWeightError(ReservoirError):
    pass


class SamplerClosedError(ReservoirError):
    pass
