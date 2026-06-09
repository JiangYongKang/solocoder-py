from __future__ import annotations

import threading
import time

import pytest

from solocoder_py.pipeline import (
    InvalidPipelineConfigError,
    ItemRetryExhaustedError,
    ItemStatus,
    PipelineExecutor,
    PipelineItem,
    PipelineResult,
    PipelineStatus,
    StageConfig,
    StageResult,
    StageStatus,
)


def _assert_all_items_have_terminal_state(result: PipelineResult, expected_total: int):
    assert len(result.items) == expected_total
    terminal_states = {ItemStatus.SUCCESS, ItemStatus.FAILED, ItemStatus.CANCELLED}
    for item in result.items:
        assert item.status in terminal_states, (
            f"Item {item.item_id} has non-terminal state: {item.status}"
        )
    assert result.success_count + result.failed_count + result.cancelled_count == expected_total


class TestPipelineConfigValidation:
    def test_empty_stages_raises(self):
        with pytest.raises(InvalidPipelineConfigError):
            PipelineExecutor(stages=[])

    def test_duplicate_stage_names_raises(self):
        def h(x):
            return x

        with pytest.raises(InvalidPipelineConfigError):
            PipelineExecutor(
                stages=[
                    StageConfig(name="same", handler=h),
                    StageConfig(name="same", handler=h),
                ]
            )

    def test_invalid_stage_config_negative_retries(self):
        def h(x):
            return x

        with pytest.raises(ValueError):
            StageConfig(name="s", handler=h, max_retries=-1)

    def test_invalid_stage_config_negative_delay(self):
        def h(x):
            return x

        with pytest.raises(ValueError):
            StageConfig(name="s", handler=h, retry_delay=-0.1)

    def test_invalid_stage_config_zero_capacity(self):
        def h(x):
            return x

        with pytest.raises(ValueError):
            StageConfig(name="s", handler=h, queue_capacity=0)

    def test_cannot_execute_twice(self, simple_pipeline: PipelineExecutor):
        simple_pipeline.execute([1, 2, 3])
        with pytest.raises(InvalidPipelineConfigError):
            simple_pipeline.execute([4, 5, 6])


class TestNormalFlow:
    def test_single_stage_simple(self, simple_pipeline: PipelineExecutor):
        inputs = [1, 2, 3, 4, 5]
        result = simple_pipeline.execute(inputs)

        assert isinstance(result, PipelineResult)
        assert result.status == PipelineStatus.COMPLETED
        _assert_all_items_have_terminal_state(result, len(inputs))
        assert result.success_count == 5
        assert result.failed_count == 0
        assert result.cancelled_count == 0
        assert result.total_duration >= 0

        for item in result.success_items:
            assert item.status == ItemStatus.SUCCESS
            assert item.stage_results["double"] == item.data * 2

    def test_three_stage_data_flow(self, three_stage_pipeline: PipelineExecutor):
        inputs = [10, 20, 30]
        result = three_stage_pipeline.execute(inputs)

        assert result.status == PipelineStatus.COMPLETED
        _assert_all_items_have_terminal_state(result, len(inputs))
        assert result.success_count == 3

        for item in result.success_items:
            assert item.stage_results["double"] == item.data * 2
            assert item.stage_results["to_str"] == f"str_{item.data * 2}"
            assert item.stage_results["wrap_dict"] == {"value": f"str_{item.data * 2}"}

    def test_stage_results_populated(self, three_stage_pipeline: PipelineExecutor):
        inputs = [1, 2, 3]
        result = three_stage_pipeline.execute(inputs)

        _assert_all_items_have_terminal_state(result, len(inputs))
        assert len(result.stage_results) == 3
        for sr in result.stage_results:
            assert isinstance(sr, StageResult)
            assert sr.status == StageStatus.COMPLETED
            assert sr.duration >= 0

        s1, s2, s3 = result.stage_results
        assert s1.stage_name == "double"
        assert s1.success_count == 3
        assert s1.processed_count == 3

        assert s2.stage_name == "to_str"
        assert s2.success_count == 3
        assert s2.processed_count == 3

        assert s3.stage_name == "wrap_dict"
        assert s3.success_count == 3
        assert s3.processed_count == 3

    def test_empty_input(self, simple_pipeline: PipelineExecutor):
        result = simple_pipeline.execute([])
        assert result.status == PipelineStatus.COMPLETED
        _assert_all_items_have_terminal_state(result, 0)
        assert result.success_count == 0
        assert result.failed_count == 0
        assert result.cancelled_count == 0
        assert len(result.items) == 0

    def test_single_item(self, simple_pipeline: PipelineExecutor):
        result = simple_pipeline.execute([42])
        _assert_all_items_have_terminal_state(result, 1)
        assert result.success_count == 1
        assert result.success_items[0].stage_results["double"] == 84

    def test_preserves_input_order(self, simple_pipeline: PipelineExecutor):
        inputs = list(range(100))
        result = simple_pipeline.execute(inputs)
        _assert_all_items_have_terminal_state(result, len(inputs))
        assert [item.data for item in result.items] == inputs


class TestItemRetry:
    def test_retry_succeeds_after_failures(self):
        call_counts = {}

        def fail_twice_then_succeed(x):
            call_counts[x] = call_counts.get(x, 0) + 1
            if call_counts[x] <= 2:
                raise ValueError(f"fail attempt {call_counts[x]}")
            return x * 10

        stage = StageConfig(
            name="retry_stage",
            handler=fail_twice_then_succeed,
            max_retries=3,
        )
        pipeline = PipelineExecutor(stages=[stage])
        inputs = [1, 2, 3]
        result = pipeline.execute(inputs)

        _assert_all_items_have_terminal_state(result, len(inputs))
        assert result.status == PipelineStatus.COMPLETED
        assert result.success_count == 3
        for item in result.success_items:
            assert item.attempts == 2
            assert item.stage_results["retry_stage"] == item.data * 10

    def test_all_items_need_retry(self):
        per_item_attempts = {}

        def fail_once_per_item(x):
            per_item_attempts[x] = per_item_attempts.get(x, 0) + 1
            if per_item_attempts[x] == 1:
                raise ValueError(f"first attempt for {x} fails")
            return x

        stage = StageConfig(
            name="batch_retry",
            handler=fail_once_per_item,
            max_retries=3,
            retry_delay=0.0,
        )
        pipeline = PipelineExecutor(stages=[stage])
        inputs = [1, 2, 3, 4, 5]
        result = pipeline.execute(inputs)

        _assert_all_items_have_terminal_state(result, len(inputs))
        assert result.success_count == 5
        for item in result.items:
            assert item.status == ItemStatus.SUCCESS
            assert item.attempts == 1

    def test_retry_exhausted_still_fails(self):
        def always_fail(x):
            raise ValueError("permanent failure")

        stage = StageConfig(
            name="fails_forever",
            handler=always_fail,
            max_retries=2,
        )
        pipeline = PipelineExecutor(stages=[stage])
        inputs = [1, 2, 3]
        result = pipeline.execute(inputs)

        _assert_all_items_have_terminal_state(result, len(inputs))
        assert result.failed_count == 3
        for item in result.failed_items:
            assert item.attempts == 2
            assert isinstance(item.error, ItemRetryExhaustedError)
            assert item.error.stage_name == "fails_forever"
            assert item.error.attempts == 3
            assert isinstance(item.error.last_error, ValueError)

    def test_retry_does_not_affect_other_items(self):
        success_ids = set()

        def fail_item_5(x):
            if x == 5:
                raise ValueError("item 5 always fails")
            success_ids.add(x)
            return x * 2

        stage = StageConfig(
            name="mixed",
            handler=fail_item_5,
            max_retries=3,
        )
        pipeline = PipelineExecutor(stages=[stage])
        inputs = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        result = pipeline.execute(inputs)

        _assert_all_items_have_terminal_state(result, len(inputs))
        assert result.success_count == 9
        assert result.failed_count == 1
        failed_item = result.failed_items[0]
        assert failed_item.data == 5
        assert failed_item.attempts == 3

    def test_zero_retries_fails_immediately(self):
        def fail(x):
            raise ValueError("boom")

        stage = StageConfig(name="no_retry", handler=fail, max_retries=0)
        pipeline = PipelineExecutor(stages=[stage])
        result = pipeline.execute([1])

        _assert_all_items_have_terminal_state(result, 1)
        assert result.failed_count == 1
        assert result.items[0].attempts == 0


class TestPipelineTimeout:
    def test_timeout_cancels_pipeline_full_state_check(self):
        def very_slow(x):
            time.sleep(0.5)
            return x

        stage = StageConfig(name="slow", handler=very_slow, queue_capacity=2)
        pipeline = PipelineExecutor(stages=[stage], timeout=0.3)

        inputs = [1, 2, 3, 4, 5]
        result = pipeline.execute(inputs)

        assert result.status == PipelineStatus.TIMED_OUT
        _assert_all_items_have_terminal_state(result, len(inputs))
        assert isinstance(result.error, Exception)
        for item in result.items:
            assert item.status in (ItemStatus.SUCCESS, ItemStatus.CANCELLED)

    def test_timeout_preserves_completed_results_full_state_check(self):
        def fast_first_then_slow(x):
            if x <= 2:
                return x * 2
            time.sleep(0.3)
            return x * 2

        stage = StageConfig(
            name="mixed_speed", handler=fast_first_then_slow, queue_capacity=2
        )
        pipeline = PipelineExecutor(stages=[stage], timeout=0.4)

        inputs = [1, 2, 3, 4, 5]
        result = pipeline.execute(inputs)

        _assert_all_items_have_terminal_state(result, len(inputs))
        successful_data = {item.data for item in result.success_items}
        assert 1 in successful_data
        assert 2 in successful_data
        for item in result.success_items:
            if item.data in (1, 2):
                assert item.stage_results["mixed_speed"] == item.data * 2

    def test_long_timeout_allows_completion(self):
        def handler(x):
            time.sleep(0.01)
            return x * 2

        stage = StageConfig(name="quick", handler=handler, queue_capacity=10)
        pipeline = PipelineExecutor(stages=[stage], timeout=10.0)

        inputs = [1, 2, 3, 4, 5]
        result = pipeline.execute(inputs)

        _assert_all_items_have_terminal_state(result, len(inputs))
        assert result.status == PipelineStatus.COMPLETED
        assert result.success_count == 5

    def test_timeout_near_boundary_just_in_time(self):
        def just_under_timeout(x):
            time.sleep(0.05)
            return x

        stage = StageConfig(name="fast", handler=just_under_timeout)
        pipeline = PipelineExecutor(stages=[stage], timeout=5.0)

        result = pipeline.execute([1])
        _assert_all_items_have_terminal_state(result, 1)
        assert result.status == PipelineStatus.COMPLETED
        assert result.success_count == 1


class TestPipelineCancel:
    def test_manual_cancel(self):
        def slow_handler(x):
            time.sleep(0.2)
            return x

        stage = StageConfig(name="slow", handler=slow_handler, queue_capacity=2)
        pipeline = PipelineExecutor(stages=[stage])

        cancel_timer = threading.Timer(0.15, pipeline.cancel)
        cancel_timer.start()

        inputs = [1, 2, 3, 4, 5]
        result = pipeline.execute(inputs)
        cancel_timer.join()

        _assert_all_items_have_terminal_state(result, len(inputs))
        assert pipeline.is_cancelled
        assert result.status == PipelineStatus.CANCELLED

    def test_cancel_before_execute(self):
        def h(x):
            return x

        stage = StageConfig(name="s", handler=h)
        pipeline = PipelineExecutor(stages=[stage])
        pipeline.cancel()

        assert pipeline.status == PipelineStatus.CANCELLED


class TestBackpressure:
    def test_backpressure_slows_down_fast_producer(self):
        def fast_handler(x):
            return x

        def slow_handler(x):
            time.sleep(0.05)
            return x * 2

        pipeline = PipelineExecutor(
            stages=[
                StageConfig(name="fast", handler=fast_handler, queue_capacity=3),
                StageConfig(name="slow", handler=slow_handler, queue_capacity=3),
            ]
        )

        start = time.monotonic()
        inputs = list(range(10))
        result = pipeline.execute(inputs)
        elapsed = time.monotonic() - start

        _assert_all_items_have_terminal_state(result, len(inputs))
        assert result.status == PipelineStatus.COMPLETED
        assert result.success_count == 10
        assert elapsed >= 0.4

    def test_small_queue_capacity(self):
        def h(x):
            return x * 2

        stage = StageConfig(name="s", handler=h, queue_capacity=1)
        pipeline = PipelineExecutor(stages=[stage])

        inputs = [1, 2, 3, 4, 5]
        result = pipeline.execute(inputs)
        _assert_all_items_have_terminal_state(result, len(inputs))
        assert result.success_count == 5

    def test_multiple_stages_with_backpressure(self):
        def s1(x):
            return x + 1

        def s2(x):
            time.sleep(0.03)
            return x * 2

        def s3(x):
            return str(x)

        pipeline = PipelineExecutor(
            stages=[
                StageConfig(name="s1", handler=s1, queue_capacity=2),
                StageConfig(name="s2", handler=s2, queue_capacity=2),
                StageConfig(name="s3", handler=s3, queue_capacity=2),
            ]
        )

        inputs = [1, 2, 3, 4, 5]
        result = pipeline.execute(inputs)
        _assert_all_items_have_terminal_state(result, len(inputs))
        assert result.success_count == 5
        for item in result.success_items:
            expected = str((item.data + 1) * 2)
            assert item.stage_results["s3"] == expected


class TestFailurePropagation:
    def test_failed_items_not_forwarded_to_next_stage(self):
        processed = {"stage2": []}

        def stage1_fail_even(x):
            if x % 2 == 0:
                raise ValueError("even fails")
            return x

        def stage2_collect(x):
            processed["stage2"].append(x)
            return x * 10

        pipeline = PipelineExecutor(
            stages=[
                StageConfig(name="s1", handler=stage1_fail_even, max_retries=0),
                StageConfig(name="s2", handler=stage2_collect),
            ]
        )

        inputs = [1, 2, 3, 4, 5]
        result = pipeline.execute(inputs)

        _assert_all_items_have_terminal_state(result, len(inputs))
        assert result.success_count == 3
        assert result.failed_count == 2
        assert sorted(processed["stage2"]) == [1, 3, 5]

        stage2_result = result.stage_results[1]
        assert stage2_result.processed_count == 3
        assert stage2_result.success_count == 3

    def test_all_items_fail_early_skip_remaining_stages(self):
        def fail_all(x):
            raise ValueError("all fail")

        never_called_flag = {"called": False}

        def never_called(x):
            never_called_flag["called"] = True
            return x

        pipeline = PipelineExecutor(
            stages=[
                StageConfig(name="s1", handler=fail_all, max_retries=0),
                StageConfig(name="s2", handler=never_called),
                StageConfig(name="s3", handler=never_called),
            ]
        )

        inputs = [1, 2, 3]
        result = pipeline.execute(inputs)

        _assert_all_items_have_terminal_state(result, len(inputs))
        assert result.failed_count == 3
        assert never_called_flag["called"] is False

        s1 = result.stage_results[0]
        assert s1.failed_count == 3

        for sr in result.stage_results[1:]:
            assert sr.processed_count == 0
            assert sr.success_count == 0


class TestEdgeCases:
    def test_handler_returns_none(self):
        def return_none(x):
            return None

        stage = StageConfig(name="none_stage", handler=return_none)
        pipeline = PipelineExecutor(stages=[stage])
        inputs = [1, 2, 3]
        result = pipeline.execute(inputs)

        _assert_all_items_have_terminal_state(result, len(inputs))
        assert result.success_count == 3
        for item in result.success_items:
            assert item.stage_results["none_stage"] is None

    def test_large_input_batch(self):
        def h(x):
            return x * 2

        stage = StageConfig(name="bulk", handler=h, queue_capacity=50)
        pipeline = PipelineExecutor(stages=[stage])

        large_input = list(range(500))
        result = pipeline.execute(large_input)

        _assert_all_items_have_terminal_state(result, len(large_input))
        assert result.success_count == 500
        assert len(result.items) == 500

    def test_mixed_success_failure_cancel(self):
        def fail_item2_slow_item5(x):
            if x == 2:
                raise ValueError("item 2 fails")
            if x == 5:
                time.sleep(0.5)
            return x

        stage = StageConfig(
            name="mixed",
            handler=fail_item2_slow_item5,
            max_retries=0,
            queue_capacity=10,
        )
        pipeline = PipelineExecutor(stages=[stage], timeout=0.3)

        inputs = [1, 2, 3, 4, 5, 6]
        result = pipeline.execute(inputs)

        _assert_all_items_have_terminal_state(result, len(inputs))
        assert result.success_count + result.failed_count + result.cancelled_count == 6
        assert result.failed_count == 1
        assert result.failed_items[0].data == 2


class TestPipelineItem:
    def test_item_status_transitions(self):
        item = PipelineItem(item_id="1", data=42)
        assert item.status == ItemStatus.PENDING
        assert item.attempts == 0

        item.mark_processing()
        assert item.status == ItemStatus.PROCESSING

        item.mark_retrying()
        assert item.status == ItemStatus.RETRYING
        assert item.attempts == 1

        item.mark_success("stage1", "result")
        assert item.status == ItemStatus.SUCCESS
        assert item.stage_results["stage1"] == "result"

    def test_item_mark_failed(self):
        item = PipelineItem(item_id="2", data="x")
        err = ValueError("bad")
        item.mark_failed("stage1", err)

        assert item.status == ItemStatus.FAILED
        assert item.error is err
        assert item.stage_results["stage1"] is err

    def test_item_mark_cancelled(self):
        item = PipelineItem(item_id="3", data=99)
        item.mark_cancelled()
        assert item.status == ItemStatus.CANCELLED


class TestPipelineResultProperties:
    def test_result_count_properties(self):
        def fail_even(x):
            if x % 2 == 0:
                raise ValueError("even")
            return x

        stage = StageConfig(name="s", handler=fail_even, max_retries=0)
        pipeline = PipelineExecutor(stages=[stage])

        inputs = [1, 2, 3, 4, 5]
        result = pipeline.execute(inputs)

        _assert_all_items_have_terminal_state(result, len(inputs))
        assert result.success_count == len(result.success_items) == 3
        assert result.failed_count == len(result.failed_items) == 2
        assert result.cancelled_count == len(result.cancelled_items) == 0

        assert [i.data for i in result.success_items] == [1, 3, 5]
        assert [i.data for i in result.failed_items] == [2, 4]


class TestStageResult:
    def test_stage_result_total_count(self):
        sr = StageResult(
            stage_name="test",
            status=StageStatus.COMPLETED,
            success_count=5,
            failed_count=2,
            cancelled_count=1,
        )
        assert sr.total_count == 8


class TestNoOrphanItems:
    def test_timeout_no_pending_items(self):
        def slow(x):
            time.sleep(0.3)
            return x

        stage = StageConfig(name="slow", handler=slow, queue_capacity=2)
        pipeline = PipelineExecutor(stages=[stage], timeout=0.2)

        inputs = list(range(10))
        result = pipeline.execute(inputs)

        terminal = {ItemStatus.SUCCESS, ItemStatus.FAILED, ItemStatus.CANCELLED}
        for item in result.items:
            assert item.status in terminal, (
                f"Found orphan item id={item.item_id} data={item.data} status={item.status}"
            )

    def test_cancel_no_pending_items(self):
        def slow(x):
            time.sleep(0.2)
            return x

        stage = StageConfig(name="slow", handler=slow, queue_capacity=3)
        pipeline = PipelineExecutor(stages=[stage])

        def cancel_after_delay():
            time.sleep(0.15)
            pipeline.cancel()

        t = threading.Thread(target=cancel_after_delay)
        t.start()

        inputs = list(range(10))
        result = pipeline.execute(inputs)
        t.join()

        terminal = {ItemStatus.SUCCESS, ItemStatus.FAILED, ItemStatus.CANCELLED}
        for item in result.items:
            assert item.status in terminal

    def test_feeder_no_orphans_when_interrupted(self):
        call_count = {"n": 0}

        def fail_first_two(x):
            call_count["n"] += 1
            if call_count["n"] <= 2:
                time.sleep(0.2)
            return x

        stage = StageConfig(
            name="s", handler=fail_first_two, queue_capacity=2, max_retries=0
        )
        pipeline = PipelineExecutor(stages=[stage], timeout=0.25)

        inputs = list(range(20))
        result = pipeline.execute(inputs)

        terminal = {ItemStatus.SUCCESS, ItemStatus.FAILED, ItemStatus.CANCELLED}
        for item in result.items:
            assert item.status in terminal, (
                f"Orphan: id={item.item_id} data={item.data} status={item.status}"
            )
        assert result.success_count + result.failed_count + result.cancelled_count == len(
            inputs
        )


class TestEndToEndResultConsistency:
    def test_success_failed_cancelled_sum_equals_total(self):
        def maybe_fail_or_slow(x):
            if x % 7 == 0:
                raise ValueError("div by 7")
            if x % 5 == 0:
                time.sleep(0.3)
            return x * 2

        stage = StageConfig(
            name="mixed", handler=maybe_fail_or_slow, max_retries=0, queue_capacity=5
        )
        pipeline = PipelineExecutor(stages=[stage], timeout=0.5)

        inputs = list(range(1, 21))
        result = pipeline.execute(inputs)

        total = result.success_count + result.failed_count + result.cancelled_count
        assert total == len(inputs), f"{total} != {len(inputs)}"

    def test_multistage_all_items_accounted_for(self):
        def s1_fail_mod3(x):
            if x % 3 == 0:
                raise ValueError("mod 3 fails")
            return x + 1

        def s2_slow_mod5(x):
            if x % 5 == 0:
                time.sleep(0.25)
            return x * 2

        pipeline = PipelineExecutor(
            stages=[
                StageConfig(name="s1", handler=s1_fail_mod3, max_retries=0, queue_capacity=3),
                StageConfig(name="s2", handler=s2_slow_mod5, max_retries=0, queue_capacity=3),
            ],
            timeout=0.5,
        )

        inputs = list(range(1, 16))
        result = pipeline.execute(inputs)

        terminal = {ItemStatus.SUCCESS, ItemStatus.FAILED, ItemStatus.CANCELLED}
        for item in result.items:
            assert item.status in terminal
        assert (
            result.success_count + result.failed_count + result.cancelled_count
            == len(inputs)
        )
