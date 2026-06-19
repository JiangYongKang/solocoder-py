from __future__ import annotations

import pytest

from solocoder_py.metrics import (
    Counter,
    DuplicateMetricError,
    Gauge,
    Histogram,
    InvalidBoundariesError,
    InvalidLabelError,
    InvalidOperationError,
    MetricNotFoundError,
    MetricsRegistry,
)


class TestCounterInvalidOperations:
    def test_counter_dec_raises(self):
        counter = Counter("requests_total")
        with pytest.raises(InvalidOperationError, match="does not support dec"):
            counter.dec()

    def test_counter_dec_with_value_raises(self):
        counter = Counter("requests_total")
        with pytest.raises(InvalidOperationError, match="does not support dec"):
            counter.dec(5)

    def test_counter_observe_raises(self):
        counter = Counter("requests_total")
        with pytest.raises(InvalidOperationError, match="does not support observe"):
            counter.observe(1.0)

    def test_counter_inc_negative_raises(self):
        counter = Counter("requests_total")
        with pytest.raises(InvalidOperationError, match="cannot be decremented"):
            counter.inc(-1)


class TestGaugeInvalidOperations:
    def test_gauge_observe_raises(self):
        gauge = Gauge("temperature")
        with pytest.raises(InvalidOperationError, match="does not support observe"):
            gauge.observe(25.0)


class TestHistogramInvalidOperations:
    def test_histogram_inc_raises(self):
        hist = Histogram("duration", [0.1, 0.5, 1.0])
        with pytest.raises(InvalidOperationError, match="does not support inc"):
            hist.inc()

    def test_histogram_dec_raises(self):
        hist = Histogram("duration", [0.1, 0.5, 1.0])
        with pytest.raises(InvalidOperationError, match="does not support dec"):
            hist.dec()

    def test_histogram_set_raises(self):
        hist = Histogram("duration", [0.1, 0.5, 1.0])
        with pytest.raises(InvalidOperationError, match="does not support set"):
            hist.set(1.0)

    def test_histogram_empty_buckets_raises(self):
        with pytest.raises(InvalidBoundariesError, match="cannot be empty"):
            Histogram("test", [])

    def test_histogram_none_buckets_raises(self):
        with pytest.raises(InvalidBoundariesError):
            Histogram("test", None)  # type: ignore

    def test_histogram_negative_boundary_raises(self):
        with pytest.raises(InvalidBoundariesError, match="must be positive"):
            Histogram("test", [-1, 1, 2])

    def test_histogram_zero_boundary_raises(self):
        with pytest.raises(InvalidBoundariesError, match="must be positive"):
            Histogram("test", [0, 1, 2])

    def test_histogram_duplicate_boundaries_raises(self):
        with pytest.raises(InvalidBoundariesError, match="must be unique"):
            Histogram("test", [1, 2, 2, 3])

    def test_histogram_quantile_out_of_range_low(self):
        hist = Histogram("test", [1, 2, 3])
        hist.observe(1.5)
        with pytest.raises(InvalidOperationError, match="range \\[0, 1\\]"):
            hist.quantile(-0.1)

    def test_histogram_quantile_out_of_range_high(self):
        hist = Histogram("test", [1, 2, 3])
        hist.observe(1.5)
        with pytest.raises(InvalidOperationError, match="range \\[0, 1\\]"):
            hist.quantile(1.1)


class TestRegistryDuplicateMetrics:
    def test_duplicate_counter_same_labels_raises(self, registry):
        registry.create_counter("requests_total", labels={"method": "GET"})
        with pytest.raises(DuplicateMetricError, match="already exists"):
            registry.create_counter("requests_total", labels={"method": "GET"})

    def test_duplicate_counter_no_labels_raises(self, registry):
        registry.create_counter("simple_counter")
        with pytest.raises(DuplicateMetricError, match="already exists"):
            registry.create_counter("simple_counter")

    def test_duplicate_gauge_raises(self, registry):
        registry.create_gauge("temperature", labels={"room": "kitchen"})
        with pytest.raises(DuplicateMetricError, match="already exists"):
            registry.create_gauge("temperature", labels={"room": "kitchen"})

    def test_duplicate_histogram_raises(self, registry):
        registry.create_histogram("duration", [0.1, 0.5])
        with pytest.raises(DuplicateMetricError, match="already exists"):
            registry.create_histogram("duration", [0.1, 0.5])

    def test_same_name_different_types_raises(self, registry):
        registry.create_counter("my_metric")
        with pytest.raises(ValueError, match="different type"):
            registry.create_gauge("my_metric")

    def test_same_name_different_labels_allowed(self, registry):
        c1 = registry.create_counter("requests_total", labels={"method": "GET"})
        c2 = registry.create_counter("requests_total", labels={"method": "POST"})
        assert c1 is not c2
        assert c1.labels["method"] == "GET"
        assert c2.labels["method"] == "POST"


class TestRegistryNotFound:
    def test_get_counter_nonexistent_family_raises(self, registry):
        with pytest.raises(MetricNotFoundError, match="not found"):
            registry.get_counter("nonexistent")

    def test_get_gauge_nonexistent_family_raises(self, registry):
        with pytest.raises(MetricNotFoundError, match="not found"):
            registry.get_gauge("nonexistent")

    def test_get_histogram_nonexistent_family_raises(self, registry):
        with pytest.raises(MetricNotFoundError, match="not found"):
            registry.get_histogram("nonexistent")

    def test_get_counter_wrong_type_raises(self, registry):
        registry.create_gauge("my_gauge")
        with pytest.raises(MetricNotFoundError, match="not a counter"):
            registry.get_counter("my_gauge")

    def test_get_gauge_wrong_type_raises(self, registry):
        registry.create_counter("my_counter")
        with pytest.raises(MetricNotFoundError, match="not a gauge"):
            registry.get_gauge("my_counter")

    def test_get_histogram_wrong_type_raises(self, registry):
        registry.create_counter("my_counter")
        with pytest.raises(MetricNotFoundError, match="not a histogram"):
            registry.get_histogram("my_counter")

    def test_get_counter_labels_not_found(self, registry):
        registry.create_counter("requests_total", labels={"method": "GET"})
        with pytest.raises(MetricNotFoundError, match="not found"):
            registry.get_counter("requests_total", labels={"method": "POST"})


class TestRegistryInvalidLabels:
    def test_empty_label_key_raises(self, registry):
        with pytest.raises(InvalidLabelError, match="cannot be empty"):
            registry.create_counter("test", labels={"": "value"})

    def test_invalid_label_key_type_raises(self, registry):
        with pytest.raises(InvalidLabelError, match="must be a string"):
            registry.create_counter("test", labels={123: "value"})  # type: ignore


class TestRegistryInvalidName:
    def test_empty_name_raises(self, registry):
        with pytest.raises(ValueError, match="cannot be empty"):
            registry.create_counter("")

    def test_non_string_name_raises(self, registry):
        with pytest.raises(ValueError, match="must be a string"):
            registry.create_counter(123)  # type: ignore


class TestMetricFamilyErrors:
    def test_family_get_nonexistent_labels_raises(self):
        from solocoder_py.metrics import MetricFamily

        family = MetricFamily("test", "counter")
        with pytest.raises(MetricNotFoundError, match="not found"):
            family.get({"env": "prod"})

    def test_family_add_duplicate_raises(self):
        from solocoder_py.metrics import MetricFamily

        family = MetricFamily("test", "counter")
        c1 = Counter("test", labels={"env": "prod"})
        c2 = Counter("test", labels={"env": "prod"})
        family.add(c1)
        with pytest.raises(DuplicateMetricError, match="already exists"):
            family.add(c2)


class TestHistogramRegistryErrors:
    def test_registry_create_histogram_invalid_buckets_empty(self, registry):
        with pytest.raises(InvalidBoundariesError):
            registry.create_histogram("test", [])

    def test_registry_create_histogram_invalid_buckets_negative(self, registry):
        with pytest.raises(InvalidBoundariesError):
            registry.create_histogram("test", [-1, 1, 2])
