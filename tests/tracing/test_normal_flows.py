from __future__ import annotations

import threading
import time

import pytest

from solocoder_py.tracing import Span, Tracer, TraceContext


class TestTraceIdGeneration:
    def test_trace_id_format(self, tracer):
        span = tracer.start_span("test")
        assert len(span.trace_id) == 32
        assert all(c in "0123456789abcdef" for c in span.trace_id)

    def test_trace_id_unique_single_thread(self, tracer):
        trace_ids = set()
        for _ in range(1000):
            span = tracer.start_span("test")
            trace_ids.add(span.trace_id)
            tracer.end_span(span)
        assert len(trace_ids) == 1000

    def test_trace_id_unique_concurrent(self, tracer):
        trace_ids = set()
        lock = threading.Lock()
        num_threads = 20
        spans_per_thread = 100

        def worker():
            local_ids = set()
            for _ in range(spans_per_thread):
                span = tracer.start_span("concurrent")
                local_ids.add(span.trace_id)
                tracer.end_span(span)
            with lock:
                trace_ids.update(local_ids)

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        expected = num_threads * spans_per_thread
        assert len(trace_ids) == expected

    def test_trace_id_contains_timestamp_component(self, tracer):
        before = time.time_ns() >> 16
        span = tracer.start_span("test")
        after = time.time_ns() >> 16

        trace_id = span.trace_id
        timestamp_part = int(trace_id[:12], 16)
        assert before <= timestamp_part <= after


class TestSpanIdGeneration:
    def test_span_id_format(self, tracer):
        span = tracer.start_span("test")
        assert len(span.span_id) == 16
        assert all(c in "0123456789abcdef" for c in span.span_id)

    def test_span_id_unique(self, tracer):
        span_ids = set()
        root = tracer.start_span("root")
        span_ids.add(root.span_id)
        for i in range(100):
            child = tracer.start_span(f"child-{i}", parent=root)
            assert child.span_id not in span_ids
            span_ids.add(child.span_id)
            tracer.end_span(child)
        tracer.end_span(root)
        assert len(span_ids) == 101


class TestParentChildSpanLinking:
    def test_root_span_no_parent(self, tracer):
        root = tracer.start_span("root")
        assert root.parent_span_id is None
        tracer.end_span(root)

    def test_child_span_inherits_trace_id(self, tracer):
        root = tracer.start_span("root")
        child = tracer.start_span("child", parent=root)
        assert child.trace_id == root.trace_id
        tracer.end_span(child)
        tracer.end_span(root)

    def test_child_span_parent_id(self, tracer):
        root = tracer.start_span("root")
        child = tracer.start_span("child", parent=root)
        assert child.parent_span_id == root.span_id
        tracer.end_span(child)
        tracer.end_span(root)

    def test_multi_level_nesting(self, tracer):
        level0 = tracer.start_span("level0")
        level1 = tracer.start_span("level1", parent=level0)
        level2 = tracer.start_span("level2", parent=level1)
        level3 = tracer.start_span("level3", parent=level2)

        assert level0.trace_id == level1.trace_id == level2.trace_id == level3.trace_id
        assert level0.parent_span_id is None
        assert level1.parent_span_id == level0.span_id
        assert level2.parent_span_id == level1.span_id
        assert level3.parent_span_id == level2.span_id

        tracer.end_span(level3)
        tracer.end_span(level2)
        tracer.end_span(level1)
        tracer.end_span(level0)

    def test_multiple_children_same_parent(self, tracer):
        root = tracer.start_span("root")
        child1 = tracer.start_span("child1", parent=root)
        child2 = tracer.start_span("child2", parent=root)
        child3 = tracer.start_span("child3", parent=root)

        assert len(root.children) == 3
        assert child1.parent_span_id == root.span_id
        assert child2.parent_span_id == root.span_id
        assert child3.parent_span_id == root.span_id
        assert child1.trace_id == child2.trace_id == child3.trace_id == root.trace_id

        tracer.end_span(child1)
        tracer.end_span(child2)
        tracer.end_span(child3)
        tracer.end_span(root)

    def test_children_order_preserved(self, tracer):
        root = tracer.start_span("root")
        for i in range(10):
            child = tracer.start_span(f"child-{i}", parent=root)
            tracer.end_span(child)

        for i, child in enumerate(root.children):
            assert child.name == f"child-{i}"

        tracer.end_span(root)

    def test_span_records_timestamps(self, tracer):
        span = tracer.start_span("test")
        start_time = span.start_time
        assert start_time > 0

        time.sleep(0.001)
        tracer.end_span(span)

        assert span.end_time is not None
        assert span.end_time > start_time
        assert span.duration_ns > 0


class TestSamplingPropagation:
    def test_sampling_decision_made_at_root(self, tracer_half_sampling):
        sampled_decisions = set()
        for _ in range(100):
            root = tracer_half_sampling.start_span("root")
            sampled_decisions.add(root.sampled)
            tracer_half_sampling.end_span(root)
        assert len(sampled_decisions) == 2

    def test_sampling_propagates_to_children(self, tracer_half_sampling):
        for _ in range(100):
            root = tracer_half_sampling.start_span("root")
            child1 = tracer_half_sampling.start_span("child1", parent=root)
            child2 = tracer_half_sampling.start_span("child2", parent=root)
            grandchild = tracer_half_sampling.start_span("grandchild", parent=child1)

            assert root.sampled == child1.sampled
            assert root.sampled == child2.sampled
            assert root.sampled == grandchild.sampled

            tracer_half_sampling.end_span(grandchild)
            tracer_half_sampling.end_span(child2)
            tracer_half_sampling.end_span(child1)
            tracer_half_sampling.end_span(root)

    def test_sampling_rate_approximate(self, tracer_half_sampling):
        sampled_count = 0
        total = 10000
        for _ in range(total):
            root = tracer_half_sampling.start_span("root")
            if root.sampled:
                sampled_count += 1
            tracer_half_sampling.end_span(root)

        ratio = sampled_count / total
        assert 0.4 < ratio < 0.6

    def test_sampled_spans_exported(self, tracer_full_sampling):
        root = tracer_full_sampling.start_span("root")
        child = tracer_full_sampling.start_span("child", parent=root)
        tracer_full_sampling.end_span(child)
        tracer_full_sampling.end_span(root)

        exported = tracer_full_sampling.export_spans()
        assert len(exported) == 2
        assert all(s["sampled"] for s in exported)

    def test_unsampled_spans_not_exported(self, tracer_no_sampling):
        for _ in range(10):
            root = tracer_no_sampling.start_span("root")
            child = tracer_no_sampling.start_span("child", parent=root)
            tracer_no_sampling.end_span(child)
            tracer_no_sampling.end_span(root)

        exported = tracer_no_sampling.export_spans()
        assert len(exported) == 0

    def test_sampling_consistent_within_trace(self, tracer):
        tracer.sampling_rate = 0.3
        for _ in range(100):
            root = tracer.start_span("root")
            sampled = root.sampled
            for i in range(10):
                child = tracer.start_span(f"child-{i}", parent=root)
                assert child.sampled == sampled
                tracer.end_span(child)
            tracer.end_span(root)


class TestSpanLifecycle:
    def test_span_starts_active(self, tracer):
        span = tracer.start_span("test")
        assert span.is_ended is False
        assert tracer.get_active_span(span.span_id) is span

    def test_end_span_moves_to_completed(self, tracer):
        span = tracer.start_span("test")
        span_id = span.span_id
        trace_id = span.trace_id

        tracer.end_span(span)

        assert span.is_ended is True
        assert tracer.get_active_span(span_id) is None
        completed = tracer.get_trace_spans(trace_id)
        assert len(completed) == 1
        assert completed[0].span_id == span_id

    def test_active_span_count(self, tracer):
        assert tracer.active_span_count == 0

        spans = [tracer.start_span(f"span-{i}") for i in range(5)]
        assert tracer.active_span_count == 5

        for span in spans[:3]:
            tracer.end_span(span)
        assert tracer.active_span_count == 2

        for span in spans[3:]:
            tracer.end_span(span)
        assert tracer.active_span_count == 0


class TestSpanAttributes:
    def test_set_and_get_attribute(self, tracer):
        span = tracer.start_span("test")
        span.set_attribute("key1", "value1")
        span.set_attribute("key2", "value2")

        assert span.get_attribute("key1") == "value1"
        assert span.get_attribute("key2") == "value2"
        assert span.get_attribute("nonexistent") is None

        tracer.end_span(span)

    def test_attributes_included_in_export(self, tracer):
        span = tracer.start_span("test")
        span.set_attribute("service", "api")
        span.set_attribute("version", "v1")
        tracer.end_span(span)

        exported = tracer.export_spans()[0]
        assert exported["attributes"]["service"] == "api"
        assert exported["attributes"]["version"] == "v1"


class TestTraceContext:
    def test_span_context(self, tracer):
        span = tracer.start_span("test")
        context = span.context

        assert isinstance(context, TraceContext)
        assert context.trace_id == span.trace_id
        assert context.span_id == span.span_id
        assert context.sampled == span.sampled
        assert context.parent_span_id == span.parent_span_id

        tracer.end_span(span)

    def test_start_span_from_context(self, tracer):
        parent = tracer.start_span("parent")
        context = parent.context

        child = tracer.start_span_from_context("child", context)
        assert child.trace_id == parent.trace_id
        assert child.parent_span_id == parent.span_id
        assert child.sampled == parent.sampled

        tracer.end_span(child)
        tracer.end_span(parent)

    def test_context_propagation_across_independent_spans(self, tracer):
        span1 = tracer.start_span("span1")
        context = span1.context
        tracer.end_span(span1)

        span2 = tracer.start_span_from_context("span2", context)
        assert span2.trace_id == span1.trace_id
        assert span2.parent_span_id == span1.span_id
        assert span2.sampled == span1.sampled

        tracer.end_span(span2)


class TestQueryOperations:
    def test_get_trace_spans(self, tracer):
        root = tracer.start_span("root")
        child1 = tracer.start_span("child1", parent=root)
        child2 = tracer.start_span("child2", parent=root)

        tracer.end_span(child1)
        tracer.end_span(child2)
        tracer.end_span(root)

        spans = tracer.get_trace_spans(root.trace_id)
        assert len(spans) == 3
        span_names = {s.name for s in spans}
        assert span_names == {"root", "child1", "child2"}

    def test_get_trace_root(self, tracer):
        root = tracer.start_span("root")
        child = tracer.start_span("child", parent=root)

        tracer.end_span(child)
        tracer.end_span(root)

        found_root = tracer.get_trace_root(root.trace_id)
        assert found_root is not None
        assert found_root.span_id == root.span_id

    def test_get_span_active_and_completed(self, tracer):
        span = tracer.start_span("test")
        span_id = span.span_id

        assert tracer.get_span(span_id) is span

        tracer.end_span(span)
        assert tracer.get_span(span_id) is span

    def test_get_nonexistent_span_returns_none(self, tracer):
        assert tracer.get_span("nonexistent-id") is None


class TestTracerSingleton:
    def test_get_instance_returns_same_object(self):
        Tracer.reset_instance()
        t1 = Tracer.get_instance(sampling_rate=0.5)
        t2 = Tracer.get_instance()
        assert t1 is t2

    def test_reset_instance_creates_new(self):
        Tracer.reset_instance()
        t1 = Tracer.get_instance()
        Tracer.reset_instance()
        t2 = Tracer.get_instance()
        assert t1 is not t2

    def test_independent_tracer_instances(self):
        t1 = Tracer(sampling_rate=1.0)
        t2 = Tracer(sampling_rate=0.0)

        span1 = t1.start_span("span1")
        span2 = t2.start_span("span2")

        assert span1.sampled is True
        assert span2.sampled is False

        t1.end_span(span1)
        t2.end_span(span2)

        assert len(t1.export_spans()) == 1
        assert len(t2.export_spans()) == 0


class TestConcurrency:
    def test_concurrent_span_creation_no_id_collision(self, tracer):
        num_threads = 50
        spans_per_thread = 200
        all_span_ids = set()
        all_trace_ids = set()
        lock = threading.Lock()

        def worker():
            local_span_ids = set()
            local_trace_ids = set()
            for _ in range(spans_per_thread):
                span = tracer.start_span("concurrent")
                local_span_ids.add(span.span_id)
                local_trace_ids.add(span.trace_id)
                tracer.end_span(span)
            with lock:
                all_span_ids.update(local_span_ids)
                all_trace_ids.update(local_trace_ids)

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        expected = num_threads * spans_per_thread
        assert len(all_span_ids) == expected
        assert len(all_trace_ids) == expected

    def test_concurrent_end_span(self, tracer):
        spans = [tracer.start_span(f"span-{i}") for i in range(100)]

        def end_worker(span_list):
            for span in span_list:
                tracer.end_span(span)

        half = len(spans) // 2
        t1 = threading.Thread(target=end_worker, args=(spans[:half],))
        t2 = threading.Thread(target=end_worker, args=(spans[half:],))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert tracer.active_span_count == 0
        assert len(tracer.export_spans()) == 100

    def test_concurrent_nested_spans(self, tracer):
        def worker(worker_id):
            root = tracer.start_span(f"root-{worker_id}")
            for i in range(10):
                child = tracer.start_span(f"child-{worker_id}-{i}", parent=root)
                tracer.end_span(child)
            tracer.end_span(root)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert tracer.completed_trace_count == 20
        total_spans = sum(
            len(tracer.get_trace_spans(trace_id))
            for trace_id in [s[0].trace_id for s in tracer.get_sampled_traces()]
        )
        assert total_spans == 20 * 11
