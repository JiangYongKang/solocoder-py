from __future__ import annotations

import io

import pytest

from solocoder_py.request_limiter import (
    BodySizeLimiter,
    IncompleteReadError,
    InvalidLimitError,
    LimitConfig,
    LimitStatus,
    PayloadTooLargeError,
    Request,
    Response,
)


# ============================================================
# LimitConfig 验证测试
# ============================================================


class TestLimitConfigValidation:
    def test_valid_config_defaults(self):
        config = LimitConfig(max_body_bytes=1024)
        assert config.max_body_bytes == 1024
        assert config.chunk_size == 8192
        assert config.error_status_code == 413
        assert config.error_message == "Payload Too Large"

    def test_valid_config_custom(self):
        config = LimitConfig(
            max_body_bytes=4096,
            chunk_size=512,
            error_status_code=431,
            error_message="Request Entity Too Large",
        )
        assert config.max_body_bytes == 4096
        assert config.chunk_size == 512
        assert config.error_status_code == 431
        assert config.error_message == "Request Entity Too Large"

    def test_negative_max_body_bytes_raises(self):
        with pytest.raises(InvalidLimitError) as exc_info:
            LimitConfig(max_body_bytes=-1)
        assert exc_info.value.limit == -1

    def test_zero_max_body_bytes_valid(self):
        config = LimitConfig(max_body_bytes=0)
        assert config.max_body_bytes == 0

    def test_zero_chunk_size_raises(self):
        with pytest.raises(InvalidLimitError):
            LimitConfig(max_body_bytes=1024, chunk_size=0)

    def test_negative_chunk_size_raises(self):
        with pytest.raises(InvalidLimitError):
            LimitConfig(max_body_bytes=1024, chunk_size=-512)

    def test_error_status_code_below_400_raises(self):
        with pytest.raises(InvalidLimitError):
            LimitConfig(max_body_bytes=1024, error_status_code=200)


# ============================================================
# 正常流程测试
# ============================================================


class TestNormalFlowWithinLimit:
    def test_body_small_within_limit_bytes_source(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=1024))
        body = b"Hello, World! This is a test body."
        result = limiter.limit_stream(body)
        assert result.is_ok
        assert result.status == LimitStatus.OK
        assert result.total_read_bytes == len(body)
        assert result.body == body
        assert result.limit_bytes == 1024

    def test_body_exactly_at_limit_bytes_source(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=100))
        body = b"A" * 100
        result = limiter.limit_stream(body)
        assert result.is_ok
        assert result.status == LimitStatus.OK
        assert result.total_read_bytes == 100
        assert result.body == body
        assert len(result.body) == 100

    def test_body_within_limit_stream_source(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=1024, chunk_size=64))
        body = b"B" * 512
        stream = io.BytesIO(body)
        result = limiter.limit_stream(stream)
        assert result.is_ok
        assert result.total_read_bytes == 512
        assert result.body == body

    def test_body_exactly_at_limit_stream_source(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=256, chunk_size=64))
        body = b"C" * 256
        stream = io.BytesIO(body)
        result = limiter.limit_stream(stream)
        assert result.is_ok
        assert result.total_read_bytes == 256
        assert result.body == body

    def test_body_within_limit_chunked_list_source(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=1024, chunk_size=100))
        chunks = [b"chunk1 ", b"chunk2 ", b"chunk3"]
        result = limiter.limit_stream(chunks)
        assert result.is_ok
        expected = b"chunk1 chunk2 chunk3"
        assert result.total_read_bytes == len(expected)
        assert result.body == expected

    def test_body_at_limit_with_content_length_header(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=500))
        body = b"D" * 500
        result = limiter.limit_stream(body, expected_content_length=500)
        assert result.is_ok
        assert result.total_read_bytes == 500
        assert result.body == body

    def test_process_request_within_limit(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=1024))

        def handler(request: Request, body: bytes) -> Response:
            return Response(
                status_code=200,
                body={"received_len": len(body), "data": body.decode("utf-8")},
            )

        body_data = b"Valid body content"
        request = Request(
            method="POST",
            path="/api/data",
            body_stream=body_data,
        )
        response = limiter.process_request(request, handler)
        assert response.status_code == 200
        assert response.body["received_len"] == len(body_data)
        assert response.body["data"] == body_data.decode("utf-8")

    def test_safe_process_within_limit(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=1024))

        def handler(request: Request, body: bytes) -> Response:
            return Response(status_code=201, body={"len": len(body)})

        body_data = b"Created resource"
        request = Request(
            method="POST",
            path="/api/resource",
            body_stream=body_data,
        )
        response, result = limiter.safe_process(request, handler)
        assert response.status_code == 201
        assert result.is_ok
        assert result.total_read_bytes == len(body_data)


# ============================================================
# 边界条件测试
# ============================================================


class TestBoundaryConditions:
    def test_empty_body_bytes_source(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=1024))
        result = limiter.limit_stream(b"")
        assert result.is_ok
        assert result.total_read_bytes == 0
        assert result.body == b""

    def test_empty_body_stream_source(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=1024))
        result = limiter.limit_stream(io.BytesIO(b""))
        assert result.is_ok
        assert result.total_read_bytes == 0
        assert result.body == b""

    def test_none_body_source(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=1024))
        result = limiter.limit_stream(None)
        assert result.is_ok
        assert result.total_read_bytes == 0
        assert result.body == b""

    def test_zero_limit_empty_body_allowed(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=0))
        result = limiter.limit_stream(b"")
        assert result.is_ok
        assert result.total_read_bytes == 0
        assert result.body == b""

    def test_zero_limit_any_body_rejected(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=0))
        with pytest.raises(PayloadTooLargeError) as exc_info:
            limiter.limit_stream(b"x")
        assert exc_info.value.limit_bytes == 0
        assert exc_info.value.received_bytes >= 1

    def test_chunk_size_aligned_with_threshold(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=512, chunk_size=64))
        body = b"E" * 512
        stream = io.BytesIO(body)
        result = limiter.limit_stream(stream)
        assert result.is_ok
        assert result.total_read_bytes == 512

    def test_chunk_size_not_aligned_body_exactly_at_limit(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=100, chunk_size=30))
        body = b"F" * 100
        stream = io.BytesIO(body)
        result = limiter.limit_stream(stream)
        assert result.is_ok
        assert result.total_read_bytes == 100
        assert result.body == body

    def test_chunk_size_not_aligned_just_below_limit(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=100, chunk_size=30))
        body = b"G" * 99
        stream = io.BytesIO(body)
        result = limiter.limit_stream(stream)
        assert result.is_ok
        assert result.total_read_bytes == 99

    def test_minimal_threshold_one_byte(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=1))
        result = limiter.limit_stream(b"X")
        assert result.is_ok
        assert result.total_read_bytes == 1
        assert result.body == b"X"

    def test_content_length_header_within_limit(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=1000))
        body = b"H" * 500
        result = limiter.limit_stream(body, expected_content_length=500)
        assert result.is_ok
        assert result.total_read_bytes == 500

    def test_content_length_zero_with_empty_body(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=1000))
        result = limiter.limit_stream(b"", expected_content_length=0)
        assert result.is_ok
        assert result.total_read_bytes == 0

    def test_single_byte_larger_than_chunk(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=1024, chunk_size=1))
        body = b"test"
        result = limiter.limit_stream(body)
        assert result.is_ok
        assert result.total_read_bytes == 4
        assert result.body == body


# ============================================================
# 超限检测测试
# ============================================================


class TestPayloadTooLargeDetection:
    def test_body_exceeds_limit_by_one_byte(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=100))
        body = b"I" * 101
        with pytest.raises(PayloadTooLargeError) as exc_info:
            limiter.limit_stream(body)
        assert exc_info.value.limit_bytes == 100
        assert exc_info.value.received_bytes == 101

    def test_body_exceeds_limit_stream_source(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=64, chunk_size=16))
        body = b"J" * 200
        stream = io.BytesIO(body)
        with pytest.raises(PayloadTooLargeError) as exc_info:
            limiter.limit_stream(stream)
        assert exc_info.value.limit_bytes == 64
        assert exc_info.value.received_bytes > 64

    def test_body_exceeds_limit_during_chunked_read(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=100, chunk_size=30))
        chunks = []
        for i in range(5):
            chunks.append(b"K" * 30)
        body = b"".join(chunks)
        stream = io.BytesIO(body)
        with pytest.raises(PayloadTooLargeError):
            limiter.limit_stream(stream)

    def test_content_length_header_exceeds_limit_short_circuit(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=100))
        body = b"L" * 50
        result = None
        with pytest.raises(PayloadTooLargeError) as exc_info:
            limiter.limit_stream(body, expected_content_length=200)
        assert exc_info.value.limit_bytes == 100

    def test_process_request_returns_413_on_overflow(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=10))
        call_count = [0]

        def handler(request: Request, body: bytes) -> Response:
            call_count[0] += 1
            return Response(status_code=200, body="should not reach here")

        request = Request(
            method="POST",
            path="/api/overflow",
            body_stream=b"M" * 100,
        )
        response = limiter.process_request(request, handler)
        assert response.status_code == 413
        assert call_count[0] == 0

    def test_safe_process_returns_413_and_result(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=10))
        call_count = [0]

        def handler(request: Request, body: bytes) -> Response:
            call_count[0] += 1
            return Response(status_code=200, body="should not reach here")

        request = Request(
            method="POST",
            path="/api/overflow2",
            body_stream=b"N" * 50,
        )
        response, result = limiter.safe_process(request, handler)
        assert response.status_code == 413
        assert result.is_too_large
        assert call_count[0] == 0

    def test_body_is_none_on_too_large_result(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=50))
        response, result = limiter.safe_process(
            Request(method="POST", path="/x", body_stream=b"O" * 200),
            lambda req, b: Response(status_code=200),
        )
        assert result.body is None
        assert result.is_too_large

    def test_custom_error_status_code(self):
        limiter = BodySizeLimiter(
            LimitConfig(
                max_body_bytes=10,
                error_status_code=431,
                error_message="Too Big!",
            )
        )
        request = Request(
            method="POST",
            path="/api/custom",
            body_stream=b"P" * 50,
        )
        response = limiter.process_request(
            request,
            lambda req, b: Response(status_code=200),
        )
        assert response.status_code == 431


# ============================================================
# 部分读取与中断安全兜底测试
# ============================================================


class TestIncompleteReadSafety:
    def test_content_length_more_than_actual_read(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=1000))
        body = b"Q" * 500
        with pytest.raises(IncompleteReadError) as exc_info:
            limiter.limit_stream(body, expected_content_length=800)
        assert exc_info.value.received_bytes == 500
        assert exc_info.value.expected_bytes == 800

    def test_incomplete_read_result_status(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=1000))
        body = b"R" * 300
        response, result = limiter.safe_process(
            Request(
                method="POST",
                path="/api/incomplete",
                body_stream=body,
                expected_content_length=600,
            ),
            lambda req, b: Response(status_code=200),
        )
        assert result.is_incomplete
        assert result.body is None
        assert response.status_code == 400

    def test_incomplete_read_handler_not_called(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=1000))
        call_count = [0]

        def handler(request: Request, body: bytes) -> Response:
            call_count[0] += 1
            return Response(status_code=200)

        response, result = limiter.safe_process(
            Request(
                method="POST",
                path="/api/handler",
                body_stream=b"S" * 100,
                expected_content_length=500,
            ),
            handler,
        )
        assert call_count[0] == 0
        assert result.is_incomplete

    def test_incomplete_read_within_size_limit_but_truncated(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=10000, chunk_size=100))
        with pytest.raises(IncompleteReadError):
            limiter.limit_stream(
                b"T" * 5000,
                expected_content_length=8000,
            )

    def test_connection_interrupt_stream_raises_incomplete(self):
        class InterruptingStream:
            def __init__(self, fail_after_chunks: int) -> None:
                self._chunks_read = 0
                self._fail_after = fail_after_chunks

            def read(self, size: int) -> bytes:
                self._chunks_read += 1
                if self._chunks_read > self._fail_after:
                    raise ConnectionError("Connection reset by peer")
                return b"U" * size

        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=10000, chunk_size=100))
        with pytest.raises(IncompleteReadError):
            limiter.limit_stream(InterruptingStream(fail_after_chunks=3))

    def test_interrupted_stream_handler_not_called(self):
        class FailingStream:
            def read(self, size: int) -> bytes:
                raise OSError("Broken pipe")

        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=1000))
        call_count = [0]

        def handler(request: Request, body: bytes) -> Response:
            call_count[0] += 1
            return Response(status_code=200)

        response, result = limiter.safe_process(
            Request(method="POST", path="/api/fail", body_stream=FailingStream()),
            handler,
        )
        assert call_count[0] == 0
        assert result.is_incomplete

    def test_incomplete_read_body_discarded(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=1000))
        body = b"sensitive-data-should-be-discarded" * 10
        response, result = limiter.safe_process(
            Request(
                method="POST",
                path="/api/sensitive",
                body_stream=body,
                expected_content_length=len(body) + 100,
            ),
            lambda req, b: Response(status_code=200),
        )
        assert result.body is None
        assert response.status_code == 400


# ============================================================
# 多次请求统计与连续处理测试
# ============================================================


class TestMultipleRequestsSequential:
    def test_stats_tracking_multiple_requests(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=100))

        limiter.limit_stream(b"a" * 50)
        limiter.limit_stream(b"b" * 100)
        try:
            limiter.limit_stream(b"c" * 101)
        except PayloadTooLargeError:
            pass
        try:
            limiter.limit_stream(b"d" * 30, expected_content_length=100)
        except IncompleteReadError:
            pass

        stats = limiter.stats
        assert stats.total_requests == 4
        assert stats.accepted_requests == 2
        assert stats.rejected_too_large == 1
        assert stats.rejected_incomplete == 1
        assert stats.max_observed_bytes == 101

    def test_consecutive_overflow_requests_handled_cleanly(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=50))
        results: list[tuple[int, LimitStatus]] = []

        for i in range(10):
            body = b"X" * (100 + i)
            response, result = limiter.safe_process(
                Request(method="POST", path=f"/api/{i}", body_stream=body),
                lambda req, b: Response(status_code=200),
            )
            results.append((response.status_code, result.status))

        for status_code, status in results:
            assert status_code == 413
            assert status == LimitStatus.TOO_LARGE

        assert limiter.stats.rejected_too_large == 10

    def test_mixed_requests_alternating_accept_reject(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=32))
        responses: list[tuple[int, int]] = []

        pattern = [10, 100, 20, 200, 32, 33, 0, 500]

        for size in pattern:
            body = b"Y" * size
            response, result = limiter.safe_process(
                Request(method="POST", path="/api/mix", body_stream=body),
                lambda req, b: Response(status_code=200, body={"len": len(b)}),
            )
            responses.append((response.status_code, result.total_read_bytes))

        assert responses[0] == (200, 10)
        assert responses[1][0] == 413
        assert responses[2] == (200, 20)
        assert responses[3][0] == 413
        assert responses[4] == (200, 32)
        assert responses[5][0] == 413
        assert responses[6] == (200, 0)
        assert responses[7][0] == 413

        stats = limiter.stats
        assert stats.accepted_requests == 4
        assert stats.rejected_too_large == 4

    def test_reset_stats(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=100))

        limiter.limit_stream(b"z" * 50)
        try:
            limiter.limit_stream(b"z" * 200)
        except PayloadTooLargeError:
            pass

        assert limiter.stats.total_requests == 2
        limiter.reset_stats()
        assert limiter.stats.total_requests == 0
        assert limiter.stats.accepted_requests == 0
        assert limiter.stats.rejected_too_large == 0
        assert limiter.stats.rejected_incomplete == 0
        assert limiter.stats.total_bytes_read == 0

    def test_each_request_isolated_state(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=100))
        first_body = b"A" * 60
        first_result = limiter.limit_stream(first_body)
        assert first_result.body == first_body

        second_body = b"B" * 60
        second_result = limiter.limit_stream(second_body)
        assert second_result.body == second_body
        assert b"A" not in second_result.body


# ============================================================
# 流式阈值检测点测试
# ============================================================


class TestStreamingThresholdCheckpoints:
    def test_threshold_triggered_mid_chunk_exact(self):
        class ChunkControlledStream:
            def __init__(self, chunks: list[bytes]) -> None:
                self._chunks = list(chunks)
                self._index = 0

            def read(self, size: int) -> bytes:
                if self._index >= len(self._chunks):
                    return b""
                chunk = self._chunks[self._index]
                self._index += 1
                return chunk

        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=100, chunk_size=1000))

        chunks = [b"A" * 40, b"B" * 30, b"C" * 35, b"D" * 50]
        stream = ChunkControlledStream(chunks)

        with pytest.raises(PayloadTooLargeError) as exc_info:
            limiter.limit_stream(stream)

        assert exc_info.value.received_bytes == 105
        assert exc_info.value.limit_bytes == 100

    def test_stream_stops_reading_after_threshold(self):
        read_count = [0]

        class CountingStream:
            def __init__(self, total_chunks: int, chunk_size: int) -> None:
                self._chunks_left = total_chunks
                self._chunk_size = chunk_size

            def read(self, size: int) -> bytes:
                read_count[0] += 1
                if self._chunks_left <= 0:
                    return b""
                self._chunks_left -= 1
                return b"Z" * min(self._chunk_size, size)

        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=100, chunk_size=30))
        stream = CountingStream(total_chunks=100, chunk_size=30)

        try:
            limiter.limit_stream(stream)
        except PayloadTooLargeError:
            pass

        assert read_count[0] <= 5

    def test_exact_boundary_multiple_chunks(self):
        chunks = [b"1" * 25, b"2" * 25, b"3" * 25, b"4" * 25]
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=100, chunk_size=1000))
        result = limiter.limit_stream(chunks)
        assert result.is_ok
        assert result.total_read_bytes == 100
        assert result.body == b"1" * 25 + b"2" * 25 + b"3" * 25 + b"4" * 25

    def test_one_past_boundary_multiple_chunks(self):
        chunks = [b"1" * 25, b"2" * 25, b"3" * 25, b"4" * 26]
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=100, chunk_size=1000))
        with pytest.raises(PayloadTooLargeError):
            limiter.limit_stream(chunks)


# ============================================================
# 异常对象属性测试
# ============================================================


class TestExceptionAttributes:
    def test_payload_too_large_attributes(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=50))
        try:
            limiter.limit_stream(b"a" * 75)
            assert False, "Expected PayloadTooLargeError"
        except PayloadTooLargeError as exc:
            assert exc.limit_bytes == 50
            assert exc.received_bytes == 75
            assert "75" in str(exc)
            assert "50" in str(exc)

    def test_incomplete_read_with_expected_attributes(self):
        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=1000))
        try:
            limiter.limit_stream(b"b" * 100, expected_content_length=500)
            assert False, "Expected IncompleteReadError"
        except IncompleteReadError as exc:
            assert exc.received_bytes == 100
            assert exc.expected_bytes == 500
            assert "100" in str(exc)
            assert "500" in str(exc)

    def test_incomplete_read_without_expected_attributes(self):
        class BadStream:
            def read(self, size):
                raise RuntimeError("stream failed")

        limiter = BodySizeLimiter(LimitConfig(max_body_bytes=1000))
        try:
            limiter.limit_stream(BadStream())
            assert False, "Expected IncompleteReadError"
        except IncompleteReadError as exc:
            assert exc.received_bytes == 0
            assert exc.expected_bytes is None
