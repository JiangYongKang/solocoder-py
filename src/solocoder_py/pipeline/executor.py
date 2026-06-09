from __future__ import annotations

import logging
import threading
import time
from typing import Any, Iterable, List, Optional

from ..backpressure import BackpressureStrategy, BoundedQueue
from .exceptions import (
    InvalidPipelineConfigError,
    ItemRetryExhaustedError,
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

_POISON = object()


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
        self._timed_out = threading.Event()
        self._items: List[PipelineItem] = []
        self._start_time: Optional[float] = None
        self._end_time: Optional[float] = None
        self._error: Optional[Exception] = None

        self._stage_results: List[StageResult] = []
        self._stage_locks: List[threading.Lock] = []
        for _ in stages:
            self._stage_locks.append(threading.Lock())

    @property
    def status(self) -> PipelineStatus:
        return self._status

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled.is_set()

    @property
    def is_timed_out(self) -> bool:
        return self._timed_out.is_set()

    def cancel(self) -> None:
        if self._status in (PipelineStatus.RUNNING, PipelineStatus.CREATED):
            self._cancelled.set()
            if not self._timed_out.is_set():
                self._status = PipelineStatus.CANCELLED

    def _set_timed_out(self) -> None:
        if not self._timed_out.is_set():
            self._timed_out.set()
            self._cancelled.set()
            self._status = PipelineStatus.TIMED_OUT
            self._error = PipelineTimeoutError(self._timeout or 0.0)

    def _should_stop(self) -> bool:
        return self._cancelled.is_set()

    def _check_and_set_timeout(self) -> None:
        if self._timeout is not None and self._start_time is not None:
            if not self._timed_out.is_set():
                elapsed = time.monotonic() - self._start_time
                if elapsed >= self._timeout:
                    self._set_timed_out()

    def _is_time_remaining(self) -> bool:
        if self._should_stop():
            return False
        if self._timeout is None or self._start_time is None:
            return True
        self._check_and_set_timeout()
        return not self._should_stop()

    def _remaining_time(self) -> Optional[float]:
        if self._timeout is None or self._start_time is None:
            return None
        self._check_and_set_timeout()
        elapsed = time.monotonic() - self._start_time
        remaining = self._timeout - elapsed
        return max(0.0, remaining)

    def _sleep_checking_cancel(self, seconds: float) -> bool:
        end = time.monotonic() + seconds
        while True:
            remaining = end - time.monotonic()
            if remaining <= 0:
                return True
            if self._should_stop():
                return False
            time.sleep(min(0.01, remaining))

    def _get_stage_input(self, item: PipelineItem) -> Any:
        if not item.stage_results:
            return item.data
        prev_keys = list(item.stage_results.keys())
        return item.stage_results[prev_keys[-1]]

    def _run_handler_with_timeout_check(
        self, handler, input_data: Any
    ) -> tuple[bool, Any, Optional[Exception]]:
        if not self._is_time_remaining():
            return False, None, None

        remaining = self._remaining_time()
        if remaining is not None and remaining <= 0:
            return False, None, None

        result_holder: dict = {"done": False, "result": None, "error": None}

        def target():
            try:
                result_holder["result"] = handler(input_data)
            except Exception as e:
                result_holder["error"] = e
            finally:
                result_holder["done"] = True

        worker = threading.Thread(target=target, daemon=True)
        worker.start()

        while True:
            worker.join(timeout=0.05)
            if not worker.is_alive():
                break
            self._check_and_set_timeout()
            if self._should_stop():
                return False, None, None

        return True, result_holder["result"], result_holder["error"]

    def _process_single_item_at_stage(
        self,
        stage_idx: int,
        stage_config: StageConfig,
        item: PipelineItem,
    ) -> None:
        stage_result = self._stage_results[stage_idx]
        stage_lock = self._stage_locks[stage_idx]

        if not self._is_time_remaining():
            item.mark_cancelled()
            with stage_lock:
                stage_result.cancelled_count += 1
                stage_result.processed_count += 1
            return

        item.mark_processing()
        max_attempts = stage_config.max_retries + 1
        last_error: Optional[Exception] = None

        for attempt in range(1, max_attempts + 1):
            if not self._is_time_remaining():
                item.mark_cancelled()
                with stage_lock:
                    stage_result.cancelled_count += 1
                    stage_result.processed_count += 1
                return

            input_data = self._get_stage_input(item)
            ok, handler_result, handler_error = self._run_handler_with_timeout_check(
                stage_config.handler, input_data
            )

            if not ok:
                item.mark_cancelled()
                with stage_lock:
                    stage_result.cancelled_count += 1
                    stage_result.processed_count += 1
                return

            if handler_error is None:
                item.mark_success(stage_config.name, handler_result)
                with stage_lock:
                    stage_result.success_count += 1
                    stage_result.processed_count += 1
                return

            last_error = handler_error
            if attempt < max_attempts:
                item.mark_retrying()
                if stage_config.retry_delay > 0:
                    if not self._sleep_checking_cancel(stage_config.retry_delay):
                        item.mark_cancelled()
                        with stage_lock:
                            stage_result.cancelled_count += 1
                            stage_result.processed_count += 1
                        return
            else:
                retry_error = ItemRetryExhaustedError(
                    stage_name=stage_config.name,
                    item_id=item.item_id,
                    attempts=max_attempts,
                    last_error=handler_error,
                )
                item.mark_failed(stage_config.name, retry_error)
                with stage_lock:
                    stage_result.failed_count += 1
                    stage_result.processed_count += 1
                return

        if last_error is not None:
            retry_error = ItemRetryExhaustedError(
                stage_name=stage_config.name,
                item_id=item.item_id,
                attempts=max_attempts,
                last_error=last_error,
            )
            item.mark_failed(stage_config.name, retry_error)
            with stage_lock:
                stage_result.failed_count += 1
                stage_result.processed_count += 1

    def _try_enqueue(self, queue: BoundedQueue, item: Any) -> bool:
        while True:
            self._check_and_set_timeout()
            if self._should_stop():
                return False
            remaining = self._remaining_time()
            put_timeout = 0.05 if remaining is None else min(0.05, max(0.001, remaining))
            result = queue.enqueue(item, timeout=put_timeout)
            if result.success:
                return True
            if self._should_stop():
                return False

    def _stage_worker(
        self,
        stage_idx: int,
        stage_config: StageConfig,
        in_queue: BoundedQueue,
        out_queue: Optional[BoundedQueue],
        worker_started: threading.Event,
    ) -> None:
        worker_started.set()
        try:
            while True:
                self._check_and_set_timeout()
                if self._should_stop():
                    break

                remaining = self._remaining_time()
                wait_timeout = 0.1 if remaining is None else min(0.1, max(0.001, remaining))

                try:
                    item = in_queue.dequeue(timeout=wait_timeout)
                except Exception:
                    continue

                if item is _POISON:
                    if out_queue is not None:
                        self._try_enqueue(out_queue, _POISON)
                    break

                if item is None:
                    continue

                self._process_single_item_at_stage(stage_idx, stage_config, item)

                if out_queue is not None and item.status == ItemStatus.SUCCESS:
                    if not self._try_enqueue(out_queue, item):
                        if item.status == ItemStatus.SUCCESS:
                            item.mark_cancelled()
                            stage_lock = self._stage_locks[stage_idx]
                            stage_result = self._stage_results[stage_idx]
                            with stage_lock:
                                if stage_result.success_count > 0:
                                    stage_result.success_count -= 1
                                    stage_result.cancelled_count += 1

        except Exception as exc:
            logger.exception(f"Stage worker {stage_config.name} crashed", exc_info=exc)

    def _cancel_all_remaining_items(self) -> None:
        for item in self._items:
            if item.status in (
                ItemStatus.PENDING,
                ItemStatus.PROCESSING,
                ItemStatus.RETRYING,
            ):
                item.mark_cancelled()

    def execute(self, input_data: Iterable[Any]) -> PipelineResult:
        if self._status != PipelineStatus.CREATED:
            raise InvalidPipelineConfigError(
                f"Pipeline already executed. Current status: {self._status}"
            )

        self._start_time = time.monotonic()
        self._status = PipelineStatus.RUNNING

        self._stage_results = []
        for sc in self._stages:
            self._stage_results.append(
                StageResult(
                    stage_name=sc.name,
                    status=StageStatus.RUNNING,
                )
            )

        try:
            items: List[PipelineItem] = []
            for idx, data in enumerate(input_data):
                items.append(PipelineItem(item_id=str(idx), data=data))
            self._items = items

            num_stages = len(self._stages)
            queues: List[BoundedQueue] = []
            for i in range(num_stages):
                sc = self._stages[i]
                q = BoundedQueue(
                    capacity=sc.queue_capacity,
                    strategy=BackpressureStrategy.BLOCK,
                )
                queues.append(q)

            worker_threads: List[threading.Thread] = []
            worker_events: List[threading.Event] = []

            for stage_idx in range(num_stages):
                sc = self._stages[stage_idx]
                in_q = queues[stage_idx]
                out_q = queues[stage_idx + 1] if stage_idx < num_stages - 1 else None

                started = threading.Event()
                t = threading.Thread(
                    target=self._stage_worker,
                    args=(stage_idx, sc, in_q, out_q, started),
                    daemon=True,
                )
                worker_threads.append(t)
                worker_events.append(started)
                t.start()

            for ev in worker_events:
                ev.wait(timeout=1.0)

            feeder_done = threading.Event()

            def feeder():
                try:
                    for item in items:
                        if not self._is_time_remaining():
                            break
                        if item.status in (ItemStatus.FAILED, ItemStatus.CANCELLED):
                            continue
                        if not self._try_enqueue(queues[0], item):
                            break
                finally:
                    self._try_enqueue(queues[0], _POISON)
                    feeder_done.set()

            feeder_thread = threading.Thread(target=feeder, daemon=True)
            feeder_thread.start()

            poll_interval = 0.05
            while True:
                self._check_and_set_timeout()
                if self._should_stop():
                    break

                all_dead = all(not t.is_alive() for t in worker_threads)
                if all_dead and feeder_done.is_set():
                    break

                remaining = self._remaining_time()
                if remaining is not None and remaining <= 0:
                    break

                time.sleep(poll_interval)

            if self._should_stop():
                for q in queues:
                    for _ in range(q.capacity + 5):
                        try:
                            q.enqueue(_POISON, strategy=BackpressureStrategy.DROP, timeout=0.001)
                        except Exception:
                            break

            for t in worker_threads:
                t.join(timeout=1.0)

            feeder_thread.join(timeout=1.0)

            for q in queues:
                while q.size > 0:
                    try:
                        leftover = q.dequeue(block=False)
                    except Exception:
                        break
                    if leftover is _POISON or leftover is None:
                        continue
                    if isinstance(leftover, PipelineItem):
                        if leftover.status in (
                            ItemStatus.PENDING,
                            ItemStatus.PROCESSING,
                            ItemStatus.RETRYING,
                        ):
                            leftover.mark_cancelled()

            self._cancel_all_remaining_items()

            self._end_time = time.monotonic()

            for sr in self._stage_results:
                sr.status = StageStatus.COMPLETED
                sr.duration = self._end_time - self._start_time

            if self._timed_out.is_set():
                final_status = PipelineStatus.TIMED_OUT
            elif self._cancelled.is_set():
                final_status = PipelineStatus.CANCELLED
            else:
                final_status = PipelineStatus.COMPLETED

            self._status = final_status
            total_duration = self._end_time - self._start_time

            return PipelineResult(
                status=final_status,
                items=self._items,
                stage_results=list(self._stage_results),
                total_duration=total_duration,
                error=self._error,
            )

        except Exception as exc:
            self._end_time = time.monotonic()
            self._status = PipelineStatus.FAILED
            self._error = exc
            self._cancel_all_remaining_items()
            total_duration = (
                (self._end_time - self._start_time) if self._end_time else 0.0
            )
            for sr in self._stage_results:
                sr.status = StageStatus.COMPLETED
                sr.duration = total_duration
            return PipelineResult(
                status=PipelineStatus.FAILED,
                items=self._items,
                stage_results=list(self._stage_results),
                total_duration=total_duration,
                error=exc,
            )
