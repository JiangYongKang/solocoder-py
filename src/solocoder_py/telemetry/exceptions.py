from __future__ import annotations


class TelemetryError(Exception):
    pass


class InvalidBufferConfigError(TelemetryError):
    pass


class BufferClosedError(TelemetryError):
    pass


class InvalidDataError(TelemetryError):
    pass


class SchemaMappingError(TelemetryError):
    pass


class CircularMappingError(SchemaMappingError):
    pass


class TargetConflictError(SchemaMappingError):
    pass


class InvalidWindowConfigError(TelemetryError):
    pass


class LateDataError(TelemetryError):
    pass
