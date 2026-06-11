from __future__ import annotations

import threading
from typing import Optional

from .exceptions import FutureTimeoutError
from .future import Future
from .models import FutureState


def with_timeout(future: Future, timeout: float) -> Future:
    if timeout <= 0:
        raise ValueError("timeout must be positive")

    if future.is_done:
        return future

    result_future: Future = Future()
    settled = threading.Event()

    def on_original_complete(f: Future) -> None:
        if settled.is_set():
            return
        settled.set()
        if f.state == FutureState.COMPLETED:
            result_future.set_result(f.result)
        else:
            result_future.set_error(f.error)

    def on_timeout() -> None:
        if settled.is_set():
            return
        settled.set()
        result_future.set_error(
            FutureTimeoutError(f"Future timed out after {timeout} seconds")
        )

    future.add_callback(on_original_complete)

    timer = threading.Timer(timeout, on_timeout)
    timer.daemon = True
    timer.start()

    def cancel_timer(f: Future) -> None:
        timer.cancel()

    result_future.add_callback(cancel_timer)

    return result_future
