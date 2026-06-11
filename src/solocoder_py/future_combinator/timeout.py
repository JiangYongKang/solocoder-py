from __future__ import annotations

import logging
import threading
from typing import Optional

from .exceptions import FutureAlreadyCompletedError, FutureTimeoutError
from .future import Future
from .models import FutureState

logger = logging.getLogger(__name__)


def with_timeout(future: Future, timeout: float) -> Future:
    if timeout <= 0:
        raise ValueError("timeout must be positive")

    if future.is_done:
        return future

    result_future: Future = Future()
    settled_lock = threading.Lock()
    settled_flag: bool = False

    def on_original_complete(f: Future) -> None:
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
                logger.exception("Unexpected error in with_timeout on_original_complete")
        else:
            try:
                result_future.set_error(f.error)
            except FutureAlreadyCompletedError:
                pass
            except Exception:
                logger.exception("Unexpected error in with_timeout on_original_complete")

    def on_timeout() -> None:
        nonlocal settled_flag

        with settled_lock:
            if settled_flag:
                return
            settled_flag = True

        try:
            result_future.set_error(
                FutureTimeoutError(f"Future timed out after {timeout} seconds")
            )
        except FutureAlreadyCompletedError:
            pass
        except Exception:
            logger.exception("Unexpected error in with_timeout on_timeout")

    future.add_callback(on_original_complete)

    timer = threading.Timer(timeout, on_timeout)
    timer.daemon = True
    timer.start()

    def cancel_timer(f: Future) -> None:
        timer.cancel()

    result_future.add_callback(cancel_timer)

    return result_future
