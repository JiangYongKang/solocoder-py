from __future__ import annotations

import math
from typing import Mapping

from .models import Counter, FrozenLabels, Gauge, Histogram
from .registry import MetricFamily, MetricsRegistry


def _escape_help(text: str) -> str:
    return text.replace("\\", "\\\\").replace("\n", "\\n")


def _escape_label_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _format_value(value: float) -> str:
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "+Inf" if value > 0 else "-Inf"
    if value == int(value):
        return str(int(value))
    return repr(value)


def _format_labels(labels: FrozenLabels, extra: Mapping[str, str] | None = None) -> str:
    all_labels: dict[str, str] = dict(labels.labels)
    if extra:
        all_labels.update(extra)
    if not all_labels:
        return ""
    parts = []
    for key in sorted(all_labels.keys()):
        value = _escape_label_value(all_labels[key])
        parts.append(f'{key}="{value}"')
    return "{" + ",".join(parts) + "}"


class PrometheusExporter:
    def __init__(self, registry: MetricsRegistry) -> None:
        self._registry = registry

    def export(self) -> str:
        lines: list[str] = []
        families = self._registry.all_families()
        families.sort(key=lambda f: f.name)

        for family in families:
            help_text = family.help or ""
            lines.append(f"# HELP {family.name} {_escape_help(help_text)}")
            lines.append(f"# TYPE {family.name} {family.type}")

            metrics = family.all()
            metrics.sort(key=lambda m: _format_labels(m.labels))

            for metric in metrics:
                if isinstance(metric, Counter):
                    self._export_counter(lines, metric)
                elif isinstance(metric, Gauge):
                    self._export_gauge(lines, metric)
                elif isinstance(metric, Histogram):
                    self._export_histogram(lines, metric)

        return "\n".join(lines) + ("\n" if lines else "")

    def _export_counter(self, lines: list[str], counter: Counter) -> None:
        label_str = _format_labels(counter.labels)
        value_str = _format_value(counter.value)
        lines.append(f"{counter.name}{label_str} {value_str}")

    def _export_gauge(self, lines: list[str], gauge: Gauge) -> None:
        label_str = _format_labels(gauge.labels)
        value_str = _format_value(gauge.value)
        lines.append(f"{gauge.name}{label_str} {value_str}")

    def _export_histogram(self, lines: list[str], histogram: Histogram) -> None:
        buckets = histogram.buckets
        cumulative = histogram.cumulative_counts()

        for i, bucket in enumerate(buckets):
            label_str = _format_labels(histogram.labels, {"le": _format_value(bucket)})
            count_str = _format_value(float(cumulative[i]))
            lines.append(f"{histogram.name}_bucket{label_str} {count_str}")

        inf_label_str = _format_labels(histogram.labels, {"le": "+Inf"})
        inf_count_str = _format_value(float(cumulative[-1]))
        lines.append(f"{histogram.name}_bucket{inf_label_str} {inf_count_str}")

        sum_label_str = _format_labels(histogram.labels)
        sum_value_str = _format_value(histogram.sum)
        lines.append(f"{histogram.name}_sum{sum_label_str} {sum_value_str}")

        count_label_str = _format_labels(histogram.labels)
        count_value_str = _format_value(float(histogram.count))
        lines.append(f"{histogram.name}_count{count_label_str} {count_value_str}")


def export_to_prometheus(registry: MetricsRegistry) -> str:
    exporter = PrometheusExporter(registry)
    return exporter.export()
