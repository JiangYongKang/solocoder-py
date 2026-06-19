from __future__ import annotations

import os
import random
import threading
import time
from typing import Optional

from .exceptions import InvalidSamplingRateError
from .models import Span, TraceContext


def _generate_trace_id(timestamp_ns: int, counter: int, random_bits: int) -> str:
    part1 = format(timestamp_ns >> 16, "012x")
    part2 = format(counter & 0xFFFF, "04x")
    part3 = format(random_bits, "016x")
    return (part1 + part2 + part3).zfill(32)


def _generate_span_id(random_bits: int) -> str:
    return format(random_bits, "016x")


class Tracer:
    _instance: Optional["Tracer"] = None
    _instance_lock = threading.Lock()

    def __init__(self, sampling_rate: float = 1.0) -> None:
        self._validate_sampling_rate(sampling_rate)
        self._sampling_rate = sampling_rate
        self._trace_id_counter = 0
        self._span_id_counter = 0
        self._lock = threading.RLock()
        self._rng = random.Random()
        self._active_spans: dict[str, Span] = {}
        self._completed_spans: dict[str, list[Span]] = {}
        self._pid = os.getpid()

    @classmethod
    def get_instance(cls, sampling_rate: float = 1.0) -> "Tracer":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls(sampling_rate)
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._instance_lock:
            cls._instance = None

    @property
    def sampling_rate(self) -> float:
        return self._sampling_rate

    @sampling_rate.setter
    def sampling_rate(self, value: float) -> None:
        self._validate_sampling_rate(value)
        self._sampling_rate = value

    @staticmethod
    def _validate_sampling_rate(rate: float) -> None:
        if not isinstance(rate, (int, float)):
            raise InvalidSamplingRateError(
                f"sampling rate must be a number, got {type(rate).__name__}"
            )
        if rate < 0.0 or rate > 1.0:
            raise InvalidSamplingRateError(
                f"sampling rate must be between 0.0 and 1.0, got {rate}"
            )

    def _make_sampling_decision(self) -> bool:
        if self._sampling_rate >= 1.0:
            return True
        if self._sampling_rate <= 0.0:
            return False
        with self._lock:
            return self._rng.random() < self._sampling_rate

    def _generate_new_trace_id(self) -> tuple[str, bool]:
        with self._lock:
            timestamp_ns = time.time_ns()
            self._trace_id_counter = (self._trace_id_counter + 1) & 0xFFFF
            counter = self._trace_id_counter
            random_bits = self._rng.getrandbits(64)
            sampled = self._make_sampling_decision()
        return _generate_trace_id(timestamp_ns, counter, random_bits), sampled

    def _generate_new_span_id(self) -> str:
        with self._lock:
            random_bits = self._rng.getrandbits(64)
        return _generate_span_id(random_bits)

    def start_span(self, name: str, parent: Optional[Span] = None) -> Span:
        if parent is not None:
            if parent.is_ended:
                from .exceptions import CannotCreateChildSpanError

                raise CannotCreateChildSpanError(
                    f"cannot create child span for already ended span '{parent.name}'"
                )
            trace_id = parent.trace_id
            parent_span_id = parent.span_id
            sampled = parent.sampled
            span_id = self._generate_new_span_id()
        else:
            trace_id, sampled = self._generate_new_trace_id()
            parent_span_id = None
            span_id = self._generate_new_span_id()

        span = Span(
            name=name,
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            sampled=sampled,
        )

        if parent is not None:
            parent.add_child(span)

        with self._lock:
            self._active_spans[span_id] = span

        return span

    def start_span_from_context(
        self, name: str, context: TraceContext
    ) -> Span:
        with self._lock:
            parent_span = self._active_spans.get(context.span_id)
            if parent_span is not None and parent_span.is_ended:
                from .exceptions import CannotCreateChildSpanError

                raise CannotCreateChildSpanError(
                    f"cannot create child span for already ended span '{parent_span.name}'"
                )

            if parent_span is None:
                for spans in self._completed_spans.values():
                    for span in spans:
                        if span.span_id == context.span_id:
                            from .exceptions import CannotCreateChildSpanError

                            raise CannotCreateChildSpanError(
                                f"cannot create child span for already ended span '{span.name}'"
                            )

        span_id = self._generate_new_span_id()

        span = Span(
            name=name,
            trace_id=context.trace_id,
            span_id=span_id,
            parent_span_id=context.span_id,
            sampled=context.sampled,
        )

        with self._lock:
            self._active_spans[span_id] = span

        return span

    def end_span(self, span: Span) -> None:
        span.end()

        with self._lock:
            if span.span_id in self._active_spans:
                del self._active_spans[span.span_id]

            if span.sampled:
                if span.trace_id not in self._completed_spans:
                    self._completed_spans[span.trace_id] = []
                self._completed_spans[span.trace_id].append(span)

    def get_active_span(self, span_id: str) -> Optional[Span]:
        with self._lock:
            return self._active_spans.get(span_id)

    def get_span(self, span_id: str) -> Optional[Span]:
        with self._lock:
            span = self._active_spans.get(span_id)
            if span is not None:
                return span

            for spans in self._completed_spans.values():
                for s in spans:
                    if s.span_id == span_id:
                        return s
        return None

    def get_trace_spans(self, trace_id: str) -> list[Span]:
        with self._lock:
            spans = self._completed_spans.get(trace_id, [])
            return list(spans)

    def get_sampled_traces(self) -> list[list[Span]]:
        with self._lock:
            return [list(spans) for spans in self._completed_spans.values()]

    def export_spans(self) -> list[dict]:
        with self._lock:
            result = []
            for spans in self._completed_spans.values():
                for span in spans:
                    if span.sampled:
                        result.append(span.to_dict())
            return result

    def clear(self) -> None:
        with self._lock:
            self._active_spans.clear()
            self._completed_spans.clear()
            self._trace_id_counter = 0
            self._span_id_counter = 0

    @property
    def active_span_count(self) -> int:
        with self._lock:
            return len(self._active_spans)

    @property
    def completed_trace_count(self) -> int:
        with self._lock:
            return len(self._completed_spans)

    def get_trace_root(self, trace_id: str) -> Optional[Span]:
        with self._lock:
            spans = self._completed_spans.get(trace_id, [])
            for span in spans:
                if span.parent_span_id is None:
                    return span

            for span in self._active_spans.values():
                if span.trace_id == trace_id and span.parent_span_id is None:
                    return span
        return None
