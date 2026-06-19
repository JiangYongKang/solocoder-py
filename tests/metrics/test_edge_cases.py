from __future__ import annotations

import pytest

from solocoder_py.metrics import (
    Counter,
    FrozenLabels,
    Gauge,
    Histogram,
    MetricsRegistry,
    export_to_prometheus,
)


class TestZeroLabelMetrics:
    def test_counter_zero_labels(self, registry):
        counter = registry.create_counter("no_labels_counter")
        assert len(counter.labels) == 0
        counter.inc(10)
        assert counter.value == 10

    def test_gauge_zero_labels(self, registry):
        gauge = registry.create_gauge("no_labels_gauge")
        assert len(gauge.labels) == 0
        gauge.set(42)
        assert gauge.value == 42

    def test_histogram_zero_labels(self, registry):
        hist = registry.create_histogram("no_labels_hist", [1, 5, 10])
        assert len(hist.labels) == 0
        hist.observe(3)
        assert hist.count == 1

    def test_get_zero_label_metric(self, registry):
        counter = registry.create_counter("test")
        counter.inc(5)
        retrieved = registry.get_counter("test")
        assert retrieved.value == 5

    def test_export_zero_label_counter(self, registry):
        counter = registry.create_counter("simple_counter", "A simple counter")
        counter.inc(7)
        output = export_to_prometheus(registry)
        assert "simple_counter 7" in output

    def test_export_zero_label_gauge(self, registry):
        gauge = registry.create_gauge("simple_gauge")
        gauge.set(3.14)
        output = export_to_prometheus(registry)
        assert "simple_gauge 3.14" in output


class TestManyLabelCombinations:
    def test_counter_many_label_combinations(self, registry):
        methods = ["GET", "POST", "PUT", "DELETE"]
        paths = ["/", "/api", "/api/v1", "/api/v2", "/health"]
        codes = ["200", "201", "400", "404", "500"]

        created = 0
        for method in methods:
            for path in paths:
                for code in codes:
                    labels = {"method": method, "path": path, "code": code}
                    counter = registry.create_counter(
                        "http_requests_total", labels=labels
                    )
                    counter.inc(created + 1)
                    created += 1

        assert created == len(methods) * len(paths) * len(codes)
        all_metrics = registry.find_by_labels(name="http_requests_total")
        assert len(all_metrics) == created

    def test_find_by_label_subset_many_combinations(self, registry):
        for env in ["prod", "staging", "dev"]:
            for host in [f"host-{i}" for i in range(10)]:
                registry.create_gauge(
                    "cpu_usage", labels={"env": env, "host": host}
                )

        prod_metrics = registry.find_by_labels(
            name="cpu_usage", label_query={"env": "prod"}
        )
        assert len(prod_metrics) == 10

    def test_prometheus_export_many_label_lines(self, registry):
        for i in range(50):
            counter = registry.create_counter(
                "items_total", labels={"id": str(i)}
            )
            counter.inc(i + 1)

        output = export_to_prometheus(registry)
        lines = output.strip().split("\n")
        assert lines[0].startswith("# HELP")
        assert lines[1].startswith("# TYPE")
        data_lines = [l for l in lines[2:] if l.strip()]
        assert len(data_lines) == 50


class TestEmptyHistogramBuckets:
    def test_histogram_single_bucket(self):
        hist = Histogram("test", [1.0])
        hist.observe(0.5)
        hist.observe(1.5)
        assert hist.count == 2
        assert hist.bucket_counts == [1, 1]
        assert hist.cumulative_counts() == [1, 2]

    def test_histogram_no_observations(self):
        hist = Histogram("empty_hist", [0.1, 0.5, 1.0])
        assert hist.count == 0
        assert hist.sum == 0
        assert all(c == 0 for c in hist.bucket_counts)
        assert all(c == 0 for c in hist.cumulative_counts())

    def test_histogram_quantile_empty_returns_zero(self):
        hist = Histogram("empty_hist", [0.1, 0.5, 1.0])
        assert hist.quantile(0.5) == 0.0
        assert hist.quantile(0.0) == 0.1
        assert hist.quantile(1.0) == 1.0

    def test_export_empty_histogram(self, registry):
        registry.create_histogram("empty_hist", [0.1, 0.5, 1.0], "Empty histogram")
        output = export_to_prometheus(registry)
        assert 'empty_hist_bucket{le="0.1"} 0' in output
        assert 'empty_hist_bucket{le="0.5"} 0' in output
        assert 'empty_hist_bucket{le="1"} 0' in output
        assert 'empty_hist_bucket{le="+Inf"} 0' in output
        assert "empty_hist_sum 0" in output
        assert "empty_hist_count 0" in output


class TestGaugeNegativeValues:
    def test_gauge_set_negative(self):
        gauge = Gauge("temperature_celsius")
        gauge.set(-10.5)
        assert gauge.value == -10.5

    def test_gauge_dec_below_zero(self):
        gauge = Gauge("balance")
        gauge.set(5)
        gauge.dec(10)
        assert gauge.value == -5

    def test_gauge_negative_inc(self):
        gauge = Gauge("delta")
        gauge.set(0)
        gauge.inc(-3)
        assert gauge.value == -3

    def test_gauge_mixed_positive_negative(self):
        gauge = Gauge("value")
        gauge.set(100)
        gauge.dec(150)
        gauge.inc(20)
        gauge.dec(10)
        assert gauge.value == -40

    def test_export_gauge_negative(self, registry):
        gauge = registry.create_gauge("offset", "Offset value")
        gauge.set(-25.75)
        output = export_to_prometheus(registry)
        assert "offset -25.75" in output


class TestLabelsEdgeCases:
    def test_label_with_special_chars_in_value(self, registry):
        counter = registry.create_counter(
            "test",
            labels={"path": "/api/v1/users", "msg": 'hello "world" \\n'},
        )
        counter.inc(1)
        output = export_to_prometheus(registry)
        assert "msg=" in output

    def test_many_label_keys(self, registry):
        labels = {f"key_{i}": f"value_{i}" for i in range(20)}
        counter = registry.create_counter("many_labels", labels=labels)
        assert len(counter.labels) == 20
        for i in range(20):
            assert counter.labels[f"key_{i}"] == f"value_{i}"

    def test_frozen_labels_immutable(self):
        original = {"a": "1", "b": "2"}
        frozen = FrozenLabels(original)
        original["c"] = "3"
        assert len(frozen) == 2
        assert "c" not in frozen

    def test_frozen_labels_independent_copy(self):
        labels_dict = {"a": "1"}
        frozen = FrozenLabels(labels_dict)
        labels_dict["a"] = "modified"
        assert frozen["a"] == "1"


class TestHistogramBoundaryEdgeCases:
    def test_histogram_value_at_boundary(self):
        hist = Histogram("latency", [10, 50, 100])
        hist.observe(10)
        hist.observe(50)
        hist.observe(100)
        cumulative = hist.cumulative_counts()
        assert cumulative[0] == 1
        assert cumulative[1] == 2
        assert cumulative[2] == 3
        assert cumulative[3] == 3

    def test_histogram_all_values_in_one_bucket(self):
        hist = Histogram("values", [10, 50, 100])
        for _ in range(100):
            hist.observe(25)
        assert hist.bucket_counts[1] == 100
        assert hist.count == 100

    def test_histogram_large_bucket_values(self):
        hist = Histogram("big_values", [1e3, 1e6, 1e9])
        hist.observe(500)
        hist.observe(5e5)
        hist.observe(5e8)
        hist.observe(5e12)
        assert hist.count == 4
        assert hist.sum == pytest.approx(500 + 5e5 + 5e8 + 5e12)


class TestPrometheusExportEdgeCases:
    def test_export_help_with_special_chars(self, registry):
        registry.create_counter("test", 'Counter with "quotes" and \\backslashes\\')
        output = export_to_prometheus(registry)
        assert "# HELP test " in output

    def test_export_zero_value_counter(self, registry):
        registry.create_counter("zero_counter")
        output = export_to_prometheus(registry)
        assert "zero_counter 0" in output

    def test_export_integer_and_float_values(self, registry):
        c = registry.create_counter("int_counter")
        c.inc(42)
        g = registry.create_gauge("float_gauge")
        g.set(3.14159)
        output = export_to_prometheus(registry)
        assert "int_counter 42" in output
        assert "float_gauge 3.14159" in output

    def test_export_sorted_metrics(self, registry):
        registry.create_counter("z_counter")
        registry.create_counter("a_counter")
        registry.create_gauge("m_gauge")
        output = export_to_prometheus(registry)
        assert output.index("a_counter") < output.index("m_gauge") < output.index("z_counter")

    def test_histogram_export_with_labels(self, registry):
        hist = registry.create_histogram(
            "request_duration",
            [0.1, 0.5, 1.0],
            labels={"service": "api"},
        )
        hist.observe(0.3)
        output = export_to_prometheus(registry)
        assert 'request_duration_bucket{le="0.1",service="api"} 0' in output
        assert 'request_duration_bucket{le="0.5",service="api"} 1' in output
        assert 'request_duration_bucket{le="1",service="api"} 1' in output
        assert 'request_duration_bucket{le="+Inf",service="api"} 1' in output
        assert 'request_duration_sum{service="api"} 0.3' in output


class TestHistogramQuantileAllInInfBucket:
    def test_all_samples_same_value_in_inf_bucket_monotonicity(self, registry):
        hist = registry.create_histogram("latency", [1, 2, 3])
        for _ in range(100):
            hist.observe(100)
        q0 = hist.quantile(0)
        q25 = hist.quantile(0.25)
        q50 = hist.quantile(0.5)
        q75 = hist.quantile(0.75)
        q100 = hist.quantile(1)
        assert q0 <= q25 <= q50 <= q75 <= q100
        assert q0 == 100
        assert q50 == 100
        assert q100 == 100

    def test_all_samples_in_inf_bucket_quantile_returns_near_true_value(self, registry):
        hist = registry.create_histogram("latency", [1, 2, 3])
        for _ in range(100):
            hist.observe(100)
        q50 = hist.quantile(0.5)
        assert abs(q50 - 100) < 1.0
        assert q50 > 50

    def test_all_samples_different_values_in_inf_bucket_monotonicity(self, registry):
        hist = registry.create_histogram("latency", [1, 2, 3])
        for i in range(100):
            hist.observe(100 + i)
        q0 = hist.quantile(0)
        q25 = hist.quantile(0.25)
        q50 = hist.quantile(0.5)
        q75 = hist.quantile(0.75)
        q100 = hist.quantile(1)
        assert q0 <= q25 <= q50 <= q75 <= q100
        assert q0 == 100
        assert abs(q50 - 150) < 1.0
        assert q100 == 199

    def test_mixed_samples_monotonicity(self, registry):
        hist = registry.create_histogram("latency", [1, 2, 3])
        for v in [0.5, 1.5, 2.5, 100, 200]:
            hist.observe(v)
        quantiles = [hist.quantile(q / 10) for q in range(11)]
        for i in range(len(quantiles) - 1):
            assert quantiles[i] <= quantiles[i + 1]

    def test_all_in_inf_bucket_various_quantiles(self, registry):
        hist = registry.create_histogram("latency", [1, 2, 3])
        values = list(range(100, 200))
        for v in values:
            hist.observe(v)
        for q in [0, 0.1, 0.25, 0.5, 0.75, 0.9, 1]:
            q_val = hist.quantile(q)
            expected_idx = int(q * (len(values) - 1))
            expected = values[expected_idx]
            assert abs(q_val - expected) <= 1.0

    def test_all_in_inf_bucket_single_value_all_quantiles(self, registry):
        hist = registry.create_histogram("latency", [1, 2, 3])
        hist.observe(100)
        for q in [0, 0.25, 0.5, 0.75, 1]:
            assert hist.quantile(q) == 100

    def test_mixed_samples_inf_bucket_lower_bound_correct(self, registry):
        hist = registry.create_histogram("latency", [1, 2, 3])
        hist.observe(2.5)
        hist.observe(100)
        q0 = hist.quantile(0)
        q50 = hist.quantile(0.5)
        q100 = hist.quantile(1)
        assert q0 <= q50 <= q100
        assert q0 == 2.5
        assert q100 == 100
