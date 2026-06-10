from __future__ import annotations

import threading
from typing import Dict, List, Optional, Tuple

from .clock import Clock, SystemClock
from .exceptions import (
    InvalidWindowConfigError,
    OperationRejectedError,
    SubjectNotFoundError,
)
from .models import (
    RateCapConfig,
    SubjectQuotas,
    WindowConfig,
    WindowUsage,
)
from .sliding_window import SlidingWindowCounter


class RateCapManager:
    def __init__(
        self,
        config: RateCapConfig,
        clock: Clock | None = None,
    ) -> None:
        self._config: RateCapConfig = config
        self._clock: Clock = clock or SystemClock()
        self._lock: threading.RLock = threading.RLock()

        self._global_counters: Dict[str, SlidingWindowCounter] = {}
        for window in self._config.windows:
            self._global_counters[window.name] = SlidingWindowCounter(
                window_seconds=window.window_seconds,
                max_operations=window.max_operations,
                slide_granularity_seconds=window.slide_granularity_seconds,
                clock=self._clock,
            )

        self._subject_counters: Dict[Tuple[str, str], SlidingWindowCounter] = {}
        for subject_id, quotas in self._config.subject_quotas.items():
            for window in self._config.windows:
                limit = quotas.get_quota(
                    window.name,
                    self._config.get_subject_limit(subject_id, window.name)
                    or window.max_operations,
                )
                key = (subject_id, window.name)
                self._subject_counters[key] = SlidingWindowCounter(
                    window_seconds=window.window_seconds,
                    max_operations=limit,
                    slide_granularity_seconds=window.slide_granularity_seconds,
                    clock=self._clock,
                )

    @property
    def config(self) -> RateCapConfig:
        return self._config

    def _window_names(self) -> List[str]:
        return [w.name for w in self._config.windows]

    def _subject_is_known(self, subject_id: str) -> bool:
        if subject_id in self._config.subject_quotas:
            return True
        if self._config.default_subject_quotas:
            return True
        for window in self._config.windows:
            key = (subject_id, window.name)
            if key in self._subject_counters:
                return True
        return False

    def _ensure_subject_counter(
        self, subject_id: str, window_name: str
    ) -> SlidingWindowCounter:
        key = (subject_id, window_name)
        counter = self._subject_counters.get(key)
        if counter is not None:
            return counter

        limit = self._config.get_subject_limit(subject_id, window_name)
        if limit is None:
            window = self._config.get_window(window_name)
            if window is None:
                raise InvalidWindowConfigError(
                    f"Unknown window: '{window_name}'"
                )
            limit = window.max_operations

        window = self._config.get_window(window_name)
        assert window is not None
        counter = SlidingWindowCounter(
            window_seconds=window.window_seconds,
            max_operations=limit,
            slide_granularity_seconds=window.slide_granularity_seconds,
            clock=self._clock,
        )
        self._subject_counters[key] = counter
        return counter

    def _rollback_global(
        self,
        subject_id: str | None,
        acquired_windows: List[str],
        amount: int,
    ) -> None:
        for wname in acquired_windows:
            self._global_counters[wname]._rollback_last(amount, tag=subject_id)

    def _rollback_subject(
        self,
        subject_id: str,
        acquired_windows: List[str],
        amount: int,
    ) -> None:
        for wname in acquired_windows:
            key = (subject_id, wname)
            counter = self._subject_counters.get(key)
            if counter is not None:
                counter._rollback_last(amount, tag=subject_id)

    def check_operation(
        self, subject_id: str | None, amount: int = 1
    ) -> None:
        if amount <= 0:
            raise ValueError("amount must be positive")

        with self._lock:
            global_acquired: List[str] = []
            subject_acquired: List[str] = []

            try:
                for wname in self._window_names():
                    g_counter = self._global_counters[wname]
                    ok, used, limit = g_counter.try_acquire(
                        amount, tag=subject_id
                    )
                    if not ok:
                        raise OperationRejectedError(
                            subject_id=subject_id,
                            dimension="global",
                            window_name=wname,
                            used=used,
                            limit=limit,
                        )
                    global_acquired.append(wname)

                if subject_id is not None:
                    for wname in self._window_names():
                        s_counter = self._ensure_subject_counter(
                            subject_id, wname
                        )
                        ok, used, limit = s_counter.try_acquire(amount)
                        if not ok:
                            raise OperationRejectedError(
                                subject_id=subject_id,
                                dimension="subject",
                                window_name=wname,
                                used=used,
                                limit=limit,
                            )
                        subject_acquired.append(wname)

            except OperationRejectedError:
                if subject_id is not None:
                    self._rollback_subject(
                        subject_id, subject_acquired, amount
                    )
                self._rollback_global(subject_id, global_acquired, amount)
                raise
            except Exception:
                if subject_id is not None:
                    self._rollback_subject(
                        subject_id, subject_acquired, amount
                    )
                self._rollback_global(subject_id, global_acquired, amount)
                raise

    def is_allowed(self, subject_id: str | None, amount: int = 1) -> bool:
        if amount <= 0:
            raise ValueError("amount must be positive")

        with self._lock:
            for wname in self._window_names():
                if not self._global_counters[wname].can_acquire(amount):
                    return False

            if subject_id is not None:
                for wname in self._window_names():
                    counter = self._ensure_subject_counter(
                        subject_id, wname
                    )
                    if not counter.can_acquire(amount):
                        return False

            return True

    def _build_window_usage(
        self,
        counter: SlidingWindowCounter,
        window_name: str,
        limit: int,
    ) -> WindowUsage:
        used = counter.current_count()
        return WindowUsage(
            window_name=window_name,
            limit=limit,
            used=used,
            remaining=max(0, limit - used),
            window_seconds=counter.window_seconds,
        )

    def query_subject_usage(
        self,
        subject_id: str,
        strict: bool = False,
    ) -> Dict[str, WindowUsage]:
        if not subject_id:
            raise ValueError("subject_id cannot be empty")

        with self._lock:
            if strict and not self._subject_is_known(subject_id):
                raise SubjectNotFoundError(
                    f"Subject '{subject_id}' not found: no quota configured, "
                    f"no default quota available, and no operation history"
                )

            result: Dict[str, WindowUsage] = {}
            for window in self._config.windows:
                wname = window.name
                limit = (
                    self._config.get_subject_limit(subject_id, wname)
                    or window.max_operations
                )
                key = (subject_id, wname)
                counter = self._subject_counters.get(key)
                if counter is None:
                    result[wname] = WindowUsage(
                        window_name=wname,
                        limit=limit,
                        used=0,
                        remaining=limit,
                        window_seconds=window.window_seconds,
                    )
                else:
                    result[wname] = self._build_window_usage(
                        counter, wname, limit
                    )
            return result

    def query_global_usage(self) -> Dict[str, WindowUsage]:
        with self._lock:
            result: Dict[str, WindowUsage] = {}
            for window in self._config.windows:
                wname = window.name
                result[wname] = self._build_window_usage(
                    self._global_counters[wname],
                    wname,
                    window.max_operations,
                )
            return result

    def query_usage(
        self,
        subject_id: str | None = None,
        strict: bool = False,
    ) -> Dict[str, Dict[str, WindowUsage]]:
        result: Dict[str, Dict[str, WindowUsage]] = {
            "global": self.query_global_usage(),
        }
        if subject_id is not None:
            result["subject"] = self.query_subject_usage(
                subject_id, strict=strict
            )
        return result

    def add_subject_quota(
        self,
        subject_id: str,
        per_window_quotas: Dict[str, int],
    ) -> None:
        if not subject_id:
            raise ValueError("subject_id cannot be empty")

        with self._lock:
            if subject_id in self._config.subject_quotas:
                return

            for wname, limit in per_window_quotas.items():
                if self._config.get_window(wname) is None:
                    raise InvalidWindowConfigError(
                        f"Unknown window: '{wname}'"
                    )
                if limit <= 0:
                    raise InvalidWindowConfigError(
                        f"Window '{wname}' quota must be positive"
                    )

            quotas = SubjectQuotas(
                subject_id=subject_id,
                per_window_quotas=dict(per_window_quotas),
            )
            self._config.subject_quotas[subject_id] = quotas

            for window in self._config.windows:
                wname = window.name
                limit = quotas.get_quota(
                    wname,
                    self._config.get_subject_limit(subject_id, wname)
                    or window.max_operations,
                )
                key = (subject_id, wname)
                if key not in self._subject_counters:
                    self._subject_counters[key] = SlidingWindowCounter(
                        window_seconds=window.window_seconds,
                        max_operations=limit,
                        slide_granularity_seconds=window.slide_granularity_seconds,
                        clock=self._clock,
                    )

    def reset_subject(self, subject_id: str) -> None:
        if not subject_id:
            raise ValueError("subject_id cannot be empty")

        with self._lock:
            for window in self._config.windows:
                wname = window.name
                key = (subject_id, wname)
                counter = self._subject_counters.get(key)
                if counter is not None:
                    used = counter.current_count()
                    if used > 0:
                        counter.clear()
                        g_counter = self._global_counters.get(wname)
                        if g_counter is not None:
                            g_counter.remove_by_tag(subject_id, amount=used)

    def reset_global(self) -> None:
        with self._lock:
            for counter in self._global_counters.values():
                counter.clear()

    def reset_all(self) -> None:
        with self._lock:
            self.reset_global()
            for counter in self._subject_counters.values():
                counter.clear()
