from __future__ import annotations


class TracingError(Exception):
    pass


class SpanAlreadyEndedError(TracingError):
    pass


class SpanNotStartedError(TracingError):
    pass


class InvalidSamplingRateError(TracingError):
    pass


class SpanNotFoundError(TracingError):
    pass


class CannotCreateChildSpanError(TracingError):
    pass
