from __future__ import annotations

import threading
from typing import List, Optional

from .exceptions import AllCombinatorError, AnyCombinatorError
from .future import Future
from .models import FutureState


def all_combinator(futures: List[Future]) -> Future:
    if not futures:
        return Future.completed([])

    result_future: Future = Future()
    total = len(futures)
    completed_count: int = 0
    results: list = [None] * total
    lock = threading.Lock()
    first_error: Optional[Exception] = None

    def on_complete(index: int, f: Future) -> None:
        nonlocal completed_count, first_error

        with lock:
            if result_future.is_done:
                return

            if f.state == FutureState.FAILED:
                if first_error is None:
                    first_error = f.error
                try:
                    result_future.set_error(AllCombinatorError(first_error))
                except Exception:
                    pass
                return

            results[index] = f.result
            completed_count += 1

            if completed_count == total:
                try:
                    result_future.set_result(list(results))
                except Exception:
                    pass

    for i, f in enumerate(futures):
        f.add_callback(lambda fut, idx=i: on_complete(idx, fut))

    return result_future


def any_combinator(futures: List[Future]) -> Future:
    if not futures:
        return Future.failed(
            AnyCombinatorError([])
        )

    result_future: Future = Future()
    total = len(futures)
    failed_count: int = 0
    errors: list[Exception] = [None] * total
    lock = threading.Lock()

    def on_complete(index: int, f: Future) -> None:
        nonlocal failed_count

        with lock:
            if result_future.is_done:
                return

            if f.state == FutureState.COMPLETED:
                try:
                    result_future.set_result(f.result)
                except Exception:
                    pass
                return

            errors[index] = f.error
            failed_count += 1

            if failed_count == total:
                try:
                    result_future.set_error(AnyCombinatorError(list(errors)))
                except Exception:
                    pass

    for i, f in enumerate(futures):
        f.add_callback(lambda fut, idx=i: on_complete(idx, fut))

    return result_future


def race_combinator(futures: List[Future]) -> Future:
    if not futures:
        raise ValueError("race_combinator requires at least one Future")

    result_future: Future = Future()
    settled = threading.Event()

    def on_complete(f: Future) -> None:
        if settled.is_set():
            return
        settled.set()
        if f.state == FutureState.COMPLETED:
            try:
                result_future.set_result(f.result)
            except Exception:
                pass
        else:
            try:
                result_future.set_error(f.error)
            except Exception:
                pass

    for f in futures:
        f.add_callback(on_complete)

    return result_future
