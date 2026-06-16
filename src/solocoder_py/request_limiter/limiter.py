from __future__ import annotations

import io
from typing import Any, Generator, Optional

from .exceptions import IncompleteReadError, PayloadTooLargeError
from .models import (
    Handler,
    LimitConfig,
    LimitResult,
    LimitStats,
    LimitStatus,
    Request,
    Response,
)


class _ChunkedByteStream:
    def __init__(self, source: Any, chunk_size: int) -> None:
        self._source = source
        self._chunk_size = chunk_size
        self._bytes_read = 0

    @property
    def bytes_read(self) -> int:
        return self._bytes_read

    def __iter__(self) -> Generator[bytes, None, None]:
        if hasattr(self._source, "read"):
            yield from self._from_readable()
        elif isinstance(self._source, (bytes, bytearray)):
            yield from self._from_bytes(bytes(self._source))
        elif isinstance(self._source, (list, tuple)):
            yield from self._from_sequence(self._source)
        elif self._source is None:
            return
        else:
            yield from self._from_bytes(str(self._source).encode("utf-8"))

    def _from_readable(self) -> Generator[bytes, None, None]:
        while True:
            try:
                chunk = self._source.read(self._chunk_size)
            except Exception:
                raise IncompleteReadError(
                    received_bytes=self._bytes_read,
                    message="Connection interrupted while reading request body",
                )
            if chunk is None or len(chunk) == 0:
                break
            chunk_bytes = bytes(chunk)
            self._bytes_read += len(chunk_bytes)
            yield chunk_bytes

    def _from_bytes(self, data: bytes) -> Generator[bytes, None, None]:
        offset = 0
        total = len(data)
        while offset < total:
            end = min(offset + self._chunk_size, total)
            chunk = data[offset:end]
            self._bytes_read += len(chunk)
            yield chunk
            offset = end

    def _from_sequence(self, seq: list | tuple) -> Generator[bytes, None, None]:
        carry = b""
        for item in seq:
            if isinstance(item, (bytes, bytearray)):
                carry += bytes(item)
            else:
                carry += str(item).encode("utf-8")
            while len(carry) >= self._chunk_size:
                chunk = carry[: self._chunk_size]
                carry = carry[self._chunk_size :]
                self._bytes_read += len(chunk)
                yield chunk
        if carry:
            self._bytes_read += len(carry)
            yield carry


class BodySizeLimiter:
    def __init__(self, config: LimitConfig) -> None:
        self._config = config
        self._stats = LimitStats()

    @property
    def config(self) -> LimitConfig:
        return self._config

    @property
    def stats(self) -> LimitStats:
        return self._stats

    def reset_stats(self) -> None:
        self._stats = LimitStats()

    def _build_too_large_response(self) -> Response:
        return Response(
            status_code=self._config.error_status_code,
            body={
                "error": "Payload Too Large",
                "message": self._config.error_message,
            },
        )

    def _build_incomplete_response(self) -> Response:
        return Response(
            status_code=400,
            body={
                "error": "Bad Request",
                "message": "Incomplete request body",
            },
        )

    def _build_internal_error_response(self) -> Response:
        return Response(
            status_code=500,
            body={
                "error": "Internal Server Error",
                "message": "An internal error occurred while processing the request",
            },
        )

    def limit_stream(
        self,
        body_source: Any,
        expected_content_length: Optional[int] = None,
    ) -> LimitResult:
        max_bytes = self._config.max_body_bytes
        chunk_size = self._config.chunk_size
        total_read = 0
        collected_chunks: list[bytes] = []
        stream = _ChunkedByteStream(body_source, chunk_size)

        if (
            expected_content_length is not None
            and expected_content_length > max_bytes
        ):
            result = LimitResult(
                status=LimitStatus.TOO_LARGE,
                total_read_bytes=0,
                limit_bytes=max_bytes,
                body=None,
                error_message=(
                    f"Content-Length header {expected_content_length} bytes "
                    f"exceeds limit {max_bytes} bytes"
                ),
            )
            self._stats.record_result(result)
            raise PayloadTooLargeError(
                limit_bytes=max_bytes,
                received_bytes=0,
                message=result.error_message,
            )

        try:
            for chunk in stream:
                chunk_len = len(chunk)
                if total_read + chunk_len > max_bytes:
                    excess = total_read + chunk_len - max_bytes
                    allowed_chunk = chunk[: max_bytes - total_read]
                    if allowed_chunk:
                        collected_chunks.append(allowed_chunk)
                    total_read = max_bytes + excess
                    result = LimitResult(
                        status=LimitStatus.TOO_LARGE,
                        total_read_bytes=total_read,
                        limit_bytes=max_bytes,
                        body=None,
                        error_message=self._config.error_message,
                    )
                    self._stats.record_result(result)
                    raise PayloadTooLargeError(
                        limit_bytes=max_bytes,
                        received_bytes=total_read,
                    )
                collected_chunks.append(chunk)
                total_read += chunk_len
        except PayloadTooLargeError:
            raise
        except IncompleteReadError as exc:
            result = LimitResult(
                status=LimitStatus.INCOMPLETE,
                total_read_bytes=exc.received_bytes,
                limit_bytes=max_bytes,
                body=None,
                error_message=str(exc),
            )
            self._stats.record_result(result)
            raise

        if (
            expected_content_length is not None
            and total_read < expected_content_length
        ):
            result = LimitResult(
                status=LimitStatus.INCOMPLETE,
                total_read_bytes=total_read,
                limit_bytes=max_bytes,
                body=None,
                error_message=(
                    f"Read {total_read} bytes but Content-Length "
                    f"promised {expected_content_length} bytes"
                ),
            )
            self._stats.record_result(result)
            raise IncompleteReadError(
                received_bytes=total_read,
                expected_bytes=expected_content_length,
            )

        body = b"".join(collected_chunks) if collected_chunks else b""
        result = LimitResult(
            status=LimitStatus.OK,
            total_read_bytes=total_read,
            limit_bytes=max_bytes,
            body=body,
        )
        self._stats.record_result(result)
        return result

    def process_request(
        self,
        request: Request,
        handler: Handler,
    ) -> Response:
        try:
            result = self.limit_stream(
                request.body_stream,
                expected_content_length=request.expected_content_length,
            )
        except PayloadTooLargeError:
            return self._build_too_large_response()
        except IncompleteReadError:
            return self._build_incomplete_response()

        if result.body is None:
            return self._build_too_large_response()

        return handler(request, result.body)

    def safe_process(
        self,
        request: Request,
        handler: Handler,
    ) -> tuple[Response, LimitResult]:
        result: LimitResult | None = None
        try:
            try:
                result = self.limit_stream(
                    request.body_stream,
                    expected_content_length=request.expected_content_length,
                )
            except PayloadTooLargeError as exc:
                result = LimitResult(
                    status=LimitStatus.TOO_LARGE,
                    total_read_bytes=exc.received_bytes,
                    limit_bytes=exc.limit_bytes,
                    body=None,
                    error_message=self._config.error_message,
                )
                return (self._build_too_large_response(), result)
            except IncompleteReadError as exc:
                result = LimitResult(
                    status=LimitStatus.INCOMPLETE,
                    total_read_bytes=exc.received_bytes,
                    limit_bytes=self._config.max_body_bytes,
                    body=None,
                    error_message=str(exc),
                )
                return (self._build_incomplete_response(), result)

            if result.body is None:
                return (self._build_too_large_response(), result)

            return handler(request, result.body), result

        except Exception as exc:
            if result is None:
                result = LimitResult(
                    status=LimitStatus.INCOMPLETE,
                    total_read_bytes=0,
                    limit_bytes=self._config.max_body_bytes,
                    body=None,
                    error_message="An internal error occurred while processing the request",
                )
            return (self._build_internal_error_response(), result)
