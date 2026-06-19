from __future__ import annotations

import threading
from typing import Mapping, Optional, Sequence, Type, TypeVar

from .exceptions import DuplicateMetricError, InvalidLabelError, MetricNotFoundError
from .models import Counter, FrozenLabels, Gauge, Histogram

T = TypeVar("T", Counter, Gauge, Histogram)


class MetricFamily:
    def __init__(self, name: str, metric_type: str, help_text: str = "") -> None:
        self._name = name
        self._type = metric_type
        self._help = help_text
        self._metrics: dict[FrozenLabels, Counter | Gauge | Histogram] = {}
        self._lock = threading.RLock()

    @property
    def name(self) -> str:
        return self._name

    @property
    def type(self) -> str:
        return self._type

    @property
    def help(self) -> str:
        return self._help

    def get(self, labels: Optional[Mapping[str, str]] = None) -> Counter | Gauge | Histogram:
        frozen = FrozenLabels(labels)
        with self._lock:
            if frozen not in self._metrics:
                raise MetricNotFoundError(
                    f"Metric '{self._name}' with labels {dict(labels or {})} not found"
                )
            return self._metrics[frozen]

    def add(self, metric: Counter | Gauge | Histogram) -> None:
        frozen = metric.labels
        with self._lock:
            if frozen in self._metrics:
                raise DuplicateMetricError(
                    f"Metric '{self._name}' with labels {dict(frozen.labels)} already exists"
                )
            self._metrics[frozen] = metric

    def find(self, label_query: Optional[Mapping[str, str]] = None) -> list[Counter | Gauge | Histogram]:
        if label_query is None:
            label_query = {}
        results: list[Counter | Gauge | Histogram] = []
        with self._lock:
            for frozen_labels, metric in self._metrics.items():
                if frozen_labels.matches(label_query):
                    results.append(metric)
        return results

    def find_by_keys(self, label_keys: set[str]) -> list[Counter | Gauge | Histogram]:
        results: list[Counter | Gauge | Histogram] = []
        with self._lock:
            for frozen_labels, metric in self._metrics.items():
                if frozen_labels.has_keys(label_keys):
                    results.append(metric)
        return results

    def all(self) -> list[Counter | Gauge | Histogram]:
        with self._lock:
            return list(self._metrics.values())


class MetricsRegistry:
    def __init__(self) -> None:
        self._families: dict[str, MetricFamily] = {}
        self._lock = threading.RLock()

    def _validate_label_keys(self, labels: Optional[Mapping[str, str]]) -> None:
        if labels is None:
            return
        for key in labels.keys():
            if not key:
                raise InvalidLabelError("Label key cannot be empty")
            if not isinstance(key, str):
                raise InvalidLabelError("Label key must be a string")

    def _validate_name(self, name: str) -> None:
        if not name:
            raise ValueError("Metric name cannot be empty")
        if not isinstance(name, str):
            raise ValueError("Metric name must be a string")

    def create_counter(
        self,
        name: str,
        help_text: str = "",
        labels: Optional[Mapping[str, str]] = None,
    ) -> Counter:
        self._validate_name(name)
        self._validate_label_keys(labels)
        frozen = FrozenLabels(labels)

        with self._lock:
            if name not in self._families:
                self._families[name] = MetricFamily(name, "counter", help_text)
            family = self._families[name]
            if family.type != "counter":
                raise ValueError(f"Metric '{name}' already exists with different type '{family.type}'")

            try:
                existing = family.get(labels)
                raise DuplicateMetricError(
                    f"Counter '{name}' with labels {dict(frozen.labels)} already exists"
                )
            except MetricNotFoundError:
                pass

            counter = Counter(name, help_text, labels)
            family.add(counter)
            return counter

    def create_gauge(
        self,
        name: str,
        help_text: str = "",
        labels: Optional[Mapping[str, str]] = None,
    ) -> Gauge:
        self._validate_name(name)
        self._validate_label_keys(labels)
        frozen = FrozenLabels(labels)

        with self._lock:
            if name not in self._families:
                self._families[name] = MetricFamily(name, "gauge", help_text)
            family = self._families[name]
            if family.type != "gauge":
                raise ValueError(f"Metric '{name}' already exists with different type '{family.type}'")

            try:
                existing = family.get(labels)
                raise DuplicateMetricError(
                    f"Gauge '{name}' with labels {dict(frozen.labels)} already exists"
                )
            except MetricNotFoundError:
                pass

            gauge = Gauge(name, help_text, labels)
            family.add(gauge)
            return gauge

    def create_histogram(
        self,
        name: str,
        buckets: Sequence[float],
        help_text: str = "",
        labels: Optional[Mapping[str, str]] = None,
    ) -> Histogram:
        self._validate_name(name)
        self._validate_label_keys(labels)
        frozen = FrozenLabels(labels)

        with self._lock:
            if name not in self._families:
                self._families[name] = MetricFamily(name, "histogram", help_text)
            family = self._families[name]
            if family.type != "histogram":
                raise ValueError(f"Metric '{name}' already exists with different type '{family.type}'")

            try:
                existing = family.get(labels)
                raise DuplicateMetricError(
                    f"Histogram '{name}' with labels {dict(frozen.labels)} already exists"
                )
            except MetricNotFoundError:
                pass

            histogram = Histogram(name, buckets, help_text, labels)
            family.add(histogram)
            return histogram

    def get_counter(self, name: str, labels: Optional[Mapping[str, str]] = None) -> Counter:
        with self._lock:
            if name not in self._families:
                raise MetricNotFoundError(f"Metric family '{name}' not found")
            family = self._families[name]
            if family.type != "counter":
                raise MetricNotFoundError(f"Metric '{name}' is not a counter")
            metric = family.get(labels)
            if not isinstance(metric, Counter):
                raise MetricNotFoundError(f"Metric '{name}' is not a counter")
            return metric

    def get_gauge(self, name: str, labels: Optional[Mapping[str, str]] = None) -> Gauge:
        with self._lock:
            if name not in self._families:
                raise MetricNotFoundError(f"Metric family '{name}' not found")
            family = self._families[name]
            if family.type != "gauge":
                raise MetricNotFoundError(f"Metric '{name}' is not a gauge")
            metric = family.get(labels)
            if not isinstance(metric, Gauge):
                raise MetricNotFoundError(f"Metric '{name}' is not a gauge")
            return metric

    def get_histogram(self, name: str, labels: Optional[Mapping[str, str]] = None) -> Histogram:
        with self._lock:
            if name not in self._families:
                raise MetricNotFoundError(f"Metric family '{name}' not found")
            family = self._families[name]
            if family.type != "histogram":
                raise MetricNotFoundError(f"Metric '{name}' is not a histogram")
            metric = family.get(labels)
            if not isinstance(metric, Histogram):
                raise MetricNotFoundError(f"Metric '{name}' is not a histogram")
            return metric

    def find_by_name(self, name: str) -> Optional[MetricFamily]:
        with self._lock:
            return self._families.get(name)

    def find_by_labels(
        self,
        name: Optional[str] = None,
        label_query: Optional[Mapping[str, str]] = None,
    ) -> list[Counter | Gauge | Histogram]:
        results: list[Counter | Gauge | Histogram] = []
        with self._lock:
            families = [self._families[name]] if name else list(self._families.values())
            for family in families:
                results.extend(family.find(label_query))
        return results

    def find_by_label_keys(
        self,
        label_keys: set[str],
        name: Optional[str] = None,
    ) -> list[Counter | Gauge | Histogram]:
        results: list[Counter | Gauge | Histogram] = []
        with self._lock:
            families = [self._families[name]] if name else list(self._families.values())
            for family in families:
                results.extend(family.find_by_keys(label_keys))
        return results

    def all_families(self) -> list[MetricFamily]:
        with self._lock:
            return list(self._families.values())

    def all_metrics(self) -> list[Counter | Gauge | Histogram]:
        results: list[Counter | Gauge | Histogram] = []
        with self._lock:
            for family in self._families.values():
                results.extend(family.all())
        return results

    def clear(self) -> None:
        with self._lock:
            self._families.clear()
