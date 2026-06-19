from __future__ import annotations


class MetricsError(Exception):
    pass


class MetricTypeError(MetricsError):
    pass


class InvalidLabelError(MetricsError):
    pass


class DuplicateMetricError(MetricsError):
    pass


class MetricNotFoundError(MetricsError):
    pass


class InvalidOperationError(MetricsError):
    pass


class InvalidBoundariesError(MetricsError):
    pass
