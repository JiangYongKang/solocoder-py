from __future__ import annotations

import logging
import threading
import time
from typing import Any, Iterable, List, Optional

from ..backpressure import BackpressureStrategy, BoundedQueue
from .exceptions import (
    InvalidPipelineConfigError,
    ItemRetryExhaustedError,
    PipelineCancelledError,
    PipelineTimeoutError,
)
from .models import (
    ItemStatus,
    PipelineItem,
    PipelineResult,
    PipelineStatus,
    StageConfig,
    StageResult,
    StageStatus,
)

logger = logging.getLogger(__name__)

_SENTINEL = object()


class PipelineExecutor:
    def __init__(
        self,
        stages: List[StageConfig],
        timeout: Optional[float] = None,
    ) -> None:
        if not stages:
            raise InvalidPipelineConfigError("Pipeline must have at least one stage")

        stage_names = [s.name for s in stages]
        if len(set(stage_names)) != len(stage_names):
            raise InvalidPipelineConfigError("Stage names must be unique")

        self._stages = stages
        self._timeout = timeout

        self._status = PipelineStatus.CREATED
        self._cancelled = threading.Event()
        self._items: List[PipelineItem] = []
        self._start_time: Optional[float] = None
        self._end_time: Optional[float] = None
        self._error: Optional[Exception] = None

    @property
    def status(self) -> PipelineStatus:
        return self._status

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled.is_set()

    def cancel(self) -> None:
        if self._status in (PipelineStatus.RUNNING, PipelineStatus.CREATED):
            self._cancelled.set()
            self._status = PipelineStatus.CANCELLED

    def _check_timeout(self) -> None:
        if self._timeout is not None and self._start_time is not None:
            elapsed = time.monotonic() - self._start_time
            if elapsed >= self._timeout:
                self.cancel()
                self._status = PipelineStatus.TIMED_OUT
                self._error = PipelineTimeoutError(self._timeout)

    def _is_time_remaining(self) -> bool:
        if self._cancelled.is_set():
            return False
        if self._timeout is None or self._start_time is None:
            return True
        elapsed = time.monotonic() - self._start_time
        return elapsed < self._timeout

    def _remaining_time(self) -> Optional[float]:
        if self._timeout is None or self._start_time is None:
            return None
        elapsed = time.monotonic() - self._start_time
        remaining = self._timeout - elapsed
        return max(0.0, remaining)

    def execute(self, input_data: Iterable[Any]) -> PipelineResult:
        if self._status != PipelineStatus.CREATED:
            raise InvalidPipelineConfigError(
                f"Pipeline already executed. Current status: {self._status}"
            )

        self._start_time = time.monotonic()
        self._status = PipelineStatus.RUNNING

        try:
            items: List[PipelineItem] = []
            for idx, data in enumerate(input_data):
                items.append(PipelineItem(item_id=str(idx), data=data))

            self._items = items

            current_items = items
            stage_results: List[StageResult] = []

            for stage_idx, stage_config in enumerate(self._stages):
                if not self._is_time_remaining():
                    self._cancel_remaining_items(current_items)
                    stage_results.append(self._build_cancelled_stage_result(stage_config))
                    for remaining_stage in self._stages[stage_idx + 1 :]:
                        stage_results.append(self._build_cancelled_stage_result(remaining_stage))
                    break

                stage_result, current_items = self._run_stage(stage_config, current_items)
                stage_results.append(stage_result)

                if not current_items:
                    for remaining_stage in self._stages[stage_idx + 1 :]:
                        stage_results.append(self._build_cancelled_stage_result(remaining_stage))
                    break

            self._end_time = time.monotonic()

            if self._status == PipelineStatus.TIMED_OUT:
                final_status = PipelineStatus.TIMED_OUT
            elif self._cancelled.is_set():
                final_status = PipelineStatus.CANCELLED
            else:
                final_status = PipelineStatus.COMPLETED
                self._status = final_status

            total_duration = (self._end_time - self._start_time) if self._end_time else 0.0

            return PipelineResult(
                status=final_status,
                items=self._items,
                stage_results=stage_results,
                total_duration=total_duration,
                error=self._error,
            )

        except Exception as exc:
            self._end_time = time.monotonic()
            self._status = PipelineStatus.FAILED
            self._error = exc
            total_duration = (self._end_time - self._start_time) if self._end_time else 0.0
            return PipelineResult(
                status=PipelineStatus.FAILED,
                items=self._items,
                stage_results=[],
                total_duration=total_duration,
                error=exc,
            )

    def _cancel_remaining_items(self, items: List[PipelineItem]) -> None:
        for item in items:
            if item.status in (ItemStatus.PENDING, ItemStatus.PROCESSING, ItemStatus.RETRYING):
                item.mark_cancelled()

    def _build_cancelled_stage_result(self, stage_config: StageConfig) -> StageResult:
        return StageResult(
            stage_name=stage_config.name,
            status=StageStatus.COMPLETED,
            processed_count=0,
            success_count=0,
            failed_count=0,
            cancelled_count=0,
            duration=0.0,
        )

    def _run_stage(
        self, stage_config: StageConfig, input_items: List[PipelineItem]
    ) -> tuple[StageResult, List[PipelineItem]]:
        stage_start = time.monotonic()
        stage_result = StageResult(
            stage_name=stage_config.name,
            status=StageStatus.RUNNING,
        )

        output_items: List[PipelineItem] = []
        queue = BoundedQueue(
            capacity=stage_config.queue_capacity,
            strategy=BackpressureStrategy.BLOCK,
        )

        producer_done = threading.Event()

        def producer():
            try:
                for item in input_items:
                    if not self._is_time_remaining():
                        break
                    if item.status in (ItemStatus.FAILED, ItemStatus.CANCELLED):
                        continue

                    remaining = self._remaining_time()
                    if remaining is not None and remaining <= 0:
                        break

                    result = queue.enqueue(item, timeout=remaining)
                    if not result.success:
                        if self._is_time_remaining():
                            item.mark_cancelled()
                            stage_result.cancelled_count += 1
                        break
            finally:
                producer_done.set()

        producer_thread = threading.Thread(target=producer)
        producer_thread.start()

        try:
            while True:
                self._check_timeout()

                if producer_done.is_set() and queue.size == 0:
                    break

                if not self._is_time_remaining():
                    break

                try:
                    remaining = self._remaining_time()
                    if remaining is not None and remaining <= 0:
                        break
                    wait_timeout = 0.1 if remaining is None else min(0.1, remaining)
                    item = queue.dequeue(timeout=wait_timeout)
                except Exception:
                    continue

                if item is None:
                    continue

                self._process_single_item(stage_config, item, stage_result)

                if item.status == ItemStatus.SUCCESS:
                    stage_result.success_count += 1
                    output_items.append(item)
                elif item.status == ItemStatus.FAILED:
                    stage_result.failed_count += 1
                elif item.status == ItemStatus.CANCELLED:
                    stage_result.cancelled_count += 1

                stage_result.processed_count += 1
        finally:
            producer_thread.join(timeout=1.0)

        while queue.size > 0:
            try:
                item = queue.dequeue(block=False)
                if item is not None and item.status not in (
                    ItemStatus.SUCCESS,
                    ItemStatus.FAILED,
                    ItemStatus.CANCELLED,
                ):
                    item.mark_cancelled()
                    stage_result.cancelled_count += 1
                    stage_result.processed_count += 1
            except Exception:
                break

        stage_result.status = StageStatus.COMPLETED
        stage_result.duration = time.monotonic() - stage_start
        return stage_result, output_items

    def _process_single_item(
        self,
        stage_config: StageConfig,
        item: PipelineItem,
        stage_result: StageResult,
    ) -> None:
        if not self._is_time_remaining():
            item.mark_cancelled()
            return

        item.mark_processing()
        max_attempts = stage_config.max_retries + 1
        last_error: Optional[Exception] = None

        for attempt in range(1, max_attempts + 1):
            if not self._is_time_remaining():
                item.mark_cancelled()
                return

            try:
                input_data = item.data
                if item.stage_results:
                    prev_stages = list(item.stage_results.keys())
                    last_stage = prev_stages[-1]
                    input_data = item.stage_results[last_stage]

                result = stage_config.handler(input_data)
                item.mark_success(stage_config.name, result)
                return

            except Exception as exc:
                last_error = exc
                if attempt < max_attempts:
                    item.mark_retrying()
                    if stage_config.retry_delay > 0:
                        end_sleep = time.monotonic() + stage_config.retry_delay
                        while time.monotonic() < end_sleep:
                            if not self._is_time_remaining():
                                item.mark_cancelled()
                                return
                            time.sleep(min(0.01, end_sleep - time.monotonic()))
                else:
                    retry_error = ItemRetryExhaustedError(
                        stage_name=stage_config.name,
                        item_id=item.item_id,
                        attempts=max_attempts,
                        last_error=exc,
                    )
                    item.mark_failed(stage_config.name, retry_error)
                    return

        if last_error is not None:
            retry_error = ItemRetryExhaustedError(
                stage_name=stage_config.name,
                item_id=item.item_id,
                attempts=max_attempts,
                last_error=last_error,
            )
            item.mark_failed(stage_config.name, retry_error)
