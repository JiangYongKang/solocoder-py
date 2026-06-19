from __future__ import annotations

import pytest

from solocoder_py.metrics import (
    Counter,
    FrozenLabels,
    Gauge,
    Histogram,
    Labels,
    MetricFamily,
    MetricsRegistry,
    export_to_prometheus,
)


class TestLabels:
    def test_labels_creation(self):
        labels = Labels({"method": "GET", "path": "/api"})
        assert labels["method"] == "GET"
        assert labels["path"] == "/api"
        assert len(labels) == 2

    def test_labels_empty(self):
        labels = Labels()
        assert len(labels) == 0

    def test_labels_equality(self):
        l1 = Labels({"a": "1", "b": "2"})
        l2 = Labels({"b": "2", "a": "1"})
        assert l1 == l2
        assert hash(l1) == hash(l2)

    def test_frozen_labels_creation(self):
        frozen = FrozenLabels({"method": "POST", "code": "200"})
        assert frozen["method"] == "POST"
        assert frozen["code"] == "200"

    def test_frozen_labels_matches(self):
        frozen = FrozenLabels({"method": "GET", "path": "/api", "status": "200"})
        assert frozen.matches({"method": "GET"}) is True
        assert frozen.matches({"method": "GET", "path": "/api"}) is True
        assert frozen.matches({"method": "POST"}) is False
        assert frozen.matches({"nonexistent": "value"}) is False
        assert frozen.matches({}) is True

    def test_frozen_labels_has_keys(self):
        frozen = FrozenLabels({"a": "1", "b": "2", "c": "3"})
        assert frozen.has_keys({"a", "b"}) is True
        assert frozen.has_keys({"a", "d"}) is False
        assert frozen.has_keys(set()) is True


class TestCounterNormalFlows:
    def test_counter_increment_default(self):
        counter = Counter("requests_total")
        assert counter.value == 0
        counter.inc()
        assert counter.value == 1
        counter.inc()
        assert counter.value == 2

    def test_counter_increment_with_delta(self):
        counter = Counter("requests_total")
        counter.inc(5)
        assert counter.value == 5
        counter.inc(3.5)
        assert counter.value == 8.5

    def test_counter_with_help_and_labels(self):
        counter = Counter(
            "http_requests_total",
            help_text="Total HTTP requests",
            labels={"method": "GET", "path": "/api"},
        )
        assert counter.name == "http_requests_total"
        assert counter.help == "Total HTTP requests"
        assert counter.labels["method"] == "GET"
        assert counter.labels["path"] == "/api"


class TestGaugeNormalFlows:
    def test_gauge_set_and_get(self):
        gauge = Gauge("temperature")
        assert gauge.value == 0
        gauge.set(25.5)
        assert gauge.value == 25.5
        gauge.set(100)
        assert gauge.value == 100

    def test_gauge_inc(self):
        gauge = Gauge("active_users")
        gauge.set(10)
        gauge.inc()
        assert gauge.value == 11
        gauge.inc(5)
        assert gauge.value == 16

    def test_gauge_dec(self):
        gauge = Gauge("active_users")
        gauge.set(10)
        gauge.dec()
        assert gauge.value == 9
        gauge.dec(3)
        assert gauge.value == 6

    def test_gauge_mixed_operations(self):
        gauge = Gauge("memory_usage_bytes")
        gauge.set(100)
        gauge.inc(50)
        gauge.dec(30)
        assert gauge.value == 120


class TestHistogramNormalFlows:
    def test_histogram_basic_observe(self):
        hist = Histogram("request_duration_seconds", [0.1, 0.5, 1.0, 5.0])
        assert hist.count == 0
        assert hist.sum == 0

    def test_histogram_observe_values(self):
        hist = Histogram("request_duration_seconds", [0.1, 0.5, 1.0, 5.0])
        hist.observe(0.05)
        hist.observe(0.3)
        hist.observe(0.7)
        hist.observe(3.0)
        hist.observe(10.0)
        assert hist.count == 5
        assert hist.sum == pytest.approx(0.05 + 0.3 + 0.7 + 3.0 + 10.0)

    def test_histogram_bucket_counts(self):
        hist = Histogram("latency_ms", [10, 50, 100, 500])
        hist.observe(5)
        hist.observe(25)
        hist.observe(25)
        hist.observe(75)
        hist.observe(200)
        hist.observe(200)
        hist.observe(200)
        hist.observe(1000)
        assert hist.bucket_counts == [1, 2, 1, 3, 1]

    def test_histogram_cumulative_counts(self):
        hist = Histogram("latency_ms", [10, 50, 100])
        hist.observe(5)
        hist.observe(30)
        hist.observe(30)
        hist.observe(75)
        hist.observe(200)
        cumulative = hist.cumulative_counts()
        assert cumulative == [1, 3, 4, 5]

    def test_histogram_quantile(self):
        hist = Histogram("request_duration", [10, 20, 30, 40, 50])
        for i in range(1, 51):
            hist.observe(i)
        p50 = hist.quantile(0.5)
        assert 24 <= p50 <= 26
        p90 = hist.quantile(0.9)
        assert 44 <= p90 <= 46


class TestRegistryNormalFlows:
    def test_create_counter(self, registry):
        counter = registry.create_counter("requests_total", "Total requests")
        assert counter.name == "requests_total"
        assert counter.help == "Total requests"
        assert counter.value == 0

    def test_create_gauge(self, registry):
        gauge = registry.create_gauge("active_users", "Active user count")
        assert gauge.name == "active_users"
        assert gauge.value == 0

    def test_create_histogram(self, registry):
        hist = registry.create_histogram(
            "request_duration_seconds",
            [0.1, 0.5, 1.0],
            "Request duration",
        )
        assert hist.name == "request_duration_seconds"
        assert hist.buckets == [0.1, 0.5, 1.0]

    def test_get_counter(self, registry):
        created = registry.create_counter("requests_total")
        retrieved = registry.get_counter("requests_total")
        assert created is retrieved

    def test_counter_with_labels_independent(self, registry):
        c1 = registry.create_counter("http_requests_total", labels={"method": "GET"})
        c2 = registry.create_counter("http_requests_total", labels={"method": "POST"})
        c1.inc(5)
        c2.inc(3)
        assert c1.value == 5
        assert c2.value == 3

    def test_find_by_labels_exact_match(self, registry):
        c1 = registry.create_counter("req_total", labels={"method": "GET", "path": "/"})
        c2 = registry.create_counter("req_total", labels={"method": "POST", "path": "/"})
        c3 = registry.create_counter("req_total", labels={"method": "GET", "path": "/api"})

        results = registry.find_by_labels(name="req_total", label_query={"method": "GET"})
        assert len(results) == 2
        names = {r.labels["path"] for r in results}
        assert names == {"/", "/api"}

        results = registry.find_by_labels(
            name="req_total", label_query={"method": "GET", "path": "/"}
        )
        assert len(results) == 1
        assert results[0].labels["path"] == "/"

    def test_find_by_label_keys(self, registry):
        c1 = registry.create_counter("m1", labels={"a": "1", "b": "2"})
        c2 = registry.create_counter("m2", labels={"a": "1", "c": "3"})
        c3 = registry.create_counter("m3", labels={"a": "1", "b": "2", "c": "3"})

        results = registry.find_by_label_keys({"a", "b"})
        assert len(results) == 2
        names = {r.name for r in results}
        assert names == {"m1", "m3"}

    def test_all_metrics(self, registry):
        registry.create_counter("c1")
        registry.create_gauge("g1")
        registry.create_histogram("h1", [1, 2, 3])
        registry.create_counter("c1", labels={"env": "prod"})
        all_metrics = registry.all_metrics()
        assert len(all_metrics) == 4


class TestPrometheusExportNormalFlows:
    def test_export_counter(self, registry):
        counter = registry.create_counter("requests_total", "Total requests")
        counter.inc(42)
        output = export_to_prometheus(registry)
        assert "# HELP requests_total Total requests" in output
        assert "# TYPE requests_total counter" in output
        assert "requests_total 42" in output

    def test_export_counter_with_labels(self, registry):
        counter = registry.create_counter(
            "http_requests_total",
            "HTTP requests",
            labels={"method": "GET", "code": "200"},
        )
        counter.inc(100)
        output = export_to_prometheus(registry)
        assert 'http_requests_total{code="200",method="GET"} 100' in output

    def test_export_gauge(self, registry):
        gauge = registry.create_gauge("temperature_celsius", "Current temperature")
        gauge.set(23.5)
        output = export_to_prometheus(registry)
        assert "# HELP temperature_celsius Current temperature" in output
        assert "# TYPE temperature_celsius gauge" in output
        assert "temperature_celsius 23.5" in output

    def test_export_gauge_with_labels(self, registry):
        gauge = registry.create_gauge(
            "memory_usage_bytes",
            labels={"host": "server1", "region": "us-east"},
        )
        gauge.set(1048576)
        output = export_to_prometheus(registry)
        assert 'memory_usage_bytes{host="server1",region="us-east"} 1048576' in output

    def test_export_histogram(self, registry):
        hist = registry.create_histogram(
            "request_duration_seconds",
            [0.1, 0.5, 1.0],
            "Request duration",
        )
        hist.observe(0.05)
        hist.observe(0.3)
        hist.observe(0.3)
        hist.observe(0.7)
        hist.observe(2.0)
        output = export_to_prometheus(registry)

        assert "# HELP request_duration_seconds Request duration" in output
        assert "# TYPE request_duration_seconds histogram" in output
        assert 'request_duration_seconds_bucket{le="0.1"} 1' in output
        assert 'request_duration_seconds_bucket{le="0.5"} 3' in output
        assert 'request_duration_seconds_bucket{le="1"} 4' in output
        assert 'request_duration_seconds_bucket{le="+Inf"} 5' in output
        assert "request_duration_seconds_sum " in output
        assert "request_duration_seconds_count 5" in output

    def test_export_multiple_metrics(self, registry):
        c = registry.create_counter("req_total", "Total requests")
        c.inc(10)
        g = registry.create_gauge("active_conn", "Active connections")
        g.set(5)
        output = export_to_prometheus(registry)
        assert "# HELP req_total" in output
        assert "# TYPE req_total counter" in output
        assert "req_total 10" in output
        assert "# HELP active_conn" in output
        assert "# TYPE active_conn gauge" in output
        assert "active_conn 5" in output

    def test_export_empty_registry(self, registry):
        output = export_to_prometheus(registry)
        assert output == ""


class TestMetricFamily:
    def test_family_add_and_get(self):
        family = MetricFamily("test_counter", "counter", "Test")
        c1 = Counter("test_counter", "Test", labels={"env": "prod"})
        c2 = Counter("test_counter", "Test", labels={"env": "dev"})
        family.add(c1)
        family.add(c2)
        assert family.get({"env": "prod"}) is c1
        assert family.get({"env": "dev"}) is c2

    def test_family_find(self):
        family = MetricFamily("req", "counter")
        c1 = Counter("req", labels={"method": "GET", "path": "/"})
        c2 = Counter("req", labels={"method": "POST", "path": "/"})
        family.add(c1)
        family.add(c2)
        results = family.find({"method": "GET"})
        assert len(results) == 1
        assert results[0] is c1
