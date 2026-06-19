from __future__ import annotations

import time

import pytest

from solocoder_py.tracing import Tracer


class TestSingleSpanTrace:
    def test_single_span_trace_no_parent(self, tracer):
        span = tracer.start_span("single")
        assert span.parent_span_id is None
        assert len(span.children) == 0
        tracer.end_span(span)

        spans = tracer.get_trace_spans(span.trace_id)
        assert len(spans) == 1
        assert spans[0].span_id == span.span_id

    def test_single_span_trace_is_its_own_root(self, tracer):
        span = tracer.start_span("single")
        tracer.end_span(span)

        root = tracer.get_trace_root(span.trace_id)
        assert root is not None
        assert root.span_id == span.span_id
        assert root.parent_span_id is None

    def test_single_span_export(self, tracer):
        span = tracer.start_span("single")
        span.set_attribute("key", "value")
        tracer.end_span(span)

        exported = tracer.export_spans()
        assert len(exported) == 1
        assert exported[0]["name"] == "single"
        assert exported[0]["parent_span_id"] is None
        assert exported[0]["attributes"]["key"] == "value"


class TestMultipleChildren:
    def test_many_children_same_parent(self, tracer):
        root = tracer.start_span("root")
        num_children = 100

        children = []
        for i in range(num_children):
            child = tracer.start_span(f"child-{i}", parent=root)
            children.append(child)

        assert len(root.children) == num_children

        for i, child in enumerate(children):
            assert child.parent_span_id == root.span_id
            assert child.trace_id == root.trace_id
            tracer.end_span(child)

        tracer.end_span(root)

        spans = tracer.get_trace_spans(root.trace_id)
        assert len(spans) == num_children + 1

    def test_children_have_different_span_ids(self, tracer):
        root = tracer.start_span("root")
        span_ids = set()

        for _ in range(50):
            child = tracer.start_span("child", parent=root)
            assert child.span_id not in span_ids
            span_ids.add(child.span_id)
            tracer.end_span(child)

        tracer.end_span(root)
        assert len(span_ids) == 50

    def test_deep_nesting(self, tracer):
        depth = 20
        spans = []

        parent = None
        for i in range(depth):
            span = tracer.start_span(f"level-{i}", parent=parent)
            spans.append(span)
            parent = span

        for i in range(depth):
            if i == 0:
                assert spans[i].parent_span_id is None
            else:
                assert spans[i].parent_span_id == spans[i - 1].span_id
            assert spans[i].trace_id == spans[0].trace_id

        for span in reversed(spans):
            tracer.end_span(span)

        for i, span in enumerate(spans[:-1]):
            assert len(span.children) == 1
            assert span.children[0] == spans[i + 1]

    def test_many_children_each_with_children(self, tracer):
        root = tracer.start_span("root")
        num_children = 10
        grandchildren_per_child = 5

        for i in range(num_children):
            child = tracer.start_span(f"child-{i}", parent=root)
            for j in range(grandchildren_per_child):
                grandchild = tracer.start_span(
                    f"grandchild-{i}-{j}", parent=child
                )
                tracer.end_span(grandchild)
            tracer.end_span(child)

        tracer.end_span(root)

        assert len(root.children) == num_children
        for child in root.children:
            assert len(child.children) == grandchildren_per_child

        total_spans = 1 + num_children + num_children * grandchildren_per_child
        spans = tracer.get_trace_spans(root.trace_id)
        assert len(spans) == total_spans


class TestSamplingBoundary:
    def test_sampling_rate_zero(self, tracer_no_sampling):
        for _ in range(1000):
            root = tracer_no_sampling.start_span("root")
            child = tracer_no_sampling.start_span("child", parent=root)

            assert root.sampled is False
            assert child.sampled is False

            tracer_no_sampling.end_span(child)
            tracer_no_sampling.end_span(root)

        exported = tracer_no_sampling.export_spans()
        assert len(exported) == 0
        assert tracer_no_sampling.completed_trace_count == 0

    def test_sampling_rate_one(self, tracer_full_sampling):
        for _ in range(1000):
            root = tracer_full_sampling.start_span("root")
            child = tracer_full_sampling.start_span("child", parent=root)

            assert root.sampled is True
            assert child.sampled is True

            tracer_full_sampling.end_span(child)
            tracer_full_sampling.end_span(root)

        exported = tracer_full_sampling.export_spans()
        assert len(exported) == 2000
        assert tracer_full_sampling.completed_trace_count == 1000

    def test_sampling_rate_exactly_zero(self, tracer):
        tracer.sampling_rate = 0.0
        for _ in range(100):
            span = tracer.start_span("test")
            assert span.sampled is False
            tracer.end_span(span)

    def test_sampling_rate_exactly_one(self, tracer):
        tracer.sampling_rate = 1.0
        for _ in range(100):
            span = tracer.start_span("test")
            assert span.sampled is True
            tracer.end_span(span)

    def test_sampling_rate_boundary_float(self, tracer):
        tracer.sampling_rate = 0.0001
        sampled_count = 0
        for _ in range(10000):
            span = tracer.start_span("test")
            if span.sampled:
                sampled_count += 1
            tracer.end_span(span)
        assert 0 <= sampled_count <= 50

    def test_sampling_rate_near_one(self, tracer):
        tracer.sampling_rate = 0.9999
        not_sampled_count = 0
        for _ in range(10000):
            span = tracer.start_span("test")
            if not span.sampled:
                not_sampled_count += 1
            tracer.end_span(span)
        assert 0 <= not_sampled_count <= 50


class TestTimingEdgeCases:
    def test_span_duration_zero_if_ended_immediately(self, tracer):
        span = tracer.start_span("fast")
        tracer.end_span(span)
        assert span.duration_ns >= 0

    def test_span_end_time_after_start_time(self, tracer):
        span = tracer.start_span("test")
        time.sleep(0.01)
        tracer.end_span(span)
        assert span.end_time > span.start_time
        assert span.duration_ns >= 1000000

    def test_multiple_spans_sequential_timestamps(self, tracer):
        spans = []
        for _ in range(10):
            span = tracer.start_span("seq")
            time.sleep(0.01)
            tracer.end_span(span)
            spans.append(span)

        for i in range(1, len(spans)):
            assert spans[i].start_time >= spans[i - 1].end_time

    def test_overlapping_spans_timestamps(self, tracer):
        span1 = tracer.start_span("outer")
        time.sleep(0.001)
        span2 = tracer.start_span("inner", parent=span1)
        time.sleep(0.001)
        tracer.end_span(span2)
        time.sleep(0.001)
        tracer.end_span(span1)

        assert span1.start_time < span2.start_time
        assert span2.end_time < span1.end_time
        assert span1.duration_ns > span2.duration_ns


class TestSpanReferenceEdgeCases:
    def test_ended_span_still_has_valid_data(self, tracer):
        span = tracer.start_span("test")
        span.set_attribute("key", "value")
        child = tracer.start_span("child", parent=span)
        tracer.end_span(child)
        tracer.end_span(span)

        assert span.is_ended is True
        assert span.trace_id is not None
        assert span.span_id is not None
        assert span.sampled is True
        assert span.get_attribute("key") == "value"
        assert len(span.children) == 1
        assert span.duration_ns >= 0

    def test_unended_span_not_in_completed(self, tracer):
        span = tracer.start_span("unended")
        trace_id = span.trace_id

        completed = tracer.get_trace_spans(trace_id)
        assert len(completed) == 0

        active = tracer.get_active_span(span.span_id)
        assert active is span

    def test_get_trace_root_for_active_trace(self, tracer):
        root = tracer.start_span("root")
        child = tracer.start_span("child", parent=root)

        found_root = tracer.get_trace_root(root.trace_id)
        assert found_root is root
        assert found_root is not child

        tracer.end_span(child)
        tracer.end_span(root)

    def test_get_trace_root_nonexistent(self, tracer):
        root = tracer.get_trace_root("nonexistent-trace-id")
        assert root is None


class TestClearOperation:
    def test_clear_removes_all_data(self, tracer):
        for i in range(10):
            root = tracer.start_span(f"root-{i}")
            child = tracer.start_span(f"child-{i}", parent=root)
            tracer.end_span(child)
            tracer.end_span(root)

        assert tracer.completed_trace_count == 10
        assert len(tracer.export_spans()) == 20

        tracer.clear()

        assert tracer.completed_trace_count == 0
        assert len(tracer.export_spans()) == 0
        assert tracer.active_span_count == 0

    def test_clear_with_active_spans(self, tracer):
        active_span = tracer.start_span("active")
        root = tracer.start_span("completed")
        tracer.end_span(root)

        assert tracer.active_span_count == 1
        assert tracer.completed_trace_count == 1

        tracer.clear()

        assert tracer.active_span_count == 0
        assert tracer.completed_trace_count == 0

    def test_operations_after_clear(self, tracer):
        tracer.clear()

        span = tracer.start_span("after-clear")
        tracer.end_span(span)

        assert tracer.completed_trace_count == 1
        assert len(tracer.export_spans()) == 1


class TestSpanToDict:
    def test_span_to_dict_includes_all_fields(self, tracer):
        span = tracer.start_span("test")
        span.set_attribute("service", "api")
        span.set_attribute("version", "v1")
        tracer.end_span(span)

        data = span.to_dict()

        assert data["name"] == "test"
        assert data["trace_id"] == span.trace_id
        assert data["span_id"] == span.span_id
        assert data["parent_span_id"] is None
        assert data["start_time"] == span.start_time
        assert data["end_time"] == span.end_time
        assert data["sampled"] is True
        assert data["attributes"] == {"service": "api", "version": "v1"}
        assert data["children"] == []

    def test_span_to_dict_with_children(self, tracer):
        root = tracer.start_span("root")
        child = tracer.start_span("child", parent=root)
        tracer.end_span(child)
        tracer.end_span(root)

        data = root.to_dict()
        assert len(data["children"]) == 1
        assert data["children"][0]["name"] == "child"
        assert data["children"][0]["parent_span_id"] == root.span_id

    def test_span_to_dict_not_ended(self, tracer):
        span = tracer.start_span("not-ended")
        data = span.to_dict()

        assert data["end_time"] is None
        assert data["sampled"] is True


class TestSampledFlagInExport:
    def test_sampled_flag_true_in_export(self, tracer_full_sampling):
        span = tracer_full_sampling.start_span("sampled")
        tracer_full_sampling.end_span(span)

        exported = tracer_full_sampling.export_spans()[0]
        assert exported["sampled"] is True

    def test_sampled_flag_false_not_exported(self, tracer_no_sampling):
        span = tracer_no_sampling.start_span("not-sampled")
        assert span.sampled is False
        tracer_no_sampling.end_span(span)

        exported = tracer_no_sampling.export_spans()
        assert len(exported) == 0

    def test_mixed_sampling_export(self, tracer_half_sampling):
        for _ in range(100):
            root = tracer_half_sampling.start_span("root")
            tracer_half_sampling.end_span(root)

        exported = tracer_half_sampling.export_spans()
        for span_data in exported:
            assert span_data["sampled"] is True


class TestTraceIdEdgeCases:
    def test_trace_id_padding(self, tracer):
        for _ in range(100):
            span = tracer.start_span("test")
            assert len(span.trace_id) == 32
            assert all(c in "0123456789abcdef" for c in span.trace_id)
            tracer.end_span(span)

    def test_span_id_padding(self, tracer):
        for _ in range(100):
            span = tracer.start_span("test")
            assert len(span.span_id) == 16
            assert all(c in "0123456789abcdef" for c in span.span_id)
            tracer.end_span(span)

    def test_trace_ids_monotonically_increasing(self, tracer):
        prev_trace_id = None
        for _ in range(100):
            span = tracer.start_span("test")
            if prev_trace_id is not None:
                assert span.trace_id > prev_trace_id
            prev_trace_id = span.trace_id
            tracer.end_span(span)

    def test_counter_overflow(self, tracer):
        for i in range(65536 + 10):
            span = tracer.start_span(f"test-{i}")
            assert len(span.trace_id) == 32
            tracer.end_span(span)
