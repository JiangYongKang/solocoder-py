from __future__ import annotations

import logging
import threading
from typing import List, Optional

from .exceptions import AllCombinatorError, AnyCombinatorError, FutureAlreadyCompletedError
from .future import Future
from .models import FutureState

logger = logging.getLogger(__name__)


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
                except FutureAlreadyCompletedError:
                    pass
                except Exception:
                    logger.exception("Unexpected error in all_combinator on_complete")
                return

            results[index] = f.result
            completed_count += 1

            if completed_count == total:
                try:
                    result_future.set_result(list(results))
                except FutureAlreadyCompletedError:
                    pass
                except Exception:
                    logger.exception("Unexpected error in all_combinator on_complete")

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
                except FutureAlreadyCompletedError:
                    pass
                except Exception:
                    logger.exception("Unexpected error in any_combinator on_complete")
                return

            errors[index] = f.error
            failed_count += 1

            if failed_count == total:
                try:
                    result_future.set_error(AnyCombinatorError(list(errors)))
                except FutureAlreadyCompletedError:
                    pass
                except Exception:
                    logger.exception("Unexpected error in any_combinator on_complete")

    for i, f in enumerate(futures):
        f.add_callback(lambda fut, idx=i: on_complete(idx, fut))

    return result_future


def race_combinator(futures: List[Future]) -> Future:
    if not futures:
        raise ValueError("race_combinator requires at least one Future")

    result_future: Future = Future()
    settled_lock = threading.Lock()
    settled_flag: bool = False

    def on_complete(f: Future) -> None:
        nonlocal settled_flag

        with settled_lock:
            if settled_flag:
                return
            settled_flag = True

        if f.state == FutureState.COMPLETED:
            try:
                result_future.set_result(f.result)
            except FutureAlreadyCompletedError:
                pass
            except Exception:
                logger.exception("Unexpected error in race_combinator on_complete")
        else:
            try:
                result_future.set_error(f.error)
            except FutureAlreadyCompletedError:
                pass
            except Exception:
                logger.exception("Unexpected error in race_combinator on_complete")

    for f in futures:
        f.add_callback(on_complete)

    return result_future
