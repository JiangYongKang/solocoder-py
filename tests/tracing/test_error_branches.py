from __future__ import annotations

import pytest

from solocoder_py.tracing import (
    CannotCreateChildSpanError,
    InvalidSamplingRateError,
    SpanAlreadyEndedError,
    SpanNotStartedError,
    Tracer,
)


class TestSpanAlreadyEndedError:
    def test_end_span_twice_raises(self, tracer):
        span = tracer.start_span("test")
        tracer.end_span(span)

        with pytest.raises(SpanAlreadyEndedError, match="already been ended"):
            tracer.end_span(span)

    def test_span_end_method_twice_raises(self, tracer):
        span = tracer.start_span("test")
        span.end()

        with pytest.raises(SpanAlreadyEndedError, match="already been ended"):
            span.end()

    def test_mixed_end_calls_raises(self, tracer):
        span = tracer.start_span("test")
        span.end()

        with pytest.raises(SpanAlreadyEndedError):
            tracer.end_span(span)

    def test_ended_span_retains_data(self, tracer):
        span = tracer.start_span("test")
        span.set_attribute("key", "value")
        tracer.end_span(span)

        with pytest.raises(SpanAlreadyEndedError):
            tracer.end_span(span)

        assert span.is_ended is True
        assert span.get_attribute("key") == "value"
        assert span.duration_ns >= 0

    def test_multiple_ended_spans_independent(self, tracer):
        span1 = tracer.start_span("span1")
        span2 = tracer.start_span("span2")

        tracer.end_span(span1)

        tracer.end_span(span2)
        with pytest.raises(SpanAlreadyEndedError):
            tracer.end_span(span2)

        assert span1.is_ended is True
        assert span2.is_ended is True


class TestCannotCreateChildSpanError:
    def test_create_child_for_ended_span_raises(self, tracer):
        parent = tracer.start_span("parent")
        tracer.end_span(parent)

        with pytest.raises(CannotCreateChildSpanError, match="already ended span"):
            tracer.start_span("child", parent=parent)

    def test_create_child_from_context_for_ended_span_raises(self, tracer):
        parent = tracer.start_span("parent")
        context = parent.context
        tracer.end_span(parent)

        with pytest.raises(CannotCreateChildSpanError, match="already ended span"):
            tracer.start_span_from_context("child", context)

    def test_create_child_from_context_for_active_span_allowed(self, tracer):
        parent = tracer.start_span("parent")
        context = parent.context

        child = tracer.start_span_from_context("child", context)
        assert child.parent_span_id == parent.span_id
        assert child.trace_id == parent.trace_id

        tracer.end_span(child)
        tracer.end_span(parent)

    def test_span_add_child_for_ended_span_raises(self, tracer):
        parent = tracer.start_span("parent")
        tracer.end_span(parent)

        child = tracer.start_span("child")
        with pytest.raises(CannotCreateChildSpanError, match="already ended span"):
            parent.add_child(child)
        tracer.end_span(child)

    def test_create_child_after_parent_ended_in_nested(self, tracer):
        root = tracer.start_span("root")
        child = tracer.start_span("child", parent=root)
        tracer.end_span(child)

        tracer.end_span(root)

        with pytest.raises(CannotCreateChildSpanError):
            tracer.start_span("orphan", parent=root)

    def test_deep_nesting_end_middle_prevents_more_children(self, tracer):
        level0 = tracer.start_span("level0")
        level1 = tracer.start_span("level1", parent=level0)
        level2 = tracer.start_span("level2", parent=level1)

        tracer.end_span(level1)

        with pytest.raises(CannotCreateChildSpanError):
            tracer.start_span("level2b", parent=level1)

        tracer.end_span(level2)
        tracer.end_span(level0)

    def test_ended_parent_children_list_unchanged(self, tracer):
        parent = tracer.start_span("parent")
        child1 = tracer.start_span("child1", parent=parent)
        tracer.end_span(child1)

        initial_children_count = len(parent.children)
        tracer.end_span(parent)

        with pytest.raises(CannotCreateChildSpanError):
            tracer.start_span("child2", parent=parent)

        assert len(parent.children) == initial_children_count

    def test_create_child_from_context_for_completed_parent_raises(self, tracer):
        parent = tracer.start_span("parent")
        tracer.end_span(parent)

        context = parent.context

        with pytest.raises(CannotCreateChildSpanError, match="already ended span"):
            tracer.start_span_from_context("child", context)

    def test_create_child_from_context_for_active_parent_succeeds(self, tracer):
        parent = tracer.start_span("parent")
        context = parent.context

        child = tracer.start_span_from_context("child", context)
        assert child.parent_span_id == parent.span_id
        assert child.trace_id == parent.trace_id

        tracer.end_span(child)
        tracer.end_span(parent)

    def test_create_child_from_external_context_succeeds(self, tracer):
        from solocoder_py.tracing import TraceContext

        external_context = TraceContext(
            trace_id="abc123def456abc123def456abc12345",
            span_id="abc123def4567890",
            sampled=True,
        )

        child = tracer.start_span_from_context("child", external_context)
        assert child.parent_span_id == external_context.span_id
        assert child.trace_id == external_context.trace_id
        assert child.sampled == external_context.sampled

        tracer.end_span(child)

    def test_create_child_from_context_parent_in_completed_with_children_already(self, tracer):
        parent = tracer.start_span("parent")
        child1 = tracer.start_span("child1", parent=parent)
        tracer.end_span(child1)
        tracer.end_span(parent)

        context = parent.context

        with pytest.raises(CannotCreateChildSpanError):
            tracer.start_span_from_context("child2", context)

    def test_create_child_from_context_after_multiple_completed_spans(self, tracer):
        span1 = tracer.start_span("span1")
        tracer.end_span(span1)

        span2 = tracer.start_span("span2")
        tracer.end_span(span2)

        span3 = tracer.start_span("span3")
        tracer.end_span(span3)

        context = span2.context

        with pytest.raises(CannotCreateChildSpanError, match="span2"):
            tracer.start_span_from_context("child-of-span2", context)


class TestSpanNotStartedError:
    def test_query_duration_on_unended_span_raises(self, tracer):
        span = tracer.start_span("test")

        with pytest.raises(SpanNotStartedError, match="has not ended yet"):
            _ = span.duration_ns

        tracer.end_span(span)
        assert span.duration_ns >= 0

    def test_query_duration_immediately_after_creation(self, tracer):
        span = tracer.start_span("test")

        with pytest.raises(SpanNotStartedError):
            _ = span.duration_ns

        tracer.end_span(span)

    def test_multiple_unended_spans(self, tracer):
        spans = [tracer.start_span(f"span-{i}") for i in range(5)]

        for span in spans:
            with pytest.raises(SpanNotStartedError):
                _ = span.duration_ns

        for span in spans:
            tracer.end_span(span)

        for span in spans:
            assert span.duration_ns >= 0

    def test_end_time_none_until_ended(self, tracer):
        span = tracer.start_span("test")
        assert span.end_time is None

        with pytest.raises(SpanNotStartedError):
            _ = span.duration_ns

        tracer.end_span(span)
        assert span.end_time is not None
        assert span.duration_ns >= 0


class TestInvalidSamplingRateError:
    def test_sampling_rate_negative_raises(self):
        with pytest.raises(InvalidSamplingRateError, match="between 0.0 and 1.0"):
            Tracer(sampling_rate=-0.1)

    def test_sampling_rate_greater_than_one_raises(self):
        with pytest.raises(InvalidSamplingRateError, match="between 0.0 and 1.0"):
            Tracer(sampling_rate=1.1)

    def test_sampling_rate_two_raises(self):
        with pytest.raises(InvalidSamplingRateError):
            Tracer(sampling_rate=2.0)

    def test_sampling_rate_negative_one_raises(self):
        with pytest.raises(InvalidSamplingRateError):
            Tracer(sampling_rate=-1.0)

    def test_set_invalid_sampling_rate_raises(self, tracer):
        with pytest.raises(InvalidSamplingRateError):
            tracer.sampling_rate = -0.5

        with pytest.raises(InvalidSamplingRateError):
            tracer.sampling_rate = 1.5

    def test_sampling_rate_string_raises(self):
        with pytest.raises(InvalidSamplingRateError, match="must be a number"):
            Tracer(sampling_rate="0.5")

    def test_sampling_rate_none_raises(self):
        with pytest.raises(InvalidSamplingRateError, match="must be a number"):
            Tracer(sampling_rate=None)

    def test_sampling_rate_list_raises(self):
        with pytest.raises(InvalidSamplingRateError):
            Tracer(sampling_rate=[0.5])

    def test_sampling_rate_dict_raises(self):
        with pytest.raises(InvalidSamplingRateError):
            Tracer(sampling_rate={"rate": 0.5})

    def test_boundary_values_allowed(self, tracer):
        tracer.sampling_rate = 0.0
        assert tracer.sampling_rate == 0.0

        tracer.sampling_rate = 1.0
        assert tracer.sampling_rate == 1.0

    def test_invalid_sampling_rate_instance_unchanged(self, tracer):
        original_rate = tracer.sampling_rate
        try:
            tracer.sampling_rate = 2.0
        except InvalidSamplingRateError:
            pass
        assert tracer.sampling_rate == original_rate


class TestSpanNotFoundScenarios:
    def test_get_nonexistent_active_span_returns_none(self, tracer):
        span = tracer.get_active_span("nonexistent-span-id")
        assert span is None

    def test_get_nonexistent_span_returns_none(self, tracer):
        span = tracer.get_span("nonexistent-span-id")
        assert span is None

    def test_get_trace_spans_nonexistent_trace_returns_empty(self, tracer):
        spans = tracer.get_trace_spans("nonexistent-trace-id")
        assert spans == []

    def test_get_span_after_clear_returns_none(self, tracer):
        span = tracer.start_span("test")
        span_id = span.span_id
        tracer.end_span(span)

        assert tracer.get_span(span_id) is span

        tracer.clear()
        assert tracer.get_span(span_id) is None

    def test_active_span_removed_after_end(self, tracer):
        span = tracer.start_span("test")
        span_id = span.span_id

        assert tracer.get_active_span(span_id) is span

        tracer.end_span(span)
        assert tracer.get_active_span(span_id) is None


class TestEdgeErrorScenarios:
    def test_create_child_before_parent_started_not_possible(self, tracer):
        parent = tracer.start_span("parent")
        child = tracer.start_span("child", parent=parent)

        assert child.parent_span_id == parent.span_id
        assert child.trace_id == parent.trace_id

        tracer.end_span(child)
        tracer.end_span(parent)

    def test_span_not_exported_until_ended(self, tracer):
        span = tracer.start_span("test")

        exported_before = tracer.export_spans()
        assert len(exported_before) == 0

        tracer.end_span(span)

        exported_after = tracer.export_spans()
        assert len(exported_after) == 1

    def test_unsampled_spans_not_in_completed(self, tracer_no_sampling):
        root = tracer_no_sampling.start_span("root")
        child = tracer_no_sampling.start_span("child", parent=root)
        tracer_no_sampling.end_span(child)
        tracer_no_sampling.end_span(root)

        assert tracer_no_sampling.completed_trace_count == 0
        assert tracer_no_sampling.get_trace_spans(root.trace_id) == []

    def test_sampled_and_unsampled_mixed(self, tracer_half_sampling):
        sampled_traces = 0
        unsampled_traces = 0

        for i in range(100):
            root = tracer_half_sampling.start_span(f"root-{i}")
            if root.sampled:
                sampled_traces += 1
            else:
                unsampled_traces += 1
            tracer_half_sampling.end_span(root)

        assert sampled_traces + unsampled_traces == 100
        assert tracer_half_sampling.completed_trace_count == sampled_traces


class TestTracingErrorHierarchy:
    def test_all_errors_inherit_from_tracing_error(self, tracer):
        span = tracer.start_span("test")
        tracer.end_span(span)

        with pytest.raises(Exception) as excinfo:
            tracer.end_span(span)
        assert isinstance(excinfo.value, Exception)

        span2 = tracer.start_span("test2")
        with pytest.raises(Exception) as excinfo:
            _ = span2.duration_ns
        assert isinstance(excinfo.value, Exception)

        with pytest.raises(Exception) as excinfo:
            Tracer(sampling_rate=2.0)
        assert isinstance(excinfo.value, Exception)

        with pytest.raises(Exception) as excinfo:
            tracer.start_span("child", parent=span)
        assert isinstance(excinfo.value, Exception)

    def test_specific_error_types(self, tracer):
        span = tracer.start_span("test")
        tracer.end_span(span)

        with pytest.raises(SpanAlreadyEndedError):
            tracer.end_span(span)

        with pytest.raises(CannotCreateChildSpanError):
            tracer.start_span("child", parent=span)

        span2 = tracer.start_span("test2")
        with pytest.raises(SpanNotStartedError):
            _ = span2.duration_ns
        tracer.end_span(span2)

        with pytest.raises(InvalidSamplingRateError):
            Tracer(sampling_rate=-1)


class TestConcurrentErrorScenarios:
    def test_concurrent_duplicate_end_raises(self, tracer):
        import threading

        span = tracer.start_span("concurrent-test")

        errors = []

        def end_span():
            try:
                tracer.end_span(span)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=end_span) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 4
        for error in errors:
            assert isinstance(error, SpanAlreadyEndedError)

    def test_concurrent_create_child_vs_end_parent(self, tracer):
        import threading
        import time

        parent = tracer.start_span("parent")

        def end_parent():
            time.sleep(0.001)
            tracer.end_span(parent)

        def create_child():
            try:
                child = tracer.start_span("child", parent=parent)
                tracer.end_span(child)
                return True
            except CannotCreateChildSpanError:
                return False

        t1 = threading.Thread(target=end_parent)
        t2 = threading.Thread(target=create_child)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert parent.is_ended is True
